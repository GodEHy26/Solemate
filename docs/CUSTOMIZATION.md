# Shoe models and components

All catalog data lives in JSON under `backend/app/data/` and is loaded at startup. No code changes
are needed to add a shoe or a material.

## `components.json`

```jsonc
{
  "currency": "USD",
  "components": [
    {
      "id": "outsole",                 // referenced by shoes and orders
      "name": "Outsole",
      "description": "...",
      "required": true,
      "options": [
        {
          "id": "polyurethane",
          "name": "Polyurethane (PU)",
          "material": "Microcellular polyurethane",
          "price_delta_cents": 1500,     // added to the shoe's base price
          "properties": {"grip": 3, "durability": 5, "weight": 3, "flexibility": 3},  // 1–5, shown as bars
          "colors": ["#111111", "#f2efe8"],
          "notes": "...",
          "requires_scan": false         // true = order needs both foot profiles (e.g. printed insole)
        }
      ]
    }
  ],
  "compatibility_rules": [
    {
      "id": "knit-needs-flexible-platform",
      "when": {"upper": "engineered_knit"},
      "disallow": {"midsole": ["cork_latex"], "outsole": ["tpu"]},
      "reason": "Shown to the customer when violated"
    }
  ]
}
```

Current component types: `outsole` (solid rubber, blown rubber, gum rubber, polyurethane, TPU),
`midsole` (EVA, PU, e-TPU beads, supercritical foam, cork latex), `upper` (engineered knit,
canvas, mesh, full-grain leather, suede, recycled textile), `lining`, `insole` (incl. a custom
3D-printed lattice generated from the scan) and `laces`.

## `shoes.json`

```jsonc
{
  "slug": "solemate-court",            // URL and order key
  "name": "SoleMate Court",
  "tagline": "...", "description": "...",
  "category": "basketball",
  "last_family": "court",              // restricts the reference-last match (see reference_lasts.json)
  "base_price_cents": 21900,
  "placeholder": true,                 // shows a badge in the catalog; delete when the model is real
  "hero_color": "#2e86de",
  "allowed_options": {                 // "*" = every option of that component, or a list of ids
    "outsole": ["rubber", "blown_rubber", "gum_rubber", "tpu"],
    "lining": "*"
  },
  "defaults": {"outsole": "rubber", "midsole": "etpu", ...}
}
```

The three entries shipped (`solemate-court`, `solemate-stride`, `solemate-daily`) are placeholders
so the configurator has something to render. Replace them when the line-up is decided;
`tests/test_catalog_pricing.py::test_catalog_integrity` checks that every allowed option and
default exists.

## `reference_lasts.json`

Base lasts measured at US men's 10, with `family` matching `last_family` on shoes. The first five
are the internal shoe dimensions measured for the IA. Grading rules live in
`services/fitting/last_matcher.py` (8.47 mm length per full size, 2 mm width, 1 mm height).

## Pricing and validation

`POST /api/catalog/price` returns a breakdown and a list of errors (missing component, option not
offered on this model, rule violation, unknown ids). Orders are re-priced on the server, so the
client-side estimate in `frontend/src/lib/pricing.ts` is only for instant feedback.

## 3D preview

`frontend/src/components/configurator/ShoePreview.tsx` draws a stylised parametric shoe coloured
by the current selections. Once real models exist, swap in a GLB per model and map component ids
to mesh names.
