"""Parse declarations and overrides from Bazel module files."""

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
    from collections.abc import Callable, Iterable, Mapping

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


def get_bazel_module_name(text: str | None) -> str | None:
    for function, call, constants in _calls(text or ""):
        if function == "module":
            for keyword in call.keywords:
                if keyword.arg == "name":
                    name = _string_value(keyword.value, constants)
                    return (name or "").strip() or None
    return None


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
        for function, call, constants in _calls(content):
            if function != "include" or not call.args:
                continue
            label = _string_value(call.args[0], constants)
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
    overrides: dict[
        str,
        tuple[DependencyOverride, dict[str, str | None], tuple[tuple[str, str], ...]],
    ] = {}
    for content in contents:
        for function, call, constants in _calls(content):
            if function != "bazel_dep" and function not in _OVERRIDE_KINDS:
                continue
            arguments = {
                keyword.arg: value.strip()
                if (value := _string_value(keyword.value, constants)) is not None
                else None
                for keyword in call.keywords
                if keyword.arg is not None
            }
            if function == "bazel_dep":
                if name := arguments.get("name"):
                    versions[name] = arguments.get("version") or None
            elif module := arguments.get("module_name"):
                kind = _OVERRIDE_KINDS[function]
                source = (
                    _override_source(call, constants)
                    if kind
                    in (DependencyOverride.ARCHIVE, DependencyOverride.LOCAL_PATH)
                    else ()
                )
                overrides[module] = (kind, arguments, source)
    return tuple(
        _declaration(module, versions[module], overrides.get(module))
        for module in sorted(versions)
    )


def _declaration(
    module: str,
    version: str | None,
    override: tuple[
        DependencyOverride, dict[str, str | None], tuple[tuple[str, str], ...]
    ]
    | None,
) -> DependencyDeclaration:
    if override is None:
        return DependencyDeclaration(module=module, version=version)
    kind, arguments, source = override
    if kind is DependencyOverride.SINGLE_VERSION:
        # An empty version leaves Bazel's selection in place. An expression
        # we cannot interpret could replace it with any version.
        selected_version = arguments.get("version", "")
        # An omitted or empty registry uses the default. An expression we
        # cannot interpret may select a different registry, so retain that fact.
        registry = arguments.get("registry", "")
        return DependencyDeclaration(
            module=module,
            version=version if selected_version == "" else selected_version,
            override=kind,
            registry_override=None if registry == "" else (registry or ""),
        )
    if kind is not DependencyOverride.GIT:
        return DependencyDeclaration(
            module=module, version=version, override=kind, override_source=source
        )
    revision, pin_kind = next(
        ((value, pin) for key, pin in _GIT_PINS if (value := arguments.get(key))),
        (None, DependencyPinKind.COMMIT),
    )
    return DependencyDeclaration(
        module, version, kind, arguments.get("remote") or None, revision, pin_kind
    )


def _calls(content: str) -> Iterable[tuple[str, ast.Call, Mapping[str, ast.expr]]]:
    # MODULE.bazel uses Python-compatible syntax for top-level calls with literal
    # arguments. Reading the syntax tree never evaluates the build file.
    try:
        body = ast.parse(content).body
    except (SyntaxError, ValueError, RecursionError):
        return
    constants: dict[str, ast.expr] = {}
    for statement in body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = _constant(statement.value, constants)
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            if isinstance(call.func, ast.Name):
                yield call.func.id, call, constants


def _constant(value: ast.expr, constants: Mapping[str, ast.expr]) -> ast.expr:
    if isinstance(value, ast.Name):
        return constants.get(value.id, value)
    if isinstance(value, ast.List):
        return ast.List(
            elts=[_constant(item, constants) for item in value.elts], ctx=value.ctx
        )
    return value


def _string_value(value: ast.expr, constants: Mapping[str, ast.expr]) -> str | None:
    value = _constant(value, constants)
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def _override_source(
    call: ast.Call, constants: Mapping[str, ast.expr]
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (keyword.arg, ast.unparse(_constant(keyword.value, constants)))
            for keyword in call.keywords
            if keyword.arg is not None and keyword.arg != "module_name"
        )
    )


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
