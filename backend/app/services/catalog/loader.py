"""Load the JSON catalog (shoe models + component options)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@lru_cache
def load_components() -> dict:
    with (DATA_DIR / "components.json").open() as fh:
        return json.load(fh)


@lru_cache
def load_shoes() -> list[dict]:
    with (DATA_DIR / "shoes.json").open() as fh:
        return json.load(fh)["shoes"]


def get_shoe(slug: str) -> dict | None:
    return next((s for s in load_shoes() if s["slug"] == slug), None)


def components_by_id() -> dict[str, dict]:
    return {c["id"]: c for c in load_components()["components"]}


def option_lookup() -> dict[str, dict[str, dict]]:
    return {c["id"]: {o["id"]: o for o in c["options"]} for c in load_components()["components"]}


def allowed_option_ids(shoe: dict, component_id: str) -> list[str]:
    """Option ids a shoe model permits for a component ('*' means all)."""
    allowed = shoe.get("allowed_options", {}).get(component_id, "*")
    all_ids = [o["id"] for o in components_by_id()[component_id]["options"]]
    if allowed == "*":
        return all_ids
    return [oid for oid in all_ids if oid in allowed]


def shoe_with_options(shoe: dict) -> dict:
    """Shoe plus the fully expanded component/option lists it allows."""
    comps = []
    lookup = option_lookup()
    for comp in load_components()["components"]:
        ids = allowed_option_ids(shoe, comp["id"])
        if not ids:
            continue
        comps.append({**{k: v for k, v in comp.items() if k != "options"}, "options": [lookup[comp["id"]][i] for i in ids]})
    return {**shoe, "components": comps}
