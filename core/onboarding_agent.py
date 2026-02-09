from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class OnboardingPolicy:
    allow_add_provider: bool = True
    allow_add_subject: bool = True
    allow_bindings: bool = True
    enforce_category_match: bool = True

    @classmethod
    def from_dict(cls, raw: Dict[str, Any] | None) -> "OnboardingPolicy":
        raw = raw or {}
        return cls(
            allow_add_provider=bool(raw.get("allow_add_provider", True)),
            allow_add_subject=bool(raw.get("allow_add_subject", True)),
            allow_bindings=bool(raw.get("allow_bindings", True)),
            enforce_category_match=bool(raw.get("enforce_category_match", True)),
        )


def _default_subject(name: str, environment: str = "prod", aliases: List[str] | None = None) -> Dict[str, Any]:
    return {
        "name": name,
        "environment": environment,
        "aliases": aliases or [],
        "bindings": {},
        "dependencies": [],
        "runbooks": [],
        "known_failure_modes": [],
        "deploy_context": {},
        "vcs_context": {},
        "log_evidence": {},
    }


def _default_provider(
    provider_id: str,
    category: str,
    provider_type: str,
    operations: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "id": provider_id,
        "category": category,
        "type": provider_type,
        "operations": operations or [],
        "config": {},
    }


