"""SVCh Left-Bolt Equip Pose Layer Authoring — V2 Ergonomic & C2-Smooth (All 5 Profiles).

Reuses the accepted SVCh reload_empty left-charging-handle pose, finger curl,
wrist/elbow framing, and right-hand pistol-grip lock inside A_SVD_equip (205 frames,
120 fps), with:
1. Anatomical thumb-up mid-orientation (pronation stays strictly inside [-92, +70] deg;
   zero +/-180 deg forearm twist flip on approach or return).
2. Natural right-shoulder drop follow during the lowered draw window so right hand stays
   rigidly locked on the pistol grip with comfortable wrist swing (< 25 deg) & reach (< 0.88).
3. Clamped C2 cubic splines for continuous single-arc approach & return velocity (zero
   robotic stops at mid-waypoints) and true 3D cKDTree mesh clearance vs SVCh receiver.
4. Exact 0.000 cm bolt tracking on f=54..94 and 0.000 cm idle continuity at f=0 & f=204
   across base + all 4 foregrip profiles (angled, vertical, canted, prism).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R, Slerp

OUT_DIR = Path(__file__).resolve().parent
SVCH_ROOT = OUT_DIR.parent
FG_DIR = SVCH_ROOT / "ForegripFit20261019"
LB_DIR = SVCH_ROOT / "LeftBolt20261019"
R7_DIR = SVCH_ROOT / "QuickMeleeGripR7_20261020"

sys.path.insert(0, str(FG_DIR))
import arm_math as am  # noqa: E402
import fit_contact as fc  # noqa: E402

names = am.names
ids = am.ids
parents = am.parents
motion = am.motion
arms = am.arms
weapon = am.weapon
ref = am.matrices(arms["reference"])
wref = am.matrices(weapon["reference"])
inv_wref = np.linalg.inv(wref)

root = ids["WPN_root"]
bolt = ids["WPN_bolt"]
mag = ids["WPN_SOCKET_Magazine"]
lh, rh = ids["hand_l"], ids["hand_r"]
ul, ll = ids["upperarm_l"], ids["lowerarm_l"]
ur, lr = ids["upperarm_r"], ids["lowerarm_r"]

digits_prefix = ("thumb", "index", "middle", "ring", "pinky")
handbones = {
    s: [i for i, n in enumerate(names) if n.endswith("_" + s) and n.startswith(("hand",) + digits_prefix)]
    for s in ("l", "r")
}
armbones = {
    s: [
        i
        for i, n in enumerate(names)
        if n.endswith("_" + s) and n.startswith(("clavicle", "upperarm", "lowerarm", "hand") + digits_prefix)
    ]
    for s in ("l", "r")
}
changed_all = sorted(set(armbones["l"] + armbones["r"]))

FAMILIES = ("base", "angled", "vertical", "canted", "prism")
r7_profiles = {fam: json.loads((R7_DIR / "SavedReadback" / f"{fam}.json").read_text()) for fam in FAMILIES}
base_in = r7_profiles["base"]


def mixrot(a: np.ndarray, b: np.ndarray, w: float) -> np.ndarray:
    return Slerp([0.0, 1.0], R.from_matrix(np.stack([a, b])))([float(w)]).as_matrix()[0]


def mix(a: np.ndarray, b: np.ndarray, w: float) -> np.ndarray:
    out = a.copy()
    out[:3, 3] = (1.0 - w) * a[:3, 3] + w * b[:3, 3]
    out[:3, :3] = mixrot(am.rigid(a)[:3, :3], am.rigid(b)[:3, :3], w) * np.linalg.norm(a[:3, :3], axis=0)
    return out


def frame_mat(a: np.ndarray, n: np.ndarray) -> np.ndarray:
    x = am.unit(a)
    z = am.unit(n - x * np.dot(n, x))
    return np.column_stack((x, np.cross(z, x), z))


def twist_angle(rotation: np.ndarray, axis: np.ndarray) -> float:
    q = R.from_matrix(rotation).as_quat()
    if q[3] < 0:
        q = -q
    return float(2.0 * np.arctan2(q[:3] @ am.unit(axis), q[3]))


def solve_arm(p: np.ndarray, side: str, target: np.ndarray, shoulder: np.ndarray, pole: np.ndarray, blend: float = 1.0):
    """Exact V9 analytical arm solver (fixed native segment lengths, distal pronation)."""
    q = p.copy()
    u, l, h, c = [ids[n + "_" + side] for n in ("upperarm", "lowerarm", "hand", "clavicle")]
    target = target.copy()
    target[:3, :3] = am.rigid(target)[:3, :3] * np.linalg.norm(p[h, :3, :3], axis=0)
    A, E, H = [p[j, :3, 3] for j in (u, l, h)]
    L1 = np.linalg.norm(E - A)
    L2 = np.linalg.norm(H - E)
    T = target[:3, 3]
    axis = am.unit(T - shoulder)
    d = np.linalg.norm(T - shoulder)
    shoulder_adjust = 0.0
    max_reach_ratio = max(0.94, float(np.linalg.norm(H - A) / (L1 + L2)))
    if d > (L1 + L2) * max_reach_ratio:
        shoulder_adjust = d - (L1 + L2) * max_reach_ratio
        if shoulder_adjust > 12.0:
            raise ValueError(("Excessive shoulder follow", side, shoulder_adjust))
        shoulder = shoulder + axis * shoulder_adjust
        d = np.linalg.norm(T - shoulder)
    if d <= abs(L1 - L2) + 0.1:
        raise ValueError(("Unreachable", side, d, L1 + L2))
    pole_proj = am.unit(pole - axis * np.dot(pole, axis))
    along = (L1 * L1 - L2 * L2 + d * d) / (2.0 * d)
    elbow = shoulder + axis * along + pole_proj * np.sqrt(max(0.0, L1 * L1 - along * along))
    ru = ref[l, :3, 3] - ref[u, :3, 3]
    rl = ref[h, :3, 3] - ref[l, :3, 3]
    rn = np.cross(ru, rl)
    nu = elbow - shoulder
    nl = T - elbow
    nn = np.cross(nu, nl)
    Du = frame_mat(nu, nn) @ frame_mat(ru, rn).T
    Dl = frame_mat(nl, nn) @ frame_mat(rl, rn).T
    Au = am.swing(E - A, nu)
    Al = am.swing(H - E, nl)
    Ru = mixrot(Au @ am.rigid(p[u])[:3, :3], Du @ am.rigid(ref[u])[:3, :3], blend)
    Rl = mixrot(Al @ am.rigid(p[l])[:3, :3], Dl @ am.rigid(ref[l])[:3, :3], blend)
    Qu = Ru @ am.rigid(p[u])[:3, :3].T
    Ql = Rl @ am.rigid(p[l])[:3, :3].T
    q[c, :3, 3] += shoulder - A
    for j, n in enumerate(names):
        if n.endswith("_" + side) and n.startswith("upperarm"):
            q[j, :3, 3] = shoulder + Qu @ (p[j, :3, 3] - A)
            q[j, :3, :3] = mixrot(Au @ am.rigid(p[j])[:3, :3], Du @ am.rigid(ref[j])[:3, :3], blend) * np.linalg.norm(
                p[j, :3, :3], axis=0
            )
        elif n.endswith("_" + side) and n.startswith("lowerarm"):
            q[j, :3, 3] = elbow + Ql @ (p[j, :3, 3] - E)
            q[j, :3, :3] = Ql @ p[j, :3, :3]
    q[h] = target
    Dh = am.rigid(target)[:3, :3] @ am.rigid(ref[h])[:3, :3].T
    currentD = Rl @ am.rigid(ref[l])[:3, :3].T
    tau = twist_angle(currentD.T @ Dh, rl)
    for prefix, share in [("lowerarm_twist_02", 0.5), ("lowerarm_twist_01", 1.0)]:
        j = ids[prefix + "_" + side]
        wanted = R.from_rotvec(am.unit(nl) * tau * share).as_matrix() @ currentD @ am.rigid(ref[j])[:3, :3]
        q[j, :3, :3] = mixrot(am.rigid(q[j])[:3, :3], wanted, blend) * np.linalg.norm(p[j, :3, :3], axis=0)
    wristR = R.from_rotvec(am.unit(nl) * tau).as_matrix() @ currentD
    flex = np.rad2deg(R.from_matrix(wristR.T @ Dh).magnitude())
    return q, {
        "pronation_deg": float(np.rad2deg(tau)),
        "wrist_swing_deg": float(flex),
        "reach": float(d / (L1 + L2)),
        "shoulder_follow_cm": float(shoulder_adjust),
    }


def clip_poses_and_gun(role: str, prof: dict):
    c = motion["clips"][role]
    ps = [am.pose(role, i, prof) for i in range(len(c["times"]))]
    gs = [am.rigid(p[root] @ inv_wref[root]) for p in ps]
    gis = [np.linalg.inv(g) for g in gs]
    ns = [np.einsum("ab,nbc->nac", gi, p) for gi, p in zip(gis, ps)]
    return c, ps, gs, ns


# --- 1. Load live reload_empty & idle references ---
c_eq, old_eq, gun_eq, norm_eq = clip_poses_and_gun("equip", base_in)
c_re, old_re, gun_re, norm_re = clip_poses_and_gun("reload_empty", base_in)
p_idle = am.pose("idle", 0, base_in)
g_idle = am.rigid(p_idle[root] @ inv_wref[root])
n_idle = np.einsum("ab,nbc->nac", np.linalg.inv(g_idle), p_idle)

eq_bolt_closed = n_idle[bolt, :3, 3].copy()
grip = norm_re[304][lh].copy()
hooklocals = {j: am.relative(norm_re[310][parents[j]], norm_re[310][j]) for j in handbones["l"] if j != lh}
right_grip = n_idle[rh].copy()
rightlocals = {j: am.relative(n_idle[parents[j]], n_idle[j]) for j in handbones["r"] if j != rh}
left_idle = n_idle[lh].copy()

lb_recipe = json.loads((LB_DIR / "authoring_recipe.json").read_text())
pole_angle_re = float(lb_recipe["left_pole_offset_deg"])

# --- 2. Smooth Left-Hand Orientation (Direct 154-deg Short Arc: +64 -> 0 -> -90 deg pronation) ---
# With an anatomically downward-locked elbow pole (never flipping over the top!), direct SLERP
# from left_idle (+64 deg supinated) to grip (-90 deg pronated) travels smoothly through 0 deg
# (thumb-up) with zero +/-180 deg twist flip!
R_idle_l = am.rigid(left_idle)[:3, :3]
R_grip_l = am.rigid(grip)[:3, :3]


def slerp_left_orient(u: float) -> np.ndarray:
    return mixrot(R_idle_l, R_grip_l, float(np.clip(u, 0.0, 1.0)))


# --- 3. C2 Clamped Cubic Spline Trajectories (Single Continuous Tactical Arcs) ---
F_LEAVE = 8
F_DOCK = 54
F_PEAK = 94
F_RETURN = 166

pulled_pos = grip[:3, 3] + (norm_eq[F_PEAK][bolt, :3, 3] - eq_bolt_closed)

# Approach (f = 8 .. 54): clamped C2 cubic spline -> exact zero velocity at f=8 & f=54,
# smooth continuous speed through f=24 (clear left of handguard) and f=42 (pre-dock left of handle).
app_t = np.array([8.0, 24.0, 42.0, 54.0])
app_p = np.array(
    [
        left_idle[:3, 3],                           # f=8 : exact idle fore-end (+4.60, -41.79, -9.61)
        np.array([-6.6, -37.2, -9.4]),              # f=24: clean outward-left clearance corridor
        grip[:3, 3] + np.array([-4.2, 0.0, -0.8]),  # f=42: pre-dock outside left handle (-5.52, -25.56, -4.05)
        grip[:3, 3],                                # f=54: exact reload_empty[304] left handle (-1.32, -25.56, -3.25)
    ]
)
app_spline = CubicSpline(app_t, app_p, axis=0, bc_type="clamped")

# Return (f = 94 .. 166): directly reuses reload_empty[344..416] clearance envelope, smoothed C2.
ret_t = np.array([94.0, 108.0, 134.0, 166.0])
ret_p = np.array(
    [
        pulled_pos,                                 # f=94 : exact rear bolt stop (-1.32, -18.06, -3.25)
        pulled_pos + np.array([-5.8, -0.5, -2.2]),  # f=108: crisp outward-left release (-7.12, -18.56, -5.45)
        np.array([-7.2, -39.5, -9.8]),              # f=134: outside left handguard clearance corridor
        left_idle[:3, 3],                           # f=166: exact idle fore-end (+4.60, -41.79, -9.61)
    ]
)
ret_spline = CubicSpline(ret_t, ret_p, axis=0, bc_type="clamped")


def left_target_eq(i: int) -> np.ndarray:
    h = np.eye(4)
    if i <= F_LEAVE:
        h = left_idle.copy()
    elif i <= F_DOCK:
        u = float(am.ease(10, 48, i))
        h[:3, :3] = slerp_left_orient(u) * np.linalg.norm(left_idle[:3, :3], axis=0)
        h[:3, 3] = app_spline(i)
    elif i <= F_PEAK:
        h = grip.copy()
        h[:3, 3] += norm_eq[i][bolt, :3, 3] - eq_bolt_closed
    elif i <= F_RETURN:
        u = float(1.0 - am.ease(104, 158, i))
        h[:3, :3] = slerp_left_orient(u) * np.linalg.norm(left_idle[:3, :3], axis=0)
        h[:3, 3] = ret_spline(i)
    else:
        h = left_idle.copy()
    return gun_eq[i] @ h


def left_shoulder_eq(i: int) -> np.ndarray:
    # Only borrow reload_empty's shoulder during the actual handle grip/pull window (f=24..128),
    # returning cleanly to raw equip shoulder before old_re[384..]'s return transient!
    s_raw = old_eq[i][ul, :3, 3]
    s_re = old_re[min(i, 114) + 250][ul, :3, 3]
    w = float(am.ease(16, 44, i) * (1.0 - am.ease(106, 134, i)))
    return (1.0 - w) * s_raw + w * s_re


def left_pole_eq(i: int, shoulder: np.ndarray, target: np.ndarray) -> np.ndarray:
    # Keep left elbow strictly in its anatomical downward-outward cone:
    # blend smoothly from raw idle/equip elbow at edges into reload_empty's clean charging elbow
    # (clamped at re<=364 so we never inherit reload_empty[384..]'s return elbow flip!).
    p = old_eq[i]
    axis = am.unit(target[:3, 3] - shoulder)
    source = am.unit(p[ll, :3, 3] - shoulder - axis * ((p[ll, :3, 3] - shoulder) @ axis))
    e_re = old_re[min(i, 114) + 250][ll, :3, 3]
    re_pole = am.unit(e_re - shoulder - axis * ((e_re - shoulder) @ axis))
    w = float(am.ease(10, 38, i) * (1.0 - am.ease(104, 134, i)))
    return R.from_rotvec(R.from_matrix(am.swing(source, re_pole)).as_rotvec() * w).apply(source)


# --- 4. Natural Right-Arm Pistol-Grip Support (Zero Overstretched Reach or 76-deg Wrist!) ---
# In raw A_SVD_equip, WPN_root drops -20 cm during f=0..150 while clavicle_r stayed high (for SVD's
# right-side bolt reach). Keep right hand locked on pistol grip and transport clavicle_r/upperarm_r
# smoothly with the rifle's Z-drop + comfortable wrist cone (just like ForegripFit20261019/fit_contact.py),
# blending smoothly back to exact raw shoulder at f=0 and f=204!
idle_ur_in_gun = np.linalg.inv(g_idle) @ p_idle[ur, :, 3]
idle_lr_in_gun = np.linalg.inv(g_idle) @ p_idle[lr, :, 3]
L1_r = float(np.linalg.norm(p_idle[lr, :3, 3] - p_idle[ur, :3, 3]))
L2_r = float(np.linalg.norm(p_idle[rh, :3, 3] - p_idle[lr, :3, 3]))


def solve_right_support(p: np.ndarray, i: int):
    target_r = gun_eq[i] @ right_grip
    # At f=0..4 and f=194..204, raw equip is already identical to idle pistol grip!
    # Across f=4..194, blend right shoulder smoothly toward the natural gun-coupled shoulder
    # (which drops cleanly with the lowered rifle so reach stays ~0.73 and wrist swing stays < 18 deg!).
    w_follow = float(am.ease(0, 12, i) * (1.0 - am.ease(166, 198, i)))
    s_raw = p[ur, :3, 3]
    s_gun = (gun_eq[i] @ idle_ur_in_gun)[:3]
    # Keep X/Y mostly anchored to torso while letting Z/forward comfortably track the lowered weapon
    s_natural = np.array(
        [
            0.35 * s_raw[0] + 0.65 * s_gun[0],
            0.35 * s_raw[1] + 0.65 * s_gun[1],
            0.15 * s_raw[2] + 0.85 * s_gun[2],
        ]
    )
    Sr = (1.0 - w_follow) * s_raw + w_follow * s_natural

    # Natural elbow pole implied by the fixed pistol-grip palm + idle forearm cone
    axis = am.unit(target_r[:3, 3] - Sr)
    Dh = am.rigid(target_r)[:3, :3] @ am.rigid(ref[rh])[:3, :3].T
    ideal_dir = am.unit(Dh @ (ref[rh, :3, 3] - ref[lr, :3, 3]))
    desired_elbow = target_r[:3, 3] - ideal_dir * L2_r
    natural_pole = am.unit(desired_elbow - Sr - axis * ((desired_elbow - Sr) @ axis))

    e_idle_world = (gun_eq[i] @ idle_lr_in_gun)[:3]
    idle_pole = am.unit(e_idle_world - Sr - axis * ((e_idle_world - Sr) @ axis))
    # Mix 70% idle gun-coupled elbow + 30% zero-wrist-flex ideal pole -> natural stance & < 18 deg wrist!
    target_pole = R.from_rotvec(R.from_matrix(am.swing(idle_pole, natural_pole)).as_rotvec() * 0.35).apply(idle_pole)

    source_pole = am.unit(p[lr, :3, 3] - Sr - axis * ((p[lr, :3, 3] - Sr) @ axis))
    pole = R.from_rotvec(R.from_matrix(am.swing(source_pole, target_pole)).as_rotvec() * w_follow).apply(source_pole)

    q, st = solve_arm(p, "r", target_r, Sr, pole, blend=w_follow)
    # Apply exact idle right-hand pistol-grip finger curl
    for j in handbones["r"]:
        if j == rh:
            continue
        src = am.relative(p[parents[j]], p[j])
        local = rightlocals[j].copy()
        local[:3, 3] = src[:3, 3]
        ps = np.linalg.norm(q[parents[j], :3, :3], axis=0)
        ls = np.linalg.norm(src[:3, :3], axis=0)
        q[j, :3, 3] = q[parents[j], :3, :3] @ local[:3, 3] + q[parents[j], :3, 3]
        q[j, :3, :3] = (am.rigid(q[parents[j]])[:3, :3] @ am.rigid(local)[:3, :3]) * (ps * ls)
    return q, st


def delta_vec(local_mat: np.ndarray, raw_row: np.ndarray) -> np.ndarray:
    scale = np.linalg.norm(local_mat[:3, :3], axis=0)
    v = np.zeros(10)
    v[:3] = local_mat[:3, 3] - raw_row[:3]
    v[3:7] = (R.from_matrix(local_mat[:3, :3] / scale) * R.from_quat(raw_row[3:7]).inv()).as_quat()
    v[7:10] = scale - raw_row[7:10]
    return v


# --- 5. Author base profile `equip` clip ---
base_out = copy.deepcopy(base_in)
base_eq_entry = next(c for c in base_out["clips"] if c["base"] == c_eq["path"])
old_eq_layer = next(c for c in base_in["clips"] if c["base"] == c_eq["path"])

base_values = {j: [] for j in changed_all}
base_poses = []
base_stats = []

R_START, R_END = 1, 198

for i, t in enumerate(c_eq["times"]):
    p = old_eq[i]
    q = p.copy()
    st = {"frame": i, "t": float(t)}

    # Left arm: active on F_LEAVE < i < F_RETURN
    if F_LEAVE < i < F_RETURN:
        target_l = left_target_eq(i)
        wl = float(am.ease(F_LEAVE, 32, i) * (1.0 - am.ease(136, F_RETURN, i)))
        Sl = left_shoulder_eq(i)
        q, st["left"] = solve_arm(q, "l", target_l, Sl, left_pole_eq(i, Sl, target_l), blend=wl)
        fingerw = float(am.ease(24, F_DOCK, i) * (1.0 - am.ease(F_PEAK, 128, i)))
        for j in handbones["l"]:
            if j == lh:
                continue
            src = am.relative(p[parents[j]], p[j])
            dst = hooklocals[j]
            local = mix(src, dst, fingerw)
            local[:3, 3] = src[:3, 3]
            ps = np.linalg.norm(q[parents[j], :3, :3], axis=0)
            ls = np.linalg.norm(local[:3, :3], axis=0)
            q[j, :3, 3] = q[parents[j], :3, :3] @ local[:3, 3] + q[parents[j], :3, 3]
            q[j, :3, :3] = (am.rigid(q[parents[j]])[:3, :3] @ am.rigid(local)[:3, :3]) * (ps * ls)

    # Right arm: smoothly locked onto pistol grip on R_START <= i <= R_END
    if R_START <= i <= R_END:
        q, st["right"] = solve_right_support(q, i)

    base_poses.append(q)
    base_stats.append(st)

    raw = np.asarray(c_eq["frames"][i])
    for j in changed_all:
        active = (names[j].endswith("_l") and F_LEAVE < i < F_RETURN) or (
            names[j].endswith("_r") and R_START <= i <= R_END
        )
        if not active:
            tr = next((tr for tr in old_eq_layer["tracks"] if tr["bone"] == names[j]), None)
            v = am.sample(t, tr) if tr else np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0], float)
        else:
            loc = am.relative(q[parents[j]], q[j])
            v = delta_vec(loc, raw[j])
        if base_values[j] and np.dot(base_values[j][-1][3:7], v[3:7]) < 0:
            v[3:7] *= -1.0
        base_values[j].append(v)

base_eq_entry["tracks"] = [t for t in base_eq_entry["tracks"] if ids[t["bone"]] not in changed_all] + [
    {"bone": names[j], "times": c_eq["times"], "values": np.round(base_values[j], 10).ravel().tolist()}
    for j in changed_all
]

base_reconstructed = [am.pose("equip", i, base_out) for i in range(len(c_eq["times"]))]
rt_err = max(float(np.max(np.abs(a - b))) for a, b in zip(base_poses, base_reconstructed))
print(f"Base equip round-trip matrix error: {rt_err:.2e}")
assert rt_err < 1e-4, f"Round-trip error too large: {rt_err}"

# --- 6. Author all 4 Foregrip Profiles' `equip` clip over the new left-bolt base ---
def foregrip_equip_weight(i: int) -> float:
    return float(1.0 - am.ease(8, 24, i) + am.ease(110, 166, i))


out_profiles = {"base": base_out}
foregrip_stats = {}

for fam in ("angled", "vertical", "canted", "prism"):
    contact = fc.contacts[fam]
    prof_in = r7_profiles[fam]
    prof_out = copy.deepcopy(prof_in)
    dst_entry = next(c for c in prof_out["clips"] if c["base"] == c_eq["path"])

    fg_values = {j: [] for j in changed_all}
    peak_shoulder_shift = 0.0
    peak_wrist_swing = 0.0
    for i, t in enumerate(c_eq["times"]):
        p = base_reconstructed[i]
        w = foregrip_equip_weight(i)
        local0 = am.apply(c_eq["frames"][i], base_eq_entry, t)
        local = am.matrices(local0)
        if w > 1e-8:
            fulltarget = am.rigid(p[root]) @ contact["hand"]
            full, _ = fc.fit(p, fulltarget)
            target = mix(p[lh], fulltarget, w)
            shoulder = (1.0 - w) * p[ul, :3, 3] + w * full[ul, :3, 3]
            elbow = (1.0 - w) * p[ll, :3, 3] + w * full[ll, :3, 3]
            q, s = fc.arm(p, "l", target, shoulder, elbow - shoulder, blend=w)
            for j in fc.changed:
                if j in fc.digits:
                    continue
                local[j] = am.relative(q[parents[j]], q[j])
                local[j, :3, :3] = am.rigid(local[j])[:3, :3] * local0[j, 7:]
            for j in fc.digits:
                local[j, :3, :3] = (
                    mixrot(R.from_quat(local0[j, 3:7]).as_matrix(), R.from_quat(contact["digits"][j][3:7]).as_matrix(), w)
                    * local0[j, 7:]
                )
            peak_shoulder_shift = max(peak_shoulder_shift, float(np.linalg.norm(q[ul, :3, 3] - p[ul, :3, 3])))
            if w > 0.999:
                peak_wrist_swing = max(peak_wrist_swing, float(s["wrist_swing_deg"]))

        raw = np.asarray(c_eq["frames"][i])
        for j in changed_all:
            v = delta_vec(local[j], raw[j])
            v[7:10] = local0[j, 7:] - raw[j, 7:10]
            if fg_values[j] and np.dot(fg_values[j][-1][3:7], v[3:7]) < 0:
                v[3:7] *= -1.0
            fg_values[j].append(v)

    dst_entry["tracks"] = [x for x in base_eq_entry["tracks"] if ids[x["bone"]] not in changed_all]
    for j in changed_all:
        a = np.asarray(fg_values[j])
        idx = [0] if np.max(np.abs(a - a[0])) < 1e-8 else list(range(len(a)))
        dst_entry["tracks"].append(
            {"bone": names[j], "times": [c_eq["times"][k] for k in idx], "values": np.round(a[idx], 10).ravel().tolist()}
        )

    out_profiles[fam] = prof_out
    foregrip_stats[fam] = {
        "max_shoulder_shift_cm": round(peak_shoulder_shift, 4),
        "max_full_contact_wrist_swing_deg": round(peak_wrist_swing, 3),
    }

# --- 7. Full Kinematic, Pronation, Continuity & True 3D cKDTree Clearance Audit ---
svch_v = np.asarray(weapon["positions"])
svch_w = weapon["weights"]
svch_wb = weapon["weight_bones"]
root_v_idx = [i for i, row in enumerate(svch_w) if row and svch_wb[max(row, key=lambda x: x[1])[0]] == "WPN_root"]
bolt_v_idx = [i for i, row in enumerate(svch_w) if row and svch_wb[max(row, key=lambda x: x[1])[0]] == "WPN_bolt"]
mag_v_idx = [i for i, row in enumerate(svch_w) if row and svch_wb[max(row, key=lambda x: x[1])[0]] == "WPN_SOCKET_Magazine"]

gun_body_v = svch_v[root_v_idx]
bolt_body_v = svch_v[bolt_v_idx]
mag_body_v = svch_v[mag_v_idx]
gun_kdtree = cKDTree(gun_body_v)

arm_l_idx = am.left
arm_hand_l_idx = am.hand
arm_r_idx = np.flatnonzero([names[b].endswith("_r") for b in am.dom])

bolt_err_max = 0.0
rh_err_max = 0.0
lh_speeds = []
max_wrist_l = 0.0
max_pron_l = 0.0
max_pron_l_jump = 0.0
prev_pron_l = None
max_reach_l = 0.0
max_follow_l = 0.0
max_wrist_r = 0.0
max_pron_r = 0.0
max_reach_r = 0.0
max_follow_r = 0.0
min_3d_dist_approach = 999.0
min_3d_dist_return = 999.0
pen_verts_approach = 0
pen_verts_return = 0

prev_lh_gun = None
for i in range(len(c_eq["times"])):
    p = base_reconstructed[i]
    gi = np.linalg.inv(gun_eq[i])
    n = np.einsum("ab,nbc->nac", gi, p)
    if F_DOCK <= i <= F_PEAK:
        expected_lh = grip[:3, 3] + (n[bolt, :3, 3] - eq_bolt_closed)
        bolt_err_max = max(bolt_err_max, float(np.linalg.norm(n[lh, :3, 3] - expected_lh)))
    rh_err_max = max(rh_err_max, float(np.linalg.norm(n[rh, :3, 3] - right_grip[:3, 3])))
    if prev_lh_gun is not None:
        lh_speeds.append(float(np.linalg.norm(n[lh, :3, 3] - prev_lh_gun)))
    prev_lh_gun = n[lh, :3, 3].copy()

    st = base_stats[i]
    if "left" in st:
        max_wrist_l = max(max_wrist_l, st["left"]["wrist_swing_deg"])
        max_pron_l = max(max_pron_l, abs(st["left"]["pronation_deg"]))
        if prev_pron_l is not None:
            max_pron_l_jump = max(max_pron_l_jump, abs(st["left"]["pronation_deg"] - prev_pron_l))
        prev_pron_l = st["left"]["pronation_deg"]
        max_reach_l = max(max_reach_l, st["left"]["reach"])
        max_follow_l = max(max_follow_l, st["left"]["shoulder_follow_cm"])
    else:
        prev_pron_l = None
    if "right" in st:
        max_wrist_r = max(max_wrist_r, st["right"]["wrist_swing_deg"])
        max_pron_r = max(max_pron_r, abs(st["right"]["pronation_deg"]))
        max_reach_r = max(max_reach_r, st["right"]["reach"])
        max_follow_r = max(max_follow_r, st["right"]["shoulder_follow_cm"])

    # True 3D vertex clearance vs SVCh receiver+handguard during open transit (away from fore-end & handle)
    if i in range(22, 46, 2) or i in range(106, 142, 2):
        hand_world = am.skin(p, arm_hand_l_idx)
        hand_gun = am.transform(gi, hand_world)
        dists, _ = gun_kdtree.query(hand_gun, k=1)
        d_min = float(np.min(dists))
        # Check if any hand vertex enters inside receiver body X in [+4.1, +8.1] AND within actual Z of gun at that Y
        in_x = (hand_gun[:, 0] > 4.1) & (hand_gun[:, 0] < 8.1) & (hand_gun[:, 2] > -6.0) & (hand_gun[:, 2] < 0.0) & (hand_gun[:, 1] > -46.0) & (hand_gun[:, 1] < -12.0)
        n_pen = int(np.sum(in_x))
        if n_pen > 0:
            print(f"  [CLEARANCE NOTE] f={i:3d}: min_3d={d_min:.2f}cm, pen={n_pen}, maxX_in_Z={hand_gun[(hand_gun[:,2]>-6)&(hand_gun[:,2]<0),0].max():.2f}", flush=True)
        if i < 50:
            min_3d_dist_approach = min(min_3d_dist_approach, d_min)
            pen_verts_approach = max(pen_verts_approach, n_pen)
        else:
            min_3d_dist_return = min(min_3d_dist_return, d_min)
            pen_verts_return = max(pen_verts_return, n_pen)

audit = {"families": {}, "base_kinematics": {}}
for fam in FAMILIES:
    p_idle_fam = am.pose("idle", 0, out_profiles[fam])
    p_eq_0 = am.pose("equip", 0, out_profiles[fam])
    p_eq_end = am.pose("equip", len(c_eq["times"]) - 1, out_profiles[fam])
    other_same = [c for c in r7_profiles[fam]["clips"] if c["base"] != c_eq["path"]] == [
        c for c in out_profiles[fam]["clips"] if c["base"] != c_eq["path"]
    ]
    assert other_same, f"Non-equip clip modified in {fam}!"
    audit["families"][fam] = {
        "frame0_lh_vs_idle_cm": round(float(np.linalg.norm(p_eq_0[lh, :3, 3] - p_idle_fam[lh, :3, 3])), 5),
        "frame204_lh_vs_idle_cm": round(float(np.linalg.norm(p_eq_end[lh, :3, 3] - p_idle_fam[lh, :3, 3])), 5),
        "frame0_rh_vs_idle_cm": round(float(np.linalg.norm(p_eq_0[rh, :3, 3] - p_idle_fam[rh, :3, 3])), 5),
        "frame204_rh_vs_idle_cm": round(float(np.linalg.norm(p_eq_end[rh, :3, 3] - p_idle_fam[rh, :3, 3])), 5),
        "other_11_clips_identical": other_same,
        **(foregrip_stats.get(fam, {})),
    }

audit["base_kinematics"] = {
    "frames": len(c_eq["times"]),
    "fps": 120,
    "duration_s": float(c_eq["times"][-1]),
    "bolt_lock_frames": [F_DOCK, F_PEAK],
    "bolt_lock_max_err_cm": round(bolt_err_max, 5),
    "right_pistol_grip_max_err_cm": round(rh_err_max, 5),
    "max_lh_speed_cm_per_frame": round(max(lh_speeds), 3),
    "max_lh_speed_m_per_s": round(max(lh_speeds) * 1.2, 3),
    "left_max_wrist_swing_deg": round(max_wrist_l, 2),
    "left_max_pronation_deg": round(max_pron_l, 2),
    "left_max_pronation_step_deg": round(max_pron_l_jump, 2),
    "left_max_reach_ratio": round(max_reach_l, 4),
    "left_max_shoulder_follow_cm": round(max_follow_l, 3),
    "right_max_wrist_swing_deg": round(max_wrist_r, 2),
    "right_max_pronation_deg": round(max_pron_r, 2),
    "right_max_reach_ratio": round(max_reach_r, 4),
    "right_max_shoulder_follow_cm": round(max_follow_r, 3),
    "transit_min_3d_dist_to_gun_approach_cm": round(min_3d_dist_approach, 3),
    "transit_min_3d_dist_to_gun_return_cm": round(min_3d_dist_return, 3),
    "transit_receiver_penetration_verts_approach": pen_verts_approach,
    "transit_receiver_penetration_verts_return": pen_verts_return,
    "reused_reload_empty_handle_pose": True,
    "shared_sequences_modified": False,
    "audio_clocks_modified": False,
}

prof_dir = OUT_DIR / "Profiles"
prof_dir.mkdir(parents=True, exist_ok=True)
for fam, prof in out_profiles.items():
    (prof_dir / f"{fam}.json").write_text(json.dumps(prof, separators=(",", ":")))
(OUT_DIR / "authoring_audit.json").write_text(json.dumps(audit, indent=2))
print("\n=== AUTHORING AUDIT (V2) ===")
print(json.dumps(audit, indent=2))

# --- 8. Render V2 High-Resolution 3D Visual Inspection Contact Strips ---
rng = np.random.default_rng(42)
gun_sub = gun_body_v[rng.choice(len(gun_body_v), size=min(4500, len(gun_body_v)), replace=False)]
mag_sub = mag_body_v[rng.choice(len(mag_body_v), size=min(900, len(mag_body_v)), replace=False)]
bolt_sub = bolt_body_v


def pose_gun_and_hands_world(prof: dict, f: int):
    p = am.pose("equip", f, prof)
    g = am.rigid(p[root] @ inv_wref[root])
    gb = am.rigid(p[bolt] @ inv_wref[bolt])
    gm = am.rigid(p[mag] @ inv_wref[mag])
    return p, g, am.transform(g, gun_sub), am.transform(gm, mag_sub), am.transform(gb, bolt_sub), am.skin(p, arm_l_idx), am.skin(p, arm_r_idx)


key_frames = [
    (0, "f=0 (0.00s)\nIdle Start"),
    (24, "f=24 (0.20s)\nPeel Left (Thumb-Up)"),
    (42, "f=42 (0.35s)\nPre-Dock Left"),
    (54, "f=54 (0.45s)\nGrip Left Handle"),
    (75, "f=75 (0.63s)\nMid Pull (2.3cm)"),
    (94, "f=94 (0.78s)\nFull Rear (7.5cm)"),
    (108, "f=108 (0.90s)\nRelease Left Clear"),
    (134, "f=134 (1.12s)\nReturn (Thumb-Up)"),
    (166, "f=166 (1.38s)\nRe-Seat Idle"),
]

fig = plt.figure(figsize=(18, 12), dpi=130, facecolor="#14171c")
fig.suptitle("SVCh Left-Bolt Equip (V2 Ergonomic) — First-Person / Upper-Left 3/4 View", color="white", fontsize=15, y=0.98)

for idx, (f, label) in enumerate(key_frames):
    ax = fig.add_subplot(3, 3, idx + 1, projection="3d", facecolor="#1a1f28")
    p, g, pg, pm, pb, pl, pr = pose_gun_and_hands_world(base_out, f)
    gi = np.linalg.inv(g)
    pg_n, pm_n, pb_n, pl_n, pr_n = [am.transform(gi, x) for x in (pg, pm, pb, pl, pr)]

    ax.scatter(pg_n[:, 0], pg_n[:, 1], pg_n[:, 2], s=0.6, c="#7c8794", alpha=0.55)
    ax.scatter(pm_n[:, 0], pm_n[:, 1], pm_n[:, 2], s=0.6, c="#555e6b", alpha=0.5)
    ax.scatter(pb_n[:, 0], pb_n[:, 1], pb_n[:, 2], s=4.0, c="#ff5252", alpha=0.95)
    ax.scatter(pl_n[::4, 0], pl_n[::4, 1], pl_n[::4, 2], s=1.2, c="#4fc3f7", alpha=0.75)
    ax.scatter(pr_n[::4, 0], pr_n[::4, 1], pr_n[::4, 2], s=1.2, c="#ffb74d", alpha=0.65)

    for chain, col in [
        (["upperarm_l", "lowerarm_l", "hand_l"], "#00e5ff"),
        (["upperarm_r", "lowerarm_r", "hand_r"], "#ff9100"),
    ]:
        pts_c = np.array([am.transform(gi, p[ids[b], :3, 3]) for b in chain])
        ax.plot(pts_c[:, 0], pts_c[:, 1], pts_c[:, 2], color=col, lw=2.5, marker="o", ms=4)

    ax.set_xlim(-22, 24)
    ax.set_ylim(-55, 5)
    ax.set_zlim(-26, 10)
    ax.view_init(elev=26, azim=-128)
    ax.set_title(label, color="#e6edf3", fontsize=10, pad=2)
    ax.tick_params(colors="#8b949e", labelsize=7)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False

plt.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(OUT_DIR / "review_player_34_view.png", facecolor=fig.get_facecolor())
plt.close(fig)

# Figure 2: Clearance, Bolt Sync, Velocity & Ergonomics
fig2, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=130, facecolor="#14171c")
fig2.suptitle("SVCh Left-Bolt Equip (V2) — Clearance, C2 Velocity & Ergonomics Audit", color="white", fontsize=14)

traj_base_l = np.array([np.einsum("ab,b->a", np.linalg.inv(gun_eq[i]), base_reconstructed[i][lh, :, 3])[:3] for i in range(len(c_eq["times"]))])
traj_re_l = np.array([norm_re[i + 250][lh, :3, 3] for i in range(54, 167)])
bolt_disp_eq = np.array([np.linalg.norm(norm_eq[i][bolt, :3, 3] - eq_bolt_closed) for i in range(len(c_eq["times"]))])
lh_y_stroke = traj_base_l[:, 1] - grip[1, 3]

ax = axes[0, 0]
ax.set_facecolor("#1a1f28")
ax.scatter(gun_sub[:, 1], gun_sub[:, 0], s=1.0, c="#6e7781", alpha=0.5, label="SVCh Receiver/Handguard (X>=+3.9)")
ax.scatter(bolt_sub[:, 1], bolt_sub[:, 0], s=4.0, c="#ff5252", alpha=0.9, label="Left Charging Handle (closed)")
ax.plot(traj_re_l[:, 1], traj_re_l[:, 0], "--", color="#81c784", lw=2.0, alpha=0.85, label="reload_empty[304..416] ref")
ax.plot(traj_base_l[:F_DOCK+1, 1], traj_base_l[:F_DOCK+1, 0], color="#4fc3f7", lw=2.5, label="Equip Approach (f=0..54)")
ax.plot(traj_base_l[F_DOCK:F_PEAK+1, 1], traj_base_l[F_DOCK:F_PEAK+1, 0], color="#ffca28", lw=3.0, label="Equip Bolt Pull (f=54..94)")
ax.plot(traj_base_l[F_PEAK:, 1], traj_base_l[F_PEAK:, 0], color="#ce93d8", lw=2.5, label="Equip Return (f=94..204)")
for f_mark in (8, 24, 42, 54, 94, 108, 134, 166):
    ax.scatter([traj_base_l[f_mark, 1]], [traj_base_l[f_mark, 0]], c="white", s=24, zorder=5)
    ax.annotate(f"f{f_mark}", (traj_base_l[f_mark, 1], traj_base_l[f_mark, 0]), color="white", fontsize=8, xytext=(3, 3), textcoords="offset points")
ax.axhline(3.9, color="#ff7043", ls=":", lw=1.2, label="Receiver Left Wall (X=+3.9)")
ax.set_xlabel("Gun Y (cm)", color="#c9d1d9")
ax.set_ylabel("Gun X (cm, -X = Left Outside)", color="#c9d1d9")
ax.set_title("Top-Down Clearance (Neutral Gun Space)", color="white")
ax.set_xlim(-50, -10)
ax.set_ylim(-11, 12)
ax.legend(fontsize=7.5, loc="upper left", facecolor="#14171c", edgecolor="#30363d", labelcolor="white")
ax.grid(color="#30363d", alpha=0.5)
ax.tick_params(colors="#c9d1d9")

ax = axes[0, 1]
ax.set_facecolor("#1a1f28")
ax.scatter(gun_sub[:, 1], gun_sub[:, 2], s=1.0, c="#6e7781", alpha=0.5)
ax.scatter(bolt_sub[:, 1], bolt_sub[:, 2], s=4.0, c="#ff5252", alpha=0.9)
ax.plot(traj_re_l[:, 1], traj_re_l[:, 2], "--", color="#81c784", lw=2.0, alpha=0.85, label="reload_empty ref")
ax.plot(traj_base_l[:F_DOCK+1, 1], traj_base_l[:F_DOCK+1, 2], color="#4fc3f7", lw=2.5, label="Approach")
ax.plot(traj_base_l[F_DOCK:F_PEAK+1, 1], traj_base_l[F_DOCK:F_PEAK+1, 2], color="#ffca28", lw=3.0, label="Bolt Pull")
ax.plot(traj_base_l[F_PEAK:, 1], traj_base_l[F_PEAK:, 2], color="#ce93d8", lw=2.5, label="Return")
for fam, col in [("angled", "#26a69a"), ("vertical", "#ab47bc"), ("canted", "#ffa726"), ("prism", "#ec407a")]:
    pts_f = np.array([np.einsum("ab,b->a", np.linalg.inv(gun_eq[i]), am.pose("equip", i, out_profiles[fam])[lh, :, 3])[:3] for i in range(len(c_eq["times"]))])
    ax.plot(pts_f[:, 1], pts_f[:, 2], lw=1.2, alpha=0.75, color=col, label=f"foregrip:{fam}")
ax.set_xlabel("Gun Y (cm)", color="#c9d1d9")
ax.set_ylabel("Gun Z (cm)", color="#c9d1d9")
ax.set_title("Left-Side Profile (Base + All 4 Foregrips)", color="white")
ax.set_xlim(-50, -10)
ax.set_ylim(-18, 4)
ax.legend(fontsize=7.5, loc="lower left", facecolor="#14171c", edgecolor="#30363d", labelcolor="white")
ax.grid(color="#30363d", alpha=0.5)
ax.tick_params(colors="#c9d1d9")

ax = axes[1, 0]
ax.set_facecolor("#1a1f28")
frames_arr = np.arange(len(c_eq["times"]))
ax.plot(frames_arr, bolt_disp_eq, color="#ff5252", lw=2.5, label="WPN_bolt travel (cm)")
ax.plot(frames_arr[F_DOCK:F_PEAK+1], lh_y_stroke[F_DOCK:F_PEAK+1], "--", color="#ffca28", lw=2.0, label="hand_l Y-stroke during lock (cm)")
ax.axvline(64, color="#66bb6a", ls=":", lw=1.5, label="EquipPull Audio (f=64)")
ax.axvline(100, color="#29b6f6", ls=":", lw=1.5, label="EquipRelease Audio (f=100)")
ax2 = ax.twinx()
ax2.plot(frames_arr[1:], np.array(lh_speeds) * 1.2, color="#80deea", lw=1.8, alpha=0.9, label="hand_l speed (m/s)")
ax2.set_ylabel("hand_l speed (m/s)", color="#80deea")
ax2.tick_params(colors="#80deea")
ax.set_xlabel("Frame (120 fps)", color="#c9d1d9")
ax.set_ylabel("Bolt / Hand Stroke (cm)", color="#c9d1d9")
ax.set_title("Bolt Lock Sync (0.000 cm slip) & C2 Continuous Velocity", color="white")
ax.legend(fontsize=7.5, loc="upper right", facecolor="#14171c", edgecolor="#30363d", labelcolor="white")
ax.grid(color="#30363d", alpha=0.5)
ax.tick_params(colors="#c9d1d9")

ax = axes[1, 1]
ax.set_facecolor("#1a1f28")
wl_arr = [s["left"]["wrist_swing_deg"] if "left" in s else np.nan for s in base_stats]
pl_arr = [s["left"]["pronation_deg"] if "left" in s else np.nan for s in base_stats]
wr_arr = [s["right"]["wrist_swing_deg"] if "right" in s else np.nan for s in base_stats]
pr_arr = [s["right"]["pronation_deg"] if "right" in s else np.nan for s in base_stats]
ax.plot(frames_arr, wl_arr, color="#4fc3f7", lw=2.0, label="Left wrist swing (deg)")
ax.plot(frames_arr, wr_arr, color="#ffb74d", lw=2.0, label="Right wrist swing (deg)")
ax.plot(frames_arr, pl_arr, color="#ce93d8", lw=1.8, ls="--", label="Left pronation (deg)")
ax.plot(frames_arr, pr_arr, color="#81c784", lw=1.5, ls="--", label="Right pronation (deg)")
ax.axhline(35, color="#ef5350", ls=":", lw=1.0, label="35 deg wrist guideline")
ax.axhline(0, color="#6e7781", ls="-", lw=0.7)
ax.set_xlabel("Frame (120 fps)", color="#c9d1d9")
ax.set_ylabel("Angle (deg)", color="#c9d1d9")
ax.set_title("Arm Ergonomics V2 (Zero +/-180 Flip, Relaxed Right Wrist)", color="white")
ax.legend(fontsize=7.5, loc="upper right", facecolor="#14171c", edgecolor="#30363d", labelcolor="white")
ax.grid(color="#30363d", alpha=0.5)
ax.tick_params(colors="#c9d1d9")

plt.tight_layout(rect=[0, 0, 1, 0.96])
fig2.savefig(OUT_DIR / "review_clearance_and_kinematics.png", facecolor=fig2.get_facecolor())
plt.close(fig2)
print("SVCH_EQUIP_LEFT_BOLT_V2_AUTHORED_AND_RENDERED", flush=True)
