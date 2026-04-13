from __future__ import annotations

import fnmatch
import re
from typing import Any, TypedDict


class DeepContentPayload(TypedDict):
    is_bazel_repo: bool
    bazel_version: str | None
    codeowners: tuple[str, ...]
    docs_as_code_version: str | None
    referenced_by_reference_integration: bool
    has_gitlint_config: bool
    has_pyproject_toml: bool
    has_pre_commit_config: bool
    has_lint_config: bool
    has_ci: bool
    uses_cicd_daily_workflow: bool
    has_coverage_config: bool


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
WORKFLOW_PATH_PREFIX = ".github/workflows/"
WORKFLOW_FILE_SUFFIXES = (".yml", ".yaml")
DAILY_WORKFLOW_REFERENCE = "cicd-workflows/.github/workflows/daily.yml@"
BAZEL_DEP_PATTERN_TEMPLATE = (
    r'\bbazel_dep\s*\(\s*name\s*=\s*"{module_name}"(?P<body>.*?)\)'
)
VERSION_PATTERN = re.compile(r'\bversion\s*=\s*"(?P<version>[^"]+)"')


def inspect_repository_content_slow(
    repository: Any,
    *,
    ref: str | None,
) -> DeepContentPayload:
    """Run slow deep content inspection using repository tree and file reads."""
    tree_paths = fetch_repository_tree_paths(repository, ref=ref)
    if not tree_paths:
        return default_content_signals()

    return {
        "is_bazel_repo": detect_is_bazel_repo(tree_paths),
        "bazel_version": detect_bazel_version(
            repository,
            tree_paths=tree_paths,
            ref=ref,
        ),
        "codeowners": detect_codeowners(
            repository,
            tree_paths=tree_paths,
            ref=ref,
        ),
        "docs_as_code_version": detect_dependency_version(
            repository,
            tree_paths=tree_paths,
            ref=ref,
            module_name="score_docs_as_code",
        ),
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
        "uses_cicd_daily_workflow": uses_cicd_daily_workflow(
            repository,
            tree_paths=tree_paths,
            ref=ref,
        ),
        "has_coverage_config": any(
            tree_contains_path(tree_paths, path) for path in COVERAGE_PATHS
        ),
    }


def default_content_signals() -> DeepContentPayload:
    return {
        "is_bazel_repo": False,
        "bazel_version": None,
        "codeowners": (),
        "docs_as_code_version": None,
        "referenced_by_reference_integration": False,
        "has_gitlint_config": False,
        "has_pyproject_toml": False,
        "has_pre_commit_config": False,
        "has_lint_config": False,
        "has_ci": False,
        "uses_cicd_daily_workflow": False,
        "has_coverage_config": False,
    }


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
    for candidate in BAZEL_VERSION_PATHS:
        if not tree_contains_path(tree_paths, candidate):
            continue
        content = fetch_text_file(repository, candidate, ref=ref)
        version = first_non_comment_line(content)
        if version:
            return version

    return None


def detect_is_bazel_repo(tree_paths: set[str]) -> bool:
    return any(
        tree_contains_path(tree_paths, candidate)
        for candidate in BAZEL_REPO_MARKER_PATHS
    )


def detect_dependency_version(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
    module_name: str,
) -> str | None:
    for candidate in MODULE_PATHS:
        if not tree_contains_path(tree_paths, candidate):
            continue
        content = fetch_text_file(repository, candidate, ref=ref)
        version = get_bazel_dep_version(content, module_name=module_name)
        if version:
            return version

    return None


def detect_codeowners(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> tuple[str, ...]:
    if not tree_contains_path(tree_paths, CODEOWNERS_PATH):
        return ()

    content = fetch_text_file(repository, CODEOWNERS_PATH, ref=ref)
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
        # Bare patterns can match either the basename or the full path, mirroring CODEOWNERS behavior.
        return fnmatch.fnmatch(
            normalized_target_path.rsplit("/", maxsplit=1)[-1],
            normalized_pattern,
        ) or fnmatch.fnmatch(normalized_target_path, normalized_pattern)

    return fnmatch.fnmatch(normalized_target_path, normalized_pattern)


def get_bazel_dep_version(text: str | None, *, module_name: str) -> str | None:
    if not text:
        return None

    pattern = re.compile(
        BAZEL_DEP_PATTERN_TEMPLATE.format(module_name=re.escape(module_name)),
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        return None

    version_match = VERSION_PATTERN.search(match.group("body"))
    if version_match is None:
        return None

    version = version_match.group("version").strip()
    return version or None


def uses_cicd_daily_workflow(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> bool:
    workflow_paths = sorted(
        path
        for path in tree_paths
        if path.startswith(WORKFLOW_PATH_PREFIX)
        and path.endswith(WORKFLOW_FILE_SUFFIXES)
    )
    for workflow_path in workflow_paths:
        content = fetch_text_file(repository, workflow_path, ref=ref)
        if content is None:
            continue
        if DAILY_WORKFLOW_REFERENCE in content:
            return True
    return False


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
