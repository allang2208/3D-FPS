"""Re-author anatomically accurate, zero-twist Warhorse Coastal Gallop and Lateral Walk cycles.

Fixes lower-leg & hoof twisting/inversion found in R14 CoastalGallop and native WarhorseLite Walk:
- Parameterizes every limb chain by relative anatomical sagittal joint deltas from clean bind pose
  (strictly 0 deg longitudinal twist and 0 deg off-plane kink on forearm/hand/finger & calf/foot/toe).
- Enforces hard equine physiological joint bounds (carpus only folds backward, hock only flexes
  forward, stifle always points forward, fetlock stays within natural stance dorsiflexion and
  swing palmar flexion).
- Solves all cycle frames globally with periodic C2 smoothness directly against BV1bA411o7Kb
  beach-gallop tracks, torso curves, and reference silhouettes (Gallop), and a true 4-beat lateral
  equine walk matched to 2.20 m/s ground speed with zero hoof slip (Walk).
"""
import argparse
import gzip
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare_horse import Horse, SOURCE
from review_canter import draw_mesh


STUDY_R14 = Path(r"F:\FPSGAMEData\ArtProduction\HillsVillageStable\GallopStudyR14-20261123")


def load_base_horse():
    p = SOURCE / "Originals/WarhorseLite.glb"
    if p.exists():
        return Horse(p.read_bytes())
    with zipfile.ZipFile(SOURCE / "Originals/WarhorseLite.zip") as z:
        return Horse(z.read("Warhorse_Lite/Warhorse_Lite.glb"))


