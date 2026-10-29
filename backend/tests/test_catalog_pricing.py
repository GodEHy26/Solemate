from app.services.catalog.loader import get_shoe, load_components, load_shoes, shoe_with_options
from app.services.catalog.pricing import price_configuration


def test_catalog_integrity():
    comps = {c["id"]: {o["id"] for o in c["options"]} for c in load_components()["components"]}
    for shoe in load_shoes():
        for comp_id, allowed in shoe["allowed_options"].items():
            assert comp_id in comps
            if allowed != "*":
                assert set(allowed) <= comps[comp_id], (shoe["slug"], comp_id)
        for comp_id, default in shoe["defaults"].items():
            assert default in comps[comp_id]
        priced = price_configuration(shoe, shoe["defaults"])
        assert priced.valid, priced.errors


def test_price_breakdown():
    shoe = get_shoe("solemate-daily")
    result = price_configuration(
        shoe, {"outsole": "gum_rubber", "midsole": "eva", "upper": "suede", "lining": "textile", "insole": "cork", "laces": "flat_cotton"}
    )
    assert result.valid
    assert result.options_cents == 1000 + 0 + 3000 + 0 + 1200 + 0
    assert result.total_cents == shoe["base_price_cents"] + result.options_cents
    assert not result.requires_scan


def test_validation_errors():
    shoe = get_shoe("solemate-court")
    result = price_configuration(shoe, {"outsole": "polyurethane", "midsole": "cork_latex", "upper": "engineered_knit"})
    assert not result.valid
    joined = " ".join(result.errors)
    assert "not offered" in joined           # PU outsole not allowed on Court
    assert "Missing selection" in joined     # lining / insole / laces
    assert "flexible platforms" in joined    # knit + cork rule


def test_scan_requirement_flag():
    shoe = get_shoe("solemate-stride")
    result = price_configuration(shoe, {**shoe["defaults"], "insole": "custom_printed"})
    assert result.valid and result.requires_scan


def test_shoe_with_options_filters():
    shoe = shoe_with_options(get_shoe("solemate-daily"))
    uppers = next(c for c in shoe["components"] if c["id"] == "upper")
    assert {o["id"] for o in uppers["options"]} == {"canvas", "full_grain_leather", "suede", "recycled_textile"}
