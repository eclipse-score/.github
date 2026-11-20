"""Parse ``bazel_dep`` declarations and their overrides from Bazel module files."""

from __future__ import annotations

import posixpath
import re
from typing import TYPE_CHECKING

from generate_repo_overview.models import DependencyDeclaration, DependencyOverride

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

ROOT_MODULE_PATH = "MODULE.bazel"

_COMMENT_OR_STRING = re.compile(
    r"""(?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|#[^\n]*""",
    re.DOTALL,
)
_CALL = re.compile(
    r"\b(?P<function>bazel_dep|git_override|archive_override|local_path_override"
    r"|single_version_override|include)\s*\((?P<body>[^()]*)\)",
    re.DOTALL,
)
_ARGUMENT = re.compile(r'\b(?P<key>\w+)\s*=\s*"(?P<value>[^"]*)"')
_POSITIONAL_STRING = re.compile(r'^\s*"(?P<value>[^"]*)"')
_OVERRIDE_KINDS = {
    "git_override": DependencyOverride.GIT,
    "archive_override": DependencyOverride.ARCHIVE,
    "local_path_override": DependencyOverride.LOCAL_PATH,
    "single_version_override": DependencyOverride.SINGLE_VERSION,
}


def read_module_files(read_text: Callable[[str], str | None]) -> dict[str, str]:
    """Read ``MODULE.bazel`` and every module file it includes, keyed by path."""
    pending = [ROOT_MODULE_PATH]
    contents: dict[str, str] = {}
    while pending:
        path = pending.pop()
        if path in contents:
            continue
        content = read_text(path)
        if content is None:
            continue
        contents[path] = content
        for match in _calls(content):
            if match.group("function") != "include":
                continue
            label = _POSITIONAL_STRING.match(match.group("body"))
            included = (
                _resolve_include_label(label.group("value"), current_file=path)
                if label
                else None
            )
            if included is not None and included not in contents:
                pending.append(included)
    return contents


def parse_dependencies(contents: Iterable[str]) -> tuple[DependencyDeclaration, ...]:
    """Combine ``bazel_dep`` declarations with the overrides Bazel applies to them.

    Overrides can live in a different included file than their ``bazel_dep``,
    so all files of one module are parsed together.
    """
    versions: dict[str, str | None] = {}
    overrides: dict[str, dict[str, str]] = {}
    for content in contents:
        for match in _calls(content):
            function = match.group("function")
            arguments = {
                m.group("key"): m.group("value").strip()
                for m in _ARGUMENT.finditer(match.group("body"))
            }
            if function == "bazel_dep" and arguments.get("name"):
                versions[arguments["name"]] = arguments.get("version") or None
            elif function in _OVERRIDE_KINDS and arguments.get("module_name"):
                overrides[arguments["module_name"]] = {
                    **arguments,
                    "kind": function,
                }
    return tuple(
        _declaration(module, versions[module], overrides.get(module))
        for module in sorted(versions)
    )


def _declaration(
    module: str,
    version: str | None,
    override: dict[str, str] | None,
) -> DependencyDeclaration:
    if override is None:
        return DependencyDeclaration(module=module, version=version)
    kind = _OVERRIDE_KINDS[override["kind"]]
    if kind is DependencyOverride.SINGLE_VERSION:
        # Bazel resolves the module to this version regardless of the declaration.
        return DependencyDeclaration(
            module=module,
            version=override.get("version") or version,
            override=kind,
        )
    if kind is not DependencyOverride.GIT:
        return DependencyDeclaration(module=module, version=version, override=kind)
    return DependencyDeclaration(
        module=module,
        version=version,
        override=kind,
        remote=override.get("remote") or None,
        revision=(
            override.get("commit") or override.get("tag") or override.get("branch")
        )
        or None,
    )


def _calls(content: str) -> Iterable[re.Match[str]]:
    # Strip comments while keeping strings, so commented-out calls are ignored.
    code = _COMMENT_OR_STRING.sub(lambda m: m.group("string") or "", content)
    return _CALL.finditer(code)


def _resolve_include_label(label: str, *, current_file: str) -> str | None:
    if label.startswith("@"):
        return None
    if label.startswith("//"):
        package, separator, target = label.removeprefix("//").partition(":")
        if not separator or not target:
            return None
        path = posixpath.join(package, target)
    else:
        path = posixpath.join(posixpath.dirname(current_file), label.lstrip(":"))
    path = posixpath.normpath(path)
    if path.startswith("../") or path == ".." or posixpath.isabs(path):
        return None
    return path