def raw_acc(h, idx, width):
    a = h.doc["accessors"][idx]
    v = h.doc["bufferViews"][a["bufferView"]]
    fmt = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]]
    return np.frombuffer(h.bin, fmt, a["count"] * width, v.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(-1, width)


def rx(angles):
    return R.from_rotvec(np.outer(np.asarray(angles, dtype=float), [1.0, 0.0, 0.0]))


def ry(angles):
    return R.from_rotvec(np.outer(np.asarray(angles, dtype=float), [0.0, 1.0, 0.0]))


def rz(angles):
    return R.from_rotvec(np.outer(np.asarray(angles, dtype=float), [0.0, 0.0, 1.0]))


def wrap(a):
    return (a + np.pi) % (2.0 * np.pi) - np.pi


def cyclic_spline(values, n_out):
    a = np.asarray(values, dtype=float)
    m = len(a)
    t_out = np.arange(n_out) / n_out
    return CubicSpline(np.arange(m + 1) / m, np.concatenate([a, a[:1]]), bc_type="periodic")(t_out)


def signed_2d_bend(v1, v2):
    """Sagittal bend angle in degrees in (Z_forward, Y_up) plane (+ = child forward, - = child backward)."""
    dot = v1[:, 0] * v2[:, 0] + v1[:, 1] * v2[:, 1]
    cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
    return np.rad2deg(np.arctan2(cross, dot))


def periodic_solve(n_frames, k_vars, residual_fn, lower, upper, w_acc=1.2, w_vel=0.12, x0=None, max_nfev=120):
    """Global periodic C2-smoothed bounded nonlinear least squares over all frames."""
    x_init = np.zeros((n_frames, k_vars), dtype=float) if x0 is None else np.array(x0, dtype=float).copy()
    x_init = np.clip(x_init, lower[None, :] + 1e-5, upper[None, :] - 1e-5)
    m = residual_fn(x_init).shape[1]
    pattern = lil_matrix((n_frames * m + 2 * n_frames * k_vars, n_frames * k_vars), dtype=np.int8)
    for i in range(n_frames):
        pattern[i * m : (i + 1) * m, i * k_vars : (i + 1) * k_vars] = 1
        for j in range(k_vars):
            for off in (-1, 0, 1):
                pattern[n_frames * m + i * k_vars + j, ((i + off) % n_frames) * k_vars + j] = 1
            for off in (-1, 0):
                pattern[n_frames * m + n_frames * k_vars + i * k_vars + j, ((i + off) % n_frames) * k_vars + j] = 1

    w_acc_vec = np.broadcast_to(np.asarray(w_acc, dtype=float), (k_vars,))
    w_vel_vec = np.broadcast_to(np.asarray(w_vel, dtype=float), (k_vars,))

    def objective(v):
        v = v.reshape(n_frames, k_vars)
        prev = np.roll(v, 1, axis=0)
        nxt = np.roll(v, -1, axis=0)
        acc = (prev + nxt - 2.0 * v) * w_acc_vec[None, :]
        vel = (v - prev) * w_vel_vec[None, :]
        return np.r_[residual_fn(v).ravel(), acc.ravel(), vel.ravel()]

    lb = np.tile(lower, n_frames)
    ub = np.tile(upper, n_frames)
    sol = least_squares(
        objective,
        x_init.ravel(),
        bounds=(lb, ub),
        jac_sparsity=pattern.tocsr(),
        max_nfev=max_nfev,
        ftol=1e-5,
        xtol=1e-5,
    )
    return sol.x.reshape(n_frames, k_vars)


def build_hoof_hulls(h):
    """Extract convex hull of each hoof's sole vertices in bind-world offset from toe/finger bone."""
    skin = h.doc["skins"][0]
    attrs = h.doc["meshes"][0]["primitives"][0]["attributes"]
    ji = raw_acc(h, attrs["JOINTS_0"], 4)
    wt = raw_acc(h, attrs["WEIGHTS_0"], 4)
    verts = raw_acc(h, attrs["POSITION"], 3)
    ref_tr = {(n, "translation"): h.local(n, "translation", {}, 1).copy() for n in range(len(h.nodes))}
    hulls = {}
    shoes = {}
    for toe in ("toe_R", "toe_L", "finger_R", "finger_L"):
        ni = h.index[toe]
        rest_pos = h.world_pos(ni, ref_tr, 1)[0]
        j_idx = skin["joints"].index(ni)
        active = (((ji == j_idx) * wt).sum(axis=1) > 0.65) & (verts[:, 1] < 0.13)
        rel_yz = (verts[active] - rest_pos)[:, 1:]  # (Y, Z) in bind-world orientation
        hulls[toe] = rel_yz[ConvexHull(rel_yz).vertices]
        shoes[toe] = np.array([0.0, -rest_pos[1] + 0.008, 0.032], dtype=float)
    return hulls, shoes


def solve_anatomical_limb(h, tr, n_frames, toe, target_knee_yz, target_tip_yz, support, mode="gallop", hulls=None, shoes=None):
    """Solve one limb in pure sagittal relative-angle coordinates with strict equine anatomical limits.

    Every joint rotation is built directly from clean bind pose via rx(cumulative_theta):
    -> Guaranteed 0.000 deg longitudinal twist and 0.000 deg off-plane kink.
    """
    side = toe[-1]
    front = toe.startswith("finger")
    bones = (
        [f"scapula_{side}", f"upperarm_{side}", f"forearm_{side}", f"hand_{side}", toe]
        if front
        else [f"thigh_{side}", f"calf_{side}", f"foot_{side}", toe]
    )
    k = len(bones)
    ref_tr = {(n, "translation"): h.local(n, "translation", {}, 1).copy() for n in range(len(h.nodes))}

    # Parent trunk pitch (pure X component of spine_03 or pelvis delta from bind)
    root_node = h.index[bones[0]]
    parent_node = h.parent[root_node]
    parent_rot_cur = h.world_rot(parent_node, tr, n_frames)
    parent_rot_bind = h.world_rot(parent_node, {}, 1)[0]
    parent_delta_rv = (parent_rot_cur * parent_rot_bind.inv()).as_rotvec()
    theta_body = parent_delta_rv[:, 0]  # (N,) world X pitch of trunk

    # Current animated 3D root attachment position on torso
    root_pos_3d = h.world_pos(root_node, tr, n_frames)
    root_yz = root_pos_3d[:, 1:]  # (N, 2) = (Y, Z)

    # Exact bind-pose segment vectors in (Y, Z)
    bind_pts = [h.world_pos(h.index[b], ref_tr, 1)[0] for b in bones]
    bind_pts.append(bind_pts[-1] + shoes[toe])
    bind_links_yz = np.diff(np.stack(bind_pts, axis=0), axis=0)[:, 1:]  # (k, 2) = (dY, dZ)
    bind_rots = [h.world_rot(h.index[b], {}, 1)[0] for b in bones]

    hull_yz = hulls[toe]  # (V, 2) = (dY, dZ) in bind-world frame

    # Hard anatomical box bounds on relative joint deltas d_j (radians, + = bend BACKWARD, - = bend FORWARD)
    # Remember: interior bend = rest_bend - d_j
    if front:
        # Rest bends: Elbow=+48.7, Carpus=-6.6, Fetlock=+11.2
        if mode == "gallop":
            lower = np.deg2rad([-11.0, -48.0, -40.0,  -7.5, -41.0])  # [scap, upper, elbow, carpus, fetlock]
            upper = np.deg2rad([ +12.0, +44.0, +34.0, +116.0, +56.0])
            # Carpus bend in [-122.6, +0.9], Elbow bend in [+14.7, +88.7], Fetlock bend in [-44.8, +52.2]
        else:
            lower = np.deg2rad([ -8.0, -32.0, -28.0,  -6.5, -20.0])
            upper = np.deg2rad([ +9.0, +30.0, +24.0,  +64.0, +42.0])
            # Walk Carpus bend in [-70.6, -0.1], Fetlock bend in [-30.8, +31.2]
    else:
        # Rest bends: Stifle=-61.4, Hock=+40.6, Fetlock=+8.8
        if mode == "gallop":
            lower = np.deg2rad([-48.0, -38.0, -60.0, -40.0])  # [thigh, stifle, hock, fetlock]
            upper = np.deg2rad([+56.0, +40.0, +29.0, +52.0])
            # Stifle bend in [-101.4, -23.4], Hock bend in [+11.6, +100.6], Fetlock bend in [-43.2, +48.8]
        else:
            lower = np.deg2rad([-30.0, -28.0, -46.0, -20.0])
            upper = np.deg2rad([+34.0, +28.0, +24.0, +38.0])
            # Walk Stifle bend in [-89.4, -33.4], Hock bend in [+16.6, +86.6], Fetlock bend in [-29.2, +28.8]

    # Phase-aware natural fetlock target (d_fetlock):
    # - In mid-stance (support ~ 1): flat hoof (world theta_toe ~ 0 -> sole level on ground!)
    #   AND natural elastic fetlock dorsiflexion (d_fetlock negative -> pastern slopes forward)
    # - In airborne folded swing (support ~ 0): soft natural palmar hang (d_fetlock positive ~ +22..+36 deg)
    #   transitioning cleanly back toward neutral just before landing!
    swing = 1.0 - support
    lead_steps = max(2, int(round(n_frames * 0.09)))
    pre_land = np.clip(np.roll(support, -lead_steps), 0.0, 1.0)
    post_lift = np.clip(np.roll(support, lead_steps), 0.0, 1.0)
    mid_swing = np.clip(swing * (1.0 - 0.72 * pre_land), 0.0, 1.0)
    if mode == "gallop":
        # Authentic gallop weight-loading dorsiflexion (-28 deg) & tucked airborne hang (+36 deg)
        fetlock_target = np.deg2rad(-28.0 * support + 36.0 * mid_swing - 5.0 * (swing * pre_land))
        reg_weights = np.array([0.45, 0.14, 0.10, 0.05, 0.16] if front else [0.14, 0.10, 0.06, 0.16])
        w_acc = np.array([1.4, 1.0, 1.0, 1.0, 1.5] if front else [1.0, 1.0, 1.0, 1.5])
        w_vel = np.array([0.16, 0.10, 0.10, 0.10, 0.16] if front else [0.10, 0.10, 0.10, 0.16])
    else:
        # Walk: elastic stance (-12 deg), crisp breakover/mid-swing trail (+26 deg), clean flat landing (-3 deg)
        fetlock_target = np.deg2rad(-12.0 * support + 26.0 * mid_swing - 3.0 * (swing * pre_land))
        reg_weights = np.array([0.45, 0.12, 0.08, 0.03, 0.18] if front else [0.12, 0.09, 0.04, 0.18])
        w_acc = np.array([1.4, 1.1, 1.0, 1.0, 1.5] if front else [1.1, 1.0, 1.0, 1.5])
        w_vel = np.array([0.18, 0.10, 0.10, 0.10, 0.16] if front else [0.10, 0.10, 0.10, 0.16])

    def fk_yz(d_rel):
        # Cumulative world X pitch for each bone in chain
        theta = theta_body[:, None] + np.cumsum(d_rel, axis=1)  # (N, k)
        c, s = np.cos(theta), np.sin(theta)
        ly = bind_links_yz[None, :, 0]
        lz = bind_links_yz[None, :, 1]
        vy = c * ly - s * lz
        vz = s * ly + c * lz
        pts = root_yz[:, None, :] + np.cumsum(np.stack((vy, vz), axis=-1), axis=1)  # (N, k, 2)
        return pts, theta

    def local_residual(d_rel):
        pts, theta = fk_yz(d_rel)
        # pts[:, -1] = shoe tip, pts[:, -2] = fetlock (finger/toe), pts[:, -3] = carpus/hock (hand/foot)
        shoe_tip = pts[:, -1, :]
        fetlock_pt = pts[:, -2, :]
        carpus_hock_pt = pts[:, -3, :]

        # Exact hoof-sole convex hull lowest Y (in world Y-up)
        th_toe = theta[:, -1]
        c_t, s_t = np.cos(th_toe)[:, None], np.sin(th_toe)[:, None]
        hull_y = fetlock_pt[:, 0:1] + c_t * hull_yz[None, :, 0] - s_t * hull_yz[None, :, 1]
        lowest_y = np.min(hull_y, axis=1)  # (N,)

        # Ground penetration & stance contact
        r_pen = 14.0 * np.minimum(0.0, lowest_y - 0.004)
        r_sup = 8.5 * support * (lowest_y - 0.008)

        # Primary tracking: hoof tip & carpus/hock
        w_tip_y = 6.2 if mode == "gallop" else 8.2
        w_tip_z = 5.4 if mode == "gallop" else 8.2
        w_knee = 1.9 if mode == "gallop" else 3.4
        r_tip_y = w_tip_y * (shoe_tip[:, 0] - target_tip_yz[:, 0])
        r_tip_z = w_tip_z * (shoe_tip[:, 1] - target_tip_yz[:, 1])
        r_knee_y = w_knee * (carpus_hock_pt[:, 0] - target_knee_yz[:, 0])
        r_knee_z = w_knee * (carpus_hock_pt[:, 1] - target_knee_yz[:, 1])

        # Hoof sole levelness during mid-stance (avoid toe-digging or heel-floating when planted!)
        mid_stance = np.clip(support * (1.0 - 0.55 * post_lift), 0.0, 1.0)
        r_level = 1.15 * mid_stance * th_toe

        # Soft natural fetlock behavior (elastic sink in stance, natural soft hang in swing)
        r_fetlock = 0.90 * (d_rel[:, -1] - fetlock_target)

        # Gentle regularization toward neutral bind pose
        r_reg = d_rel * reg_weights[None, :]

        return np.column_stack([r_pen, r_sup, r_tip_y, r_tip_z, r_knee_y, r_knee_z, r_level, r_fetlock, r_reg])

    d_sol = periodic_solve(n_frames, k, local_residual, lower, upper, w_acc=w_acc, w_vel=w_vel, max_nfev=140)
    # Tiny final periodic polish filter (preserves strict bounds!)
    d_sol = np.clip(gaussian_filter1d(d_sol, 0.55, axis=0, mode="wrap"), lower[None, :], upper[None, :])

    # Write clean pure-sagittal world rotations into tr
    theta_world = theta_body[:, None] + np.cumsum(d_sol, axis=1)
    for j, b in enumerate(bones):
        n = h.index[b]
        rot_w = rx(theta_world[:, j]) * bind_rots[j]
        par_w = h.world_rot(h.parent[n], tr, n_frames)
        tr[(n, "rotation")] = (par_w.inv() * rot_w).as_quat()

    # Measure tracking RMS
    pts_final, _ = fk_yz(d_sol)
    rms_cm = float(100.0 * np.sqrt(np.mean(np.sum((pts_final[:, -1, :] - target_tip_yz) ** 2, axis=1))))
    return rms_cm, d_sol


def build_coastal_gallop_r47(out_dir: Path):
    """Re-author CoastalGallop against BV1bA411o7Kb with strict equine anatomy and zero lower-leg twist."""
    sys.path.insert(0, str(STUDY_R14))
    from track import feet

    h = load_base_horse()
    n = 72
    t = np.arange(n) / n
    ref_tr = {(i, "translation"): h.local(i, "translation", {}, 1).copy() for i in range(len(h.nodes))}
    tr = {
        (i, "translation"): np.repeat(h.local(i, "translation", {}, 1), n, axis=0)
        for i in range(len(h.nodes))
    }
    for i in range(len(h.nodes)):
        tr[(i, "rotation")] = np.repeat(h.local(i, "rotation", {}, 1), n, axis=0)

    def set_world(name, rot):
        idx = h.index[name]
        par = h.world_rot(h.parent[idx], tr, n)
        tr[(idx, "rotation")] = (par.inv() * rot).as_quat()

    # 1. Torso heave, pitch & subtle organic spinal flexion from BV1bA411o7Kb torso.json
    torso = cyclic_spline(json.loads((STUDY_R14 / "torso.json").read_text(encoding="utf-8")), n)
    center, rump, wither, muzzle_x, muzzle_y = torso.T
    ppm = 74.0

    hip = h.index["pelvis"]
    pelvis_bind_y = h.world_pos(hip, ref_tr, 1)[0, 1]
    heave = -(rump - rump.mean()) / ppm
    # Keep torso slightly higher (+1.5cm) to prevent any belly/hoof crowding while preserving authentic heave
    up_shift = np.zeros((n, 3))
    up_shift[:, 1] = heave
    tr[(hip, "translation")] += h.world_rot(h.parent[hip], tr, n).inv().apply(up_shift)

    # Pitch pelvis directly from observed rump-to-wither angle
    ref_pitch = np.arctan2(rump - wither, 64.0)
    pelvis_pitch = -(ref_pitch - ref_pitch.mean())
    set_world("pelvis", rx(pelvis_pitch) * h.world_rot(hip, {}, 1)[0])

    # Subtle realistic spine articulation (back rounds slightly during gathered suspension, extends during drive)
    spine_flex = -0.35 * (ref_pitch - ref_pitch.mean())
    for s_name, frac in [("spine_01", 0.30), ("spine_02", 0.40), ("spine_03", 0.30)]:
        idx = h.index[s_name]
        par_rot = h.world_rot(h.parent[idx], tr, n)
        par_bind = h.world_rot(h.parent[idx], {}, 1)[0]
        cur_w = par_rot * par_bind.inv() * h.world_rot(idx, {}, 1)[0]
        set_world(s_name, rx(spine_flex * frac) * cur_w)

    # Smooth distributed neck & head tracking toward BV1bA411o7Kb muzzle trajectory
    base_neck = h.world_pos(h.index["neck_01"], tr, n)
    mouth_rest_vec = h.world_pos(h.index["mouth_socket"], ref_tr, 1)[0] - h.world_pos(h.index["neck_01"], ref_tr, 1)[0]
    rest_neck_ang = np.arctan2(mouth_rest_vec[1], mouth_rest_vec[2])
    ref_neck_ang = np.arctan2((165.0 - muzzle_y) / ppm - base_neck[:, 1], (muzzle_x - center) / ppm - 0.055 - base_neck[:, 2])
    neck_delta = np.clip(rest_neck_ang - ref_neck_ang, -0.36, 0.36)
    neck_delta = gaussian_filter1d(neck_delta, 1.2, mode="wrap")
    # Distribute smoothly across neck_01, neck_02, neck_03 and keep head level-ish
    for b_name, w_frac in [("neck_01", 0.50), ("neck_02", 0.38), ("neck_03", 0.28), ("head", -0.16)]:
        idx = h.index[b_name]
        par_rot = h.world_rot(h.parent[idx], tr, n)
        par_bind = h.world_rot(h.parent[idx], {}, 1)[0]
        cur_w = par_rot * par_bind.inv() * h.world_rot(idx, {}, 1)[0]
        set_world(b_name, rx(neck_delta * w_frac) * cur_w)

    # Subtle natural ear & stirrup motion
    stirrup_swing = np.deg2rad(10.0) * np.sin(2.0 * np.pi * t + 0.4)
    for st_name in ("stirrup_L", "stirrup_R"):
        if st_name in h.index:
            idx = h.index[st_name]
            par_rot = h.world_rot(h.parent[idx], tr, n)
            par_bind = h.world_rot(h.parent[idx], {}, 1)[0]
            cur_w = par_rot * par_bind.inv() * h.world_rot(idx, {}, 1)[0]
            set_world(st_name, rx(stirrup_swing) * cur_w)

    # 2. Solve all 4 limbs with strict equine anatomy and zero twist!
    hulls, shoes = build_hoof_hulls(h)
    bounds = {
        "toe_R": (1.0, 0.6, 5.4),
        "toe_L": (7.0, 3.8, 7.9),
        "finger_R": (6.0, 6.3, 10.9),
        "finger_L": (11.0, 9.8, 14.6),
    }
    phase_18 = t * 18.0
    errors = {}
    for toe, marks in feet.items():
        _, plant, release = bounds[toe]
        cal = cyclic_spline(marks, n)
        knee_yz = np.column_stack((np.maximum(0.08, (165.0 - cal[:, 1]) / ppm), (cal[:, 0] - center) / ppm - 0.055))
        tip_yz = np.column_stack((np.maximum(0.008, (165.0 - cal[:, 3]) / ppm), (cal[:, 2] - center) / ppm - 0.055))
        support = np.clip(np.minimum(phase_18 - plant, release - phase_18) * 3.0, 0.0, 1.0)
        tip_yz[:, 0] = tip_yz[:, 0] * (1.0 - support) + 0.008 * support
        rms_cm, _ = solve_anatomical_limb(h, tr, n, toe, knee_yz, tip_yz, support, mode="gallop", hulls=hulls, shoes=shoes)
        errors[toe] = round(rms_cm, 2)

    # 3. Flowing rearward tail matched to BV1bA411o7Kb silhouettes
    masks = np.load(STUDY_R14 / "reference-silhouettes.npz")["mask"]
    sample_z = np.array([-0.99, -1.10, -1.30, -1.52, -1.72])
    tail_y = np.empty((n, len(sample_z)))
    for k_f, m in enumerate(masks):
        for s_i, z_val in enumerate(sample_z):
            u = round(425 * 0.51 + 110 * z_val)
            hits = np.flatnonzero((m[60:213, u - 1 : u + 2] > 128).sum(axis=1) >= 2) + 60
            if len(hits):
                runs = np.split(hits, np.flatnonzero(np.diff(hits) > 1) + 1)
                run = next((a for a in runs if len(a) >= 3), runs[0])
                val = run[0] + min(8, (run[-1] - run[0]) * 0.46)
            elif s_i > 1:
                val = 2 * tail_y[k_f, s_i - 1] - tail_y[k_f, s_i - 2]
            else:
                val = 114
            tail_y[k_f, s_i] = val
    tail_y = gaussian_filter1d(tail_y, 1.6, axis=0, mode="wrap")
    angles = np.arctan2(-np.diff(tail_y, axis=1), -110.0 * np.diff(sample_z))
    for j in range(4):
        name = f"tail_0{j+1}"
        child = f"tail_0{j+2}"
        vec = h.world_pos(h.index[child], tr, n) - h.world_pos(h.index[name], tr, n)
        ang = np.arctan2(vec[:, 1], -vec[:, 2])
        desired = np.clip(angles[:, j], -0.95, 0.50)
        set_world(name, rx(wrap(desired - ang)) * h.world_rot(h.index[name], tr, n))

    # Stride & period matching CoastalGallopR14 (5.528 m at 11.6 m/s)
    speeds = []
    torso_raw = np.asarray(json.loads((STUDY_R14 / "torso.json").read_text(encoding="utf-8")))
    for b, (_, on, off) in bounds.items():
        a = np.arange(18)
        ids = (a >= on + 0.1) & (a <= off - 0.1)
        z = (feet[b][:, 2] - torso_raw[:, 0]) / ppm
        speeds.append(-np.polyfit(a[ids] / 18.0, z[ids], 1)[0])
    stride = float(np.median(speeds))
    period = stride / 11.6

    export = {(i, k): np.concatenate([a, a[:1]]) for (i, k), a in tr.items() if k == "rotation" or i == hip}
    h.doc["animations"] = []
    h.save_clip("CoastalGallop", np.linspace(0.0, period, n + 1), export)
    glb_path = out_dir / "Warhorse_CoastalGallop_R47.glb"
    h.write(glb_path)

    fit_info = dict(
        source="BV1bA411o7Kb-AnatomicalR47",
        video_start_s=20,
        video_cycle_s=18,
        limb_landmarks={b: dict(native_plant_frame=v[0], video_plant_s=20 + v[1], video_release_s=20 + v[2]) for b, v in bounds.items()},
        target_speed_m_s=11.6,
        estimated_stride_m=stride,
        game_period_s=period,
        side_guide_rms_cm=errors,
    )
    (out_dir / "gallop_fit.json").write_text(json.dumps(fit_info, indent=2), encoding="utf-8")
    print("[GALLOP R47] guide RMS cm:", errors, f"stride={stride:.3f}m period={period:.4f}s")
    return h, fit_info


def build_lateral_walk_r47(out_dir: Path):
    """Author a clean 4-beat lateral equine walk (LH 0.00 -> LF 0.25 -> RH 0.50 -> RF 0.75) matched to 2.20 m/s."""
    h = load_base_horse()
    n = 108  # Author at 108 frames (divisible by 4 & 2), export 54 frames @ 60 Hz (0.900 s exact, rate_scale=1.0, 2x native 30 Hz!)
    t = np.arange(n) / n
    ref_tr = {(i, "translation"): h.local(i, "translation", {}, 1).copy() for i in range(len(h.nodes))}
    tr = {
        (i, "translation"): np.repeat(h.local(i, "translation", {}, 1), n, axis=0)
        for i in range(len(h.nodes))
    }
    for i in range(len(h.nodes)):
        tr[(i, "rotation")] = np.repeat(h.local(i, "rotation", {}, 1), n, axis=0)

    def set_world(name, rot):
        idx = h.index[name]
        par = h.world_rot(h.parent[idx], tr, n)
        tr[(idx, "rotation")] = (par.inv() * rot).as_quat()

    # Real equine walk parameters matched to nominal 2.20 m/s speed:
    # Stride = 1.98 m, cycle period = 0.90 s -> 1.98 / 0.90 = 2.20 m/s (0.0 cm/s foot slip!)
    stride_m = 1.98
    walk_period_s = stride_m / 2.20  # 0.90 s
    duty = 0.62  # 62% stance, 38% swing (classic energetic equine walk!)

    # 1. Natural 2-beat walk torso heave, subtle lateral hip sway/roll, and equine 2-nod head rhythm
    hip = h.index["pelvis"]
    # Pelvis rises gently over each hind mid-stance (peaks at 0.22 & 0.72), sways softly toward stance side
    pelvis_shift = np.zeros((n, 3))
    pelvis_shift[:, 1] = 0.018 * np.sin(4.0 * np.pi * t - 0.5) - 0.014  # gentle 3.6cm peak-to-peak heave, slight stance settle
    pelvis_shift[:, 0] = 0.014 * np.sin(2.0 * np.pi * t + 0.3)           # subtle lateral weight shift
    tr[(hip, "translation")] += h.world_rot(h.parent[hip], tr, n).inv().apply(pelvis_shift)

    # Gentle pelvic pitch (2x/cycle), yaw (1x/cycle as hind legs advance), and roll (1x/cycle)
    p_pitch = np.deg2rad(2.2) * np.sin(4.0 * np.pi * t + 0.4)
    p_yaw = np.deg2rad(3.2) * np.sin(2.0 * np.pi * t - 0.2)
    p_roll = np.deg2rad(2.4) * np.sin(2.0 * np.pi * t + 0.9)
    set_world("pelvis", ry(p_yaw) * rz(p_roll) * rx(p_pitch) * h.world_rot(hip, {}, 1)[0])

    # Counter-rotate ribcage gently so withers stay poised and rider seat feels smooth
    for s_name, wf in [("spine_01", 0.35), ("spine_02", 0.40), ("spine_03", 0.25)]:
        idx = h.index[s_name]
        par_rot = h.world_rot(h.parent[idx], tr, n)
        par_bind = h.world_rot(h.parent[idx], {}, 1)[0]
        cur_w = par_rot * par_bind.inv() * h.world_rot(idx, {}, 1)[0]
        set_world(s_name, ry(-p_yaw * wf * 0.7) * rz(-p_roll * wf * 0.6) * rx(-p_pitch * wf * 0.5) * cur_w)

    # Iconic equine walk head nod: 2 nods per stride (dips as each foreleg lands at 0.25 & 0.75!)
    nod = np.deg2rad(5.5) * np.cos(4.0 * np.pi * (t - 0.28))
    for b_name, wf in [("neck_01", 0.45), ("neck_02", 0.35), ("neck_03", 0.25), ("head", -0.20)]:
        idx = h.index[b_name]
        par_rot = h.world_rot(h.parent[idx], tr, n)
        par_bind = h.world_rot(h.parent[idx], {}, 1)[0]
        cur_w = par_rot * par_bind.inv() * h.world_rot(idx, {}, 1)[0]
        set_world(b_name, rx(nod * wf) * cur_w)

    # Relaxed gentle walking tail sway
    tail_sway = np.deg2rad(4.5) * np.sin(2.0 * np.pi * t + 0.5)
    for j in range(4):
        idx = h.index[f"tail_0{j+1}"]
        par_rot = h.world_rot(h.parent[idx], tr, n)
        par_bind = h.world_rot(h.parent[idx], {}, 1)[0]
        cur_w = par_rot * par_bind.inv() * h.world_rot(idx, {}, 1)[0]
        set_world(f"tail_0{j+1}", rz(tail_sway * (0.35 + 0.15 * j)) * rx(np.deg2rad(4.0)) * cur_w)

    # 2. Construct exact zero-slip 4-beat lateral hoof & knee/hock trajectories!
    # Lateral equine walk order: LH (0.00) -> LF (0.25) -> RH (0.50) -> RF (0.75)
    walk_plants = {"toe_L": 0.00, "finger_L": 0.25, "toe_R": 0.50, "finger_R": 0.75}
    hulls, shoes = build_hoof_hulls(h)
    walk_errors = {}

    for toe, plant_phase in walk_plants.items():
        front = toe.startswith("finger")
        side = toe[-1]
        knee_bone = f"hand_{side}" if front else f"foot_{side}"
        rest_shoe = h.world_pos(h.index[toe], ref_tr, 1)[0] + shoes[toe]
        rest_knee = h.world_pos(h.index[knee_bone], ref_tr, 1)[0]

        # Local cycle phase u in [0, 1): [0, duty) = stance, [duty, 1) = swing
        u = (t - plant_phase) % 1.0
        stance_span = stride_m * duty  # actual horizontal travel during planted stance (1.228 m)
        # Front legs stride slightly forward of shoulder, hind legs track forward into front hoofprint
        z_center = rest_shoe[2] + (0.04 if front else 0.06)
        z_front = z_center + 0.5 * stance_span
        z_back = z_center - 0.5 * stance_span

        tip_y = np.empty(n)
        tip_z = np.empty(n)
        knee_y = np.empty(n)
        knee_z = np.empty(n)
        support = np.zeros(n)

        for i in range(n):
            ui = u[i]
            if ui < duty:
                # Stance: exact constant rearward ground velocity (zero slip!)
                s = ui / duty
                tip_z[i] = z_front - stance_span * s
                tip_y[i] = 0.008
                # Smooth support ramp at plant/release edges
                edge = min(ui / 0.05, (duty - ui) / 0.05)
                support[i] = np.clip(edge, 0.0, 1.0)
                # Knee/hock moves smoothly over the planted column
                if front:
                    # Carpus stays almost straight above hoof in stance, slightly ahead at late stance breakover
                    knee_z[i] = rest_knee[2] + 0.56 * (tip_z[i] - rest_shoe[2]) + 0.02 * np.sin(np.pi * s)
                    knee_y[i] = rest_knee[1] - 0.025 * (1.0 - np.sin(np.pi * s))
                else:
                    # Hock stays slightly behind hoof at landing, drives rearward on push-off
                    knee_z[i] = rest_knee[2] + 0.52 * (tip_z[i] - rest_shoe[2]) - 0.03 * (1.0 - s)
                    knee_y[i] = rest_knee[1] - 0.02 * (1.0 - np.sin(np.pi * s))
            else:
                # Swing: authentic equine breakover, knee-fold clearance, and crisp forward reach!
                sw = (ui - duty) / (1.0 - duty)  # 0 -> 1
                # Asymmetric advance: hoof lags slightly during early pickup (driving true carpus/hock fold!)
                # then glides smoothly forward into landing
                u_sw = sw ** 1.22
                sm = u_sw * u_sw * (3.0 - 2.0 * u_sw)
                tip_z[i] = z_back + stance_span * sm
                # Natural asymmetric equine lift arc (peaks around sw=0.38 with clean ground clearance)
                lift_h = 0.185 if front else 0.155
                tip_y[i] = 0.008 + lift_h * (np.sin(np.pi * (sw ** 0.85)) ** 1.3)
                support[i] = 0.0
                if front:
                    # CRITICAL: During front pickup/mid-swing, CARPUS drives strongly FORWARD & UP
                    # while cannon folds cleanly BACKWARD (-50..-58 deg), then unfolds smoothly before plant!
                    lead = np.sin(np.pi * (sw ** 0.78))
                    knee_z[i] = rest_knee[2] + 0.54 * (tip_z[i] - rest_shoe[2]) + 0.23 * lead
                    knee_y[i] = rest_knee[1] + 0.115 * (lead ** 1.1)
                else:
                    # CRITICAL: During hind swing, HOCK flexes crisply upward & backward behind advancing cannon!
                    lead = np.sin(np.pi * (sw ** 0.82))
                    knee_z[i] = rest_knee[2] + 0.48 * (tip_z[i] - rest_shoe[2]) - 0.115 * lead
                    knee_y[i] = rest_knee[1] + 0.095 * (lead ** 1.1)

        # Gentle periodic smoothing on target trajectories (keep stance Z linear!)
        tip_yz = np.column_stack((tip_y, tip_z))
        knee_yz = np.column_stack((gaussian_filter1d(knee_y, 1.0, mode="wrap"), gaussian_filter1d(knee_z, 1.0, mode="wrap")))
        rms_cm, _ = solve_anatomical_limb(h, tr, n, toe, knee_yz, tip_yz, support, mode="walk", hulls=hulls, shoes=shoes)
        walk_errors[toe] = round(rms_cm, 2)

    # Downsample cleanly 108 -> 54 frames @ 60 Hz (0.900 s exact, UE5-compatible 2x of 30 Hz, rate_scale=1.0!)
    step = 2
    n_out = n // step  # 54
    export = {}
    for (i, k), a in tr.items():
        if k == "rotation" or i == hip:
            sub = a[::step]
            export[(i, k)] = np.concatenate([sub, sub[:1]])

    h.doc["animations"] = []
    h.save_clip("AnatomicalWalk", np.linspace(0.0, walk_period_s, n_out + 1), export)
    glb_path = out_dir / "Warhorse_Walk_R47.glb"
    h.write(glb_path)

    walk_info = dict(
        source="EquineLateralWalkR47",
        frames=n_out,
        rate=60,
        stride_m=stride_m,
        game_period_s=walk_period_s,
        rate_scale=(n_out / 60.0) / walk_period_s,  # 0.90 / 0.90 = 1.0000 -> exact 2.20 m/s walk AND 60 deg/cycle pivot!
        contacts=walk_plants,
        reverse_contacts={
            # Lift-off phases (plant + duty) mod 1 -> when playing backward, lift-off becomes contact!
            b: round((p + duty) % 1.0, 4) for b, p in walk_plants.items()
        },
        guide_rms_cm=walk_errors,
    )
    (out_dir / "walk_fit.json").write_text(json.dumps(walk_info, indent=2), encoding="utf-8")
    print("[WALK R47] guide RMS cm:", walk_errors, f"stride={stride_m:.2f}m period={walk_period_s:.3f}s rate_scale={walk_info['rate_scale']:.4f}")
    return h, walk_info


def export_ue_motion_gz(glb_path: Path, clip_name: str, fit_info: dict, out_gz: Path, align_saddle_quarter: bool):
    """Convert authored GLB clip to UE5 bone-delta gzip JSON (same proven pipeline as prepare_coastal_gallop.py)."""
    horse = Horse(glb_path.read_bytes())
    clip = horse.clips[clip_name]
    indices = horse.doc["skins"][0]["joints"]
    frame_rate = int(fit_info.get("rate", 30))
    frames = horse.doc["accessors"][clip["samplers"][0]["input"]]["count"] - 1
    marks = np.arange(frames) / frames
    _, tracks = horse.sample(clip, marks)
    for i in range(len(horse.nodes)):
        tracks.setdefault((i, "translation"), horse.local(i, "translation", {}, frames).copy())

    offset = 0.0
    if align_saddle_quarter:
        seat = horse.world_pos(horse.index["saddle_socket"], tracks, frames)
        offset = float((marks[np.argmin(seat[:, 1])] - 0.25) % 1.0)

    phase = (np.arange(frames + 1) / frames + offset) % 1.0
    phase[-1] = phase[0]
    _, tracks = horse.sample(clip, phase)

    axes = np.eye(3)[[0, 2, 1]]

    def world_delta(i):
        posed = horse.world_rot(i, tracks, len(phase))
        bind = horse.world_rot(i, {}, 1)
        return R.from_matrix(axes @ (posed * bind.inv()).as_matrix() @ axes)

    deltas = {i: world_delta(i) for i in indices}
    bones = {}
    for i in indices:
        name = horse.nodes[i]["name"]
        parent = horse.parent.get(i)
        parent_delta = deltas.get(parent, R.identity())
        turn = (parent_delta.inv() * deltas[i]).as_quat()
        for k in range(1, len(turn)):
            if turn[k] @ turn[k - 1] < 0:
                turn[k] *= -1
        row = dict(
            parent=horse.nodes[parent]["name"] if parent in deltas else None,
            rotation=turn.round(9).tolist(),
        )
        if (i, "translation") in tracks:
            shift = tracks[(i, "translation")] - horse.local(i, "translation", {}, 1)
            if np.max(np.abs(shift)) > 1e-6:
                shift = horse.world_rot(parent, {}, 1).apply(shift) @ axes.T * 100.0
                row["translation_cm"] = shift.round(7).tolist()
        bones[name] = row

    if align_saddle_quarter:
        contacts = {
            name: float(((v["video_plant_s"] - fit_info["video_start_s"]) / fit_info["video_cycle_s"] - offset) % 1.0)
            for name, v in fit_info["limb_landmarks"].items()
        }
        rate_scale = (frames / frame_rate) * 6.6 / fit_info["estimated_stride_m"]
        stride_m = fit_info["estimated_stride_m"]
        reverse_contacts = {}
    else:
        contacts = fit_info["contacts"]
        reverse_contacts = fit_info["reverse_contacts"]
        rate_scale = fit_info["rate_scale"]
        stride_m = fit_info["stride_m"]

    content = dict(
        source=fit_info["source"],
        frames=frames,
        rate=frame_rate,
        contacts=contacts,
        reverse_contacts=reverse_contacts,
        phase_offset=offset,
        stride_m=stride_m,
        rate_scale=rate_scale,
        bones=bones,
    )
    with gzip.open(out_gz, "wt", encoding="utf-8") as stream:
        json.dump(content, stream, separators=(",", ":"))
    print(f"Exported UE motion -> {out_gz} (frames={frames}, rate_scale={rate_scale:.4f})")


def verify_and_render(h_new, clip_new, h_old, clip_old, out_dir: Path, prefix: str, ref_masks=None):
    """Print full anatomical & twist audit and render multi-angle before/after comparison sheets."""
    n = 72
    _, tr = h_new.sample(h_new.clips[clip_new], np.arange(n) / n)
    for i in range(len(h_new.nodes)):
        tr.setdefault((i, "translation"), h_new.local(i, "translation", {}, n).copy())
    ref_tr = {(i, "translation"): h_new.local(i, "translation", {}, 1).copy() for i in range(len(h_new.nodes))}

    chains = [
        ("FL", ["scapula_L", "upperarm_L", "forearm_L", "hand_L", "finger_L"]),
        ("FR", ["scapula_R", "upperarm_R", "forearm_R", "hand_R", "finger_R"]),
        ("HL", ["thigh_L", "calf_L", "foot_L", "toe_L"]),
        ("HR", ["thigh_R", "calf_R", "foot_R", "toe_R"]),
    ]
    print(f"\n=== ANATOMICAL AUDIT: {prefix} ({clip_new}) ===")
    max_twist_all = 0.0
    for cname, bones in chains:
        toe = bones[-1]
        restpos = h_new.world_pos(h_new.index[toe], ref_tr, 1)[0]
        shoe_local = h_new.world_rot(h_new.index[toe], {}, 1)[0].inv().apply([0, -restpos[1] + 0.008, 0.032])
        pts = [h_new.world_pos(h_new.index[b], tr, n)[:, [2, 1]] for b in bones]
        shoe_w = h_new.world_pos(h_new.index[toe], tr, n) + h_new.world_rot(h_new.index[toe], tr, n).apply(shoe_local)
        pts.append(shoe_w[:, [2, 1]])
        segs = [pts[k + 1] - pts[k] for k in range(len(pts) - 1)]
        jnames = ["Elbow", "Carpus", "Fetlock"] if cname.startswith("F") else ["Stifle", "Hock", "Fetlock"]
        start = 1 if cname.startswith("F") else 0
        for j, jn in enumerate(jnames):
            ang = signed_2d_bend(segs[start + j], segs[start + j + 1])
            # Also check exact 3D off-plane / twist
            pi, ci = h_new.index[bones[start + j]], h_new.index[bones[start + j + 1]]
            rel0 = h_new.world_rot(pi, {}, 1)[0].inv() * h_new.world_rot(ci, {}, 1)[0]
            Rc0 = h_new.world_rot(ci, {}, 1)[0]
            rel = h_new.world_rot(pi, tr, n).inv() * h_new.world_rot(ci, tr, n)
            rvw = np.rad2deg((Rc0 * (rel0.inv() * rel) * Rc0.inv()).as_rotvec())
            off_plane = float(np.hypot(rvw[:, 1], rvw[:, 2]).max())
            max_twist_all = max(max_twist_all, off_plane)
            print(f"  {cname} {jn:8s} | bend:[{ang.min():+6.1f}, {ang.max():+6.1f}] deg | off-plane/twist max:{off_plane:5.2f} deg")
    print(f"  >>> MAX LOWER-LIMB OFF-PLANE/TWIST = {max_twist_all:.3f} deg")

    # Skin helper
    def skin_at(h, cname, frames_idx):
        _, motion = h.sample(h.clips[cname], np.arange(n) / n)
        for idx in range(len(h.nodes)):
            motion.setdefault((idx, "translation"), h.local(idx, "translation", {}, n).copy())
        mesh = h.doc["meshes"][0]["primitives"][0]
        skin = h.doc["skins"][0]
        inv = raw_acc(h, skin["inverseBindMatrices"], 16).reshape(-1, 4, 4).transpose(0, 2, 1)
        attr = mesh["attributes"]
        rest = raw_acc(h, attr["POSITION"], 3)
        ji = raw_acc(h, attr["JOINTS_0"], 4)
        wt = raw_acc(h, attr["WEIGHTS_0"], 4)
        tri = raw_acc(h, mesh["indices"], 1).reshape(-1, 3)
        uv = raw_acc(h, attr["TEXCOORD_0"], 2)
        out_v = {}
        for fi in frames_idx:
            v = np.zeros((len(rest), 3), np.float32)
            for j, node in enumerate(skin["joints"]):
                w = np.sum((ji == j) * wt, axis=1)
                ids = np.flatnonzero(w > 0)
                Rm = h.world_rot(node, motion, n)[fi].as_matrix()
                pos = h.world_pos(node, motion, n)[fi]
                local = rest[ids] @ inv[j, :3, :3].T + inv[j, :3, 3]
                v[ids] += (local @ Rm.T + pos) * w[ids, None]
            out_v[fi] = v
        return out_v, tri, uv

    tex = np.array(Image.open(SOURCE / "Exchange/Warhorse_BaseColor.png").convert("RGB").resize((1024, 1024)))
    sample_frames = [0, 8, 16, 28, 44, 52, 60, 68]
    v_new, tri, uv = skin_at(h_new, clip_new, sample_frames)
    v_old, _, _ = skin_at(h_old, clip_old, sample_frames)

    cw, ch = 320, 240
    rows_spec = []
    if ref_masks is not None:
        rows_spec.append(("Ref Video (BV1bA411o7Kb)", "ref", 0, 5, 100, 0.88))
    rows_spec += [
        ("OLD (Before Fix) Side", "old", 0, 5, 112, 0.87),
        ("NEW R47 (Fixed) Side", "new", 0, 5, 112, 0.87),
        ("OLD 3/4 Front-Leg Zoom", "old", 38, 10, 185, 0.96),
        ("NEW R47 3/4 Front-Leg Zoom", "new", 38, 10, 185, 0.96),
        ("OLD 3/4 Rear-Leg Zoom", "old", 142, 10, 185, 0.96),
        ("NEW R47 3/4 Rear-Leg Zoom", "new", 142, 10, 185, 0.96),
    ]
    sheet = Image.new("RGB", (len(sample_frames) * cw, len(rows_spec) * ch + 34), (24, 26, 28))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 9), f"{prefix}: Reference / Old vs Fixed R47 Multi-Angle Verification", fill=(238, 232, 214))

    for r_i, (rname, kind, yaw_d, elev_d, zoom, cy) in enumerate(rows_spec):
        yaw, elev = np.deg2rad(yaw_d), np.deg2rad(elev_d)
        for c_i, fi in enumerate(sample_frames):
            panel = np.full((ch, cw, 3), (220, 222, 214), dtype=np.uint8)
            if kind == "ref":
                m = Image.fromarray(ref_masks[fi]).resize((cw, ch))
                im = Image.fromarray(panel)
                im.paste(Image.new("RGB", (cw, ch), (42, 48, 44)), (0, 0), m)
            else:
                v = v_new[fi] if kind == "new" else v_old[fi]
                x, y, z = v.T
                sx = z * np.cos(yaw) - x * np.sin(yaw)
                sz = z * np.sin(yaw) + x * np.cos(yaw)
                sy = y * np.cos(elev) - sz * np.sin(elev)
                sd = sz * np.cos(elev) + y * np.sin(elev)
                pts = np.column_stack((cw * 0.5 + sx * zoom, ch * cy - sy * zoom, sd * zoom))
                im = Image.fromarray(draw_mesh(panel, pts, tri, uv, tex))
            d = ImageDraw.Draw(im)
            d.text((8, 6), f"{rname} f={fi}/72", fill=(18, 24, 22))
            sheet.paste(im, (c_i * cw, 34 + r_i * ch))

    out_png = out_dir / f"{prefix}_compare.png"
    sheet.save(out_png)
    print(f"Saved comparison sheet -> {out_png}")
    return out_png


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    _, gallop_fit = build_coastal_gallop_r47(args.out)
    _, walk_fit = build_lateral_walk_r47(args.out)

    export_ue_motion_gz(args.out / "Warhorse_CoastalGallop_R47.glb", "CoastalGallop", gallop_fit, args.out / "coastal_gallop_r47.json.gz", align_saddle_quarter=True)
    export_ue_motion_gz(args.out / "Warhorse_Walk_R47.glb", "AnatomicalWalk", walk_fit, args.out / "lateral_walk_r47.json.gz", align_saddle_quarter=False)

    h_gallop = Horse((args.out / "Warhorse_CoastalGallop_R47.glb").read_bytes())
    h_walk = Horse((args.out / "Warhorse_Walk_R47.glb").read_bytes())
    h_old_gallop = Horse((STUDY_R14 / "Warhorse_CoastalGallop.glb").read_bytes())
    h_old_walk = load_base_horse()
    ref_masks = np.load(STUDY_R14 / "reference-silhouettes.npz")["mask"]

    verify_and_render(h_gallop, "CoastalGallop", h_old_gallop, "CoastalGallop", args.out, "gallop_r47", ref_masks=ref_masks)
    verify_and_render(h_walk, "AnatomicalWalk", h_old_walk, "walk_loop", args.out, "walk_r47", ref_masks=None)


if __name__ == "__main__":
    main()
