
from __future__ import annotations

from dataclasses import dataclass, field

from .loader import allowed_option_ids, components_by_id, load_components, option_lookup


@dataclass
class PriceLine:
    component_id: str
    component_name: str
    option_id: str
    option_name: str
    cents: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class PriceResult:
    valid: bool
    currency: str
    base_cents: int
    options_cents: int
    total_cents: int
    lines: list[PriceLine] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    requires_scan: bool = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "currency": self.currency,
            "base_cents": self.base_cents,
            "options_cents": self.options_cents,
            "total_cents": self.total_cents,
            "lines": [l.to_dict() for l in self.lines],
            "errors": self.errors,
            "requires_scan": self.requires_scan,
        }


def _rule_violations(selections: dict[str, str]) -> list[str]:
    problems = []
    for rule in load_components().get("compatibility_rules", []):
        if all(selections.get(c) == o for c, o in rule["when"].items()):
            for comp, banned in rule["disallow"].items():
                if selections.get(comp) in banned:
                    problems.append(rule.get("reason") or f"{comp}={selections.get(comp)} is not compatible")
    return problems


def price_configuration(shoe: dict, selections: dict[str, str]) -> PriceResult:
    catalog = load_components()
    comps = components_by_id()
    options = option_lookup()
    currency = catalog.get("currency", "USD")
    base = int(shoe["base_price_cents"])
    errors: list[str] = []
    lines: list[PriceLine] = []
    requires_scan = False

    for comp_id, comp in comps.items():
        allowed = allowed_option_ids(shoe, comp_id)
        choice = selections.get(comp_id)
        if choice is None:
            if comp.get("required", True) and allowed:
                errors.append(f"Missing selection for {comp['name'].lower()}.")
            continue
        if choice not in options[comp_id]:
            errors.append(f"Unknown {comp['name'].lower()} option '{choice}'.")
            continue
        if choice not in allowed:
            errors.append(f"{options[comp_id][choice]['name']} is not offered on {shoe['name']}.")
            continue
        opt = options[comp_id][choice]
        requires_scan = requires_scan or bool(opt.get("requires_scan"))
        lines.append(PriceLine(comp_id, comp["name"], choice, opt["name"], int(opt.get("price_delta_cents", 0))))

    for key in selections:
        if key not in comps:
            errors.append(f"Unknown component '{key}'.")

    errors.extend(_rule_violations(selections))
    options_cents = sum(l.cents for l in lines)
    return PriceResult(
        valid=not errors,
        currency=currency,
        base_cents=base,
        options_cents=options_cents,
        total_cents=base + options_cents,
        lines=lines,
        errors=errors,
        requires_scan=requires_scan,
    )
