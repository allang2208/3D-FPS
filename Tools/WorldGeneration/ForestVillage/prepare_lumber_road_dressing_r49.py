"""Prepare LumberMill-R49 dual-theme PCG point streams:
1) RoadLandscape: preserves ALL R48b gate-road & quarry-road dressing AND adds full 5-zone
   realistic roadside PCG dressing (closed fences, stone retaining walls, oak posts, beams,
   sawmill logpile/barrel/crate vignettes, stumps, logs, branches, boulders, pebbles, crown grass,
   wild grass, ferns, weeds, Normandy shrubs) along the entire 263 m contour-matched lumber-road!
2) HillsLandscape: prunes any existing HillsLandscape trees, hazels, shrubs, grass, rocks, wood,
   and harvest-trees.f32 overlapping the new lumber-road corridor or graded Lumber Mill yard!
"""
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_slope_grass import POINT, WEST, SOUTH, grid_at
from prepare_lumber_mill_terrain_r49 import YARD_CENTER, YARD_CORNER_R, YARD_HALF, yard_sdf
from prepare_road_relief_r48 import load_road

SEED = 491823

COURTYARD_SHRUBS = [
    f"/Game/UnrealNormandy/StaticMeshes/SM_PlantType{fam}_0{i}A.SM_PlantType{fam}_0{i}A"
    for fam in ("A", "B", "C") for i in range(3)
]


