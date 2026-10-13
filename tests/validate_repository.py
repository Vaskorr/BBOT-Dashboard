#!/usr/bin/env python3
"""Fast structural validation that does not require Docker."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str):
    with (ROOT / path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_configuration_files_parse() -> None:
    for path in (
        "docker-compose.yml",
        "config/elasticsearch.yml",
        "config/kibana.yml",
        "bbot/bbot-elastic.yml",
    ):
        assert load_yaml(path), f"{path} is empty"

    for path in ("setup/index-template.json", "setup/ingest-pipeline.json"):
        with (ROOT / path).open(encoding="utf-8") as handle:
            assert json.load(handle), f"{path} is empty"


def test_compose_bootstrap_chain_and_security() -> None:
    compose = load_yaml("docker-compose.yml")
    services = compose["services"]
    assert set(services) == {
        "elasticsearch",
        "elasticsearch-setup",
        "kibana",
        "kibana-setup",
    }
    assert (
        services["kibana"]["depends_on"]["elasticsearch-setup"]["condition"]
        == "service_completed_successfully"
    )
    assert (
        services["kibana-setup"]["depends_on"]["kibana"]["condition"]
        == "service_healthy"
    )
    assert services["elasticsearch"]["environment"]["xpack.security.enabled"] == "true"

    kibana = load_yaml("config/kibana.yml")
    providers = kibana["xpack.security.authc.providers"]
    assert set(providers) == {"basic.basic1"}, "anonymous login must stay disabled"


def test_index_template_uses_normalizer() -> None:
    with (ROOT / "setup/index-template.json").open(encoding="utf-8") as handle:
        template = json.load(handle)
    assert template["index_patterns"] == ["bbot-events-*"]
    assert template["template"]["settings"]["index.default_pipeline"] == "bbot-normalize"
    properties = template["template"]["mappings"]["properties"]
    for field in (
        "scan",
        "scan_name",
        "event_url",
        "finding_name",
        "finding_severity",
        "severity_rank",
    ):
        assert field in properties


def test_saved_objects_are_complete_and_resolved() -> None:
    lines = (ROOT / "kibana/bbot-dashboards.ndjson").read_text(encoding="utf-8").splitlines()
    objects = [json.loads(line) for line in lines]
    details = objects.pop()
    assert details["type"] == "export-details"
    assert details["exportedCount"] == len(objects)

    by_key = {(obj["type"], obj["id"]): obj for obj in objects}
    for obj in objects:
        for reference in obj.get("references", []):
            key = (reference["type"], reference["id"])
            assert key in by_key, f"missing saved-object reference {key}"

    expected_dashboards = {
        "bbot-overview",
        "bbot-subdomains",
        "bbot-urls",
        "bbot-findings",
    }
    dashboards = {key[1] for key in by_key if key[0] == "dashboard"}
    assert dashboards == expected_dashboards

    for dashboard_id in expected_dashboards:
        dashboard = by_key[("dashboard", dashboard_id)]
        controls = json.loads(dashboard["attributes"]["controlGroupInput"]["panelsJSON"])
        scan = controls["scan-selector"]["explicitInput"]
        assert scan["fieldName"] == "scan"
        assert scan["singleSelect"] is True

        panels = json.loads(dashboard["attributes"]["panelsJSON"])
        navigation = next(
            panel for panel in panels if panel["panelRefName"] == "panel_0"
        )
        assert navigation["gridData"]["h"] >= 7, "navigation panel is too short"

    finding_search = by_key[("search", "bbot-finding-list")]
    assert finding_search["attributes"]["sort"][0] == ["severity_rank", "desc"]


if __name__ == "__main__":
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"OK: {len(tests)} repository validation checks passed")

