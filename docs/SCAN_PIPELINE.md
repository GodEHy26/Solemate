# 3D foot scan pipeline

The browser cannot reach a phone's depth sensor (TrueDepth / LiDAR are native-only), so the web
scan uses **shape-from-silhouette**: many photos from around the foot, each reduced to a
silhouette, carve a voxel volume into the *visual hull* of the foot. A sheet of paper in a
top-down photo supplies absolute scale. A native companion app can skip all of this and upload a
sensor mesh to the same endpoint.

## 1. Capture (frontend `ScanWizard`)

| Step | What happens |
|------|--------------|
| Intro | Choose foot, paper size (A4/Letter/A3), optional known length fallback |
| Top-down | Phone held flat above the foot on the paper; one frame, `kind=topdown`, `pitch=90` |
| Orbit | The Face-ID ring: 24 sectors of 15°. With motion sensors the device heading is mapped to a sector and a frame is auto-captured when the user holds steady in an uncovered sector. Without sensors the user taps once per ~15° step. |
| Finish | Allowed once ≥ 75 % of sectors are covered with no gap over 60° (server re-checks with a looser 50 % / 120° floor) |

Yaw convention: 0° looks at the toes, increasing counter-clockwise seen from above. Pitch is the
downward tilt (default 30°). `GET /api/scans/plan` publishes these numbers so client and server agree.

## 2. Silhouettes (`segmentation.py`)

Otsu threshold on luminance → polarity fixed by checking the frame border → open/close → largest
component near the centre → hole fill. If the result is implausible (< 2 % or > 70 % of the frame)
it retries on the saturation channel, then GrabCut. Frames are downscaled to 720 px first.

## 3. Cameras (`cameras.py`)

OpenCV pinhole model. Intrinsics from image size and an assumed horizontal FOV (65°).
Extrinsics from an **orbit rig**: camera on a sphere of radius 1 (unit-less) around a target just
above the floor, using the frame's yaw and pitch. This is an approximation of a hand-held sweep;
see "Known limitations".

## 4. Visual hull (`visual_hull.py`)

Isotropic voxel grid in a box around the origin (floor at z = 0). Every voxel centre is projected
into every view; voxels on background are carved, voxels seen by no camera are discarded, and the
largest connected blob is kept. Two passes: coarse (48³) to locate the foot, fine (128 on the long
axis) inside a padded box around it.

## 5. Scale (`scale.py`)

The top-down frame: detect the bright sheet (largest bright quad, convex hull repairs the bite
where the leg crosses the edge), warp it to a metric canvas (3 px/mm), segment the darker foot,
and measure its minimum-area rectangle → length and width in mm. The hull is scaled so its length
matches. Fallbacks: user-entered foot length (`medium` confidence) or an assumed 45 cm capture
distance (`low`).

## 6. Mesh (`meshing.py`)

Marching cubes (scikit-image) on the zero-padded occupancy → Taubin smoothing (trimesh) →
export `foot.glb` and `foot.obj`. The volume is cut at 34 % of foot length above the floor so the
lower leg does not enter the measurements.

## 7. Measurements (`measurements.py`)

1. Align: PCA on the footprint gives the long axis; the wider half is the toe end; heel to x = 0,
   floor to z = 0, footprint centred on y = 0.
2. Width and height profiles at 60 stations along the length.
3. Landmarks by window (fraction of length from heel): heel 0–20 %, waist 35–55 % (narrowest),
   instep 40–55 % (tallest), ball 55–80 % (widest), toes 85–100 %.
4. Girths: perimeter of the mesh cross-section at the ball, waist and instep stations.
5. Footprint outline polygon (mm) and per-station cross-sections for the UI.

Output: `FootMeasurements` (length, ball/heel/waist/toe widths, instep/ball/toe heights, three
girths, landmark positions, volume) plus sizing (`sizing.py`) and a custom last specification
(`fitting/last_matcher.py`).

## Alternative input: sensor meshes

`POST /api/scans/{id}/mesh` with a GLB/OBJ/PLY/STL in mm (or `units=cm|m|in`) voxelises the mesh
and runs steps 7+ unchanged, with `scale_confidence=high`. This is the hook for an ARKit/ARCore
companion app.

## Known limitations (v2.0) and what fixes them

