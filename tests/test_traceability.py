from generate_repo_overview.collector.traceability import (
    _SUPPORTED_METRICS_SCHEMA_VERSION,
    _parse_metrics_by_type,
)

# Mirrors the real structure from eclipse-score.github.io/baselibs/main/metrics.json
_BASELIBS_PAYLOAD = {
    "schema_version": "2",
    "generated_by": "sphinx_build",
    "overall_metrics": {
        "total": 150,
        "with_code_link": 0,
        "with_test_link": 0,
        "fully_linked": 0,
        "with_code_link_pct": 0.0,
        "with_test_link_pct": 0.0,
        "fully_linked_pct": 0.0,
    },
    "metrics_by_type": {
        "aou_req": {
            "total": 32,
            "with_code_link": 0,
            "with_test_link": 0,
            "fully_linked": 0,
            "with_code_link_pct": 0.0,
            "with_test_link_pct": 0.0,
            "fully_linked_pct": 0.0,
        },
        "comp_req": {
            "total": 112,
            "with_code_link": 0,
            "with_test_link": 0,
            "fully_linked": 0,
            "with_code_link_pct": 0.0,
            "with_test_link_pct": 0.0,
            "fully_linked_pct": 0.0,
        },
        "tool_req": {
            "total": 6,
            "with_code_link": 0,
            "with_test_link": 0,
            "fully_linked": 0,
            "with_code_link_pct": 0.0,
            "with_test_link_pct": 0.0,
            "fully_linked_pct": 0.0,
        },
    },
    "tests": {
        "total": 0,
        "linked_to_requirements": 0,
        "linked_to_requirements_pct": 100.0,
        "broken_references": [],
    },
}


def test_parse_baselibs_payload() -> None:
    result = _parse_metrics_by_type(_BASELIBS_PAYLOAD)
    assert len(result) == 3

    by_name = {m.type_name: m for m in result}
    assert set(by_name) == {"aou_req", "comp_req", "tool_req"}

    aou = by_name["aou_req"]
    assert aou.req_total == 32
    assert aou.req_with_code_link == 0
    assert aou.req_with_test_link == 0
    assert aou.req_fully_linked == 0
    assert aou.tests_total == 0
    assert aou.tests_linked == 0

    comp = by_name["comp_req"]
    assert comp.req_total == 112

    tool = by_name["tool_req"]
    assert tool.req_total == 6


def test_top_level_tests_shared_across_types() -> None:
    payload = {
        "schema_version": _SUPPORTED_METRICS_SCHEMA_VERSION,
        "metrics_by_type": {
            "aou_req": {"total": 10, "with_code_link": 5, "with_test_link": 3, "fully_linked": 2},
            "comp_req": {"total": 20, "with_code_link": 8, "with_test_link": 6, "fully_linked": 4},
        },
        "tests": {"total": 15, "linked_to_requirements": 12},
    }
    result = _parse_metrics_by_type(payload)
    assert len(result) == 2
    for m in result:
        assert m.tests_total == 15
        assert m.tests_linked == 12


def test_missing_schema_version_returns_empty() -> None:
    payload = dict(_BASELIBS_PAYLOAD)
    del payload["schema_version"]
    assert _parse_metrics_by_type(payload) == ()


def test_wrong_schema_version_returns_empty() -> None:
    assert _parse_metrics_by_type({**_BASELIBS_PAYLOAD, "schema_version": "1"}) == ()
    assert _parse_metrics_by_type({**_BASELIBS_PAYLOAD, "schema_version": 2}) == ()
    assert _parse_metrics_by_type({**_BASELIBS_PAYLOAD, "schema_version": "99"}) == ()


def test_non_dict_input_returns_empty() -> None:
    assert _parse_metrics_by_type([]) == ()
    assert _parse_metrics_by_type(None) == ()
    assert _parse_metrics_by_type("string") == ()


def test_missing_metrics_by_type_returns_empty() -> None:
    payload = {k: v for k, v in _BASELIBS_PAYLOAD.items() if k != "metrics_by_type"}
    assert _parse_metrics_by_type(payload) == ()


def test_missing_top_level_tests_defaults_to_zero() -> None:
    payload = {k: v for k, v in _BASELIBS_PAYLOAD.items() if k != "tests"}
    result = _parse_metrics_by_type(payload)
    assert len(result) == 3
    for m in result:
        assert m.tests_total == 0
        assert m.tests_linked == 0


def test_missing_nested_req_fields_default_to_zero() -> None:
    payload = {
        "schema_version": _SUPPORTED_METRICS_SCHEMA_VERSION,
        "metrics_by_type": {"comp_req": {}},
        "tests": {},
    }
    result = _parse_metrics_by_type(payload)
    assert len(result) == 1
    m = result[0]
    assert m.req_total == 0
    assert m.req_with_code_link == 0
    assert m.tests_total == 0
