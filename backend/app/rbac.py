"""Loads rbac_mapping.yaml and answers "can this user do X in namespace Y?"."""
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import get_settings


@lru_cache
def _load_mapping() -> dict:
    settings = get_settings()
    path = Path(settings.rbac_mapping_file)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def allowed_namespaces(groups: list[str]) -> set[str] | str:
    """Returns "*" if any group has full access, otherwise a set of namespaces."""
    mapping = _load_mapping()
    namespaces: set[str] = set()
    for g in groups:
        rule = mapping.get(g)
        if not rule:
            continue
        ns = rule.get("namespaces")
        if ns == "*":
            return "*"
        if isinstance(ns, list):
            namespaces.update(ns)
    return namespaces


def allowed_actions(groups: list[str]) -> set[str]:
    mapping = _load_mapping()
    actions: set[str] = set()
    for g in groups:
        rule = mapping.get(g)
        if not rule:
            continue
        actions.update(rule.get("actions") or [])
    return actions


def can_access_namespace(groups: list[str], namespace: str) -> bool:
    ns = allowed_namespaces(groups)
    return ns == "*" or namespace in ns


def can_perform(groups: list[str], action: str) -> bool:
    return action in allowed_actions(groups)
