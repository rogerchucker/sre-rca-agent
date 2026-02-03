#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import yaml

def load_yaml(path: str):
    return yaml.safe_load(Path(path).read_text())

def main():
    subjects_path = sys.argv[1] if len(sys.argv) > 1 else "kb/subjects.yaml"
    catalog_path = sys.argv[2] if len(sys.argv) > 2 else "catalog/instances.yaml"

    subjects_doc = load_yaml(subjects_path)
    catalog_doc = load_yaml(catalog_path)

    errors: list[str] = []

    providers = {p["id"]: p for p in catalog_doc.get("providers", []) if isinstance(p, dict) and "id" in p}

    if not providers:
        errors.append(f"No providers found in {catalog_path}")

    subjects = subjects_doc.get("subjects", [])
    if not subjects:
        errors.append(f"No subjects found in {subjects_path}")

    for s in subjects:
        name = s.get("name", "<missing-name>")
        bindings = (s.get("bindings") or {})

        # ---- Binding existence check ----
        for cap, pid in bindings.items():
            if not isinstance(pid, str) or not pid:
                errors.append(f"[{name}] binding '{cap}' must be a non-empty string")
                continue
            if pid not in providers:
                errors.append(f"[{name}] binding '{cap}' references missing provider id '{pid}'")

        # ---- Required log parse fields check (for json) ----
        log_ev = s.get("log_evidence") or {}
        parse = log_ev.get("parse") or {}
        fmt = parse.get("format")
        fields = parse.get("fields") or {}

        if fmt == "json":
            for req_field in ("env", "err_msg"):
                if req_field not in fields or not isinstance(fields.get(req_field), str) or not fields.get(req_field).strip():
                    errors.append(f"[{name}] log_evidence.parse.fields must include non-empty '{req_field}' for json logs")

        # ---- Optional: if deploy_tracker binding exists, ensure deploy context OR provider maps cover it ----
        # We keep this soft for now because you might choose pattern A or B.
        # Uncomment to enforce deploy_context presence when deploy_tracker is bound.
        #
        # if "deploy_tracker" in bindings:
        #     dc = s.get("deploy_context") or {}
        #     if not dc.get("repo") or not dc.get("workflow_path"):
        #         errors.append(f"[{name}] deploy_tracker is bound but deploy_context.repo/workflow_path missing")

    if errors:
        print("KB validation failed:\n")
        for e in errors:
            print(" - " + e)
        sys.exit(1)

    print("KB validation OK.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())