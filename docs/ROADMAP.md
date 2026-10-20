# Roadmap

## Done in v2.0 (this scaffold)

- Monorepo: FastAPI backend, React/TypeScript frontend, Docker, CI.
- Face-ID style capture flow (ring, sectors, auto capture with motion sensors, manual fallback).
- Shape-from-silhouette reconstruction, paper-based metric scale, mesh export (GLB/OBJ).
- Foot measurements, size guide, custom last specification from graded reference lasts.
- Component catalog with materials, properties, colours, compatibility rules and pricing.
- Cart, checkout and order persistence (no payment yet).
- Test suites: 39 backend tests (synthetic end-to-end scan), 8 frontend tests.

## Next

1. **Real shoe line-up** — replace the placeholder models in `backend/app/data/shoes.json`, add product
   photos and per-model GLBs for the configurator preview.
2. **Accounts** — sign-in so foot profiles and orders follow the customer (currently localStorage).
3. **Payments** — Stripe Checkout on order creation; add shipping and tax lines.
4. **Pose estimation** — use ARKit/ARCore camera poses (native wrapper) or structure-from-motion so
   the carve uses real extrinsics instead of the ideal orbit rig.
5. **Learned segmentation** — a small foot/background segmenter for difficult floors.
6. **Both feet in one flow** and left/right asymmetry report.
7. **Manufacturing export** — last spec + cross-sections as a PDF/DXF for the workshop; printed
   insole STL generated from the footprint and arch region.
8. **Admin dashboard** — order queue, scan QA (view frames and hull), re-run reconstruction.
9. **Collect real scans** under `backend/tests/fixtures/` and turn the synthetic end-to-end test into a
   regression test against measured feet (tape measurements as ground truth).
