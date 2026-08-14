from __future__ import annotations

import fnmatch
import re
import subprocess
from typing import TYPE_CHECKING, Any, TypedDict

from generate_repo_overview.models import LockfileStatus, SphinxItem

from .git_checkout import list_repository_paths, read_repository_text
from .sphinx import parse_sphinx_directives

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from generate_repo_overview.models import WorkflowSignal


class DeepContentPayload(TypedDict):
    is_bazel_repo: bool
    has_bazel_module: bool
    bazel_module_name: str | None
    bazel_version: str | None
    codeowners: tuple[str, ...]
    referenced_by_reference_integration: bool
    has_gitlint_config: bool
    has_pyproject_toml: bool
    has_pre_commit_config: bool
    has_lint_config: bool
    has_ci: bool
    matched_workflow_signals: tuple[str, ...]
    has_coverage_config: bool
    top_languages: tuple[str, ...]
    bazel_deps: tuple[tuple[str, str], ...]
    bazel_lockfile_status: LockfileStatus
    bazel_lockfile_error_output: str | None
    docs_feature_paths: tuple[str, ...]
    repo_sphinx_features: tuple[SphinxItem, ...]
    repo_sphinx_modules: tuple[SphinxItem, ...]
    sphinx_project_name: str | None
    sphinx_project_prefix: str | None


GITLINT_PATHS = (".gitlint",)
PYPROJECT_PATHS = ("pyproject.toml",)
PRE_COMMIT_PATHS = (".pre-commit-config.yaml",)
LINT_CONFIG_PATHS = GITLINT_PATHS + PRE_COMMIT_PATHS
CI_PATHS = (".github/workflows",)
COVERAGE_PATHS = ("coverage.yml", "coverage.xml", "pytest.ini", ".coveragerc")
BAZEL_VERSION_PATHS = (".bazelversion",)
MODULE_PATHS = ("MODULE.bazel",)
BAZEL_REPO_MARKER_PATHS = (
    BAZEL_VERSION_PATHS
    + MODULE_PATHS
    + (
        "WORKSPACE",
        "WORKSPACE.bazel",
    )
)
CODEOWNERS_PATH = ".github/CODEOWNERS"
SINGLE_FEATURE_DOC_SECTIONS = (
    "architecture",
    "safety_analysis",
    "safety_planning",
    "security_analysis",
    "security_planning",
)
SPHINX_CONFIG_PATHS = ("docs/conf.py", "docs/sphinx/conf.py")
WORKFLOW_PATH_PREFIX = ".github/workflows/"
WORKFLOW_FILE_SUFFIXES = (".yml", ".yaml")
VERSION_PATTERN = re.compile(r'\bversion\s*=\s*"(?P<version>[^"]+)"')


BAZEL_LOCKFILE_TIMEOUT_SECONDS = 60


def detect_bazel_lockfile_ok(checkout_path: Path) -> tuple[LockfileStatus, str | None]:
    """Run `bazel mod deps --lockfile_mode=error` in the checkout.

    Returns (status, error_output):
      (OK,      None)    — lockfile exists and is up to date
      (ERROR,   stderr)  — lockfile check failed
      (MISSING, None)    — MODULE.bazel.lock does not exist
      (TIMEOUT, None)    — bazel timed out
      (UNKNOWN, None)    — bazel unavailable or MODULE.bazel missing
    """
    if not (checkout_path / "MODULE.bazel").exists():
        return LockfileStatus.UNKNOWN, None
    if not (checkout_path / "MODULE.bazel.lock").exists():
        return LockfileStatus.MISSING, None
    try:
        result = subprocess.run(
            ["bazel", "mod", "deps", "--lockfile_mode=error"],
            cwd=checkout_path,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=BAZEL_LOCKFILE_TIMEOUT_SECONDS,
        )
    except OSError:
        return LockfileStatus.UNKNOWN, None
    except subprocess.TimeoutExpired:
        return LockfileStatus.TIMEOUT, None
    if result.returncode != 0:
        return LockfileStatus.ERROR, result.stderr.strip() or None
    return LockfileStatus.OK, None


def inspect_repository_content_slow(
    repository: Any,
    *,
    ref: str | None,
    workflow_signals: tuple[WorkflowSignal, ...] = (),
) -> DeepContentPayload:
    tree_paths = fetch_repository_tree_paths(repository, ref=ref)
    if not tree_paths:
        return default_content_signals()
    return _inspect_repository_content(
        tree_paths,
        lambda path: fetch_text_file(repository, path, ref=ref),
        workflow_signals=workflow_signals,
        top_languages=detect_top_languages(repository, n=3),
    )


