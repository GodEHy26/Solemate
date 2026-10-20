# Architecture

SoleMate v2 is a two-part web application:

```
┌──────────────────────────────┐        ┌──────────────────────────────────────┐
│  frontend/  (Vite + React)   │  /api  │  backend/  (FastAPI)                  │
│  • guided Face-ID style scan │ ─────▶ │  • scan sessions + frame storage      │
│  • three.js foot viewer      │        │  • silhouettes → visual hull → mesh   │
│  • component configurator    │ ◀───── │  • measurements, sizing, last spec    │
│  • cart + checkout           │  JSON  │  • catalog, pricing, orders (SQLite)  │
└──────────────────────────────┘        └──────────────────────────────────────┘
```

## Backend layout (`backend/app`)

| Path | Responsibility |
|------|----------------|
| `main.py` | FastAPI app factory, CORS, router registration, `/api/health` |
| `config.py` | `Settings` (pydantic-settings). Override anything with `SOLEMATE_*` env vars |
| `database.py`, `db_models.py` | SQLModel engine + tables: `scan_sessions`, `foot_profiles`, `orders` |
| `schemas.py` | Request/response models for the HTTP API |
| `api/scans.py` | Capture plan, create session, upload frames or a mesh, trigger reconstruction, status |
| `api/profiles.py` | Measurements, footprint, sections, mesh download, custom last spec |
| `api/catalog.py` | Shoe models, components, price validation |
| `api/orders.py` | Server-side re-pricing and order persistence |
| `services/scanning/` | The 3D pipeline (see `SCAN_PIPELINE.md`) |
| `services/fitting/` | KD-tree over reference lasts (from the IA) + grading/adjustment |
| `services/catalog/` | JSON catalog loader and pricing/compatibility rules |
| `data/` | `components.json`, `shoes.json`, `reference_lasts.json` |

Large artefacts (frames, meshes, `profile.json`) are written under `SOLEMATE_DATA_DIR/scans/<session id>/`.
The database holds metadata and JSON documents only, so swapping SQLite for Postgres is a URL change.

## Frontend layout (`frontend/src`)

| Path | Responsibility |
|------|----------------|
| `lib/api.ts`, `lib/types.ts` | Typed API client (relative `/api` paths; Vite proxies to the backend in dev) |
| `lib/scanSession.ts` | Pure ring/sector state machine for the capture flow (unit tested) |
| `lib/hooks/useCamera.ts` | Rear camera stream + JPEG snapshot |
| `lib/hooks/useOrientation.ts` | Device heading with iOS permission handling |
| `components/scan/` | `CaptureRing` (SVG) and `ScanWizard` (intro → top-down → orbit → processing) |
| `components/viewer/` | GLB viewer (react-three-fiber), footprint and cross-section SVGs, measurement tables |
| `components/configurator/` | Component pickers, price summary, stylised 3D shoe preview |
| `pages/` | Home, Scan, Profile, Catalog, Configurator, Checkout, Order |
| `store/` | zustand stores persisted to localStorage: cart and the two foot profiles |

## Request flow for one scan

1. `POST /api/scans` → session id (status `capturing`).
2. Client uploads the top-down frame (`kind=topdown`) and ~16–24 orbit frames with their yaw.
3. `POST /api/scans/{id}/reconstruct` validates coverage, sets `processing`, runs the pipeline in a
   background task (or inline when `SOLEMATE_SYNC_PROCESSING=1`).
4. Client polls `GET /api/scans/{id}` until `complete` and opens `/profiles/{profile_id}`.
5. The profile id is kept client-side (`useFeet`) and attached to order items.

## Where the IA code went

| IA (`Computer-Science-IB-HL-IA`) | SoleMate v2 |
|---|---|
| `models/image_processor.py` (Otsu + largest contour) | `services/scanning/segmentation.py` (polarity detection, saturation fallback, GrabCut) and `scale.py` (metric top-down measurement on paper) |
| `models/shoe_index.py` (KD-tree) | `services/fitting/shoe_index.py`, now indexing reference lasts |
| `models/fit_analyzer.py` (ratio scoring) | `services/fitting/last_matcher.py` (grade + adjust a last instead of scoring stock shoes) and `sizing.py` |
| `assets/bball_shoes.json` | `data/reference_lasts.json` (the five court geometries as base lasts) |
| Flask SPA | FastAPI + React/TypeScript |
