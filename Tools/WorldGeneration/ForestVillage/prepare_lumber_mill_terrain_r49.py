"""Generate LumberMill-R49 contour-matched logging road, graded mill yard, Landscape edit-layer maps,
expanded 3-road RoadMix/Leaves/Wear fields, and updated meadow/near-grass masks.

Extends RoadUpgrade-R48 seamlessly:
- Preserves 100% of existing gate-road, quarry-road, village, ponds, quarry, cliffs, and reference path.
- Adds organic contour-matched logging road from village gate junction (88.8, 314.0) around pond[0] to
  the Lumber Mill yard centered at (154.0, 62.0), Z = +11.00 m.
- Expands RoadWearField (1024x512), RoadMixField/TrackFrames/ShoulderLeafField (2048x1024) to cover
  ORIGIN=(-480, 24), SIZE=(704, 352) so all 3 roads + Lumber Mill yard share the R48 PBR road shader
  on BOTH M_ForestReferenceMesh (outer tiles) and M_ForestVillageLandscape (inner Landscape).
"""
import csv
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import CubicSpline
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, maximum_filter
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from continuous_meadow import bake as bake_meadow
from generate_slope_grass import WEST, SOUTH, CELL, TILES, ROWS, COLS, site_hash, grid_at
from prepare_gate_road_surface import smooth
from prepare_road_relief_r48 import fbm_field, load_road, road_coords, warped_noise

# Expanded world field box covering gate-road, quarry-road, lumber-road AND Lumber Mill yard!
FIELD_ORIGIN = (-480.0, 24.0)
FIELD_SIZE = (704.0, 352.0)
FIELD_W, FIELD_H = 2048, 1024
FIELD_STEP_X = FIELD_SIZE[0] / FIELD_W  # 0.34375 m/px
FIELD_STEP_Y = FIELD_SIZE[1] / FIELD_H  # 0.34375 m/px
WEAR_W, WEAR_H = 1024, 512
WEAR_STEP_X = FIELD_SIZE[0] / WEAR_W    # 0.6875 m/px
WEAR_STEP_Y = FIELD_SIZE[1] / WEAR_H    # 0.6875 m/px

# Lumber Mill graded yard parameters (world metres)
YARD_CENTER = (154.0, 62.0)
YARD_HALF = (17.5, 13.5)       # 35m x 27m flat inner working platform
YARD_CORNER_R = 7.2            # organic rounded yard corners
YARD_DATUM_M = 11.00           # balanced cut/fill terrace elevation (+11.00 m)
YARD_YAW_DEG = 0.0             # world-aligned (+Y faces incoming logging road!)

SEED = 490317


def yard_sdf(x, y, cx=YARD_CENTER[0], cy=YARD_CENTER[1], hx=YARD_HALF[0], hy=YARD_HALF[1], r=YARD_CORNER_R):
    """Signed distance (m) to the rounded-rectangle Lumber Mill terrace (<=0 inside flat yard)."""
    qx = np.abs(x - cx) - (hx - r)
    qy = np.abs(y - cy) - (hy - r)
    outside = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    return outside + inside - r