def inspect_repository_checkout(
    checkout_path: Path,
    *,
    workflow_signals: tuple[WorkflowSignal, ...] = (),
    top_languages: tuple[str, ...] = (),
) -> DeepContentPayload:
    tree_paths = list_repository_paths(checkout_path)
    if not tree_paths:
        raise RuntimeError(f"Could not inspect Git checkout {checkout_path}.")
    return _inspect_repository_content(
        tree_paths,
        lambda path: read_repository_text(checkout_path, path),
        workflow_signals=workflow_signals,
        top_languages=top_languages,
    )


def _inspect_repository_content(
    tree_paths: set[str],
    read_text: Callable[[str], str | None],
    *,
    workflow_signals: tuple[WorkflowSignal, ...],
    top_languages: tuple[str, ...],
) -> DeepContentPayload:
    module_content = (
        read_text(MODULE_PATHS[0])
        if tree_contains_path(tree_paths, MODULE_PATHS[0])
        else None
    )
    docs_feature_paths = detect_docs_feature_paths(tree_paths)
    repo_sphinx_features, repo_sphinx_modules = detect_repo_sphinx_items(
        tree_paths=tree_paths,
        read_text=read_text,
    )
    sphinx_project_name, sphinx_project_prefix = detect_sphinx_config_names(
        tree_paths=tree_paths,
        read_text=read_text,
    )
    return {
        "is_bazel_repo": detect_is_bazel_repo(tree_paths),
        "has_bazel_module": any(
            tree_contains_path(tree_paths, p) for p in MODULE_PATHS
        ),
        "bazel_module_name": get_bazel_module_name(module_content),
        "bazel_version": detect_bazel_version_from_reader(tree_paths, read_text),
        "codeowners": detect_codeowners_from_reader(tree_paths, read_text),
        "bazel_deps": get_all_bazel_dep_versions(module_content),
        "referenced_by_reference_integration": False,
        "has_gitlint_config": any(
            tree_contains_path(tree_paths, path) for path in GITLINT_PATHS
        ),
        "has_pyproject_toml": any(
            tree_contains_path(tree_paths, path) for path in PYPROJECT_PATHS
        ),
        "has_pre_commit_config": any(
            tree_contains_path(tree_paths, path) for path in PRE_COMMIT_PATHS
        ),
        "has_lint_config": any(
            tree_contains_path(tree_paths, path) for path in LINT_CONFIG_PATHS
        ),
        "has_ci": any(tree_contains_path(tree_paths, path) for path in CI_PATHS),
        "matched_workflow_signals": detect_matched_workflow_signals(
            tree_paths=tree_paths,
            read_text=read_text,
            workflow_signals=workflow_signals,
        ),
        "has_coverage_config": any(
            tree_contains_path(tree_paths, path) for path in COVERAGE_PATHS
        ),
        "top_languages": top_languages,
        "bazel_lockfile_status": LockfileStatus.UNKNOWN,
        "bazel_lockfile_error_output": None,
        "docs_feature_paths": docs_feature_paths,
        "repo_sphinx_features": repo_sphinx_features,
        "repo_sphinx_modules": repo_sphinx_modules,
        "sphinx_project_name": sphinx_project_name,
        "sphinx_project_prefix": sphinx_project_prefix,
    }


def default_content_signals() -> DeepContentPayload:
    return {
        "is_bazel_repo": False,
        "has_bazel_module": False,
        "bazel_module_name": None,
        "bazel_version": None,
        "codeowners": (),
        "bazel_deps": (),
        "referenced_by_reference_integration": False,
        "has_gitlint_config": False,
        "has_pyproject_toml": False,
        "has_pre_commit_config": False,
        "has_lint_config": False,
        "has_ci": False,
        "matched_workflow_signals": (),
        "has_coverage_config": False,
        "top_languages": (),
        "bazel_lockfile_status": LockfileStatus.UNKNOWN,
        "bazel_lockfile_error_output": None,
        "docs_feature_paths": (),
        "repo_sphinx_features": (),
        "repo_sphinx_modules": (),
        "sphinx_project_name": None,
        "sphinx_project_prefix": None,
    }


def detect_top_languages(repository: Any, *, n: int = 3) -> tuple[str, ...]:
    try:
        langs: object = repository.get_languages()
    except Exception:
        return ()
    if not isinstance(langs, dict):
        return ()
    sorted_langs = sorted(
        ((lang, count) for lang, count in langs.items() if isinstance(count, int)),
        key=lambda x: x[1],
        reverse=True,
    )
    return tuple(lang for lang, _ in sorted_langs[:n] if isinstance(lang, str))


