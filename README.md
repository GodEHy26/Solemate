# SoleMate

**Custom shoes built from a 3D scan of your feet.**

SoleMate:

1. **Scans each foot in 3D** with a Face-ID style sweep in the browser: a top-down photo on a
   sheet of paper for scale, then an orbit around the foot guided by a progress ring.
2. **Builds a 3D foot contour** (shape-from-silhouette → mesh) and measures it: length, ball /
   heel / waist / toe widths, instep height, girths, footprint outline and cross-sections.
3. **Grades a custom last** from the measurements and lets the customer **configure every
   component**: outsole (rubber, blown rubber, gum, polyurethane, TPU), midsole (EVA, PU, e-TPU,
   supercritical foam, cork latex), upper (engineered knit, canvas, mesh, leather, suede, recycled
   textile), lining, insole (including a 3D-printed lattice from the scan) and laces.
4. **Sells everything as a preorder** with server-side pricing, Stripe Checkout, a privacy policy and preorder terms.

> The shoe line-up in `backend/app/data/shoes.json` is a placeholder. Edit that file when the real
> models are decided; nothing else needs to change. See `docs/CUSTOMIZATION.md`.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLModel (SQLite by default), OpenCV, NumPy, scikit-image, trimesh |
| Frontend | React 18, TypeScript, Vite, react-three-fiber / three.js, zustand |
| Tests | pytest (synthetic end-to-end scan), vitest |
| Ops | Docker Compose, GitHub Actions CI |

## Quick start

```bash
# backend (API on :8000)
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend (dev server on :5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Or from the repo root: `npm install && npm run setup && npm run dev`, or `./scripts/dev.sh`,
or `docker compose up --build` (web on http://localhost:8080).

### On a phone

The app is a mobile-first PWA: bottom tab bar, sticky price bar, installable to the home screen.
Phones require HTTPS for the camera and motion sensors, so use `npm run dev:phone` (self-signed
certificate on your Wi-Fi) or a tunnel such as `cloudflared tunnel --url http://localhost:5173`.
Publishing with a real domain is covered in `docs/DEPLOYMENT.md`.

## Tests

```bash
cd backend && . .venv/bin/activate && python -m pytest      # 83 tests
cd frontend && npm test && npm run typecheck && npm run build
```

The backend suite renders a synthetic foot through the same camera model as the reconstructor,
uploads the frames through the HTTP API, reconstructs, and checks the measurements, mesh files
and last specification. No real photos are required to run CI.

## Repository layout

```
backend/
  app/
    main.py, config.py, database.py, db_models.py, schemas.py
    api/            scans, profiles, catalog, orders
    services/
      scanning/     capture_plan, segmentation, cameras, visual_hull, scale, meshing,
                    measurements, sizing, reconstructor, pipeline
      fitting/      shoe_index (KD-tree from the IA), last_matcher
      catalog/      loader, pricing
    data/           components.json, shoes.json, reference_lasts.json
  tests/            unit + end-to-end tests, synthetic renders
frontend/
  src/
    lib/            api client, types, scan ring state machine, camera & orientation hooks
    components/     scan/ viewer/ configurator/ layout/
    pages/          Home, Scan, Profile, Catalog, Configurator, Checkout, Order
    store/          cart, foot profiles
docs/               ARCHITECTURE, SCAN_PIPELINE, CUSTOMIZATION, DEPLOYMENT, PAYMENTS, ROADMAP
```

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/scans/plan` | Capture poses and ring parameters |
| POST | `/api/scans` | Start a scan session (`side`, optional `paper_size`, `known_length_mm`) |
| POST | `/api/scans/{id}/frames` | Upload one frame (`image`, `yaw_deg`, `pitch_deg`, `kind`) |
| POST | `/api/scans/{id}/mesh` | Upload a depth-sensor mesh instead of photos |
| POST | `/api/scans/{id}/reconstruct` | Build the 3D model (background task) |
| GET | `/api/scans/{id}` | Status, coverage, profile id |
| GET | `/api/profiles/{id}` | Measurements, sizing, footprint, sections, warnings |
| GET | `/api/profiles/{id}/mesh.glb` · `.obj` | Download the foot mesh |
| GET | `/api/profiles/{id}/last-spec?shoe=` | Custom last specification |
| GET | `/api/catalog/shoes` · `/shoes/{slug}` · `/components` | Catalog |
| POST | `/api/catalog/price` | Validate and price a configuration |
| POST | `/api/orders` · GET `/api/orders/{id}` | Create a preorder (needs consent and both foot profiles) |
| POST | `/api/orders/{id}/checkout` · `/confirm` | Start Stripe payment · confirm it with Stripe |
| POST | `/api/stripe/webhook` | Signed Stripe events |
| GET | `/api/profiles/fit-check?left=&right=` | Both feet: warnings, confidence, size or size range |
| DELETE | `/api/profiles/{id}` | Delete a scan |
| GET | `/api/config` | Preorder wording and operator details |

Interactive docs: http://localhost:8000/docs

## How the scan works (short version)

Silhouettes from ~16–24 angles carve a voxel volume into the foot's visual hull; the sheet of paper
in the top-down photo fixes the scale; marching cubes turns the volume into a mesh; the mesh is
aligned (heel at the origin, toes along +X) and measured at standard last-making stations.
Details, limitations and the planned upgrades (real camera poses, learned segmentation, sensor
meshes) are in `docs/SCAN_PIPELINE.md`.

## License

MIT — see `LICENSE`.