def prepare_themes(r48_root: Path, r49_root: Path, base_themes_dir: Path, rock_catalog: Path):
    ter_dir = r49_root / "Terrain"
    out_themes = r49_root / "Themes"
    out_hills = out_themes / "HillsLandscape"
    out_road = out_themes / "RoadLandscape"
    out_hills.mkdir(parents=True, exist_ok=True)
    out_road.mkdir(parents=True, exist_ok=True)

    # Load lumber-road & yard geometry
    l_pts, l_sta, l_tang, l_curv = load_road(ter_dir, "lumber")
    l_tree = cKDTree(l_pts)
    l_total_len = float(l_sta[-1])
    gate_pts, _, _, _ = load_road(ter_dir, "gate")
    quarry_pts, _, _, _ = load_road(ter_dir, "quarry")
    all_road_tree = cKDTree(np.vstack([gate_pts, quarry_pts, l_pts]))

    # =========================================================================
    # 1) PRUNE HillsLandscape (trees, shrubs, rocks, grass, wood + harvest-trees)
    # =========================================================================
    src_hills = base_themes_dir / "HillsLandscape"
    for fn in ("reference-meshes.txt", "study-granite.i32", "theme.id", "theme.json"):
        if (src_hills / fn).is_file():
            shutil.copy2(src_hills / fn, out_hills / fn)

    h_rec = np.fromfile(src_hills / "planting.bin", POINT)
    hx = h_rec["x"] * 0.01
    hy = h_rec["y"] * 0.01
    h_rd = l_tree.query(np.column_stack((hx, hy)))[0]
    h_ysdf = yard_sdf(hx, hy)
    # Trees/hazels (slot < 4): clear >= 4.2m from lumber road & >= 5.5m outside yard edge;
    # Smaller grass/floor/shrubs/rocks: clear >= 3.2m from road & >= 3.5m outside yard edge!
    is_tree = h_rec["slot"] < 4
    keep_h = np.where(is_tree, (h_rd > 4.2) & (h_ysdf > 5.5), (h_rd > 3.2) & (h_ysdf > 3.5))
    h_kept = h_rec[keep_h]

    # R55 Seam Feathering: along the Y=+252m Landscape/Outer-Tile boundary near the lumber road
    # (X in [105..168] m), HillsLandscape understory (Hazel slots 2,3 and ferns/forest-floor clutter
    # slots 21..30) previously stopped abruptly on the Y=252.0m straight line because L_ForestPathForest's
    # Hazel/Rocks/LeafyWeeds PCGVolumes have 0 instances there. Feather matching organic understory
    # southward into Y in [236..251.95] m with a domain-warped wavy edge so there is ZERO straight line!
    feather_slots = (2, 3, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30)
    hx_k, hy_k = h_kept["x"] * 0.01, h_kept["y"] * 0.01
    donor_mask = (
        (hx_k >= 105.0) & (hx_k <= 168.0)
        & (hy_k >= 252.0) & (hy_k <= 268.0)
        & np.isin(h_kept["slot"], feather_slots)
    )
    donors = h_kept[donor_mask]
    rng_f = np.random.default_rng(550252)
    extra_pts = []
    if len(donors):
        study_trees_fp = ter_dir / "Grass/study_trees.f32"
        st_tree = None
        if study_trees_fp.is_file():
            st_arr = np.fromfile(study_trees_fp, "<f4").reshape(-1, 3)
            if len(st_arr):
                st_tree = cKDTree(st_arr[:, :2])
        for rec in donors:
            dx_m = float(rec["x"]) * 0.01
            dy_m = float(rec["y"]) * 0.01
            # Mirror across Y=252m with natural XY jitter so patterns never look mirrored
            ny_m = 252.0 - (dy_m - 252.0) + float(rng_f.uniform(-0.85, 0.85))
            nx_m = dx_m + float(rng_f.uniform(-1.6, 1.6))
            if not (104.0 <= nx_m <= 169.0 and 234.0 <= ny_m <= 251.92):
                continue
            # Organic wavy south falloff edge (~235..241m) -> zero straight line at either Y=252 or Y=236!
            wave_min = 236.5 + 3.2 * math.sin(nx_m * 0.19 + 0.7) + 1.8 * math.cos(nx_m * 0.43 - 1.1)
            t_fade = max(0.0, min(1.0, (ny_m - wave_min) / max(1.0, 252.0 - wave_min)))
            prob = t_fade * t_fade * (3.0 - 2.0 * t_fade)
            if rng_f.random() > prob:
                continue
            rd_m = float(l_tree.query([nx_m, ny_m])[0])
            min_rd = 4.3 if int(rec["slot"]) < 4 else 3.3
            if rd_m <= min_rd:
                continue
            if st_tree is not None and float(st_tree.query([nx_m, ny_m])[0]) < (1.6 if int(rec["slot"]) < 4 else 0.75):
                continue
            extra_pts.append((
                nx_m * 100.0,
                ny_m * 100.0,
                float(rng_f.uniform(-180.0, 180.0)),
                float(rec["scale"]) * float(rng_f.uniform(0.90, 1.08)),
                int(rec["slot"]),
            ))
    if extra_pts:
        h_out = np.concatenate([h_kept, np.array(extra_pts, dtype=POINT)])
    else:
        h_out = h_kept
    h_out.tofile(out_hills / "planting.bin")
    hills_pruned = int((~keep_h).sum())
    print(f"[HILLS-SEAM-R55] Feathered +{len(extra_pts)} organic understory/litter points across Y=236..252m")

    # Prune harvest-trees.f32 (interactive choppable trees!) inside lumber road & yard
    ht = np.fromfile(src_hills / "harvest-trees.f32", "<f4").reshape(-1, 3)
    ht_x, ht_y = ht[:, 0] * 0.01, ht[:, 1] * 0.01
    keep_ht = (l_tree.query(np.column_stack((ht_x, ht_y)))[0] > 4.5) & (yard_sdf(ht_x, ht_y) > 6.0)
    ht[keep_ht].tofile(out_hills / "harvest-trees.f32")
    ht_pruned = int((~keep_ht).sum())
    print(f"[HILLS] Kept {int(keep_h.sum())}/{len(h_rec)} (pruned {hills_pruned}), harvest-trees pruned {ht_pruned}")

    # =========================================================================
    # 2) EXTEND RoadLandscape with full 5-zone PCG dressing along lumber-road!
    # =========================================================================
    src_road = base_themes_dir / "RoadLandscape"
    r_rec = np.fromfile(src_road / "planting.bin", POINT)
    palette = (src_road / "reference-meshes.txt").read_text(encoding="utf-8-sig").splitlines()
    slot_rules = json.loads((src_road / "road-slot-rules.json").read_text(encoding="utf-8"))
    fence_spans = json.loads((src_road / "fence-spans.json").read_text(encoding="utf-8"))
    catalog = json.loads((r48_root / "road-asset-catalog.json").read_text(encoding="utf-8"))
    granite_all = json.loads(rock_catalog.read_text(encoding="utf-8-sig"))
    granite_small = [g for g in granite_all if g["width_cm"] <= 34.0]
    granite_med = [g for g in granite_all if 34.0 < g["width_cm"] <= 95.0]

    # Prune any old gate/quarry road points that happen to sit right in the new lumber-road junction opening
    rx0, ry0 = r_rec["x"] * 0.01, r_rec["y"] * 0.01
    r_ld = l_tree.query(np.column_stack((rx0, ry0)))[0]
    keep_r = (r_ld > 2.65) | (np.hypot(rx0 - 88.85, ry0 - 314.2) > 14.0)
    r_rec = r_rec[keep_r].copy()

    def slot_of(mesh_path: str) -> int:
        if mesh_path in palette:
            return 16 + palette.index(mesh_path)
        palette.append(mesh_path)
        return 16 + len(palette) - 1

    by_role = {}
    for row in catalog:
        by_role.setdefault(row["role"], []).append(row)

    # Terrain & topology grids
    raw_h_i16 = np.fromfile(ter_dir / "region.i16", "<i2").reshape(1025, 1025)
    z_m = raw_h_i16.astype(np.float32) * 0.01
    gy, gx = np.gradient(gaussian_filter(z_m, 1.0))
    grade = np.hypot(gx, gy)
    cliff = np.fromfile(ter_dir / "cliff-mask.u8", "u1").reshape(1025, 1025).astype(np.float32) / 255.0
    pond_wet = np.fromfile(ter_dir / "Grass/pond_wet.u8", "u1").reshape(4097, 4097)
    hill = json.loads((ter_dir / "hill.json").read_text(encoding="utf-8-sig"))
    vx, vy = hill["site_min_m"]

    topo = np.load(ter_dir / "road-topo.npz")
    t_orig = topo["origin"]
    t_step = topo["step"]
    t_rut = topo["rut"]
    t_crown = topo["crown"]
    t_moist = topo["moisture"]
    t_roots = topo["roots"]
    t_cut = topo["cut_toe"]

    def topo_sample(arr, x, y):
        fi = (x - float(t_orig[0])) / float(t_step[0]) - 0.5
        fj = (y - float(t_orig[1])) / float(t_step[1]) - 0.5
        if not (0.0 <= fi < arr.shape[1] - 1 and 0.0 <= fj < arr.shape[0] - 1):
            return 0.0
        return float(map_coordinates(arr, [[fj], [fi]], order=1, mode="nearest")[0])

    # Exact AForestVillageRegion::GroundHeight mirror in cm
    def gz_cm(xm, ym):
        gx_i = max(0.0, min(1024.0, xm + 624.0))
        gy_i = max(0.0, min(1024.0, ym + 320.0))
        i0 = max(0, min(1023, int(math.floor(gx_i))))
        j0 = max(0, min(1023, int(math.floor(gy_i))))
        i = i0 if (-252 <= (i0 - 624) < 252) else (i0 & ~1)
        j = j0 if (-252 <= (j0 - 320) < 612) else (j0 & ~1)
        k = i + (1 if (-252 <= (i - 624) < 252) else 2)
        l = j + (1 if (-252 <= (j - 320) < 612) else 2)
        uf = (gx_i - i) / (k - i)
        vf = (gy_i - j) / (l - j)
        a = float(raw_h_i16[j, i])
        d = float(raw_h_i16[l, k])
        if uf >= vf:
            return a * (1.0 - uf) + float(raw_h_i16[j, k]) * (uf - vf) + d * vf
        return a * (1.0 - vf) + float(raw_h_i16[l, i]) * (vf - uf) + d * uf

    def corner_spread_cm(xm, ym, yaw_deg, hx_m, hy_m):
        rad = math.radians(yaw_deg)
        c, s = math.cos(rad), math.sin(rad)
        zs = [gz_cm(xm, ym)]
        for lx, ly in ((-hx_m, -hy_m), (hx_m, -hy_m), (hx_m, hy_m), (-hx_m, hy_m)):
            zs.append(gz_cm(xm + c * lx - s * ly, ym + s * lx + c * ly))
        return max(zs) - min(zs)

    def sample1(grid, x, y):
        return float(grid_at(grid, np.array([x]), np.array([y]))[0])

    def wet_at(x, y):
        return float(grid_at(pond_wet, np.array([x]), np.array([y]), step=0.25)[0]) / 255.0

    def town_dist(x, y):
        return math.hypot(max(vx - x, x - (vx + 118.0), 0.0), max(vy - y, y - (vy + 145.0), 0.0))

    def road_at(s):
        j = min(int(np.searchsorted(l_sta, s)), len(l_pts) - 1)
        p = l_pts[j]
        t = l_tang[j]
        left = np.array([-t[1], t[0]], dtype=np.float64)
        yaw = math.degrees(math.atan2(float(t[1]), float(t[0])))
        return p, t, left, yaw

    # Obstacles (study trees + surviving hills trees)
    obs_list = []
    for fn in ("study_trees.f32", "study_obstacles.f32", "study_pond_props.f32"):
        fp = ter_dir / "Grass" / fn
        if fp.is_file():
            arr = np.fromfile(fp, "<f4").reshape(-1, 3)
            # Exclude study trees we are going to prune inside the lumber road/yard!
            keep_o = (l_tree.query(arr[:, :2])[0] > 3.8) & (yard_sdf(arr[:, 0], arr[:, 1]) > 5.0)
            obs_list.append(arr[keep_o])
    obs_arr = np.vstack(obs_list) if obs_list else np.zeros((0, 3), dtype=np.float32)
    obs_tree = cKDTree(obs_arr[:, :2]) if len(obs_arr) else None
    obs_max_r = float(obs_arr[:, 2].max()) + 0.5 if len(obs_arr) else 1.0

    def hits_obs(x, y, rad):
        if obs_tree is None:
            return False
        for idx in obs_tree.query_ball_point([x, y], obs_max_r + rad):
            if math.hypot(x - obs_arr[idx, 0], y - obs_arr[idx, 1]) < obs_arr[idx, 2] + rad:
                return True
        return False

    solid_bins = {}
    def solid_free(x, y, rad, pad=0.15):
        ix0, iy0 = int(math.floor((x - rad - 3.0) / 4.0)), int(math.floor((y - rad - 3.0) / 4.0))
        ix1, iy1 = int(math.floor((x + rad + 3.0) / 4.0)), int(math.floor((y + rad + 3.0) / 4.0))
        for bx in range(ix0, ix1 + 1):
            for by in range(iy0, iy1 + 1):
                for ox, oy, orad in solid_bins.get((bx, by), ()):
                    if math.hypot(x - ox, y - oy) < rad + orad + pad:
                        return False
        return True

    def reserve_solid(x, y, rad):
        solid_bins.setdefault((int(math.floor(x / 4.0)), int(math.floor(y / 4.0))), []).append((x, y, rad))

    def ok_site(x, y, min_road=3.35, min_yard=4.5):
        return (
            -618.0 < x < 394.0 and -314.0 < y < 698.0
            and town_dist(x, y) > 5.0
            and float(yard_sdf(np.array([x]), np.array([y]))[0]) > min_yard
            and wet_at(x, y) < 0.05
            and all_road_tree.query([x, y])[0] > min_road
        )

    rng = np.random.default_rng(SEED)
    added = []
    counts = {}

    def emit(x, y, yaw, sc, mpath, tag, solid_rad=0.0):
        added.append((x * 100.0, y * 100.0, float(yaw), float(sc), slot_of(mpath)))
        counts[tag] = counts.get(tag, 0) + 1
        if solid_rad > 0.0:
            reserve_solid(x, y, solid_rad)

    # --- ZONE 5A: Closed split-rail roadside fences with exact end posts (0 floating!) ---
    fence_sets = []
    for key_f in ("xfrobaziy", "ufflaitdw"):
        items_f = [r for r in by_role.get("prop_fence", []) if r["key"] == key_f]
        pan = [r for r in items_f if max(r["size_cm"][0], r["size_cm"][1]) > 80.0]
        endp = [r for r in items_f if max(r["size_cm"][0], r["size_cm"][1]) <= 80.0]
        if pan and endp:
            fence_sets.append({"key": key_f, "panel": pan[0], "post": endp[0], "span_m": float(pan[0]["max_cm"][0]) * 0.01})

    s_at = 18.0
    while s_at < l_total_len - 22.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        placed = False
        if fence_sets and rng.random() < 0.60:
            fset = fence_sets[int(rng.integers(len(fence_sets)))]
            seg_n = int(rng.integers(2, 4))
            sc_run = float(rng.uniform(0.95, 1.03))
            span_m = fset["span_m"] * sc_run
            for cand_side in (1.0, -1.0) if rng.random() < 0.5 else (-1.0, 1.0):
                base_off = float(rng.uniform(3.9, 4.6))
                posts_xy = []
                s_cur = s_at
                ok_c = True
                for k in range(seg_n + 1):
                    if s_cur > l_total_len - 14.0:
                        ok_c = False
                        break
                    pk, tk, lk, _ = road_at(s_cur)
                    pt = pk + cand_side * lk * base_off
                    if k > 0:
                        dx, dy = float(pt[0]) - posts_xy[-1][0], float(pt[1]) - posts_xy[-1][1]
                        d = math.hypot(dx, dy)
                        if d < 0.5:
                            ok_c = False
                            break
                        pt = np.array([posts_xy[-1][0] + dx / d * span_m, posts_xy[-1][1] + dy / d * span_m])
                    x, y = float(pt[0]), float(pt[1])
                    if (not ok_site(x, y, min_road=3.55, min_yard=5.5) or sample1(grade, x, y) > 0.21
                            or hits_obs(x, y, 0.75) or not solid_free(x, y, 0.70)):
                        ok_c = False
                        break
                    if k > 0:
                        px0, py0 = posts_xy[-1]
                        z0, z1 = gz_cm(px0, py0), gz_cm(x, y)
                        zm = gz_cm(0.5 * (px0 + x), 0.5 * (py0 + y))
                        if abs(z1 - z0) > 15.0 * span_m or (zm - 0.5 * (z0 + z1)) > 9.0:
                            ok_c = False
                            break
                        if not solid_free(0.5 * (px0 + x), 0.5 * (py0 + y), span_m * 0.42):
                            ok_c = False
                            break
                    posts_xy.append((x, y))
                    s_cur += span_m
                if ok_c and len(posts_xy) == seg_n + 1:
                    for k in range(seg_n):
                        x0, y0 = posts_xy[k]
                        x1, y1 = posts_xy[k + 1]
                        emit(x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0)), sc_run, fset["panel"]["mesh"], "LR_Fence")
                        reserve_solid(0.5 * (x0 + x1), 0.5 * (y0 + y1), span_m * 0.46)
                        fence_spans.append({
                            "mesh": fset["panel"]["mesh"],
                            "p0_cm": [x0 * 100.0, y0 * 100.0],
                            "p1_cm": [x1 * 100.0, y1 * 100.0],
                            "scale": sc_run,
                        })
                    xe, ye = posts_xy[-1]
                    xp, yp = posts_xy[-2]
                    emit(xe, ye, math.degrees(math.atan2(ye - yp, xe - xp)), sc_run, fset["post"]["mesh"], "LR_FenceEndPost", solid_rad=0.45)
                    placed = True
                    break
            if placed:
                s_at += float(rng.uniform(34.0, 54.0))
                continue

        # --- ZONE 5B: Mossy stone bank retaining walls on gentle cut shoulders ---
        sws = by_role.get("prop_stonewall", [])
        if sws and rng.random() < 0.65:
            sw = sws[0]
            sw_len = max(sw["size_cm"][0], sw["size_cm"][1]) * 0.01
            for cand_side in (1.0, -1.0):
                pt = p0 + cand_side * left0 * float(rng.uniform(4.0, 5.2))
                x, y = float(pt[0]), float(pt[1])
                sc_sw = float(rng.uniform(0.84, 1.02))
                half_l = sw_len * sc_sw * 0.48
                axis_fix = 0.0 if sw["size_cm"][0] >= sw["size_cm"][1] else 90.0
                wyaw = yaw0 + axis_fix + float(rng.uniform(-4.0, 4.0))
                rw = math.radians(wyaw)
                z_l = gz_cm(x - math.cos(rw) * half_l, y - math.sin(rw) * half_l)
                z_m = gz_cm(x, y)
                z_r = gz_cm(x + math.cos(rw) * half_l, y + math.sin(rw) * half_l)
                if (ok_site(x, y, min_road=3.65, min_yard=5.5) and 0.07 <= sample1(grade, x, y) <= 0.34
                        and abs(z_r - z_l) / (2.0 * half_l * 100.0) <= 0.13 and (z_m - min(z_l, z_r)) <= 20.0
                        and not hits_obs(x, y, 0.95) and solid_free(x, y, half_l + 0.25)):
                    emit(x, y, wyaw, sc_sw, sw["mesh"], "LR_StoneWall", solid_rad=half_l + 0.2)
                    s_at += float(rng.uniform(28.0, 48.0))
                    break
        s_at += float(rng.uniform(18.0, 30.0))

    # --- ZONE 5C: Logging-roadside oak posts, fallen timbers, & log-stack staging vignettes ---
    oak_posts = by_role.get("prop_post", [])
    beams = by_role.get("prop_beam", [])
    logpiles = by_role.get("prop_logpile", [])
    barrels = by_role.get("prop_barrel", [])
    crates = by_role.get("prop_crate", [])
    wheels = by_role.get("prop_wheel", [])

    s_at = 16.0
    while s_at < l_total_len - 14.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        side = float(rng.choice([-1.0, 1.0]))
        pt = p0 + side * left0 * float(rng.uniform(3.45, 4.75))
        x, y = float(pt[0]), float(pt[1])
        if ok_site(x, y, min_road=3.25, min_yard=5.0) and not hits_obs(x, y, 0.55) and solid_free(x, y, 0.75):
            gr = sample1(grade, x, y)
            if beams and gr <= 0.22 and rng.random() < 0.42:
                bm = beams[0]
                axis_fix = 0.0 if bm["size_cm"][0] >= bm["size_cm"][1] else 90.0
                byaw = yaw0 + axis_fix + float(rng.uniform(-14.0, 14.0))
                rb = math.radians(byaw)
                zl, zm, zr = gz_cm(x - math.cos(rb) * 0.6, y - math.sin(rb) * 0.6), gz_cm(x, y), gz_cm(x + math.cos(rb) * 0.6, y + math.sin(rb) * 0.6)
                if abs(zm - 0.5 * (zl + zr)) <= 4.5:
                    emit(x, y, byaw, float(rng.uniform(0.92, 1.12)), bm["mesh"], "LR_TimberBeam", solid_rad=0.85)
            elif oak_posts and gr <= 0.28:
                op = oak_posts[int(rng.integers(len(oak_posts)))]
                emit(x, y, yaw0 + float(rng.uniform(-18.0, 18.0)), float(rng.uniform(0.88, 1.08)), op["mesh"], "LR_OakPost", solid_rad=0.55)
        s_at += float(rng.uniform(20.0, 34.0))

    # Logging staging vignettes (stacked logs + barrel/crate/wheel along flat shoulders!)
    for v_idx, target_s in enumerate((38.0, 96.0, 152.0, 206.0)):
        p0, t0, left0, yaw0 = road_at(target_s)
        for _ in range(20):
            side = float(rng.choice([-1.0, 1.0]))
            pt = p0 + side * left0 * float(rng.uniform(3.9, 5.8))
            x, y = float(pt[0]), float(pt[1])
            if (ok_site(x, y, min_road=3.65, min_yard=6.0) and sample1(grade, x, y) <= 0.17
                    and corner_spread_cm(x, y, yaw0, 0.45, 0.30) <= 8.5 and not hits_obs(x, y, 1.0)
                    and solid_free(x, y, 1.15) and logpiles):
                emit(x, y, yaw0 + float(rng.uniform(-22.0, 22.0)), float(rng.uniform(1.02, 1.24)), logpiles[0]["mesh"], "LR_LogPile", solid_rad=1.0)
                for kind in (("barrel", "crate") if v_idx % 2 == 0 else ("crate", "wheel")):
                    for _ in range(10):
                        ang = float(rng.uniform(0, 2 * math.pi))
                        cx, cy = x + math.cos(ang) * float(rng.uniform(1.0, 1.85)), y + math.sin(ang) * float(rng.uniform(1.0, 1.85))
                        if ok_site(cx, cy, min_road=3.45, min_yard=5.5) and sample1(grade, cx, cy) <= 0.16 and solid_free(cx, cy, 0.45, 0.05):
                            if kind == "barrel" and barrels and corner_spread_cm(cx, cy, yaw0, 0.38, 0.38) <= 7.0:
                                emit(cx, cy, float(rng.uniform(-180, 180)), float(rng.uniform(0.90, 1.04)), barrels[0]["mesh"], "LR_Barrel", solid_rad=0.45)
                                break
                            if kind == "crate" and crates and corner_spread_cm(cx, cy, yaw0, 0.38, 0.38) <= 6.5:
                                emit(cx, cy, yaw0 + float(rng.uniform(-35, 35)), float(rng.uniform(1.12, 1.35)), crates[0]["mesh"], "LR_Crate", solid_rad=0.45)
                                break
                            if kind == "wheel" and wheels and corner_spread_cm(cx, cy, yaw0, 0.42, 0.42) <= 12.0:
                                emit(cx, cy, float(rng.uniform(-180, 180)), float(rng.uniform(0.86, 1.04)), wheels[0]["mesh"], "LR_Wheel", solid_rad=0.48)
                                break
                break

    # --- ZONE 3: Felled stumps (extra authentic near logging road!), fallen logs, branches, mossy boulders ---
    stumps = by_role.get("stump", [])
    logs = by_role.get("log", [])
    branches = by_role.get("branch", [])
    boulders = by_role.get("rock_boulder", [])
    small_rock = by_role.get("rock_small", [])

    # Stumps (higher logging frequency along lumber-road!)
    s_at = 10.0
    while s_at < l_total_len - 8.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        for _ in range(5):
            side = float(rng.choice([-1.0, 1.0]))
            pt = p0 + side * left0 * float(rng.uniform(3.9, 10.2))
            x, y = float(pt[0]), float(pt[1])
            if ok_site(x, y, min_road=3.65, min_yard=4.2) and sample1(grade, x, y) <= 0.35 and not hits_obs(x, y, 0.7) and solid_free(x, y, 0.85) and stumps:
                st = stumps[int(rng.integers(len(stumps)))]
                sc = float(rng.uniform(0.46, 0.70)) if st["size_cm"][2] > 180.0 else float(rng.uniform(0.78, 1.15))
                emit(x, y, float(rng.uniform(-180, 180)), sc, st["mesh"], "LR_Stump", solid_rad=0.85)
                break
        s_at += float(rng.uniform(8.0, 16.0))

    # Fallen logs (strict anti-bridge check)
    s_at = 14.0
    while s_at < l_total_len - 12.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        for _ in range(8):
            side = float(rng.choice([-1.0, 1.0]))
            pt = p0 + side * left0 * float(rng.uniform(4.4, 10.8))
            x, y = float(pt[0]), float(pt[1])
            if ok_site(x, y, min_road=4.2, min_yard=4.8) and sample1(grade, x, y) <= 0.25 and not hits_obs(x, y, 1.0) and solid_free(x, y, 1.55) and logs:
                lg = logs[int(rng.integers(len(logs)))]
                sc = float(rng.uniform(0.72, 1.02))
                yaw = yaw0 + float(rng.uniform(-35, 35)) + float(rng.choice([0, 180]))
                rl = math.radians(yaw)
                hl = max(lg["size_cm"][0], lg["size_cm"][1]) * 0.005 * sc
                za, zm, zb = gz_cm(x - math.cos(rl) * hl, y - math.sin(rl) * hl), gz_cm(x, y), gz_cm(x + math.cos(rl) * hl, y + math.sin(rl) * hl)
                if abs(zb - za) <= 22.0 * (2.0 * hl) and abs(zm - 0.5 * (za + zb)) <= 15.0:
                    emit(x, y, yaw, sc, lg["mesh"], "LR_Log", solid_rad=1.55)
                    break
        s_at += float(rng.uniform(13.0, 24.0))

    # Branches & Mossy Boulders
    s_at = 5.0
    while s_at < l_total_len - 5.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        side = float(rng.choice([-1.0, 1.0]))
        pt = p0 + side * left0 * float(rng.uniform(2.55, 8.2))
        x, y = float(pt[0]), float(pt[1])
        if ok_site(x, y, min_road=2.40, min_yard=4.2) and sample1(grade, x, y) <= 0.45 and solid_free(x, y, 0.45) and branches:
            br = branches[int(rng.integers(len(branches)))]
            emit(x, y, float(rng.uniform(-180, 180)), float(rng.uniform(0.68, 1.15)), br["mesh"], "LR_Branch", solid_rad=0.40)
        s_at += float(rng.uniform(4.8, 10.2))

    s_at = 9.0
    while s_at < l_total_len - 8.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        side = float(rng.choice([-1.0, 1.0]))
        pt = p0 + side * left0 * float(rng.uniform(3.7, 10.0))
        x, y = float(pt[0]), float(pt[1])
        if ok_site(x, y, min_road=3.5, min_yard=4.5) and sample1(grade, x, y) <= 0.60 and not hits_obs(x, y, 0.6) and solid_free(x, y, 0.80):
            if boulders and rng.random() < 0.55:
                rk = boulders[int(rng.integers(len(boulders)))]
                sc = float(rng.uniform(0.32, 0.68))
                emit(x, y, float(rng.uniform(-180, 180)), sc, rk["mesh"], "LR_Boulder", solid_rad=0.75 * sc)
            elif granite_med:
                gm = granite_med[int(rng.integers(len(granite_med)))]
                sc = float(rng.uniform(0.55, 1.02))
                emit(x, y, float(rng.uniform(-180, 180)), sc, gm["mesh"], "LR_GraniteMed", solid_rad=0.55 * sc)
        s_at += float(rng.uniform(7.5, 15.0))

    # --- ZONE 2: Clustered pebbles + dry verge grass + weeds ---
    pebble_meshes = [r["mesh"] for r in small_rock] + [g["mesh"] for g in granite_small[:8]]
    fol_crown = by_role.get("fol_crown_grass", [])
    fol_dry = by_role.get("fol_dry_grass", [])
    fol_wild = by_role.get("fol_wild_grass", [])
    fol_tuft = by_role.get("fol_tuft_grass", [])
    fol_fern = by_role.get("fol_fern", [])
    fol_weed = by_role.get("fol_weed", [])
    fol_clover = by_role.get("fol_clover", [])

    s_at = 3.0
    while s_at < l_total_len - 3.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        for side in (-1.0, 1.0):
            c_pt = p0 + side * left0 * float(rng.uniform(1.9, 4.2))
            cx, cy = float(c_pt[0]), float(c_pt[1])
            if ok_site(cx, cy, min_road=1.65, min_yard=3.5) and pebble_meshes:
                for _ in range(int(rng.integers(2, 6))):
                    ang = float(rng.uniform(0, 2 * math.pi))
                    rad = float(rng.uniform(0.10, 0.95))
                    px, py = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
                    if ok_site(px, py, min_road=1.55, min_yard=3.2):
                        mp = pebble_meshes[int(rng.integers(len(pebble_meshes)))]
                        sc = float(rng.uniform(0.55, 1.25)) if "/RoadUpgrade/" in mp else float(rng.uniform(0.35, 0.72))
                        emit(px, py, float(rng.uniform(-180, 180)), sc, mp, "LR_Pebble")
        s_at += float(rng.uniform(4.2, 8.2))

    # --- ZONE 1: Center crown grass & weeds along logging road center ---
    crown_pool = fol_crown + fol_tuft + fol_clover + fol_weed
    s_at = 6.0
    while s_at < l_total_len - 6.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        cr_w = topo_sample(t_crown, float(p0[0]), float(p0[1]))
        if cr_w > 0.24 and crown_pool and rng.random() < 0.62:
            for _ in range(int(rng.integers(2, 5))):
                s_j = min(l_total_len - 2.0, max(2.0, s_at + float(rng.uniform(-1.3, 1.3))))
                pj, _, lj, _ = road_at(s_j)
                pt = pj + lj * float(rng.uniform(-0.34, 0.34))
                x, y = float(pt[0]), float(pt[1])
                if ok_site(x, y, min_road=0.0, min_yard=4.0) and topo_sample(t_rut, x, y) < 0.34:
                    it = crown_pool[int(rng.integers(len(crown_pool)))]
                    emit(x, y, float(rng.uniform(-180, 180)), float(rng.uniform(0.62, 0.96)), it["mesh"], "LR_CrownGrass")
        s_at += float(rng.uniform(3.8, 7.6))

    # --- ZONE 2 & 3: Verge dry grass, wild grass, ferns & Normandy roadside shrubs ---
    verge_pool = fol_dry + fol_wild + fol_tuft + fol_weed + fol_clover
    s_at = 3.0
    while s_at < l_total_len - 3.0:
        p0, t0, left0, yaw0 = road_at(s_at)
        for side in (-1.0, 1.0):
            # Inner/mid verge grass drift (2.1..4.6 m)
            pt = p0 + side * left0 * float(rng.uniform(2.1, 4.6))
            x, y = float(pt[0]), float(pt[1])
            if ok_site(x, y, min_road=1.95, min_yard=3.6) and verge_pool and sample1(grade, x, y) < 0.55:
                it = verge_pool[int(rng.integers(len(verge_pool)))]
                for _ in range(int(rng.integers(2, 4))):
                    px = x + float(rng.uniform(-0.9, 0.9))
                    py = y + float(rng.uniform(-0.9, 0.9))
                    if ok_site(px, py, min_road=1.85, min_yard=3.4):
                        emit(px, py, float(rng.uniform(-180, 180)), float(rng.uniform(0.68, 1.15)), it["mesh"], "LR_VergeGrass")
            # Outer verge ferns (3.3..8.2 m)
            if fol_fern and rng.random() < 0.55:
                fp = p0 + side * left0 * float(rng.uniform(3.3, 8.2))
                fx, fy = float(fp[0]), float(fp[1])
                if ok_site(fx, fy, min_road=3.1, min_yard=4.2) and sample1(grade, fx, fy) < 0.50:
                    fn_it = fol_fern[int(rng.integers(len(fol_fern)))]
                    emit(fx, fy, float(rng.uniform(-180, 180)), float(rng.uniform(0.75, 1.25)), fn_it["mesh"], "LR_Fern")
            # Normandy woodland roadside shrubs (4.2..9.5 m)
            if rng.random() < 0.16:
                sp = p0 + side * left0 * float(rng.uniform(4.2, 9.5))
                sx, sy = float(sp[0]), float(sp[1])
                if ok_site(sx, sy, min_road=3.9, min_yard=5.2) and sample1(grade, sx, sy) < 0.40 and not hits_obs(sx, sy, 0.6) and solid_free(sx, sy, 0.65):
                    sh_m = COURTYARD_SHRUBS[int(rng.integers(len(COURTYARD_SHRUBS)))]
                    emit(sx, sy, float(rng.uniform(-180, 180)), float(rng.uniform(0.78, 1.18)), sh_m, "LR_Shrub", solid_rad=0.60)
        s_at += float(rng.uniform(3.2, 6.2))

    # Merge new lumber-road dressing into RoadLandscape planting.bin!
    new_arr = np.array(added, dtype=POINT) if added else np.empty(0, dtype=POINT)
    merged_road = np.concatenate([r_rec, new_arr])
    merged_road.tofile(out_road / "planting.bin")
    (out_road / "reference-meshes.txt").write_text("\n".join(palette) + "\n", encoding="utf-8")
    (out_road / "road-slot-rules.json").write_text(json.dumps(slot_rules, indent=2), encoding="utf-8")
    (out_road / "fence-spans.json").write_text(json.dumps(fence_spans, indent=2), encoding="utf-8")
    for fn in ("theme.id", "theme.json"):
        if (src_road / fn).is_file():
            shutil.copy2(src_road / fn, out_road / fn)

    summary = {
        "hills_pruned": hills_pruned,
        "harvest_trees_pruned": ht_pruned,
        "road_prev_kept": int(len(r_rec)),
        "lumber_road_added": int(len(new_arr)),
        "road_total": int(len(merged_road)),
        "fence_spans_total": len(fence_spans),
        "by_zone": counts,
    }
    (out_road / "dressing-r49.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("LUMBER_THEMES_OK:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    r48 = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/RoadUpgrade-R48")
    r49 = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49")
    themes_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("D:/FPS3D/FPSGAME/SourceAssets/HillsForestPathThemes")
    rocks = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageFlora-R20/rock-pool.json")
    prepare_themes(r48, r49, themes_dir, rocks)
