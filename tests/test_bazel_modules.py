from generate_repo_overview.collector.bazel_modules import (
    parse_dependencies,
    read_module_files,
)
from generate_repo_overview.models import (
    DependencyDeclaration,
    DependencyOverride,
    DependencyPinKind,
)


def test_parse_dependencies_applies_overrides_from_any_module_file() -> None:
    root = """
module(name = "consumer", version = "1.0.0")
bazel_dep(name = 'score_baselibs', version = '0.2.0')
bazel_dep(name = "score_logging", version = "0.0.0")
bazel_dep(name = "rules_python", version = "1.0.0")
bazel_dep(name = "some_lib", dev_dependency = True)
bazel_dep(name = "vendored", version = "2.0.0")
# bazel_dep(name = "commented_out", version = "9.9.9")
'''bazel_dep(name = "example_only", version = "9.9.9")'''
single_version_override(module_name = "rules_python", version = "1.2.0")
"""
    overrides = """
git_override(
    module_name = "score_logging",
    remote = "https://github.com/eclipse-score/logging.git",
    commit = "0123456789abcdef0123456789abcdef01234567",
)
archive_override(module_name = "vendored", urls = ["https://example.com/v.tgz"])
"""

    assert parse_dependencies([root, overrides]) == (
        DependencyDeclaration(
            "rules_python", "1.2.0", DependencyOverride.SINGLE_VERSION
        ),
        DependencyDeclaration("score_baselibs", "0.2.0"),
        DependencyDeclaration(
            "score_logging",
            "0.0.0",
            DependencyOverride.GIT,
            remote="https://github.com/eclipse-score/logging.git",
            revision="0123456789abcdef0123456789abcdef01234567",
            pin_kind=DependencyPinKind.COMMIT,
        ),
        DependencyDeclaration("some_lib"),
        DependencyDeclaration(
            "vendored",
            "2.0.0",
            DependencyOverride.ARCHIVE,
            override_source=(("urls", "['https://example.com/v.tgz']"),),
        ),
    )


def test_pinned_revision_reflects_declared_versions_and_overrides() -> None:
    [baselibs, logging, vendored] = parse_dependencies(
        [
            'bazel_dep(name = "baselibs", version = "0.2.0")\n'
            'bazel_dep(name = "logging", version = "0.0.0")\n'
            'bazel_dep(name = "vendored", version = "2.0.0")\n'
            'git_override(module_name = "logging", remote = "r", tag = "v1.0.0")\n'
            'local_path_override(module_name = "vendored", path = "third_party")\n'
        ]
    )

    assert baselibs.pinned_revision == "0.2.0"
    assert logging.pinned_revision == "v1.0.0"
    assert logging.pin_kind is DependencyPinKind.TAG
    assert logging.display_version == "v1.0.0"
    assert vendored.pinned_revision is None


def test_read_module_files_follows_includes_within_the_repository() -> None:
    files = {
        "MODULE.bazel": 'bazel_dep(name = "root")\n'
        'include("//bazel_common:deps.MODULE.bazel")\n'
        'include("//:../outside.MODULE.bazel")\n'
        'include("@other//:external.MODULE.bazel")\n',
        "bazel_common/deps.MODULE.bazel": 'bazel_dep(name = "tooling")\n'
        'include(":nested.MODULE.bazel")\n',
        "bazel_common/nested.MODULE.bazel": 'bazel_dep(name = "logging")\n',
        "../outside.MODULE.bazel": 'bazel_dep(name = "escaped")\n',
    }

    contents = read_module_files(files.get)

    assert set(contents) == {
        "MODULE.bazel",
        "bazel_common/deps.MODULE.bazel",
        "bazel_common/nested.MODULE.bazel",
    }
    assert [d.module for d in parse_dependencies(contents.values())] == [
        "logging",
        "root",
        "tooling",
    ]


def test_single_version_override_resolves_constants_and_marks_computed_pins_unknown() -> (
    None
):
    resolved, unchanged, unknown = parse_dependencies(
        [
            """
PIN = "2.0.0"
ALIAS = PIN
bazel_dep(name = "resolved", version = "1.0.0")
bazel_dep(name = "unknown", version = "1.0.0")
bazel_dep(name = "unchanged", version = "1.0.0")
single_version_override(module_name = "resolved", version = ALIAS)
single_version_override(module_name = "unknown", version = versions["current"])
single_version_override(module_name = "unchanged", patch_strip = 1)
"""
        ]
    )

    assert resolved.pinned_revision == "2.0.0"
    assert unknown.pinned_revision is None
    assert unknown.display_version == "unknown"
    assert unchanged.pinned_revision == "1.0.0"


def test_single_version_override_distinguishes_unknown_and_default_registries() -> None:
    default, explicit, unknown = parse_dependencies(
        [
            """
REGISTRY = "https://raw.githubusercontent.com/example/registry/main/"
bazel_dep(name = "default", version = "1.0.0")
bazel_dep(name = "explicit", version = "1.0.0")
bazel_dep(name = "unknown", version = "1.0.0")
single_version_override(module_name = "default", registry = "")
single_version_override(module_name = "explicit", registry = REGISTRY)
single_version_override(module_name = "unknown", registry = registries["current"])
"""
        ]
    )

    assert default.registry_override is None
    assert (
        explicit.registry_override
        == "https://raw.githubusercontent.com/example/registry/main/"
    )
    assert unknown.registry_override == ""