def trace_contour_lumber_road(z_m: np.ndarray, pond_shore: np.ndarray):
    """Build an organic, contour-hugging, non-straight logging road from gate junction to Lumber Mill yard."""
    # Hand-surveyed anchor guide following user's red line around pond[0] (133, 303) & hillside contours
    # First point joins gate-road tangentially at (88.85, 314.2); last enters Lumber Mill gate at (154.0, 74.5)
    anchors = np.array([
        [88.85, 314.20],  # T-junction with gate-road outside village west entrance
        [95.80, 306.80],  # sweeping gently NW out of gate-road
        [106.50, 297.20], # curving cleanly southwest of pond[0] (dry margin > 15m)
        [117.00, 286.00], # clearing pond shore along gentle rise
        [126.20, 271.50], # organic contour curve
        [134.20, 255.00], # approaching Y=252m Landscape border smoothly
        [139.20, 238.00], # inside L_ForestPathForest Landscape, gentle S-bend
        [141.50, 219.00], # hugging natural hillside contour
        [146.50, 200.00], # subtle climb along ridge shoulder
        [152.80, 181.00], # organic rightward bend matching red curve
        [158.20, 162.00], # following upper contour shelf
        [161.00, 143.00], # gentle broad outer arc (matches user red trail apex)
        [159.40, 124.00], # easing smoothly back toward lumber yard
        [155.20, 105.00], # soft counter-curve on final approach
        [153.60, 88.00],  # approaching Lumber Mill entrance gate
        [154.00, 73.00],  # straight arrival into Lumber Mill north gate
    ], dtype=np.float64)

    # Parameterize by cumulative chord length and sample cubic spline at 0.5m steps
    t_anc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(anchors, axis=0), axis=1))]
    cs_x = CubicSpline(t_anc, anchors[:, 0], bc_type="natural")
    cs_y = CubicSpline(t_anc, anchors[:, 1], bc_type="natural")
    n_dense = int(round(t_anc[-1] / 0.5)) + 1
    ts = np.linspace(0.0, t_anc[-1], n_dense)
    pts = np.column_stack((cs_x(ts), cs_y(ts)))

    # Add gentle non-periodic organic meander (zero at endpoints & pond clearance!) and contour-relax!
    sta = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    total_len = float(sta[-1])
    tang = np.gradient(pts, axis=0)
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-6)
    nrm = np.column_stack((-tang[:, 1], tang[:, 0]))

    # Natural multi-wavelength non-straight contour meander (±2.1m, faded smoothly to 0 at endpoints)
    end_env = smooth(0.0, 18.0, sta) * smooth(0.0, 20.0, total_len - sta)
    # Keep extra calm around pond[0] (s ~ 22..55 m)
    pond_d = np.hypot(pts[:, 0] - 133.0, pts[:, 1] - 303.0)
    pond_env = smooth(15.0, 26.0, pond_d)
    meander = (
        1.45 * np.sin(sta * 0.068 + 0.35)
        + 0.85 * np.cos(sta * 0.131 - 1.05)
        + 0.38 * np.sin(sta * 0.227 + 2.15)
    ) * end_env * pond_env
    pts = pts + nrm * meander[:, None]

    # Mild contour-hugging nudge: nudge road slightly down/up-slope toward local iso-contour smoothness
    z_smooth = gaussian_filter(z_m, 3.0)
    gy_s, gx_s = np.gradient(z_smooth)
    for _ in range(3):
        z_along = grid_at(z_smooth, pts[:, 0], pts[:, 1])
        z_target = gaussian_filter(z_along, sigma=14.0)
        # Keep endpoints fixed at exact gate road & yard datum
        z_target[0] = z_along[0]
        z_target[-1] = YARD_DATUM_M
        err = z_along - z_target
        gxp = grid_at(gx_s, pts[:, 0], pts[:, 1])
        gyp = grid_at(gy_s, pts[:, 0], pts[:, 1])
        g2 = gxp * gxp + gyp * gyp + 0.04
        # Project contour correction perpendicular to road tangent only (never bunches stations)
        tang = np.gradient(pts, axis=0)
        tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-6)
        nrm = np.column_stack((-tang[:, 1], tang[:, 0]))
        g_lat = gxp * nrm[:, 0] + gyp * nrm[:, 1]
        shift = np.clip(-0.35 * err * g_lat / g2, -0.45, 0.45) * end_env * pond_env
        pts += nrm * shift[:, None]
        pts[:, 0] = gaussian_filter(pts[:, 0], sigma=2.2)
        pts[:, 1] = gaussian_filter(pts[:, 1], sigma=2.2)
        pts[0] = anchors[0]
        pts[-1] = anchors[-1]

    # Re-parameterize uniformly at exact 0.50 m arc-length intervals
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    n_out = int(round(arc[-1] / 0.5)) + 1
    s_uni = np.linspace(0.0, arc[-1], n_out)
    out_x = np.interp(s_uni, arc, pts[:, 0])
    out_y = np.interp(s_uni, arc, pts[:, 1])

    # Compute smoothly graded road centerline elevation Z_road(s) connecting gate Z to Yard Datum (+11.00 m)
    z_nat = grid_at(z_m, out_x, out_y)
    # Smoothly filter longitudinal elevation while strictly pinning start (gate-road) & end (yard datum)
    z_grade = gaussian_filter(z_nat, sigma=18.0)
    w_start = 1.0 - smooth(0.0, 14.0, s_uni)
    w_end = smooth(arc[-1] - 38.0, arc[-1] - 2.0, s_uni)
    z_grade = z_grade * (1.0 - w_start) + z_nat[0] * w_start
    z_grade = z_grade * (1.0 - w_end) + YARD_DATUM_M * w_end
    # Iteratively enforce wagon-friendly maximum longitudinal grade <= 11.5% along the entire climb!
    max_dz = 0.115 * float(s_uni[1] - s_uni[0])
    for _ in range(900):
        dz = np.diff(z_grade)
        excess = dz - np.clip(dz, -max_dz, max_dz)
        if np.max(np.abs(excess)) < 1e-4:
            break
        z_grade[:-1] += 0.45 * excess
        z_grade[1:] -= 0.45 * excess
        z_grade[0] = z_nat[0]
        z_grade[-1] = YARD_DATUM_M
    # Gentle polish while honoring endpoints & grade cap
    z_grade = gaussian_filter(z_grade, sigma=4.0)
    z_grade = z_grade * (1.0 - (1.0 - smooth(0.0, 5.0, s_uni))) + z_nat[0] * (1.0 - smooth(0.0, 5.0, s_uni))
    z_grade = z_grade * (1.0 - smooth(arc[-1] - 7.0, arc[-1], s_uni)) + YARD_DATUM_M * smooth(arc[-1] - 7.0, arc[-1], s_uni)
    for _ in range(300):
        dz = np.diff(z_grade)
        excess = dz - np.clip(dz, -max_dz, max_dz)
        if np.max(np.abs(excess)) < 1e-4:
            break
        z_grade[:-1] += 0.45 * excess
        z_grade[1:] -= 0.45 * excess
        z_grade[0] = z_nat[0]
        z_grade[-1] = YARD_DATUM_M

    out_pts = np.column_stack((out_x, out_y, z_grade))
    ds = np.maximum(np.diff(s_uni), 1e-4)
    long_grade = np.abs(np.diff(z_grade) / ds)
    min_pond_d = float(np.hypot(out_x - 133.0, out_y - 303.0).min())
    return out_pts, {
        "length_m": round(float(arc[-1]), 2),
        "points": int(len(out_pts)),
        "start_xyz": [round(float(v), 2) for v in out_pts[0]],
        "end_xyz": [round(float(v), 2) for v in out_pts[-1]],
        "max_longitudinal_grade": round(float(long_grade.max()), 4),
        "mean_longitudinal_grade": round(float(long_grade.mean()), 4),
        "min_pond0_clearance_m": round(min_pond_d, 2),
    }


def save_road_csv(path: Path, pts_xyz: np.ndarray):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["x_m", "y_m", "z_m"])
        for x, y, z in pts_xyz:
            w.writerow([f"{x:.3f}", f"{y:.3f}", f"{z:.3f}"])


