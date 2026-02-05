from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import yaml
from langchain_core.prompts import PromptTemplate


def deep_merge(base: Any, override: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    merged = dict(base)
    for key, value in override.items():
        merged[key] = deep_merge(base.get(key), value)
    return merged


def render_template(text: str, context: Dict[str, Any]) -> str:
    template = PromptTemplate.from_template(text, template_format="jinja2")
    return template.format(**context)


def load_spec(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def apply_overrides(spec: Dict[str, Any]) -> Dict[str, Any]:
    overrides = spec.get("overrides", {})
    if not overrides:
        return spec

    spec = dict(spec)
    spec["variables"] = deep_merge(spec.get("variables", {}), overrides.get("variables", {}))
    spec["modules"] = deep_merge(spec.get("modules", {}), overrides.get("modules", {}))
    return spec


def build_context(spec: Dict[str, Any]) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    context.update(spec.get("inputs", {}))
    context.update(spec.get("variables", {}))
    return context


def render_prompt(spec: Dict[str, Any]) -> str:
    spec = apply_overrides(spec)
    context = build_context(spec)

    parts = []
    for module_name in spec["render"]["order"]:
        module = spec["modules"].get(module_name, {})
        if module.get("enabled") is True:
            parts.append(render_template(module["content"], context))

    wrapper = spec.get("render", {}).get("wrapper", {})
    header = render_template(wrapper.get("header", ""), context).rstrip()
    footer = render_template(wrapper.get("footer", ""), context).lstrip()

    body = "\n\n".join(parts)
    if header:
        body = f"{header}\n\n{body}"
    if footer:
        body = f"{body}\n\n{footer}"
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a UI prompt spec with LangChain PromptTemplate.")
    parser.add_argument(
        "--spec",
        default="docs/ui-prompts.md",
        help="Path to the prompt spec file.",
    )
    args = parser.parse_args()

    spec = load_spec(Path(args.spec))
    print(render_prompt(spec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