| Limitation | Effect | Planned fix |
|---|---|---|
| Orbit rig assumes constant radius and exact yaw | Slight anisotropic distortion of the hull | Estimate real poses (ARKit/ARCore pose stream, or SfM such as COLMAP) and feed them to `carve` — the carving code already takes arbitrary `Camera`s |
| Visual hull cannot see concavities | Arch underside and the gap between toes are filled | Add the top-down silhouette as a view, multi-view stereo, or sensor meshes |
| Classical segmentation | Fails on floors that match skin tone (warned about when it shows; see Warnings) | Replace `segment` with a learned segmenter (same signature) |
| Scale from one sheet of paper | ±2–3 % length error if the sheet is not flat | Detect the sheet in several frames; use a printed marker |

## Warnings

Every scan gets a list of warnings and an overall confidence (`backend/app/services/scanning/quality.py`).
Each warning has a `code`, a `severity`, a plain-language `message` and a `fix`.

| Severity | What the customer sees | Ordering |
|----------|------------------------|----------|
| none | **high** confidence, one size | allowed |
| `warn` | **medium** confidence, a half-size range such as "9 to 9.5", with the reason | allowed after ticking "I understand the scan may be less accurate" |
| `block` | **low** confidence, no size, only the retake prompt | refused by the server |

### The checks

| Code | Severity | Trigger (threshold) | Message / fix |
|------|----------|---------------------|---------------|
| `incomplete_orbit` | warn | Usable orbit frames cover under **75 %** of the 24 sectors, or the largest gap between them is over **60°**. The server still refuses to build below 50 % / 120°. | "Part of your foot wasn't captured." / "Retake the scan from the {toe end, left side, heel end, right side}." The side is the centre of the largest gap. |
| `paper_not_found` | block | Scale came from a typed length or the assumed 45 cm distance, because no sheet of paper was found in the top-down photo. A sheet must not fill the frame and must be within **20 %** of the chosen paper's proportions. | "We couldn't find the paper." / "Retake the top-down photo with the whole sheet flat and visible." |
| `confusing_background` | warn | **25 %** or more of orbit frames needed the saturation or GrabCut fallback, or had no usable outline; or the outline area jumps by more than **1.5×** between neighbouring frames (within 40°) at least **2** times. Clean synthetic scans stay at or under 1.15×. Also attached to a failed scan when it explains the failure. | "Your floor may be confusing the scan." / "Retake on a plain floor that contrasts with your skin." |
| `measurements_disagree` | warn | The foot **width** measured in the paper photo and the widest point of the 3D model differ by more than **3 %**, after allowing one voxel for the model's grid size. | "Your measurements don't agree with each other." / "Please rescan." |
| `left_right_mismatch` | warn | Left and right foot lengths differ by more than **8 mm**. Checked for the pair (`GET /api/profiles/fit-check`), never blocks. | "Your feet measured N mm apart in length." / "A small difference is normal. Check both scans and rescan either foot if it looks wrong." |

**Why width, not length, for `measurements_disagree`.** The 3D model is scaled so that its length
equals the paper-photo length, so the two lengths agree by construction and comparing them would
never catch anything. Width is measured independently in both: from the paper photo's outline and
from the carved 3D shape. That makes it the honest cross-check of one measurement against another.

**Size ranges.** A range is the two half sizes that the exact chart value falls between, computed
for every size system. A pair is sized from the longer foot. See `services/fitting/fit_check.py`.

**Known gaps.** A floor almost exactly the colour of the skin can segment *consistently* wrong, so
neither background trigger fires. The width cross-check is the backstop there. All thresholds were
tuned on synthetic scans (`backend/tests/test_scan_quality.py`, `tests/synthetic_scenarios.py`)
so that a clean scan raises nothing. Re-tune them on real scans before relying on them.

### Capture direction

Yaw grows counter-clockwise seen from above, starting in front of the toes. The phone reports a
compass heading, which grows clockwise, so the client converts it (`relativeYaw` in
`frontend/src/lib/scanSession.ts`). Before this was fixed, auto-captured scans were mirrored.

## Testing without photos

`backend/tests/synthetic.py` renders an ellipsoid "foot" through the same camera model and writes
JPEG frames plus a synthetic paper scene, so `tests/test_api.py` exercises upload → carve → mesh →
measurements → last spec end to end. Replace the ellipsoid with real frames under
`backend/tests/fixtures/` to turn these into regression tests on real data.
