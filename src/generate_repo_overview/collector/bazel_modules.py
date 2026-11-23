"""Parse ``bazel_dep`` declarations and their overrides from Bazel module files."""

from __future__ import annotations

import ast
import posixpath
from typing import TYPE_CHECKING

from generate_repo_overview.models import (
    DependencyDeclaration,
    DependencyOverride,
    DependencyPinKind,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

ROOT_MODULE_PATH = "MODULE.bazel"

_OVERRIDE_KINDS = {
    "git_override": DependencyOverride.GIT,
    "archive_override": DependencyOverride.ARCHIVE,
    "local_path_override": DependencyOverride.LOCAL_PATH,
    "single_version_override": DependencyOverride.SINGLE_VERSION,
}
_GIT_PINS = (
    ("commit", DependencyPinKind.COMMIT),
    ("tag", DependencyPinKind.TAG),
    ("branch", DependencyPinKind.BRANCH),
)


def read_module_files(read_text: Callable[[str], str | None]) -> dict[str, str]:
    """Read ``MODULE.bazel`` and every module file it includes, keyed by path."""
    pending = [ROOT_MODULE_PATH]
    seen: set[str] = set()
    contents: dict[str, str] = {}
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        content = read_text(path)
        if content is None:
            continue
        contents[path] = content
        for function, call in _calls(content):
            if function != "include" or not call.args:
                continue
            label = _string_literal(call.args[0])
            included = (
                _resolve_include_label(label, current_file=path) if label else None
            )
            if included is not None:
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
        for function, call in _calls(content):
            if function != "bazel_dep" and function not in _OVERRIDE_KINDS:
                continue
            arguments = {
                keyword.arg: value.strip()
                for keyword in call.keywords
                if keyword.arg is not None
                and (value := _string_literal(keyword.value)) is not None
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
    revision, pin_kind = next(
        ((value, pin) for key, pin in _GIT_PINS if (value := override.get(key))),
        (None, DependencyPinKind.COMMIT),
    )
    return DependencyDeclaration(
        module, version, kind, override.get("remote") or None, revision, pin_kind
    )


def _calls(content: str) -> Iterable[tuple[str, ast.Call]]:
    # MODULE.bazel uses Python-compatible syntax for top-level calls with literal
    # arguments. Reading the syntax tree never evaluates the build file.
    try:
        body = ast.parse(content).body
    except (SyntaxError, ValueError, RecursionError):
        return
    for statement in body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            if isinstance(call.func, ast.Name):
                yield call.func.id, call


def _string_literal(value: ast.expr) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


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
