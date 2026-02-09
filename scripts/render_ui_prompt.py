#!/usr/bin/env python3
"""
Render a simple multi-module UI prompt spec.

This is a small utility used by unit tests and for iterating on prompt text.

Spec shape (YAML):
- inputs: mapping
- variables: mapping (optional)
- modules: mapping of module_id -> { enabled: bool, content: str }
- render:
    order: [module_id, ...]
    wrapper: { header: str, footer: str } (optional)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from jinja2 import Template


def _load_yaml(path: Path) -> Dict[str, Any]:
    raw = path.read_text()
    data = yaml.safe_load(raw) if raw.strip() else {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("spec must be a mapping")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    args = ap.parse_args()

    spec = _load_yaml(Path(args.spec))
    inputs = spec.get("inputs") or {}
    variables = spec.get("variables") or {}
    modules = spec.get("modules") or {}
    render = spec.get("render") or {}
    order = render.get("order") or []
    wrapper = render.get("wrapper") or {}

    ctx: Dict[str, Any] = {}
    if isinstance(inputs, dict):
        ctx.update(inputs)
    if isinstance(variables, dict):
        ctx.update(variables)

    parts: list[str] = []
    for module_id in order:
        module = modules.get(module_id) if isinstance(modules, dict) else None
        if not isinstance(module, dict):
            continue
        if module.get("enabled") is False:
            continue
        content = module.get("content") or ""
        if not isinstance(content, str):
            continue
        parts.append(Template(content).render(**ctx))

    header = wrapper.get("header") if isinstance(wrapper, dict) else None
    footer = wrapper.get("footer") if isinstance(wrapper, dict) else None
    if isinstance(header, str) and header:
        parts.insert(0, header)
    if isinstance(footer, str) and footer:
        parts.append(footer)

    sys.stdout.write("\n".join(parts).strip() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