def _parse_json_intent(intent: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(intent)
    except json.JSONDecodeError:
        return []

    ops = payload.get("operations") if isinstance(payload, dict) else None
    if not isinstance(ops, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for op in ops:
        if isinstance(op, dict) and isinstance(op.get("type"), str):
            normalized.append(op)
    return normalized


def _parse_text_intent(intent: str) -> List[Dict[str, Any]]:
    operations: List[Dict[str, Any]] = []
    chunks = [part.strip() for part in re.split(r"[\n;]+", intent) if part.strip()]

    for chunk in chunks:
        lower = chunk.lower()

        match = re.match(
            r"^add\s+provider\s+([a-zA-Z0-9_.-]+)(?:\s+category\s+([a-zA-Z0-9_.-]+))?(?:\s+type\s+([a-zA-Z0-9_.-]+))?(?:\s+operations?\s+(.+))?$",
            lower,
        )
        if match:
            provider_id = match.group(1)
            category = match.group(2) or "log_store"
            provider_type = match.group(3) or "custom"
            ops_raw = match.group(4) or ""
            parsed_ops = [op.strip() for op in ops_raw.split(",") if op.strip()]
            operations.append(
                {
                    "type": "add_provider",
                    "provider": _default_provider(provider_id, category, provider_type, parsed_ops),
                }
            )
            continue

        match = re.match(
            r"^add\s+subject\s+([a-zA-Z0-9_.-]+)(?:\s+env(?:ironment)?\s+([a-zA-Z0-9_.-]+))?(?:\s+aliases?\s+(.+))?$",
            lower,
        )
        if match:
            subject_name = match.group(1)
            env = match.group(2) or "prod"
            aliases_raw = match.group(3) or ""
            aliases = [alias.strip() for alias in aliases_raw.split(",") if alias.strip()]
            operations.append(
                {
                    "type": "add_subject",
                    "subject": _default_subject(subject_name, env, aliases),
                }
            )
            continue

        match = re.match(
            r"^bind\s+([a-zA-Z0-9_.-]+)\s+([a-zA-Z0-9_.-]+)\s+to\s+([a-zA-Z0-9_.-]+)$",
            lower,
        )
        if match:
            operations.append(
                {
                    "type": "bind_subject_provider",
                    "binding": {
                        "subject": match.group(1),
                        "capability": match.group(2),
                        "provider_id": match.group(3),
                    },
                }
            )
            continue

    return operations


def parse_intent_to_ops(intent: str) -> List[Dict[str, Any]]:
    normalized = intent.strip()
    if not normalized:
        return []

    if normalized.startswith("{"):
        parsed = _parse_json_intent(normalized)
        if parsed:
            return parsed

    return _parse_text_intent(normalized)


def _provider_map(model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    providers = model.get("providers", [])
    out: Dict[str, Dict[str, Any]] = {}
    for provider in providers:
        if isinstance(provider, dict) and isinstance(provider.get("id"), str) and provider.get("id"):
            out[provider["id"]] = provider
    return out


def _subject_index(model: Dict[str, Any]) -> Dict[str, int]:
    subjects = model.get("subjects", [])
    out: Dict[str, int] = {}
    for idx, subject in enumerate(subjects):
        if isinstance(subject, dict) and isinstance(subject.get("name"), str) and subject.get("name"):
            out[subject["name"]] = idx
    return out


def _binding_warnings(model: Dict[str, Any], enforce_category_match: bool) -> List[str]:
    warnings: List[str] = []
    provider_map = _provider_map(model)
    all_bound_providers: set[str] = set()

    for subject in model.get("subjects", []):
        if not isinstance(subject, dict):
            continue
        subject_name = subject.get("name", "<unknown-subject>")
        bindings = subject.get("bindings", {})
        if not isinstance(bindings, dict):
            continue

        for capability, provider_id in bindings.items():
            if not isinstance(provider_id, str) or not provider_id:
                warnings.append(f"[{subject_name}] capability '{capability}' has an empty provider binding")
                continue
            provider = provider_map.get(provider_id)
            if provider is None:
                warnings.append(f"[{subject_name}] capability '{capability}' references missing provider '{provider_id}'")
                continue
            all_bound_providers.add(provider_id)
            if enforce_category_match and provider.get("category") != capability:
                warnings.append(
                    f"[{subject_name}] capability '{capability}' is bound to provider '{provider_id}' "
                    f"with category '{provider.get('category')}'"
                )

    for provider_id, provider in provider_map.items():
        if provider_id not in all_bound_providers:
            warnings.append(f"Provider '{provider_id}' is currently unused by any subject binding")

    return warnings


def apply_ops(
    model: Dict[str, Any],
    ops: List[Dict[str, Any]],
    policy_raw: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    policy = OnboardingPolicy.from_dict(policy_raw)
    next_model = copy.deepcopy(model)
    applied_ops: List[Dict[str, Any]] = []
    rejected_ops: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for op in ops:
        op_type = op.get("type")

        if op_type == "add_provider":
            if not policy.allow_add_provider:
                rejected_ops.append(op)
                warnings.append("Policy rejected add_provider operation")
                continue
            provider = op.get("provider")
            if not isinstance(provider, dict):
                rejected_ops.append(op)
                warnings.append("add_provider operation missing provider payload")
                continue
            provider_id = provider.get("id")
            if not isinstance(provider_id, str) or not provider_id:
                rejected_ops.append(op)
                warnings.append("add_provider operation requires a non-empty provider id")
                continue
            if provider_id in _provider_map(next_model):
                rejected_ops.append(op)
                warnings.append(f"Provider '{provider_id}' already exists")
                continue
            next_model.setdefault("providers", []).append(
                {
                    "id": provider_id,
                    "category": provider.get("category", "log_store"),
                    "type": provider.get("type", "custom"),
                    "operations": provider.get("operations", []) if isinstance(provider.get("operations"), list) else [],
                    "config": provider.get("config", {}) if isinstance(provider.get("config"), dict) else {},
                }
            )
            applied_ops.append(op)
            continue

        if op_type == "add_subject":
            if not policy.allow_add_subject:
                rejected_ops.append(op)
                warnings.append("Policy rejected add_subject operation")
                continue
            subject = op.get("subject")
            if not isinstance(subject, dict):
                rejected_ops.append(op)
                warnings.append("add_subject operation missing subject payload")
                continue
            subject_name = subject.get("name")
            if not isinstance(subject_name, str) or not subject_name:
                rejected_ops.append(op)
                warnings.append("add_subject operation requires a non-empty subject name")
                continue
            if subject_name in _subject_index(next_model):
                rejected_ops.append(op)
                warnings.append(f"Subject '{subject_name}' already exists")
                continue
            next_model.setdefault("subjects", []).append(
                _default_subject(
                    name=subject_name,
                    environment=subject.get("environment", "prod"),
                    aliases=subject.get("aliases", []) if isinstance(subject.get("aliases"), list) else [],
                )
            )
            applied_ops.append(op)
            continue

        if op_type == "bind_subject_provider":
            if not policy.allow_bindings:
                rejected_ops.append(op)
                warnings.append("Policy rejected bind_subject_provider operation")
                continue

            binding = op.get("binding")
            if not isinstance(binding, dict):
                rejected_ops.append(op)
                warnings.append("bind_subject_provider operation missing binding payload")
                continue

            subject_name = binding.get("subject")
            capability = binding.get("capability")
            provider_id = binding.get("provider_id")
            if not isinstance(subject_name, str) or not subject_name or not isinstance(capability, str) or not capability:
                rejected_ops.append(op)
                warnings.append("bind_subject_provider requires subject and capability")
                continue
            if not isinstance(provider_id, str) or not provider_id:
                rejected_ops.append(op)
                warnings.append("bind_subject_provider requires a non-empty provider_id")
                continue

            subject_idx = _subject_index(next_model).get(subject_name)
            if subject_idx is None:
                rejected_ops.append(op)
                warnings.append(f"Subject '{subject_name}' does not exist")
                continue
            provider = _provider_map(next_model).get(provider_id)
            if provider is None:
                rejected_ops.append(op)
                warnings.append(f"Provider '{provider_id}' does not exist")
                continue
            if policy.enforce_category_match and provider.get("category") != capability:
                rejected_ops.append(op)
                warnings.append(
                    f"Binding rejected: capability '{capability}' does not match provider '{provider_id}' "
                    f"category '{provider.get('category')}'"
                )
                continue

            subject = next_model["subjects"][subject_idx]
            subject.setdefault("bindings", {})[capability] = provider_id
            applied_ops.append(op)
            continue

        rejected_ops.append(op)
        warnings.append(f"Unsupported operation type '{op_type}'")

    warnings.extend(_binding_warnings(next_model, policy.enforce_category_match))
    return next_model, applied_ops, rejected_ops, sorted(set(warnings))


def plan_ops(
    intent: str,
    model: Dict[str, Any],
    policy_raw: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    proposed_ops = parse_intent_to_ops(intent)
    if not proposed_ops:
        return {
            "proposed_ops": [],
            "preview_model": model,
            "warnings": [
                "No actionable operations parsed from intent. Supported forms: "
                "'add provider ...', 'add subject ...', 'bind <subject> <capability> to <provider_id>', "
                "or JSON object with operations array."
            ],
            "requires_confirmation": False,
            "applied_ops": [],
            "rejected_ops": [],
        }

    preview_model, applied_ops, rejected_ops, warnings = apply_ops(model, proposed_ops, policy_raw)
    return {
        "proposed_ops": proposed_ops,
        "preview_model": preview_model,
        "warnings": warnings,
        "requires_confirmation": len(proposed_ops) > 0,
        "applied_ops": applied_ops,
        "rejected_ops": rejected_ops,
    }