def detect_docs_feature_paths(tree_paths: set[str]) -> tuple[str, ...]:
    prefix = "docs/features/"
    children = {
        remainder.split("/", maxsplit=1)[0]
        for path in tree_paths
        if path.startswith(prefix)
        and (remainder := path.removeprefix(prefix))
        and "/" in remainder
    }
    named_features = sorted(children - set(SINGLE_FEATURE_DOC_SECTIONS))
    if named_features:
        return tuple(f"docs/features/{name}" for name in named_features)
    if children & set(SINGLE_FEATURE_DOC_SECTIONS):
        return ("docs/features",)
    return ()


def detect_repo_sphinx_items(
    *,
    tree_paths: set[str],
    read_text: Callable[[str], str | None],
) -> tuple[tuple[SphinxItem, ...], tuple[SphinxItem, ...]]:
    candidate_paths = sorted(
        path
        for path in tree_paths
        if path == "docs/module/index.rst"
        or path == "docs/architecture/features.rst"
        or (
            path.startswith("docs/features/")
            and path.endswith(
                (
                    "/architecture/index.rst",
                    "/architecture/feature_architecture.rst",
                )
            )
        )
    )
    features: list[SphinxItem] = []
    modules: list[SphinxItem] = []
    for path in candidate_paths:
        text = read_text(path)
        features.extend(parse_sphinx_directives(text, "feat", path=path))
        modules.extend(parse_sphinx_directives(text, "mod", path=path))
    return (_dedupe_sphinx_items(features), _dedupe_sphinx_items(modules))


def detect_sphinx_config_names(
    *,
    tree_paths: set[str],
    read_text: Callable[[str], str | None],
) -> tuple[str | None, str | None]:
    for path in SPHINX_CONFIG_PATHS:
        if path not in tree_paths:
            continue
        return parse_sphinx_config_names(read_text(path))
    return (None, None)


