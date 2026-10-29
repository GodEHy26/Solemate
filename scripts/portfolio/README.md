# Portfolio images

Everything here runs on **your own computer** so the screenshots show real software on real hardware.

## 0. One-time setup (Mac, Linux or Windows)

```bash
git clone https://github.com/GodEHy26/Solemate && cd Solemate
npm install                      # root tools, including Playwright
npx playwright install chromium  # browser used for the screenshots
npm run setup                    # backend virtualenv + frontend packages
backend/.venv/bin/pip install matplotlib
```
On Windows use `backend\.venv\Scripts\python` wherever these steps say `backend/.venv/bin/python`.

## 1. App screenshots (12 PNGs)

Terminal 1:
```bash
npm run dev                      # API on :8000, web app on :5173
```
Terminal 2:
```bash
npm run portfolio:seed           # builds 4 demo scans through the real pipeline (~10 s)
npm run portfolio:shots          # saves portfolio-shots/01..12-*.png
```
Add `HEADED=1` before the second command to watch the browser do it. Once you have scanned your
own foot (section 4), add `REAL_PROFILE=<id from the profile page URL>` so shots 04 and 05 show
your foot instead of the test shape.

| File | What it shows |
|------|---------------|
| 01-home-desktop, 02-home-phone | Landing page on desktop and phone |
| 03-scan-start-phone | Start of the scan flow |
| 04-foot-profile-desktop | Full profile: 3D model, footprint, measurements, size |
| 05-foot-3d-viewer-desktop | Close-up of the 3D viewer |
| 06-scan-warning-desktop | A scan with a warning: size range and retake advice |
| 07-scan-blocked-phone | A blocked scan: no size, retake prompt |
| 08-catalog-desktop, 09-configurator-desktop, 10-configurator-phone | Shoes and component configurator |
| 11-checkout-with-warning-desktop | Checkout with the scan check and acknowledgement |
| 12-fit-guarantee-phone | Fit guarantee page |

## 2. Pipeline figures (6 PNGs)

```bash
npm run portfolio:figures                                   # synthetic test foot
backend/.venv/bin/python scripts/portfolio/pipeline_figures.py --mesh ~/Downloads/foot_left.glb   # your own scan for figs 4-5
```

| File | What it shows |
|------|---------------|
| fig-1-silhouettes | Orbit frames with the detected foot outline |
| fig-2-paper-scale | Finding the A4 sheet and converting to millimetres |
| fig-3-visual-hull | Voxels carved away as views are added (2 → 6 → 24) |
| fig-4-mesh | The resulting 3D mesh from three angles |
| fig-5-measurements | Footprint, width profile with landmarks, cross-section girths |
| fig-6-quality-checks | The automatic scan checks firing on bad scans and staying quiet on a clean one |

Figures made from the synthetic test foot say so in their title. Keep that label.

## 3. Terminal screenshots (take these yourself)

Run each, then screenshot the terminal window (Mac: Cmd+Shift+4 then Space; Windows: Win+Shift+S).

```bash
cd backend && .venv/bin/python -m pytest -q                       # whole suite passing
cd backend && .venv/bin/python -m pytest tests/test_scan_quality.py -v   # each named quality test
npm --prefix frontend test
git log --oneline --graph -15                                      # project history
```

## 4. Photos only you can take

These are the strongest images for a maker portfolio, because they show the thing working in the
physical world. Nothing in the repo can produce them.

1. **The setup:** you (or a friend's photo of you) scanning a real foot, with the sheet of paper on
   the floor and the phone held about 45 cm away.
2. **The phone mid-scan:** a phone screenshot of the capture ring filling up.
3. **Validation:** your real foot next to a tape measure or ruler, beside the app's measured length
   for the same foot. Note the difference in mm in the caption, good or bad.
4. **Before and after:** the original Sole-Mate IA (one photo → stock shoe) next to this version.
5. **Any physical work:** material samples (rubber vs PU outsole, knit vs canvas), a printed insole
   or last, a shoe teardown, sketches. A maker portfolio rewards physical making most.
