#!/usr/bin/env python3
"""Generate the version-pinned Kibana saved-object bundle.

The generated NDJSON is committed so deployment does not need Python.
Run this script after changing dashboard definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "kibana" / "bbot-dashboards.ndjson"
DATA_VIEW_ID = "bbot-events"
KIBANA_VERSION = "8.16.6"


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


objects: list[dict[str, Any]] = []


def add(obj_type: str, obj_id: str, attributes: dict[str, Any], references=None) -> str:
    objects.append(
        {
            "type": obj_type,
            "id": obj_id,
            "attributes": attributes,
            "references": references or [],
        }
    )
    return obj_id


def search_source(query: str = "", with_index: bool = True) -> str:
    source: dict[str, Any] = {
        "query": {"query": query, "language": "kuery"},
        "filter": [],
    }
    if with_index:
        source["indexRefName"] = "kibanaSavedObjectMeta.searchSourceJSON.index"
    return compact(source)


DATA_VIEW_REFERENCE = [
    {
        "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
        "type": "index-pattern",
        "id": DATA_VIEW_ID,
    }
]


add(
    "index-pattern",
    DATA_VIEW_ID,
    {
        "title": "bbot-events-*",
        "timeFieldName": "timestamp",
        "allowNoIndex": True,
        "fieldAttrs": compact(
            {
                "scan": {"customLabel": "Scan ID"},
                "scan_name": {"customLabel": "Scan name"},
                "data": {"customLabel": "Subdomain"},
                "dns_record_types": {"customLabel": "DNS records"},
                "resolved_hosts": {"customLabel": "Resolved hosts"},
                "scope_description": {"customLabel": "Scope"},
                "event_url": {"customLabel": "URL"},
                "url_status_code": {"customLabel": "HTTP status"},
                "http_title": {"customLabel": "Title"},
                "finding_severity": {"customLabel": "Severity"},
                "finding_name": {"customLabel": "Finding"},
                "finding_description": {"customLabel": "Description"},
                "finding_url": {"customLabel": "URL"},
                "finding_confidence": {"customLabel": "Confidence"},
            }
        ),
        "fieldFormatMap": compact(
            {
                "finding_severity": {
                    "id": "color",
                    "params": {
                        "fieldType": "string",
                        "colors": [
                            {"range": "-Infinity:Infinity", "regex": "^INFO$", "text": "#FFFFFF", "background": "#006BB4"},
                            {"range": "-Infinity:Infinity", "regex": "^LOW$", "text": "#000000", "background": "#54B399"},
                            {"range": "-Infinity:Infinity", "regex": "^MEDIUM$", "text": "#000000", "background": "#FEC514"},
                            {"range": "-Infinity:Infinity", "regex": "^HIGH$", "text": "#FFFFFF", "background": "#F04E98"},
                            {"range": "-Infinity:Infinity", "regex": "^CRITICAL$", "text": "#FFFFFF", "background": "#BD271E"},
                        ],
                    },
                }
            }
        ),
        "runtimeFieldMap": "{}",
        "sourceFilters": "[]",
        "name": "BBOT events",
    },
)


def metric(obj_id: str, title: str, query: str, field: str = "uuid") -> str:
    vis_state = {
        "title": title,
        "type": "metric",
        "aggs": [
            {
                "id": "1",
                "enabled": True,
                "type": "cardinality",
                "schema": "metric",
                "params": {"field": field, "customLabel": title},
            }
        ],
        "params": {
            "addLegend": False,
            "addTooltip": True,
            "type": "metric",
            "metric": {
                "percentageMode": False,
                "useRanges": False,
                "colorSchema": "Green to Red",
                "metricColorMode": "None",
                "colorsRange": [{"from": 0, "to": 10000}],
                "labels": {"show": True},
                "invertColors": False,
                "style": {
                    "bgFill": "#000",
                    "bgColor": False,
                    "labelColor": False,
                    "subText": "",
                    "fontSize": 54,
                },
            },
        },
    }
    return add(
        "visualization",
        obj_id,
        {
            "title": title,
            "description": "Managed by BBOT Dashboard",
            "uiStateJSON": "{}",
            "version": 1,
            "visState": compact(vis_state),
            "kibanaSavedObjectMeta": {"searchSourceJSON": search_source(query)},
        },
        DATA_VIEW_REFERENCE,
    )


def saved_search(
    obj_id: str,
    title: str,
    query: str,
    columns: list[str],
    sort: list[list[str]],
    rows_per_page: int = 100,
) -> str:
    source = {
        "highlightAll": True,
        "version": True,
        "query": {"query": query, "language": "kuery"},
        "filter": [],
        "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index",
    }
    return add(
        "search",
        obj_id,
        {
            "title": title,
            "description": "Managed by BBOT Dashboard",
            "columns": columns,
            "sort": sort,
            "grid": {},
            "hideChart": True,
            "isTextBasedQuery": False,
            "rowsPerPage": rows_per_page,
            "timeRestore": False,
            "usesAdHocDataView": False,
            "kibanaSavedObjectMeta": {"searchSourceJSON": compact(source)},
        },
        DATA_VIEW_REFERENCE,
    )


navigation_markdown = """
| [◉ **OVERVIEW**](/app/dashboards#/view/bbot-overview) | [⌁ **SUBDOMAINS**](/app/dashboards#/view/bbot-subdomains) | [↗ **URLS**](/app/dashboards#/view/bbot-urls) | [⚑ **FINDINGS**](/app/dashboards#/view/bbot-findings) |
|:---:|:---:|:---:|:---:|
""".strip()

add(
    "visualization",
    "bbot-navigation",
    {
        "title": "BBOT navigation",
        "description": "Managed by BBOT Dashboard",
        "uiStateJSON": "{}",
        "version": 1,
        "visState": compact(
            {
                "title": "BBOT navigation",
                "type": "markdown",
                "aggs": [],
                "params": {
                    "fontSize": 18,
                    "openLinksInNewTab": False,
                    "markdown": navigation_markdown,
                },
            }
        ),
        "kibanaSavedObjectMeta": {"searchSourceJSON": search_source("", False)},
    },
)

status_spec = {
    "$schema": "https://vega.github.io/schema/vega/v5.json",
    "autosize": {"type": "fit", "contains": "padding"},
    "background": "transparent",
    "padding": 8,
    "data": [
        {
            "name": "source",
            "url": {
                "%context%": True,
                "%timefield%": "timestamp",
                "index": "bbot-events-*",
                "body": {
                    "size": 0,
                    "aggs": {
                        "scan_docs": {
                            "filter": {"term": {"type": "SCAN"}},
                            "aggs": {
                                "latest": {
                                    "top_hits": {
                                        "size": 1,
                                        "sort": [{"timestamp": {"order": "desc"}}],
                                        "_source": {"includes": ["scan_status_code"]},
                                    }
                                }
                            },
                        }
                    },
                },
            },
            "format": {"property": "aggregations.scan_docs.latest.hits.hits"},
        },
        {
            "name": "status",
            "source": "source",
            "transform": [
                {
                    "type": "formula",
                    "as": "label",
                    "expr": "datum._source.scan_status_code <= 5 ? 'ACTIVE' : datum._source.scan_status_code == 6 ? 'FINISHED' : datum._source.scan_status_code == 7 ? 'FAILED' : 'ABORTED'",
                },
                {
                    "type": "formula",
                    "as": "color",
                    "expr": "datum.label == 'ACTIVE' ? '#00BFB3' : datum.label == 'FAILED' || datum.label == 'ABORTED' ? '#BD271E' : datum.label == 'FINISHED' ? '#6092C0' : '#98A2B3'",
                },
            ],
        },
    ],
    "marks": [
        {
            "type": "text",
            "from": {"data": "status"},
            "encode": {
                "enter": {
                    "x": {"signal": "width / 2"},
                    "y": {"signal": "height / 2"},
                    "align": {"value": "center"},
                    "baseline": {"value": "middle"},
                    "fontSize": {"value": 31},
                    "fontWeight": {"value": "bold"},
                },
                "update": {"text": {"field": "label"}, "fill": {"field": "color"}},
            },
        }
    ],
}

add(
    "visualization",
    "bbot-scan-status",
    {
        "title": "Scan status",
        "description": "Latest status for exactly one selected scan",
        "uiStateJSON": "{}",
        "version": 1,
        "visState": compact(
            {
                "title": "Scan status",
                "type": "vega",
                "aggs": [],
                "params": {"spec": json.dumps(status_spec, ensure_ascii=False, indent=2)},
            }
        ),
        "kibanaSavedObjectMeta": {"searchSourceJSON": search_source("", False)},
    },
)

metric(
    "bbot-count-subdomains",
    "Subdomains",
    'type : "DNS_NAME" and tags : "subdomain"',
    "data",
)
metric("bbot-count-mx", "MX records", 'type : "DNS_NAME" and tags : "mx-record"', "data")
metric("bbot-count-urls", "URLs", 'type : "URL" and url_status_code >= 200 and url_status_code < 300', "event_url")
metric("bbot-count-findings", "All findings", 'type : "FINDING"')
for severity in ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
    metric(
        f"bbot-count-{severity.lower()}",
        severity.title(),
        f'type : "FINDING" and finding_severity : "{severity}"',
    )

saved_search(
    "bbot-scan-registry",
    "Scan registry",
    'type : "SCAN"',
    ["scan_name", "scan", "scan_status", "data_json.started_at", "data_json.finished_at"],
    [["timestamp", "desc"]],
    50,
)
saved_search(
    "bbot-subdomain-list",
    "Subdomains and resolved IP addresses",
    'type : "DNS_NAME" and tags : "subdomain"',
    ["data", "dns_record_types", "resolved_hosts", "scope_description"],
    [["data", "asc"]],
)
saved_search(
    "bbot-url-list",
    "Discovered URLs",
    'type : "URL" and url_status_code >= 200 and url_status_code < 300',
    ["event_url", "url_status_code", "http_title", "host"],
    [["event_url", "asc"]],
)
saved_search(
    "bbot-finding-list",
    "Findings by severity",
    'type : "FINDING"',
    [
        "finding_severity",
        "finding_name",
        "finding_description",
        "finding_url",
        "finding_confidence",
        "host",
    ],
    [["severity_rank", "desc"], ["timestamp", "desc"]],
)


def control(control_id: str, field: str, title: str, order: int, single=True) -> dict[str, Any]:
    return {
        "type": "optionsListControl",
        "order": order,
        "grow": True,
        "width": "medium",
        "explicitInput": {
            "id": control_id,
            "dataViewId": DATA_VIEW_ID,
            "fieldName": field,
            "title": title,
            "grow": True,
            "width": "medium",
            "searchTechnique": "prefix",
            "selectedOptions": [],
            "singleSelect": single,
            "sort": {"by": "_count", "direction": "desc"},
            "enhancements": {},
        },
    }


def dashboard(
    obj_id: str,
    title: str,
    panels: list[tuple[str, str, int, int, int, int]],
    extra_controls: list[tuple[str, str]] | None = None,
) -> None:
    controls = {
        "scan-selector": control("scan-selector", "scan", "Scan ID — select exactly one", 0)
    }
    for position, (field, label) in enumerate(extra_controls or [], start=1):
        controls[f"{field}-selector"] = control(
            f"{field}-selector", field, label, position, single=False
        )

    panel_json = []
    references = []
    for index, (saved_type, saved_id, x, y, w, h) in enumerate(panels):
        panel_name = f"panel_{index}"
        panel_index = f"{obj_id}-{index}"
        panel_json.append(
            {
                "version": KIBANA_VERSION,
                "type": saved_type,
                "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_index},
                "panelIndex": panel_index,
                "embeddableConfig": {},
                "panelRefName": panel_name,
            }
        )
        references.append({"name": panel_name, "type": saved_type, "id": saved_id})

    add(
        "dashboard",
        obj_id,
        {
            "title": title,
            "description": "BBOT security scan dashboard. Managed by BBOT Dashboard.",
            "hits": 0,
            "version": 1,
            "timeRestore": True,
            "timeFrom": "now-10y",
            "timeTo": "now",
            "refreshInterval": {"pause": False, "value": 10000},
            "optionsJSON": compact(
                {
                    "useMargins": True,
                    "syncColors": False,
                    "syncCursor": True,
                    "syncTooltips": False,
                    "hidePanelTitles": False,
                }
            ),
            "panelsJSON": compact(panel_json),
            "controlGroupInput": {
                "chainingSystem": "HIERARCHICAL",
                "controlStyle": "oneLine",
                "showApplySelections": False,
                "ignoreParentSettingsJSON": compact(
                    {
                        "ignoreFilters": False,
                        "ignoreQuery": False,
                        "ignoreTimerange": False,
                        "ignoreValidations": False,
                    }
                ),
                "panelsJSON": compact(controls),
            },
            "kibanaSavedObjectMeta": {"searchSourceJSON": search_source("", False)},
        },
        references,
    )


dashboard(
    "bbot-overview",
    "BBOT — Overview",
    [
        ("visualization", "bbot-navigation", 0, 0, 48, 5),
        ("visualization", "bbot-scan-status", 0, 5, 12, 8),
        ("visualization", "bbot-count-subdomains", 12, 5, 12, 8),
        ("visualization", "bbot-count-mx", 24, 5, 12, 8),
        ("visualization", "bbot-count-urls", 36, 5, 12, 8),
        ("visualization", "bbot-count-findings", 0, 13, 8, 8),
        ("visualization", "bbot-count-info", 8, 13, 8, 8),
        ("visualization", "bbot-count-low", 16, 13, 8, 8),
        ("visualization", "bbot-count-medium", 24, 13, 8, 8),
        ("visualization", "bbot-count-high", 32, 13, 8, 8),
        ("visualization", "bbot-count-critical", 40, 13, 8, 8),
        ("search", "bbot-scan-registry", 0, 21, 48, 14),
    ],
)
dashboard(
    "bbot-subdomains",
    "BBOT — Subdomains",
    [
        ("visualization", "bbot-navigation", 0, 0, 48, 5),
        ("search", "bbot-subdomain-list", 0, 5, 48, 30),
    ],
)
dashboard(
    "bbot-urls",
    "BBOT — URLs",
    [
        ("visualization", "bbot-navigation", 0, 0, 48, 5),
        ("search", "bbot-url-list", 0, 5, 48, 30),
    ],
)
dashboard(
    "bbot-findings",
    "BBOT — Findings",
    [
        ("visualization", "bbot-navigation", 0, 0, 48, 5),
        ("search", "bbot-finding-list", 0, 5, 48, 30),
    ],
    [("finding_severity", "Severity"), ("finding_name", "Finding type")],
)

objects.append(
    {
        "type": "export-details",
        "exportedCount": len(objects),
        "missingRefCount": 0,
        "missingReferences": [],
    }
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(compact(obj) for obj in objects) + "\n", encoding="utf-8")
print(f"Wrote {len(objects) - 1} saved objects to {OUTPUT}")

