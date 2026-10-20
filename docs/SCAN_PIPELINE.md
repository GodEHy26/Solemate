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
| Classical segmentation | Fails on floors that match skin tone | Replace `extract_silhouette` with a learned segmenter (same signature) |
| Scale from one sheet of paper | ±2–3 % length error if the sheet is not flat | Detect the sheet in several frames; use a printed marker |

## Testing without photos

`backend/tests/synthetic.py` renders an ellipsoid "foot" through the same camera model and writes
JPEG frames plus a synthetic paper scene, so `tests/test_api.py` exercises upload → carve → mesh →
measurements → last spec end to end. Replace the ellipsoid with real frames under
`backend/tests/fixtures/` to turn these into regression tests on real data.