def build_terrain_and_fields(r48_root: Path, out_root: Path):
    base_ter = r48_root / "Terrain"
    ter_dir = out_root / "Terrain"
    rm_dir = out_root / "RoadMix"
    leaves_dir = rm_dir / "Leaves"
    ter_dir.mkdir(parents=True, exist_ok=True)
    leaves_dir.mkdir(parents=True, exist_ok=True)

    # Copy authoritative upstream terrain artifacts from RoadUpgrade-R48
    for fname in (
        "reference.f32", "quarry-clear.u8", "gate-road.csv", "quarry-road.csv",
        "hill.json", "settlement.i16", "cliff-mask.u8", "cliff-landscape-delta.i16",
        "ledge-sites.bin", "cliff-exposure.json",
        "T_CliffField.png", "T_CliffColor.png", "T_CliffNormal.png", "T_CliffARH.png",
        "T_ContinuousMeadowBlades.png", "T_ContinuousMeadowNormal.png",
    ):
        src_f = base_ter / fname
        if src_f.is_file():
            shutil.copy2(src_f, ter_dir / fname)
    for sub in ("Grass", "Turf"):
        if (base_ter / sub).is_dir():
            shutil.copytree(base_ter / sub, ter_dir / sub, dirs_exist_ok=True)
    # Reuse already-built R48 PBR road & debris color/normal/surface atlases verbatim (0 extra downloads!)
    for fname in ("T_StonyColor.png", "T_StonyNormal.png", "T_StonyARH.png",
                  "T_TireColor.png", "T_TireNormal.png", "T_TireARH.png"):
        src_f = r48_root / "RoadMix" / fname
        if src_f.is_file():
            shutil.copy2(src_f, rm_dir / fname)
    for fname in ("T_ShoulderLeafColor.png", "T_ShoulderLeafSurface.png"):
        src_f = r48_root / "RoadMix/Leaves" / fname
        if src_f.is_file():
            shutil.copy2(src_f, leaves_dir / fname)

    rng = np.random.default_rng(SEED)
    z0_cm = np.fromfile(base_ter / "region.i16", "<i2").reshape(1025, 1025).astype(np.float32)
    z0 = z0_cm * 0.01
    paint = np.fromfile(base_ter / "paint.rg8", "u1").reshape(1025, 1025, 2).copy()
    cliff = np.fromfile(base_ter / "cliff-mask.u8", "u1").reshape(1025, 1025).astype(np.float32) / 255.0
    quarry_u8 = np.fromfile(base_ter / "quarry-clear.u8", "u1").reshape(1025, 1025).astype(np.float32) / 255.0
    pond_wet = np.fromfile(base_ter / "Grass/pond_wet.u8", "u1").reshape(4097, 4097)
    pond_shore = np.fromfile(base_ter / "Grass/pond_shore.u8", "u1").reshape(1025, 1025).astype(np.float32) / 255.0
    pond_1m = maximum_filter(pond_wet, size=5)[::4, ::4].astype(np.float32) / 255.0
    hill = json.loads((base_ter / "hill.json").read_text(encoding="utf-8-sig"))
    vx, vy = hill["site_min_m"]
    cx_v, cy_v = hill["village_center_m"]
    layout_path = Path(__file__).resolve().parents[3] / "SourceAssets/TemperateHillsVillage/layout.json"
    ex_v, ey_v = json.loads(layout_path.read_text(encoding="utf-8-sig"))["surface_extent_m"]

    # 1) Trace contour-matched logging road and save lumber-road.csv
    lumber_xyz, road_stats = trace_contour_lumber_road(z0, pond_shore)
    save_road_csv(ter_dir / "lumber-road.csv", lumber_xyz)
    print("Lumber road stats:", json.dumps(road_stats))

    # 2) Grade 1m terrain for BOTH logging roadbed AND Lumber Mill yard platform!
    yy, xx = np.mgrid[SOUTH:SOUTH + 1025, WEST:WEST + 1025].astype(np.float32)

    # Protection masks (never disturb village, ponds, quarry, or original gate-road junction!)
    town_rect = np.hypot(
        np.maximum.reduce([vx - xx, xx - (vx + 118.0), np.zeros_like(xx)]),
        np.maximum.reduce([vy - yy, yy - (vy + 145.0), np.zeros_like(yy)]),
    )
    lx_v, ly_v = np.abs(cy_v - yy), np.abs(xx - cx_v)
    town_oct = np.maximum.reduce([lx_v - ex_v, ly_v - ey_v, (lx_v + ly_v - ex_v - ey_v + 6.0) * 0.70710678])
    town_safe = smooth(1.0, 7.0, np.minimum(town_rect, np.maximum(0.0, town_oct)))
    pond_safe = (1.0 - smooth(0.02, 0.45, pond_shore)) * (1.0 - smooth(0.0, 0.15, pond_1m))
    quarry_safe = 1.0 - smooth(0.10, 0.75, quarry_u8)
    safe_1m = town_safe * pond_safe * quarry_safe

    # Roadbed cross-level grading + organic cut-fill banks along lumber-road
    l_pts, l_sta, l_tang, l_curv = load_road(ter_dir, "lumber")
    l_dist, l_lat, l_s, l_tx, l_ty, l_kcurv, l_len = road_coords(l_pts, l_sta, l_tang, l_curv, xx, yy)
    l_tree = cKDTree(l_pts)
    _, l_idx = l_tree.query(np.column_stack((xx.ravel(), yy.ravel())))
    l_idx = l_idx.reshape(xx.shape)
    z_road_target = lumber_xyz[l_idx, 2].astype(np.float32)

    n_bank = warped_noise(rng, xx, yy, 11.0, 2.5, ((16.0, 0.55), (7.0, 0.30), (3.0, 0.15)))
    n_rut = warped_noise(rng, xx, yy, 9.0, 2.0, ((14.0, 0.50), (6.0, 0.32), (2.5, 0.18)))
    n_lat = fbm_field(rng, xx, yy, [(18.0, 0.65), (7.5, 0.35)])

    # Seamless start blend at gate-road junction (s=0..10m); roadbed width ~2.3m half-width + smooth 9.5m cut/fill blend
    road_start_fade = smooth(1.5, 11.0, l_s)
    road_end_fade = 1.0 - smooth(l_len - 10.0, l_len + 2.0, l_s)
    bank_reach = 9.5 + 2.2 * n_bank
    w_road = (1.0 - smooth(2.35, 2.35 + np.maximum(5.0, bank_reach), l_dist)) * road_start_fade * smooth(0.0, 4.0, l_len - l_s + 6.0)

    # Subtle realistic roadbed cross-crown (+3.5cm) + twin wheel ruts (-5.5cm) + uphill ditch (-6cm)
    lat_sh = l_lat - 0.18 * n_lat
    rut_l = np.exp(-((lat_sh - 0.78) / 0.46) ** 2)
    rut_r = np.exp(-((lat_sh + 0.78) / 0.46) ** 2)
    wear_a = np.clip(0.72 + 0.25 * n_rut, 0.30, 1.20)
    road_micro = (
        -0.058 * wear_a * (rut_l + rut_r)
        + 0.036 * np.exp(-(lat_sh / 0.50) ** 2)
        + 0.045 * n_rut * (1.0 - smooth(2.0, 4.5, l_dist))
    ) * (1.0 - smooth(2.8, 5.5, l_dist)) * road_start_fade * road_end_fade

    # Lumber Mill graded yard terrace centered at (154, 62), Z = +11.00 m
    y_sdf = yard_sdf(xx, yy)
    yard_skirt = 21.0 + 4.0 * n_bank
    w_yard = 1.0 - smooth(0.5, 0.5 + np.maximum(15.0, yard_skirt), y_sdf)
    # Keep inner yard super flat
    z_yard_target = np.full_like(z0, YARD_DATUM_M, dtype=np.float32)

    # Combine road target & yard target smoothly (yard dominates smoothly inside yard!)
    w_total = np.clip(np.maximum(w_road, w_yard), 0.0, 1.0) * safe_1m
    z_blend_target = (z_road_target * w_road * (1.0 - w_yard) + z_yard_target * w_yard) / np.maximum(w_road * (1.0 - w_yard) + w_yard, 1e-5)
    z_graded = z0 * (1.0 - w_total) + z_blend_target * w_total + road_micro * safe_1m

    # Smooth any tiny kinks along cut/fill hinge while keeping inner flat yard & untouched terrain exact!
    z_polish = gaussian_filter(z_graded, sigma=2.0)
    hinge_w = smooth(0.02, 0.25, w_total) * (1.0 - smooth(0.86, 0.99, w_yard)) * safe_1m
    z_final = z_graded * (1.0 - 0.72 * hinge_w) + z_polish * (0.72 * hinge_w)
    # Lock exact flat inner building/working yard (y_sdf <= -0.5 m) to YARD_DATUM_M!
    inner_lock = 1.0 - smooth(-1.2, 1.0, y_sdf)
    z_final = z_final * (1.0 - inner_lock) + YARD_DATUM_M * inner_lock

    # Compute exact integer cm heightmap & delta
    z_new_cm = np.rint(z_final * 100.0).astype("<i2")
    delta_cm = (z_new_cm.astype(np.int32) - z0_cm.astype(np.int32)).astype("<i2")
    # Strict zero outside active corridor/yard mask so untouched world has 0.00 cm drift!
    active_1m = (w_total > 0.002) | (l_dist < 16.0) | (y_sdf < 22.0)
    delta_cm[~active_1m] = 0
    z_new_cm = (z0_cm.astype(np.int32) + delta_cm.astype(np.int32)).astype("<i2")
    z_new_m = z_new_cm.astype(np.float32) * 0.01

    z_new_cm.tofile(ter_dir / "region.i16")
    delta_cm.tofile(ter_dir / "lumber-terrain-delta.i16")

    # Extract exact 505x505 Landscape Edit Layer height delta inside [-252..252, -252..252]!
    # Grid indices: ix = X - WEST = X + 624, iy = Y - SOUTH = Y + 320
    # X=-252..252 -> ix=372..876 (505); Y=-252..252 -> iy=68..572 (505)
    ls_delta_i16 = delta_cm[68:573, 372:877].copy()
    ls_delta_i16.tofile(ter_dir / "lumber-landscape-delta.i16")
    # Also update reference.f32 inside [-252..252] so outer tiles match Y=+252m seam to 0.00 cm!
    ref_arr = np.fromfile(ter_dir / "reference.f32", "<f4").copy()
    ref_arr[:505 * 505] += ls_delta_i16.ravel().astype(np.float32)
    ref_arr.tofile(ter_dir / "reference.f32")

    # 3) Compute road + Lumber Mill yard paint mask (1025x1025) for BOTH outer tiles (paint.rg8) & Landscape (C_LayerInfo)!
    l_road_paint = (1.0 - smooth(2.05, 3.35 + 0.30 * n_rut, l_dist)) * smooth(0.0, 2.5, l_s + 1.5) * safe_1m
    l_yard_paint = (1.0 - smooth(-0.8, 3.2 + 0.65 * n_bank, y_sdf)) * safe_1m
    l_dirt_1m = np.clip(np.maximum(l_road_paint, l_yard_paint), 0.0, 1.0)

    # Update paint.rg8 R channel (dirt/road weight) — maximum with existing paint (preserves village, gate, quarry!)
    paint_u8 = np.rint(l_dirt_1m * 255.0).clip(0, 255).astype("u1")
    paint[:, :, 0] = np.maximum(paint[:, :, 0], paint_u8)
    paint.tofile(ter_dir / "paint.rg8")

    # Extract 505x505 Landscape C_LayerInfo weight overlay inside [-252..252]!
    ls_paint_u8 = paint_u8[68:573, 372:877].copy()
    ls_paint_u8.tofile(ter_dir / "lumber-landscape-paint.u8")

    # Also update Grass/study_dirt_2m.u8 (253x253 inside [-252..252] step 2m) so bake_meadow clears grass on Landscape road & yard!
    study_dirt_path = ter_dir / "Grass/study_dirt_2m.u8"
    if study_dirt_path.is_file():
        sd = np.fromfile(study_dirt_path, "u1").reshape(253, 253).copy()
        sd_new = maximum_filter(ls_paint_u8, size=3)[::2, ::2]
        np.maximum(sd, sd_new).tofile(study_dirt_path)

    # Clear near_grass.u8 (TILES x TILES x ROWS x COLS packed mask) inside Lumber Mill yard & lumber road core!
    near_grass_path = ter_dir / "Grass/near_grass.u8"
    near_removed = 0
    if near_grass_path.is_file():
        ng = np.fromfile(near_grass_path, "u1").reshape(TILES, TILES, ROWS, COLS).copy()
        clear_grid = np.clip(np.maximum(l_dirt_1m, 1.0 - smooth(0.5, 3.8, y_sdf)), 0.0, 1.0)
        jj, ii = np.indices((ROWS, COLS), dtype="u4")
        for tj in range(TILES):
            for ti in range(TILES):
                if clear_grid[tj * 16:(tj + 1) * 16 + 1, ti * 16:(ti + 1) * 16 + 1].max() < 0.15:
                    continue
                ids = ((tj * TILES + ti) * ROWS + jj) * COLS + ii
                h = site_hash(ids)
                gx_p = WEST + CELL * (ti + (ii + 0.25 + 0.5 * (jj % 2) + ((h & 255) / 255.0 - 0.5) * 0.20) / COLS)
                gy_p = SOUTH + CELL * (tj + (jj + 0.5 + (((h >> 8) & 255) / 255.0 - 0.5) * 0.20) / ROWS)
                rem = (ng[tj, ti] != 0) & (grid_at(clear_grid, gx_p, gy_p) > 0.22)
                near_removed += int(rem.sum())
                ng[tj, ti][rem] = 0
        ng.tofile(near_grass_path)
    print(f"Cleared {near_removed} near-grass instances on lumber road & mill yard")

    # Re-bake continuous meadow & fine grass onto updated heightmap + lumber road/yard clearing!
    cliff_ref = r48_root.parent / "CliffExposure-R35"
    meadow_count = bake_meadow(cliff_ref, ter_dir, z_new_cm.astype(np.float32), paint)
    # Apply exact lumber road & yard grass suppression onto T_ContinuousMeadowField.png (handles Landscape [-252..252] too!)
    cm_im = np.asarray(Image.open(ter_dir / "T_ContinuousMeadowField.png").convert("RGBA"), dtype=np.float32) / 255.0
    clear_1025 = np.clip(np.maximum(l_dirt_1m, 1.0 - smooth(-0.5, 3.0, y_sdf)), 0.0, 1.0)
    clear_1024 = 0.25 * (clear_1025[:-1, :-1] + clear_1025[1:, :-1] + clear_1025[:-1, 1:] + clear_1025[1:, 1:])
    cm_im[:, :, 0] *= (1.0 - smooth(0.10, 0.72, clear_1024))
    Image.fromarray(np.rint(cm_im * 255.0).clip(0, 255).astype("u1")).save(ter_dir / "T_ContinuousMeadowField.png")
    fine = np.fromfile(ter_dir / "meadow-fine.f32", "<f4").reshape(-1, 8)
    fpx, fpy = fine[:, 0] * 0.01, fine[:, 1] * 0.01
    rng_m = np.random.default_rng(237890)
    keep_fine = rng_m.random(len(fpx)) >= smooth(0.30, 0.88, grid_at(cliff, fpx, fpy))
    # Also ensure zero fine meadow clumps poke inside the Lumber Mill yard or roadbed
    keep_fine &= (yard_sdf(fpx, fpy) > 2.5) & (grid_at(l_dirt_1m, fpx, fpy) < 0.20)
    fine[keep_fine].tofile(ter_dir / "meadow-fine.f32")

    # 4) Build Expanded 3-Road + Yard High-Res Fields (2048x1024, ORIGIN=(-480, 24), SIZE=(704, 352))!
    # A) Expanded T_RoadWearField (1024x512)
    wy_i, wx_i = np.indices((WEAR_H, WEAR_W), dtype=np.float32)
    wx = FIELD_ORIGIN[0] + (wx_i + 0.5) * WEAR_STEP_X
    wy = FIELD_ORIGIN[1] + (wy_i + 0.5) * WEAR_STEP_Y
    w_pts_flat = np.column_stack((wx.ravel(), wy.ravel()))
    w_core = np.zeros_like(wx)
    w_quarry = np.zeros_like(wx)
    w_sample = np.zeros_like(wx)
    for rfile in ("gate-road", "quarry-road", "lumber-road"):
        rline = np.loadtxt(ter_dir / f"{rfile}.csv", delimiter=",", skiprows=1)[:, :2]
        if rfile == "gate-road":
            rline = rline[::-1]
        chain = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(rline, axis=0), axis=1))]
        d, idx = cKDTree(rline).query(w_pts_flat)
        d = d.reshape(wx.shape)
        idx = idx.reshape(wx.shape)
        sta = chain[idx]
        hd = np.gradient(rline, axis=0)
        hd /= np.maximum(np.linalg.norm(hd, axis=1, keepdims=True), 0.001)
        side = hd[idx, 0] * (wy - rline[idx, 1]) - hd[idx, 1] * (wx - rline[idx, 0])
        width = 1.95 + 0.38 * np.sin(sta * 0.14 + np.sign(side) * 1.4) + 0.22 * np.sin(0.41 * wx + 0.21 * wy)
        end_w = smooth(0.0, 2.0, sta) if rfile != "lumber-road" else (smooth(0.0, 1.5, sta + 1.0) * smooth(0.0, 2.0, chain[-1] - sta + 3.0))
        wear = (1.0 - smooth(width - 0.55, width + 1.25, d)) * end_w
        w_core = np.maximum(w_core, wear)
        if rfile == "gate-road":
            w_sample = smooth(9.0, 11.0, sta) * (1.0 - smooth(37.0, 39.0, sta)) * (1.0 - smooth(4.0, 5.5, d))
        elif rfile == "quarry-road":
            w_quarry = smooth(chain[-1] - 75.0, chain[-1] - 8.0, sta) * (1.0 - smooth(4.0, 7.0, d))
    # Include the graded Lumber Mill working yard inside T_RoadWearField so it gets crisp compacted earth/gravel finish!
    w_yard_wear = 1.0 - smooth(-0.6, 3.0, yard_sdf(wx, wy))
    w_core = np.maximum(w_core, w_yard_wear)
    w_macro = np.clip(0.5 + 0.25 * np.sin(wx * 0.113 + wy * 0.074) + 0.15 * np.sin(wy * 0.29 - wx * 0.09) + 0.10 * np.cos(wy * 0.57 + wx * 0.25), 0, 1)
    Image.fromarray(np.rint(np.stack([w_core, w_quarry, w_sample, w_macro], axis=-1) * 255.0).clip(0, 255).astype("u1")).save(rm_dir / "T_RoadWearField.png")

    # B) Expanded 2048x1024 Topology Fields (RoadMixField + TrackFrames + ShoulderLeafField)
    fy_i, fx_i = np.indices((FIELD_H, FIELD_W), dtype=np.float32)
    fx = FIELD_ORIGIN[0] + (fx_i + 0.5) * FIELD_STEP_X
    fy = FIELD_ORIGIN[1] + (fy_i + 0.5) * FIELD_STEP_Y

    lx_f, ly_f = np.abs(cy_v - fy), np.abs(fx - cx_v)
    ext_f = smooth(0.20, 2.45, np.maximum.reduce([lx_f - ex_v, ly_f - ey_v, (lx_f + ly_f - ex_v - ey_v + 6.0) * 0.70710678]))
    q_f = grid_at(quarry_u8, fx, fy)
    w_f = map_coordinates(pond_wet.astype(np.float32) / 255.0, [(fy - SOUTH) * 4.0, (fx - WEST) * 4.0], order=1, mode="nearest")
    ext_f *= (1.0 - smooth(0.18, 0.85, q_f)) * (1.0 - smooth(0.02, 0.38, w_f))

    gy_n, gx_n = np.gradient(gaussian_filter(z_new_m, 1.2))
    gx_f = grid_at(gx_n, fx, fy)
    gy_f = grid_at(gy_n, fx, fy)
    slope_f = np.hypot(gx_f, gy_f)
    cliff_f = grid_at(cliff, fx, fy)
    lap_z = gaussian_filter(z_new_m, 2.2) - gaussian_filter(z_new_m, 0.8)
    concav_f = np.clip(grid_at(lap_z, fx, fy) * 8.0, 0.0, 1.0)

    nf_macro = warped_noise(rng, fx, fy, 18.0, 4.0, ((26.0, 0.52), (11.0, 0.32), (4.5, 0.16)))
    nf_edge_l = warped_noise(rng, fx, fy, 9.0, 2.2, ((13.0, 0.45), (5.2, 0.35), (1.9, 0.20)))
    nf_edge_r = warped_noise(rng, fx + 31.7, fy - 19.3, 9.5, 2.3, ((12.0, 0.45), (4.8, 0.35), (1.8, 0.20)))
    nf_rut = warped_noise(rng, fx, fy, 7.5, 1.8, ((16.0, 0.42), (6.0, 0.36), (2.1, 0.22)))
    nf_weave = fbm_field(rng, fx, fy, [(20.0, 0.62), (8.0, 0.38)])
    nf_detail = fbm_field(rng, fx, fy, [(3.2, 0.55), (1.2, 0.45)])

    lane_f = np.zeros_like(fx)
    gravel_f = np.zeros_like(fx)
    roots_f = np.zeros_like(fx)
    rut_f = np.zeros_like(fx)
    crown_f = np.zeros_like(fx)
    moist_f = np.zeros_like(fx)
    cut_toe_f = np.zeros_like(fx)
    tx_best = np.ones_like(fx)
    ty_best = np.zeros_like(fx)
    best_prox = np.zeros_like(fx)

    roads = {name: load_road(ter_dir, name) for name in ("gate", "quarry", "lumber")}
    for name, (pts, sta, tang, curv) in roads.items():
        dist, lat, s, tx, ty, kcurv, total_len = road_coords(pts, sta, tang, curv, fx, fy)
        cap = smooth(0.0, 2.2, s) * smooth(0.0, 2.2, total_len - s)
        if name == "lumber":
            cap = smooth(0.0, 1.2, s + 0.8) * smooth(0.0, 2.2, total_len - s + 4.0)
        quarry_grad = smooth(total_len - 150.0, total_len - 12.0, s) if name == "quarry" else np.zeros_like(s)
        gate_grad = (1.0 - smooth(15.0, 85.0, s)) if name == "gate" else np.zeros_like(s)
        lumber_grad = np.ones_like(s) if name == "lumber" else np.zeros_like(s)

        edge_n = np.where(lat >= 0.0, nf_edge_l, nf_edge_r)
        road_w = 3.25 + 0.52 * edge_n + 0.35 * quarry_grad + 0.22 * gate_grad - 0.12 * lumber_grad
        band = (1.0 - smooth(road_w - 0.35, road_w + 1.85 + 0.45 * nf_detail, dist)) * cap
        lane_f = np.maximum(lane_f, band)

        # Flow-aligned twin wheel ruts (heavier logging wagon ruts on lumber-road!)
        lat_w = lat - 0.22 * nf_weave
        rl = np.exp(-((lat_w - 0.78) / 0.36) ** 2)
        rr = np.exp(-((lat_w + 0.78) / 0.36) ** 2)
        rut_mod = np.clip(0.68 + 0.34 * nf_rut + 0.20 * quarry_grad + 0.14 * lumber_grad, 0.18, 1.0)
        rut_here = np.clip((rl + rr) * rut_mod * (1.0 - smooth(2.2, 3.2, dist)) * cap, 0.0, 1.0)
        rut_f = np.maximum(rut_f, rut_here)

        # Center grassy crown strip
        cr = np.exp(-(lat_w / 0.42) ** 2) * np.clip(0.68 - 0.32 * nf_rut - 0.42 * quarry_grad - 0.15 * gate_grad, 0.0, 1.0) * cap
        crown_f = np.maximum(crown_f, cr)

        # Gravel on slopes & quarry; woodland roots & bark along lumber-road verges!
        grav = np.clip(
            0.16 + 0.58 * quarry_grad + 0.24 * smooth(0.11, 0.30, slope_f) + 0.18 * np.clip(nf_macro, 0.0, 1.0),
            0.0, 1.0,
        ) * band
        gravel_f = np.maximum(gravel_f, grav)

        shld_in = smooth(road_w - 1.55, road_w - 0.15, dist)
        shld_out = 1.0 - smooth(road_w + 0.75, road_w + 2.85, dist)
        r_here = shld_in * shld_out * np.clip(0.65 + 0.38 * nf_edge_l + 0.15 * lumber_grad - 0.40 * quarry_grad, 0.0, 1.0) * cap
        roots_f = np.maximum(roots_f, r_here)

        # Uphill cut-bank toe
        x_slope = -ty * gx_f + tx * gy_f
        up_side = np.sign(x_slope)
        cut_w = smooth(0.11, 0.28, np.abs(x_slope)) * np.exp(-((lat - up_side * (road_w - 0.15)) / 1.15) ** 2) * cap
        cut_toe_f = np.maximum(cut_toe_f, cut_w)

        # Damp ruts & concave low-grade mud pockets
        low_grade = 1.0 - smooth(0.08, 0.22, slope_f)
        moist_here = np.clip(
            (0.45 * rut_here + 0.35 * concav_f + 0.28 * np.clip(-nf_macro, 0.0, 1.0)) * low_grade * band,
            0.0, 0.92,
        )
        moist_f = np.maximum(moist_f, moist_here)

        prox = (1.0 - smooth(0.0, 6.0, dist)) * cap
        take = prox > best_prox
        tx_best = np.where(take, tx, tx_best)
        ty_best = np.where(take, ty, ty_best)
        best_prox = np.maximum(best_prox, prox)

    # Blend the Lumber Mill working yard into the RoadMix surface!
    # Inside yard: compacted earth + stony working gravel + damp cart turning apron + bark/root fringes at perimeter!
    y_sdf_f = yard_sdf(fx, fy)
    yard_band = 1.0 - smooth(-0.4, 3.4 + 0.65 * nf_detail, y_sdf_f)
    lane_f = np.maximum(lane_f, yard_band)
    # Compacted gravel/earth in central work apron, roots/bark mulch around the yard perimeter!
    yard_gravel = (1.0 - smooth(-4.0, 1.5, y_sdf_f)) * np.clip(0.28 + 0.22 * nf_macro, 0.10, 0.55)
    yard_roots = smooth(-5.0, 0.5, y_sdf_f) * (1.0 - smooth(1.5, 4.8, y_sdf_f)) * np.clip(0.72 + 0.30 * nf_edge_l, 0.2, 1.0)
    # Sawing yard bark/mulch/mud pockets near log decks (east/south work area)
    yard_moist = (1.0 - smooth(-3.0, 2.0, y_sdf_f)) * np.clip(0.18 + 0.22 * (-nf_macro), 0.0, 0.42)
    gravel_f = np.maximum(gravel_f, yard_gravel)
    roots_f = np.maximum(roots_f, yard_roots)
    moist_f = np.maximum(moist_f, yard_moist)

    macro_f = np.clip(0.5 + 0.38 * nf_macro, 0.0, 1.0)

    # Save RoadMixField & TrackFrames PNGs
    mix_rgba = np.stack([ext_f * lane_f, gravel_f, roots_f, macro_f], axis=-1)
    Image.fromarray(np.rint(mix_rgba * 255.0).clip(0, 255).astype("u1")).save(rm_dir / "T_RoadMixField.png")

    flow_rgba = np.stack([rut_f * ext_f, tx_best * 0.5 + 0.5, ty_best * 0.5 + 0.5, moist_f], axis=-1)
    Image.fromarray(np.rint(flow_rgba * 255.0).clip(0, 255).astype("u1")).save(rm_dir / "T_TrackFrames.png")

    # Build expanded 2048x1024 T_ShoulderLeafField.png (includes bark chips/needles along lumber-road + yard fringes!)
    drift_n = warped_noise(rng, fx, fy, 6.5, 1.8, ((9.5, 0.45), (3.8, 0.35), (1.4, 0.20)))
    gust_n = warped_noise(rng, fx + 53.1, fy - 27.4, 4.0, 1.1, ((5.0, 0.55), (1.8, 0.45)))
    shld_litter = roots_f * np.clip(0.55 + 0.42 * drift_n, 0.0, 1.0)
    toe_litter = cut_toe_f * np.clip(0.75 + 0.30 * drift_n, 0.0, 1.0)
    rut_trapped = rut_f * smooth(0.35, 1.15, gust_n) * (1.0 - smooth(0.55, 0.85, gravel_f)) * 0.45
    wet_rim = smooth(0.22, 0.58, moist_f) * (1.0 - smooth(0.72, 0.92, moist_f)) * 0.50
    # Add rich bark/needle/wood-debris scatter across Lumber Mill log-deck & perimeter edges!
    yard_debris = yard_band * np.clip(0.32 + 0.45 * drift_n, 0.0, 0.88) * smooth(-12.0, 1.5, y_sdf_f)
    leaf_field = np.maximum.reduce([shld_litter * 0.95, toe_litter * 0.98, rut_trapped, wet_rim, yard_debris * 0.85])
    leaf_field *= ext_f * (1.0 - 0.55 * smooth(0.58, 0.88, gravel_f))
    leaf_field = np.clip(leaf_field * np.clip(0.82 + 0.26 * (macro_f - 0.5) * 2.0, 0.55, 1.15), 0.0, 1.0)
    Image.fromarray(np.rint(leaf_field * 255.0).clip(0, 255).astype("u1")).save(leaves_dir / "T_ShoulderLeafField.png")

    # Save road-topo.npz for R49 PCG road dressing
    np.savez_compressed(
        ter_dir / "road-topo.npz",
        origin=np.array(FIELD_ORIGIN, dtype=np.float32),
        size=np.array(FIELD_SIZE, dtype=np.float32),
        step=np.array([FIELD_STEP_X, FIELD_STEP_Y], dtype=np.float32),
        exterior=ext_f.astype(np.float32),
        lane=lane_f.astype(np.float32),
        gravel=gravel_f.astype(np.float32),
        roots=roots_f.astype(np.float32),
        macro=macro_f.astype(np.float32),
        rut=rut_f.astype(np.float32),
        crown=crown_f.astype(np.float32),
        moisture=moist_f.astype(np.float32),
        cut_toe=cut_toe_f.astype(np.float32),
        puddle=(moist_f > 0.58).astype(np.float32),
        tangent_x=tx_best.astype(np.float32),
        tangent_y=ty_best.astype(np.float32),
    )

    # Compute earthwork & seam QA metrics
    gy_f1, gx_f1 = np.gradient(z_new_m)
    slope_new = np.hypot(gx_f1, gy_f1)
    yard_mask = y_sdf <= 0.0
    bank_mask = (y_sdf > 0.0) & (y_sdf <= 16.0)
    seam_row = 320 + 252  # Y = +252 m Landscape border
    seam_diff = np.abs(z_new_m[seam_row, 624 + 120:624 + 160] - z_new_m[seam_row - 1, 624 + 120:624 + 160])

    yard_info = {
        "center_m": list(YARD_CENTER),
        "half_extents_m": list(YARD_HALF),
        "corner_radius_m": YARD_CORNER_R,
        "datum_m": YARD_DATUM_M,
        "yaw_deg": YARD_YAW_DEG,
        "yard_z_min_m": round(float(z_new_m[yard_mask].min()), 3),
        "yard_z_max_m": round(float(z_new_m[yard_mask].max()), 3),
        "max_cut_m": round(float((-delta_cm.min()) * 0.01), 2),
        "max_fill_m": round(float((delta_cm.max()) * 0.01), 2),
        "bank_max_slope": round(float(slope_new[bank_mask].max()), 3),
        "bank_p95_slope": round(float(np.percentile(slope_new[bank_mask], 95)), 3),
        "ls_delta_nonzero_px": int((ls_delta_i16 != 0).sum()),
        "ls_paint_nonzero_px": int((ls_paint_u8 > 0).sum()),
        "y252_seam_max_step_m": round(float(seam_diff.max()), 3),
        "meadow_fine_kept": int(keep_fine.sum()),
        "field_origin_m": list(FIELD_ORIGIN),
        "field_size_m": list(FIELD_SIZE),
        "road": road_stats,
    }
    (ter_dir / "lumber-yard.json").write_text(json.dumps(yard_info, indent=2), encoding="utf-8")

    # 5) Render clean diagnostic contour + road + yard verification PNG (same M-key map orientation: Screen +X = World +Y, Screen -Y = World +X!)
    # Crop world X in [15..205] (190m), Y in [20..475] (455m) at 2 px/m -> 910 x 380 px
    px_per_m = 2
    x0_v, x1_v = 15, 205
    y0_v, y1_v = 20, 475
    W_v = (y1_v - y0_v) * px_per_m
    H_v = (x1_v - x0_v) * px_per_m
    # Map (wx, wy) -> (u, v): u = (wy - y0_v)*px_per_m, v = (x1_v - wx)*px_per_m
    wy_g = y0_v + (np.arange(W_v) + 0.5) / px_per_m
    wx_g = x1_v - (np.arange(H_v) + 0.5) / px_per_m
    WYG, WXG = np.meshgrid(wy_g, wx_g)
    zv = grid_at(z_new_m, WXG, WYG)
    pv = grid_at(paint[:, :, 0].astype(np.float32) / 255.0, WXG, WYG)
    pwv = grid_at(pond_1m, WXG, WYG)
    # Hillshade + 2m contour lines
    gv_y, gv_x = np.gradient(zv)
    shade = np.clip(0.75 + 0.25 * (-gv_x * 0.6 + gv_y * 0.6), 0.4, 1.05)
    rgb = np.zeros((H_v, W_v, 3), dtype=np.float32)
    # Green forest base
    rgb[:, :, 0] = 68 * shade
    rgb[:, :, 1] = 96 * shade
    rgb[:, :, 2] = 66 * shade
    # Dirt / roads / village tan
    tan = np.array([175.0, 140.0, 92.0])
    rgb = rgb * (1.0 - pv[:, :, None] * 0.85) + (tan[None, None, :] * shade[:, :, None]) * (pv[:, :, None] * 0.85)
    # Ponds blue
    blue = np.array([45.0, 118.0, 195.0])
    rgb = rgb * (1.0 - pwv[:, :, None]) + blue[None, None, :] * pwv[:, :, None]
    # 2.0 m contour lines
    c_mod = np.abs(((zv + 0.05) % 2.0) - 1.0)
    contour = (c_mod > 0.93).astype(np.float32) * 0.35
    rgb *= (1.0 - contour[:, :, None])
    im = Image.fromarray(rgb.clip(0, 255).astype("u1"))
    dr = ImageDraw.Draw(im)

    def w2p(wx, wy):
        return ((wy - y0_v) * px_per_m, (x1_v - wx) * px_per_m)

    # Draw Y=252m Landscape boundary line (dashed cyan)
    p_a, p_b = w2p(x0_v, 252.0), w2p(x1_v, 252.0)
    dr.line([p_a, p_b], fill=(100, 220, 255), width=1)
    # Draw gate-road centerline (orange) & lumber-road centerline (bright yellow)
    gpts = np.loadtxt(ter_dir / "gate-road.csv", delimiter=",", skiprows=1)[:, :2]
    gxy = [w2p(float(px), float(py)) for px, py in gpts if x0_v <= px <= x1_v and y0_v <= py <= y1_v]
    if len(gxy) >= 2:
        dr.line(gxy, fill=(255, 165, 50), width=2)
    lxy = [w2p(float(px), float(py)) for px, py in lumber_xyz[:, :2]]
    dr.line(lxy, fill=(255, 240, 70), width=3)
    # Draw Lumber Mill flat yard outline (white)
    yx0, yy0 = w2p(YARD_CENTER[0] + YARD_HALF[0], YARD_CENTER[1] - YARD_HALF[1])
    yx1, yy1 = w2p(YARD_CENTER[0] - YARD_HALF[0], YARD_CENTER[1] + YARD_HALF[1])
    dr.rectangle([yx0, yy0, yx1, yy1], outline=(255, 255, 255), width=2)
    dr.text((yx0 + 4, yy0 - 14), "LUMBER MILL YARD (35x27m, Z=+11.0m)", fill=(255, 255, 255))
    dr.text((w2p(195, 254)[0], 8), "Y=252m Landscape Seam", fill=(100, 220, 255))
    dr.text((w2p(92, 330)[0], w2p(92, 330)[1]), "VILLAGE GATE", fill=(255, 230, 160))
    im.save(out_root / "terrain-plan.png")

    print("LUMBER_TERRAIN_OK:", json.dumps(yard_info, indent=2))


if __name__ == "__main__":
    r48 = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/RoadUpgrade-R48")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49")
    build_terrain_and_fields(r48, out)
