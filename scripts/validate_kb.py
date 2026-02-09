#!/usr/bin/env python3
"""
Validate onboarding YAML docs (catalog + subjects) without running the API.

Checks:
- YAML parses and has expected top-level keys.
- All subject bindings reference existing provider ids.
- Provider categories are known and provider operations are valid per RCA tools schema.

Usage:
  uv run python scripts/validate_kb.py
  uv run python scripts/validate_kb.py --catalog catalog/instances.yaml --kb kb/subjects.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml


CATEGORY_TO_CAPABILITY_TYPES: Dict[str, List[str]] = {
    "log_store": ["logs"],
    "metrics_store": ["metrics"],
    "trace_store": ["traces"],
    "alerting": ["alerts"],
    "deploy_tracker": ["deployments", "pipelines"],
    "build_tracker": ["pipelines"],
    "vcs": ["changes"],
    "runtime": ["workloads", "nodes"],
}

LEGACY_OP_ALIASES: Dict[str, str] = {
    "query.samples": "search",
    "query.signature_counts": "aggregate",
    "query_range": "timeseries_query",
    "search_traces": "search",
    "list_alerts": "list",
    "list_deployments": "list",
    "get_deployment_metadata": "get",
    "list_changes": "list_prs",
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    raw = path.read_text()
    data = yaml.safe_load(raw) if raw.strip() else {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a YAML mapping at top level")
    return data


def _load_rca_tools_schema_doc(schema_path: Path) -> Dict[str, Any]:
    if not schema_path.exists():
        return {}
    raw = schema_path.read_text()
    try:
        parsed = yaml.safe_load(raw) if raw.strip() else {}
    except yaml.YAMLError:
        # The human-readable schema may contain non-YAML type shorthand in other sections.
        # Extract only `tool_catalog:` block and parse it.
        marker = "\ntool_catalog:"
        start = raw.find(marker)
        if start < 0:
            return {}
        tail = raw[start + 1 :]
        end_marker = "\n# -----------------------------\n# 4)"
        end = tail.find(end_marker)
        fragment = tail if end < 0 else tail[:end]
        try:
            parsed_fragment = yaml.safe_load(fragment)
        except yaml.YAMLError:
            return {}
        if not isinstance(parsed_fragment, dict):
            return {}
        return {"tool_catalog": parsed_fragment.get("tool_catalog", {})}

    if parsed is None:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _schema_allowed_operations_by_capability(schema_doc: Dict[str, Any]) -> Dict[str, Set[str]]:
    by_capability: Dict[str, Set[str]] = {}
    tools = (schema_doc.get("tool_catalog") or {}).get("tools") or []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        capabilities = tool.get("capabilities") or {}
        for mode in ("read", "write", "execute"):
            entries = capabilities.get(mode) or []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cap_type = entry.get("type")
                operations = entry.get("operations") or []
                if not isinstance(cap_type, str) or not isinstance(operations, list):
                    continue
                by_capability.setdefault(cap_type, set()).update(
                    op for op in operations if isinstance(op, str) and op
                )
    return by_capability


def _validate_catalog_against_rca_schema(catalog_doc: Dict[str, Any], schema_path: Path) -> List[str]:
    schema_doc = _load_rca_tools_schema_doc(schema_path)
    if not schema_doc:
        return []

    allowed_ops_by_capability = _schema_allowed_operations_by_capability(schema_doc)
    if not allowed_ops_by_capability:
        return ["RCA tools schema has no declared capability operations under tool_catalog.tools."]

    errors: List[str] = []
    providers = catalog_doc.get("providers", [])
    if not isinstance(providers, list):
        return ["catalog.providers must be a list"]

    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider_id = provider.get("id", "<missing-id>")
        category = provider.get("category")
        # Keep this script usable for minimal unit tests and early scaffolding:
        # if category isn't present yet, skip schema validation for this provider.
        if not isinstance(category, str) or not category:
            continue

        capability_types = CATEGORY_TO_CAPABILITY_TYPES.get(category)
        if not capability_types:
            errors.append(f"[provider:{provider_id}] unknown category '{category}'")
            continue

        allowed_ops: Set[str] = set()
        for cap_type in capability_types:
            allowed_ops.update(allowed_ops_by_capability.get(cap_type, set()))
        if not allowed_ops:
            errors.append(f"[provider:{provider_id}] category '{category}' has no matching capability ops in schema")
            continue

        operations = ((provider.get("capabilities") or {}).get("operations")) or []
        if not isinstance(operations, list):
            errors.append(f"[provider:{provider_id}] capabilities.operations must be a list")
            continue

        for operation in operations:
            if not isinstance(operation, str) or not operation:
                errors.append(f"[provider:{provider_id}] contains non-string operation entry")
                continue
            canonical = LEGACY_OP_ALIASES.get(operation, operation)
            if canonical not in allowed_ops:
                allowed_display = ", ".join(sorted(allowed_ops))
                errors.append(
                    f"[provider:{provider_id}] operation '{operation}' is not allowed for category '{category}'. "
                    f"Allowed: {allowed_display}"
                )
    return errors


def _validate_bindings(subjects_doc: Dict[str, Any], catalog_doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    providers = {
        p.get("id"): p
        for p in (catalog_doc.get("providers") or [])
        if isinstance(p, dict) and isinstance(p.get("id"), str)
    }

    subjects = subjects_doc.get("subjects") or []
    if not isinstance(subjects, list):
        return ["kb.subjects must be a list"]

    if not providers:
        errors.append("No providers found in catalog YAML.")
    if not subjects:
        errors.append("No subjects found in subjects YAML.")

    for s in subjects:
        if not isinstance(s, dict):
            continue
        name = s.get("name", "<missing-name>")
        bindings = s.get("bindings") or {}
        if not isinstance(bindings, dict):
            errors.append(f"[{name}] bindings must be a mapping")
            continue

        for cap, pid in bindings.items():
            if not isinstance(pid, str) or not pid:
                errors.append(f"[{name}] binding '{cap}' must be a non-empty string")
                continue
            if pid not in providers:
                errors.append(f"[{name}] binding '{cap}' references unknown provider '{pid}'")
                continue

            provider_cat = (providers[pid] or {}).get("category")
            if isinstance(cap, str) and isinstance(provider_cat, str) and cap != provider_cat:
                # In current model, capability keys are equal to provider category.
                errors.append(
                    f"[{name}] binding '{cap}' points to provider '{pid}' with category '{provider_cat}'"
                )

    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    # Backwards compatible positional args used by older tests/tools:
    #   validate_kb.py <subjects.yaml> <catalog.yaml>
    ap.add_argument("kb_pos", nargs="?", help="Path to subjects.yaml (positional)")
    ap.add_argument("catalog_pos", nargs="?", help="Path to instances.yaml (positional)")
    ap.add_argument("--catalog", default="catalog/instances.yaml")
    ap.add_argument("--kb", default="kb/subjects.yaml")
    ap.add_argument("--schema", default="catalog/rca-tools.schema.yaml")
    args = ap.parse_args()

    kb_value = args.kb_pos or args.kb
    catalog_value = args.catalog_pos or args.catalog

    catalog_path = Path(catalog_value)
    kb_path = Path(kb_value)
    schema_path = Path(args.schema)

    try:
        catalog = _load_yaml(catalog_path)
        kb = _load_yaml(kb_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    errors: List[str] = []
    errors.extend(_validate_catalog_against_rca_schema(catalog, schema_path))
    errors.extend(_validate_bindings(kb, catalog))

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print("OK: onboarding YAML validates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