def parse_sphinx_config_names(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return (None, None)

    def assignment(name: str) -> str | None:
        match = re.search(
            rf"^\s*{re.escape(name)}\s*=\s*([\"'])(?P<value>.*?)\1\s*$",
            text,
            re.MULTILINE,
        )
        return match.group("value").strip() or None if match else None

    return (assignment("project"), assignment("project_prefix"))


def _dedupe_sphinx_items(items: list[SphinxItem]) -> tuple[SphinxItem, ...]:
    return tuple(
        {(item.path, item.identifier or item.title): item for item in items}.values()
    )


def fetch_repository_tree_paths(repository: Any, *, ref: str | None) -> set[str]:
    if ref is None or not hasattr(repository, "get_git_tree"):
        return set()

    try:
        tree = repository.get_git_tree(ref, recursive=True)
    except Exception:
        return set()

    return {
        path
        for item in getattr(tree, "tree", [])
        if isinstance((path := getattr(item, "path", None)), str)
    }


def tree_contains_path(tree_paths: set[str], candidate: str) -> bool:
    if candidate in tree_paths:
        return True
    prefix = f"{candidate}/"
    return any(path.startswith(prefix) for path in tree_paths)


def detect_bazel_version(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> str | None:
    return detect_bazel_version_from_reader(
        tree_paths,
        lambda path: fetch_text_file(repository, path, ref=ref),
    )


def detect_bazel_version_from_reader(
    tree_paths: set[str],
    read_text: Callable[[str], str | None],
) -> str | None:
    for candidate in BAZEL_VERSION_PATHS:
        if not tree_contains_path(tree_paths, candidate):
            continue
        content = read_text(candidate)
        version = first_non_comment_line(content)
        if version:
            return version

    return None


def detect_is_bazel_repo(tree_paths: set[str]) -> bool:
    return any(
        tree_contains_path(tree_paths, candidate)
        for candidate in BAZEL_REPO_MARKER_PATHS
    )


def detect_all_bazel_deps(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> tuple[tuple[str, str], ...]:
    for candidate in MODULE_PATHS:
        if not tree_contains_path(tree_paths, candidate):
            continue
        content = fetch_text_file(repository, candidate, ref=ref)
        return get_all_bazel_dep_versions(content)
    return ()


def detect_codeowners(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> tuple[str, ...]:
    return detect_codeowners_from_reader(
        tree_paths,
        lambda path: fetch_text_file(repository, path, ref=ref),
    )


def detect_codeowners_from_reader(
    tree_paths: set[str],
    read_text: Callable[[str], str | None],
) -> tuple[str, ...]:
    if not tree_contains_path(tree_paths, CODEOWNERS_PATH):
        return ()

    content = read_text(CODEOWNERS_PATH)
    return get_codeowners_for_path(content, target_path=CODEOWNERS_PATH)


def get_codeowners_for_path(
    text: str | None,
    *,
    target_path: str,
) -> tuple[str, ...]:
    if not text:
        return ()

    owners: tuple[str, ...] = ()
    for raw_line in text.splitlines():
        line = raw_line.split("#", maxsplit=1)[0].strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        pattern, *candidate_owners = parts
        if codeowners_pattern_matches(pattern, target_path=target_path):
            owners = normalize_codeowners(candidate_owners)

    return owners


def codeowners_pattern_matches(pattern: str, *, target_path: str) -> bool:
    normalized_pattern = pattern.lstrip("/")
    normalized_target_path = target_path.lstrip("/")

    if pattern == "/":
        return True
    if normalized_pattern in {"*", "**", "/*"}:
        return True

    if normalized_pattern.endswith("/"):
        directory_pattern = normalized_pattern.rstrip("/")
        return (
            normalized_target_path == directory_pattern
            or normalized_target_path.startswith(f"{directory_pattern}/")
        )

    if "/" not in normalized_pattern:
        return fnmatch.fnmatch(
            normalized_target_path.rsplit("/", maxsplit=1)[-1],
            normalized_pattern,
        ) or fnmatch.fnmatch(normalized_target_path, normalized_pattern)

    return fnmatch.fnmatch(normalized_target_path, normalized_pattern)


def get_all_bazel_dep_versions(text: str | None) -> tuple[tuple[str, str], ...]:
    if not text:
        return ()

    name_pattern = re.compile(r'\bname\s*=\s*"(?P<name>[^"]+)"')
    bazel_dep_re = re.compile(
        r"\bbazel_dep\s*\((?P<body>.*?)\)",
        re.DOTALL,
    )
    result: list[tuple[str, str]] = []
    for match in bazel_dep_re.finditer(text):
        body = match.group("body")
        name_match = name_pattern.search(body)
        if name_match is None:
            continue
        name = name_match.group("name").strip()
        if not name:
            continue
        version_match = VERSION_PATTERN.search(body)
        version = (
            version_match.group("version").strip() if version_match else "unversioned"
        )
        result.append((name, version))

    return tuple(sorted(result, key=lambda x: x[0]))


def get_bazel_module_name(text: str | None) -> str | None:
    if not text:
        return None

    module_match = re.search(r"\bmodule\s*\((?P<body>.*?)\)", text, re.DOTALL)
    if module_match is None:
        return None
    name_match = re.search(
        r'\bname\s*=\s*"(?P<name>[^"]+)"',
        module_match.group("body"),
    )
    if name_match is None:
        return None
    return name_match.group("name").strip() or None


def detect_matched_workflow_signals(
    *,
    tree_paths: set[str],
    read_text: Callable[[str], str | None],
    workflow_signals: tuple[WorkflowSignal, ...] = (),
) -> tuple[str, ...]:
    """Return labels of workflow signals whose reference string appears in any workflow file."""
    if not workflow_signals:
        return ()

    workflow_contents: list[str] = []
    workflow_paths = sorted(
        path
        for path in tree_paths
        if path.startswith(WORKFLOW_PATH_PREFIX)
        and path.endswith(WORKFLOW_FILE_SUFFIXES)
    )
    for workflow_path in workflow_paths:
        content = read_text(workflow_path)
        if content is not None:
            workflow_contents.append(content)

    if not workflow_contents:
        return ()

    matched: list[str] = []
    for signal in workflow_signals:
        if any(signal.reference in content for content in workflow_contents):
            matched.append(signal.label)
    return tuple(matched)


def fetch_text_file(repository: Any, path: str, *, ref: str | None) -> str | None:
    if not hasattr(repository, "get_contents"):
        return None

    try:
        if ref is None:
            content = repository.get_contents(path)
        else:
            content = repository.get_contents(path, ref=ref)
    except Exception:
        return None

    raw_content = getattr(content, "decoded_content", None)
    if not isinstance(raw_content, (bytes, bytearray)):
        return None
    return raw_content.decode("utf-8", errors="replace")


def normalize_codeowners(values: list[str]) -> tuple[str, ...]:
    return dedupe_preserving_order(" ".join(values).replace(",", " ").split())


def dedupe_preserving_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return tuple(deduped)


def first_non_comment_line(text: str | None) -> str | None:
    if not text:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return None
