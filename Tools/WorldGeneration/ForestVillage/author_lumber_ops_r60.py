"""Headless UE 5.8 Authoring Pipeline for LumberMillOps-R60:
Ergonomic Firewood-Splitting (A_LJ_SplitLog_Loop) & Tree-Felling (A_LJ_ChopTree_Loop) Rebuild.

Applies proven FPSGAME animation SKILL principles (two-handed-tools, overhead-reach-wrist,
pose-contact 2026-11-26 dynamics, kimodo-motion-tool mirror grip, FPSPlayerBodyToolGrip FitShaft):
  1. Exact measured SM_BattleAxe curved wooden/leather handle contact (ZERO X=0 assumption!):
       - Upper wooden shaft grip (hand_r): P_R = (-2.85, -0.04, +1.50) cm, r = 2.65 cm, 19+ cm below steel blade!
       - Lower leather grip (hand_l):      P_L = (-4.65, -0.02, -23.75) cm, r = 3.10 cm, 15 cm above butt!
       - Rigid hand_r <-> SM_BattleAxe local transform `AxeInHandR` exported directly for C++
         `ALumberMillWorker::UpdateDynamicToolTransform()` (0.000 mm runtime right-hand drift/slip/head-grab!).
       - Anatomical left-hand mirror across axe blade plane (both thumbs UP toward steel head, both palms
         wrapping flush around the real curved shaft with 2-bone cylinder-surface FitShaft finger IK!).
  2. True continuous periodic C1 kinetic-chain whip motion (NO stop-start piecewise Ease(T)!):
       - Hips/pelvis & torso lead the downswing ahead of the arms (phase-shifted kinetic chain).
       - Full high overhead lift (hands Z ~ 170 cm, axe blade Z ~ 215 cm) with thoracic arch & 2:1 clavicle lift.
       - Wide extended mid-downswing arc (overhead-reach-wrist: elbows extend cleanly to ~30..45 deg).
       - Heavy wood-bite impact cushion + hold + pry-out + elliptical S-arc recovery (never reverses along chop line).
  3. Exports dense 3D audit + SM_BattleAxe mesh & pose snapshot JSON for visual contact-sheet inspection!
"""
import json
import math
import sys
from pathlib import Path

import unreal as ue

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
sys.path.insert(0, str(TOOLS))

lib = ue.EditorAssetLibrary
asset_tools = ue.AssetToolsHelpers.get_asset_tools()

LM_ANIMS = "/Game/ForestPathStudy/VillageRegion/LumberMill/Animations"
SK_SMITH_BODY = "/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Body"
SM_BATTLE_AXE = "/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe"
BASE_IDLE = "/Game/Characters/JasonPlayer20261003/Animations/J_MM_Idle"
BASE_BENCH = "/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/RefineV2/A_Rest_Bench_Idle"

BATCH_DIR = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60")
BATCH_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_PATH = BATCH_DIR / "authored-ops-r60.json"
VISUAL_DUMP_PATH = BATCH_DIR / "visual-inspect-r60.json"


# ==============================================================================
# Vector / Quaternion / Periodic C1 Cubic Spline Math
# ==============================================================================
def v_add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def v_sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def v_scale(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def v_dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def v_cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def v_len(a): return math.sqrt(v_dot(a, a))
def v_norm(a):
    l = v_len(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-8 else (0.0, 0.0, 1.0)
def v_lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def q_norm(q):
    l = math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
    return (q[0]/l, q[1]/l, q[2]/l, q[3]/l) if l > 1e-9 else (0.0, 0.0, 0.0, 1.0)


def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw,
        aw*bw - ax*bx - ay*by - az*bz,
    )


def q_inv(q): return (-q[0], -q[1], -q[2], q[3])


def q_rot(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx),
    )


def q_axis_angle(axis, deg):
    u = v_norm(axis)
    h = math.radians(deg) * 0.5
    s = math.sin(h)
    return (u[0] * s, u[1] * s, u[2] * s, math.cos(h))


def q_between(a, b):
    ua, ub = v_norm(a), v_norm(b)
    d = max(-1.0, min(1.0, v_dot(ua, ub)))
    if d > 0.999999:
        return (0.0, 0.0, 0.0, 1.0)
    if d < -0.999999:
        ortho = v_cross(ua, (1.0, 0.0, 0.0))
        if v_len(ortho) < 1e-3:
            ortho = v_cross(ua, (0.0, 1.0, 0.0))
        return q_axis_angle(ortho, 180.0)
    c = v_cross(ua, ub)
    return q_norm((c[0], c[1], c[2], 1.0 + d))


def q_angle_deg(q):
    q = q_norm(q)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(q[3])))))


def q_from_basis(ex, ey, ez):
    if v_dot(v_cross(ex, ey), ez) < 0.0:
        ez = v_scale(ez, -1.0)
    m00, m01, m02 = ex[0], ey[0], ez[0]
    m10, m11, m12 = ex[1], ey[1], ez[1]
    m20, m21, m22 = ex[2], ey[2], ez[2]
    tr = m00 + m11 + m22
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        return q_norm(((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s))
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        return q_norm((0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s))
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        return q_norm(((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s))
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        return q_norm(((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s))


def q_swing_twist(q, axis):
    q = q_norm(q)
    if q[3] < 0.0:
        q = (-q[0], -q[1], -q[2], -q[3])
    ax = v_norm(axis)
    proj = q[0]*ax[0] + q[1]*ax[1] + q[2]*ax[2]
    tw = q_norm((ax[0]*proj, ax[1]*proj, ax[2]*proj, q[3]))
    sw = q_norm(q_mul(q, q_inv(tw)))
    tw_sin = tw[0]*ax[0] + tw[1]*ax[1] + tw[2]*ax[2]
    tw_deg = math.degrees(2.0 * math.atan2(tw_sin, tw[3]))
    return sw, tw, tw_deg


def q_clamp_angle(q, max_deg):
    q = q_norm(q)
    if q[3] < 0.0:
        q = (-q[0], -q[1], -q[2], -q[3])
    ang = math.degrees(2.0 * math.acos(max(-1.0, min(1.0, q[3]))))
    if ang <= max_deg or ang < 1e-4:
        return q, ang
    ax = v_norm((q[0], q[1], q[2]))
    return q_axis_angle(ax, max_deg), max_deg


def tf_from_ue(t: ue.Transform):
    p = (float(t.translation.x), float(t.translation.y), float(t.translation.z))
    r = q_norm((float(t.rotation.x), float(t.rotation.y), float(t.rotation.z), float(t.rotation.w)))
    s = (float(t.scale3d.x), float(t.scale3d.y), float(t.scale3d.z))
    return (p, r, s)


def tf_mul(parent, local):
    pp, pr, ps = parent
    lp, lr, ls = local
    sp = (lp[0] * ps[0], lp[1] * ps[1], lp[2] * ps[2])
    wp = v_add(pp, q_rot(pr, sp))
    wr = q_norm(q_mul(pr, lr))
    ws = (ps[0] * ls[0], ps[1] * ls[1], ps[2] * ls[2])
    return (wp, wr, ws)


def tf_inv(tf):
    p, r, _ = tf
    ri = q_inv(r)
    pi = q_rot(ri, v_scale(p, -1.0))
    return (pi, ri, (1.0, 1.0, 1.0))


def tf_point(tf, pt):
    p, r, s = tf
    sp = (pt[0] * s[0], pt[1] * s[1], pt[2] * s[2])
    return v_add(p, q_rot(r, sp))


def eval_periodic_pchip(knots, u):
    """True C1 monotonic periodic cubic Hermite spline (PCHIP) — ZERO robotic stop-start at intermediate knots!
    `knots`: sorted list of (u_i, val_i) with u_i in [0, 1). Preserves velocity cleanly across mid-points
    and only pauses naturally at true reversals (zero overshoot!).
    """
    u = u % 1.0
    n = len(knots)
    us = [k[0] for k in knots]
    vs = [k[1] for k in knots]

    # Compute cyclic segment spans h[i] and secants d[i]
    h = [((us[(i + 1) % n] - us[i]) % 1.0) for i in range(n)]
    d = [(vs[(i + 1) % n] - vs[i]) / max(1e-6, h[i]) for i in range(n)]

    # Fritsch-Carlson monotonic tangents m[i]: smooth nonzero slope across monotonic knots, zero at extrema!
    m = []
    for i in range(n):
        d_prev = d[(i - 1) % n]
        d_next = d[i]
        if d_prev * d_next <= 0.0:
            m.append(0.0)
        else:
            h_prev = h[(i - 1) % n]
            h_next = h[i]
            w1 = 2.0 * h_next + h_prev
            w2 = h_next + 2.0 * h_prev
            m.append((w1 + w2) / (w1 / d_prev + w2 / d_next))

    # Locate segment containing u
    for i in range(n):
        u0 = us[i]
        span = h[i]
        rel = (u - u0) % 1.0
        if rel <= span + 1e-7:
            t = max(0.0, min(1.0, rel / max(1e-6, span)))
            t2 = t * t
            t3 = t2 * t
            h00 = 2.0 * t3 - 3.0 * t2 + 1.0
            h10 = t3 - 2.0 * t2 + t
            h01 = -2.0 * t3 + 3.0 * t2
            h11 = t3 - t2
            v0 = vs[i]
            v1 = vs[(i + 1) % n]
            m0 = m[i] * span
            m1 = m[(i + 1) % n] * span
            return h00 * v0 + h10 * m0 + h01 * v1 + h11 * m1
    return vs[0]


def eval_channels(ch_dict, u):
    return {k: eval_periodic_pchip(v, u) for k, v in ch_dict.items()}


# ==============================================================================
# Exact SM_BattleAxe Curved-Handle Contact Measurement
# ==============================================================================
class BattleAxeGeometry:
    """Exact measured curved wooden/leather handle sections from SM_BattleAxe LOD0."""
    # Directly verified from battleaxe_slices.json (SM_BattleAxe bounds X[-11.52..+11.54], Y[-3.86..+3.86], Z[-38.97..+39.01]):
    #   - Steel cutting edge tip: (+11.54, 0.0, +29.93) cm; blade starts Z = +20.85 cm; collar Z = +18.75 cm.
    #   - True woodcutter leverage zone (20.0 cm grip spacing, +47.4 cm lever arm from grip_mid to cutting edge!):
    #       * Upper smooth wood grip (hand_r): Z = -7.50 cm -> 28.4 cm BELOW blade edge, 26.2 cm BELOW collar!
    #       * Lower leather wrap grip (hand_l): Z = -27.50 cm -> centered in sculpted leather wrap (-28.75..-16.25 cm), 11.5 cm above butt!
    GRIP_R_LOCAL = (-3.61, 0.01, -7.50)
    GRIP_R_TANGENT = v_norm((0.112, 0.0, 1.0))
    GRIP_R_RADIUS = 2.58

    GRIP_L_LOCAL = (-4.88, 0.01, -27.50)
    GRIP_L_TANGENT = v_norm((0.090, 0.0, 1.0))
    GRIP_L_RADIUS = 3.18

    BLADE_EDGE_LOCAL = (11.54, 0.0, 29.93)
    HEAD_CENTER_LOCAL = (2.20, 0.0, 29.50)
    BUTT_LOCAL = (-6.29, -0.02, -38.97)
    SCALE = 1.00  # True 78 cm woodcutting axe proportion (fits adult fingers cleanly!)

    @classmethod
    def shaft_dir_grip_pair(cls):
        return v_norm(v_sub(cls.GRIP_R_LOCAL, cls.GRIP_L_LOCAL))


# ==============================================================================
# Anatomically Calibrated Rig Session (SK_Smith_Body / SKM_Jason_body_Skeleton)
# ==============================================================================
class RigSessionR60:
    def __init__(self, body_mesh):
        self.body = body_mesh
        self.skeleton = body_mesh.skeleton
        self.opts = ue.AnimPoseEvaluationOptions()
        self.opts.optional_skeletal_mesh = body_mesh
        self.opts.evaluation_type = ue.AnimDataEvalType.RAW
        self.opts.should_retarget = False

        self.idle_clip = ue.load_asset(BASE_IDLE)
        self.bench_clip = ue.load_asset(BASE_BENCH)
        pose = ue.AnimPoseExtensions.get_anim_pose_at_time(self.idle_clip, 0.0, self.opts)
        self.bone_names = [str(n) for n in ue.AnimPoseExtensions.get_bone_names(pose)]
        self._resolve_parents(pose)
        self.idle_local, self.idle_world = self.sample_clip_frame(self.idle_clip, 0.0)
        self.bench_local, self.bench_world = self.sample_clip_frame(self.bench_clip, 0.0)

        # SK_Smith_Body handedness: upperarm_r.X < 0, upperarm_l.X > 0 => right_sign = -1 (+Y=FWD, +Z=UP)
        self.right_sign = -1.0 if (self.idle_world["upperarm_r"][0][0] < self.idle_world["upperarm_l"][0][0]) else 1.0
        self._calibrate_limbs()
        self._build_rigid_axe_grips()

    def pt(self, right_cm, fwd_cm, up_cm):
        return (right_cm * self.right_sign, fwd_cm, up_cm)

    def vec(self, right, fwd, up):
        return v_norm((right * self.right_sign, fwd, up))

    def _resolve_parents(self, pose):
        locals_map = {b: tf_from_ue(ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.LOCAL)) for b in self.bone_names}
        worlds_map = {b: tf_from_ue(ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD)) for b in self.bone_names}
        known = {
            "root": None, "pelvis": "root",
            "spine_01": "pelvis", "spine_02": "spine_01", "spine_03": "spine_02",
            "spine_04": "spine_03", "spine_05": "spine_04",
            "neck_01": "spine_05", "neck_02": "neck_01", "head": "neck_02",
            "clavicle_l": "spine_05", "upperarm_l": "clavicle_l", "lowerarm_l": "upperarm_l", "hand_l": "lowerarm_l",
            "clavicle_r": "spine_05", "upperarm_r": "clavicle_r", "lowerarm_r": "upperarm_r", "hand_r": "lowerarm_r",
            "thigh_l": "pelvis", "calf_l": "thigh_l", "foot_l": "calf_l", "ball_l": "foot_l",
            "thigh_r": "pelvis", "calf_r": "thigh_r", "foot_r": "calf_r", "ball_r": "foot_r",
        }
        for side in ("l", "r"):
            for digit in ("thumb", "index", "middle", "ring", "pinky"):
                meta = f"{digit}_metacarpal_{side}"
                j1, j2, j3 = f"{digit}_01_{side}", f"{digit}_02_{side}", f"{digit}_03_{side}"
                if meta in locals_map:
                    known[meta] = f"hand_{side}"
                    known[j1] = meta
                else:
                    known[j1] = f"hand_{side}"
                known[j2] = j1
                known[j3] = j2
            for tw in ("upperarm_twist_01", "upperarm_twist_02", "lowerarm_twist_01", "lowerarm_twist_02"):
                known[f"{tw}_{side}"] = f"{'upperarm' if 'upperarm' in tw else 'lowerarm'}_{side}"
            for tw in ("thigh_twist_01", "thigh_twist_02", "calf_twist_01", "calf_twist_02"):
                known[f"{tw}_{side}"] = f"{'thigh' if 'thigh' in tw else 'calf'}_{side}"

        self.parent = {}
        for b in self.bone_names:
            cand = known.get(b)
            if cand is not None and cand in worlds_map:
                pred_p, _, _ = tf_mul(worlds_map[cand], locals_map[b])
                if v_len(v_sub(pred_p, worlds_map[b][0])) < 0.25:
                    self.parent[b] = cand
                    continue
            if b == "root":
                self.parent[b] = None
                continue
            best_p, best_err = None, 0.25
            for p_cand in self.bone_names:
                if p_cand == b:
                    continue
                pred_p, _, _ = tf_mul(worlds_map[p_cand], locals_map[b])
                err = v_len(v_sub(pred_p, worlds_map[b][0]))
                if err < best_err:
                    best_err = err
                    best_p = p_cand
            self.parent[b] = best_p

        self.topo = []
        visited = set()
        def visit(bn):
            if bn in visited or bn not in locals_map:
                return
            p = self.parent.get(bn)
            if p:
                visit(p)
            visited.add(bn)
            self.topo.append(bn)
        for b in self.bone_names:
            visit(b)

    def sample_clip_frame(self, clip, time_sec):
        pose = ue.AnimPoseExtensions.get_anim_pose_at_time(clip, time_sec, self.opts)
        loc, wld = {}, {}
        for b in self.bone_names:
            loc[b] = tf_from_ue(ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.LOCAL))
            wld[b] = tf_from_ue(ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD))
        return loc, wld

    def compute_fk(self, local_map):
        world = {}
        for b in self.topo:
            p = self.parent.get(b)
            world[b] = local_map[b] if (p is None or p not in world) else tf_mul(world[p], local_map[b])
        return world

    def _calibrate_chain_frame(self, world_pose, b_u, b_l, b_e):
        p_u, r_u, _ = world_pose[b_u]
        p_l, r_l, _ = world_pose[b_l]
        p_e, _, _ = world_pose[b_e]
        v_u = v_sub(p_l, p_u)
        v_l = v_sub(p_e, p_l)
        l1, l2 = v_len(v_u), v_len(v_l)
        u_dir_w, l_dir_w = v_norm(v_u), v_norm(v_l)
        hinge_w = v_norm(v_cross(u_dir_w, l_dir_w))
        u_in_w = v_norm(v_cross(hinge_w, u_dir_w))
        l_in_w = v_norm(v_cross(hinge_w, l_dir_w))

        u_ldir = v_norm(q_rot(q_inv(r_u), u_dir_w))
        u_lin = v_norm(q_rot(q_inv(r_u), u_in_w))
        u_lh = v_norm(q_rot(q_inv(r_u), hinge_w))
        l_ldir = v_norm(q_rot(q_inv(r_l), l_dir_w))
        l_lin = v_norm(q_rot(q_inv(r_l), l_in_w))
        l_lh = v_norm(q_rot(q_inv(r_l), hinge_w))

        return dict(
            l1=l1, l2=l2, u_ldir=u_ldir, l_ldir=l_ldir,
            q_local_u=q_from_basis(u_ldir, u_lin, u_lh),
            q_local_l=q_from_basis(l_ldir, l_lin, l_lh),
        )

    def _calibrate_limbs(self):
        self.arm_info = {}
        self.leg_info = {}
        for side in ("l", "r"):
            ua, la, hd = f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"
            chain = self._calibrate_chain_frame(self.idle_world, ua, la, hd)

            # Measure exact hand-local anatomical basis directly from SK_Smith_Body finger bones!
            hd_inv = tf_inv(self.idle_world[hd])
            p_idx = tf_point(hd_inv, self.idle_world[f"index_01_{side}"][0])
            p_mid = tf_point(hd_inv, self.idle_world[f"middle_01_{side}"][0])
            p_pnk = tf_point(hd_inv, self.idle_world[f"pinky_01_{side}"][0])
            p_m2 = tf_point(hd_inv, self.idle_world[f"middle_02_{side}"][0])
            p_m3 = tf_point(hd_inv, self.idle_world[f"middle_03_{side}"][0])

            # finger_fwd: wrist -> middle_01; radial_up: pinky -> index (thumb-up side!)
            f_fwd = v_norm(p_mid)
            rad_raw = v_sub(p_idx, p_pnk)
            f_rad = v_norm(v_sub(rad_raw, v_scale(f_fwd, v_dot(rad_raw, f_fwd))))
            # palm_in: direction curled fingers bend inward toward palm
            curl_vec = v_sub(p_m3, p_mid)
            palm_raw = v_sub(curl_vec, v_scale(f_fwd, v_dot(curl_vec, f_fwd)))
            palm_raw = v_sub(palm_raw, v_scale(f_rad, v_dot(palm_raw, f_rad)))
            f_palm = v_norm(palm_raw)
            # Re-orthogonalize exact right-handed triple
            if v_dot(v_cross(f_fwd, f_rad), f_palm) < 0.0:
                pass  # f_fwd, f_rad, f_palm sign handled explicitly per side below

            self.arm_info[side] = dict(
                ua=ua, la=la, hd=hd,
                f_fwd_loc=f_fwd,
                f_rad_loc=f_rad,
                f_palm_loc=f_palm,
                idle_hd_local_r=self.idle_local[hd][1],
                **chain,
            )
            ue.log(f"[R60-HAND-{side.upper()}] fwd={tuple(round(x,3) for x in f_fwd)} rad_up={tuple(round(x,3) for x in f_rad)} palm_in={tuple(round(x,3) for x in f_palm)}")

            th, cf, ft = f"thigh_{side}", f"calf_{side}", f"foot_{side}"
            self.leg_info[side] = dict(th=th, cf=cf, ft=ft, **self._calibrate_chain_frame(self.bench_world, th, cf, ft))

    def _build_rigid_axe_grips(self):
        """Build EXACT rigid tool-local hand transforms (`HandR_In_Axe`, `HandL_In_Axe`, `Axe_In_HandR`)
        and exact cylinder-wrapped finger local rotations (`FitShaft` on SM_BattleAxe's REAL curved wood/leather shaft!).
        Uses true anatomical diagonal-palm woodcutter grip (44 deg inward pronation around shaft + 42 deg ulnar oblique):
        aligns hand metacarpals directly along natural forearm approach vector (~18..25 deg wrist bend across ENTIRE swing!).
        """
        roll_in_deg = 44.0   # Pronated knuckles-out wrap around shaft (right wrist on back-right, left on back-left!)
        oblique_deg = 42.0   # Shaft runs diagonally across palm crease (index base -> pinky heel, natural handshake!)
        c_rl, s_rl = math.cos(math.radians(roll_in_deg)), math.sin(math.radians(roll_in_deg))
        c_ob, s_ob = math.cos(math.radians(oblique_deg)), math.sin(math.radians(oblique_deg))

        self.hand_in_axe = {}
        self.grip_finger_locals = {}

        for side, p_shaft, t_shaft, rad_cm in (
            ("r", BattleAxeGeometry.GRIP_R_LOCAL, BattleAxeGeometry.GRIP_R_TANGENT, BattleAxeGeometry.GRIP_R_RADIUS),
            ("l", BattleAxeGeometry.GRIP_L_LOCAL, BattleAxeGeometry.GRIP_L_TANGENT, BattleAxeGeometry.GRIP_L_RADIUS),
        ):
            info = self.arm_info[side]
            # Local curved-handle frame in Axe space:
            #   ez_s = tangent UP toward blade (+Z_axe)
            #   ex_s = cutting edge (+X_axe) projected ortho to ez_s
            #   ey_s = ez_s x ex_s (points toward worker's RIGHT when holding axe straight ahead!)
            ez_s = v_norm(t_shaft)
            ex_s = v_norm(v_sub((1.0, 0.0, 0.0), v_scale(ez_s, v_dot((1.0, 0.0, 0.0), ez_s))))
            ey_s = v_norm(v_cross(ez_s, ex_s))

            # True anatomical diagonal-palm grip frame in AXE space (exact L/R mirror across cleave plane!):
            #   - Right hand approaches from back-right (+ey_s, -ex_s, -ez_s): fingers wrap forward-inward (u_wrap_r)
            #     and angled +42 deg up toward blade head (+ez_s), palm presses inward-back (-ex_s, -ey_s).
            #   - Left hand mirrors across cleave plane: fingers wrap forward-inward (u_wrap_l) +42 deg up,
            #     palm presses inward-back (-ex_s, +ey_s). Both thumbs point UP along shaft toward steel head!
            side_sgn = 1.0 if side == "r" else -1.0
            u_wrap = v_norm(v_add(v_scale(ex_s, c_rl), v_scale(ey_s, -side_sgn * s_rl)))
            des_palm = v_norm(v_add(v_scale(ex_s, -s_rl), v_scale(ey_s, -side_sgn * c_rl)))
            des_fwd = v_norm(v_add(v_scale(u_wrap, c_ob), v_scale(ez_s, s_ob)))
            des_rad = v_norm(v_add(v_scale(ez_s, c_ob), v_scale(u_wrap, -s_ob)))

            # Match hand-local basis [f_fwd_loc, f_rad_loc, f_third_loc] -> [des_fwd, des_rad, des_third]
            # Ensure IDENTICAL right-handed handedness on both sides!
            loc_3 = v_norm(v_cross(info["f_fwd_loc"], info["f_rad_loc"]))
            sgn = 1.0 if v_dot(loc_3, info["f_palm_loc"]) >= 0.0 else -1.0
            des_3 = v_norm(v_cross(des_fwd, des_rad))
            if v_dot(des_3, v_scale(des_palm, sgn)) < 0.0:
                raise RuntimeError(f"Handedness mismatch on hand_{side}!")

            q_loc_frame = q_from_basis(info["f_fwd_loc"], info["f_rad_loc"], loc_3)
            q_des_frame = q_from_basis(des_fwd, des_rad, des_3)
            q_hand_in_axe = q_norm(q_mul(q_des_frame, q_inv(q_loc_frame)))

            # Verify hand anatomical axes mapped into Axe space!
            chk_fwd = q_rot(q_hand_in_axe, info["f_fwd_loc"])
            chk_rad = q_rot(q_hand_in_axe, info["f_rad_loc"])
            chk_palm = q_rot(q_hand_in_axe, info["f_palm_loc"])
            assert v_dot(chk_fwd, des_fwd) > 0.99 and v_dot(chk_rad, des_rad) > 0.99 and v_dot(chk_palm, des_palm) > 0.99

            # Position wrist so wooden shaft center `p_shaft` sits 100% FLUSH in the diagonal palm crease!
            palm_fwd_cm = 6.75
            palm_in_cm = rad_cm + 1.15
            wrist_pos_axe = v_sub(v_sub(p_shaft, v_scale(des_fwd, palm_fwd_cm)), v_scale(des_palm, palm_in_cm))

            hand_tf_axe = (wrist_pos_axe, q_hand_in_axe, (1.0, 1.0, 1.0))
            self.hand_in_axe[side] = hand_tf_axe

            # Solve exact 2-bone FitShaft finger wrap onto the REAL curved wooden shaft surface!
            self.grip_finger_locals[side] = self._solve_fit_shaft_fingers(side, hand_tf_axe, p_shaft, ez_s, ex_s, des_palm, rad_cm)

            ue.log(f"[R60-GRIP-{side.upper()}] shaft={p_shaft} r={rad_cm:.2f}cm -> wrist_in_axe={tuple(round(x,2) for x in wrist_pos_axe)}")

        # Exact rigid attachment for C++ `ALumberMillWorker::UpdateDynamicToolTransform()`:
        #   AxeWorld = HandRWorld * AxeInHandR  (in UE: AxeInHandR * HandRWorld)
        self.axe_in_hand_r = tf_inv(self.hand_in_axe["r"])
        ap, aq, _ = self.axe_in_hand_r
        ue.log(f"[R60-CPP-CONST] AxeInHandR Pos=({ap[0]:.4f}, {ap[1]:.4f}, {ap[2]:.4f}) Quat=({aq[0]:.6f}, {aq[1]:.6f}, {aq[2]:.6f}, {aq[3]:.6f})")

    def _solve_fit_shaft_fingers(self, side, hand_tf_axe, p_shaft, ez_s, ex_s, des_palm, rad_cm):
        """Exact cylinder-surface finger wrap in Axe space (ported from FPSPlayerBodyToolGrip.cpp::FitShaft).
        Places every finger knuckle/tip cleanly around the actual curved SM_BattleAxe radius + soft-tissue clearance!
        """
        # Start from idle finger local transforms and evaluate in Axe space under `hand_tf_axe`
        loc = dict(self.idle_local)
        hd = f"hand_{side}"

        def eval_hand_children():
            w = {hd: hand_tf_axe}
            for b in self.topo:
                if b == hd:
                    continue
                p = self.parent.get(b)
                if p in w:
                    w[b] = tf_mul(w[p], loc[b])
            return w

        info = self.arm_info[side]
        palm_n_axe = q_rot(hand_tf_axe[1], info["f_palm_loc"])
        fwd_axe = q_rot(hand_tf_axe[1], info["f_fwd_loc"])
        flex_axis_axe = v_norm(v_cross(fwd_axe, palm_n_axe))

        # Target wrap radius = shaft radius + 0.65 cm finger pad half-thickness
        wrap_r = rad_cm + 0.65

        # First curl each of the 4 digits naturally onto the cylinder surface using analytic angular search per phalanx!
        for digit, base_angles in (
            ("index",  (42.0, 56.0, 38.0)),
            ("middle", (44.0, 58.0, 40.0)),
            ("ring",   (46.0, 58.0, 40.0)),
            ("pinky",  (48.0, 56.0, 38.0)),
        ):
            j1, j2, j3 = f"{digit}_01_{side}", f"{digit}_02_{side}", f"{digit}_03_{side}"
            # Search clean curl scale s in [0.65 .. 1.35] so j2 & j3 hug `wrap_r` around shaft centerline `(p_shaft, ez_s)`!
            best_s = 1.0
            best_cost = 1e9
            orig_j = {b: loc[b] for b in (j1, j2, j3) if b in loc}
            for step_i in range(29):
                s = 0.65 + step_i * 0.025
                for b in orig_j:
                    loc[b] = orig_j[b]
                for ji, deg in enumerate(base_angles):
                    bn = f"{digit}_0{ji+1}_{side}"
                    if bn in loc:
                        w = eval_hand_children()
                        pr = w[self.parent[bn]][1]
                        br = w[bn][1]
                        new_br = q_norm(q_mul(q_axis_angle(flex_axis_axe, deg * s), br))
                        lp, _, ls = loc[bn]
                        loc[bn] = (lp, q_norm(q_mul(q_inv(pr), new_br)), ls)
                w = eval_hand_children()
                # Measure radial clearance of j2 (PIP) and j3 (DIP) from shaft axis!
                p2 = w[j2][0]
                p3 = w[j3][0]
                # Estimate fingertip ~2.0 cm past j3 along j2->j3
                p_tip = v_add(p3, v_scale(v_norm(v_sub(p3, p2)), 1.9))
                cost = 0.0
                for pt_c, weight in ((p2, 1.5), (p3, 2.5), (p_tip, 1.5)):
                    rel = v_sub(pt_c, p_shaft)
                    rad_v = v_sub(rel, v_scale(ez_s, v_dot(rel, ez_s)))
                    r_dist = v_len(rad_v)
                    err = r_dist - wrap_r
                    # Heavy penalty for penetrating inside the wooden shaft (r_dist < wrap_r - 0.15)!
                    cost += weight * (err * err * (12.0 if err < -0.15 else 1.0))
                if cost < best_cost:
                    best_cost = cost
                    best_s = s
            # Apply winning best_s
            for b in orig_j:
                loc[b] = orig_j[b]
            for ji, deg in enumerate(base_angles):
                bn = f"{digit}_0{ji+1}_{side}"
                if bn in loc:
                    w = eval_hand_children()
                    pr = w[self.parent[bn]][1]
                    br = w[bn][1]
                    new_br = q_norm(q_mul(q_axis_angle(flex_axis_axe, deg * best_s), br))
                    lp, _, ls = loc[bn]
                    loc[bn] = (lp, q_norm(q_mul(q_inv(pr), new_br)), ls)

        # Opposing thumb: wrap naturally around front-top of shaft resting cleanly outside index_02/middle_02
        # (matching AxeThumb20260919/delivered_side.png!)
        w = eval_hand_children()
        t1, t2, t3 = f"thumb_01_{side}", f"thumb_02_{side}", f"thumb_03_{side}"
        m2 = f"middle_02_{side}"
        if t1 in w and t2 in w and m2 in w:
            p_t1, p_t2 = w[t1][0], w[t2][0]
            # Target point just outside the shaft in front-palm quadrant (resting over index_02!)
            i2_p = w[f"index_02_{side}"][0]
            rel_i2 = v_sub(i2_p, p_shaft)
            i2_rad = v_norm(v_sub(rel_i2, v_scale(ez_s, v_dot(rel_i2, ez_s))))
            aim_pt = v_add(v_add(p_shaft, v_scale(ez_s, v_dot(rel_i2, ez_s) + 0.4)), v_scale(i2_rad, wrap_r + 1.0))
            t_dir = v_norm(v_sub(p_t2, p_t1))
            to_aim = v_norm(v_sub(aim_pt, p_t1))
            t_axis = v_cross(t_dir, to_aim)
            if v_len(t_axis) > 1e-3:
                t_axis = v_norm(t_axis)
                for ji, deg in enumerate((22.0, 26.0, 20.0)):
                    bn = f"thumb_0{ji+1}_{side}"
                    if bn in loc:
                        w = eval_hand_children()
                        pr = w[self.parent[bn]][1]
                        br = w[bn][1]
                        new_br = q_norm(q_mul(q_axis_angle(t_axis, deg), br))
                        lp, _, ls = loc[bn]
                        loc[bn] = (lp, q_norm(q_mul(q_inv(pr), new_br)), ls)

        # Save all finger bone local transforms for this side
        out = {}
        for digit in ("thumb", "index", "middle", "ring", "pinky"):
            for ji in (1, 2, 3):
                bn = f"{digit}_0{ji}_{side}"
                if bn in loc:
                    out[bn] = loc[bn]
        return out

    def apply_world_turn(self, local_map, bone, axis_world, deg, world_cache=None):
        if bone not in local_map or abs(deg) < 1e-6:
            return
        w = world_cache if world_cache is not None else self.compute_fk(local_map)
        p = self.parent.get(bone)
        pr = w[p][1] if (p and p in w) else (0.0, 0.0, 0.0, 1.0)
        br = w[bone][1]
        new_br = q_norm(q_mul(q_axis_angle(axis_world, deg), br))
        lp, _, ls = local_map[bone]
        local_map[bone] = (lp, q_norm(q_mul(q_inv(pr), new_br)), ls)

    def turn_pitch_fwd(self, local_map, bone, deg_fwd, world_cache=None):
        self.apply_world_turn(local_map, bone, (1.0, 0.0, 0.0), -deg_fwd, world_cache)

    def turn_lean_right(self, local_map, bone, deg_right, world_cache=None):
        self.apply_world_turn(local_map, bone, (0.0, 1.0, 0.0), deg_right * self.right_sign, world_cache)

    def turn_yaw_right(self, local_map, bone, deg_right, world_cache=None):
        self.apply_world_turn(local_map, bone, (0.0, 0.0, 1.0), -deg_right * self.right_sign, world_cache)

    def drive_clavicle(self, local_map, side, target_hand_w):
        """Anatomical scapulohumeral rhythm (clavicle rises cleanly with overhead lift up to 18 deg
        so shoulder joints stay lifted and R59 T-pose re-tailored armpit workwear NEVER pinches!)."""
        clav = f"clavicle_{side}"
        if clav not in local_map:
            return
        w = self.compute_fk(local_map)
        sh = w[f"upperarm_{side}"][0]
        # Smooth upward shrug when hand rises above shoulder (max 18 deg), gentle protraction forward (max 12 deg)
        dz = target_hand_w[2] - sh[2]
        dy = target_hand_w[1] - sh[1]
        elev = max(-3.0, min(18.0, (dz + 6.0) * 0.34))
        prot = max(-6.0, min(12.0, (dy - 18.0) * 0.24))
        side_sgn = 1.0 if side == "r" else -1.0
        self.turn_lean_right(local_map, clav, -side_sgn * elev)
        self.turn_yaw_right(local_map, clav, -side_sgn * prot)

    def solve_arm_to_exact_hand_tf(self, local_map, side, target_hand_tf_w, pole_w, enforce_exact_wrist=True):
        """Exact 1-DOF anatomical hinge-plane 2-bone arm IK targeting a RIGID world hand transform!
        - `enforce_exact_wrist=True` (for hand_r): preserves 0.000 deg exact wrist orientation so
          rigidly attached SM_BattleAxe hits the exact authored blade trajectory & billet contact!
        - Softly clamps wrist swing/twist only if out of safe bounds, and reports exact anatomical metrics.
        """
        target_pos_w, target_rot_w, _ = target_hand_tf_w
        self.drive_clavicle(local_map, side, target_pos_w)

        info = self.arm_info[side]
        ua, la, hd = info["ua"], info["la"], info["hd"]
        l1, l2 = info["l1"], info["l2"]

        world = self.compute_fk(local_map)
        p_ua = world[ua][0]
        r_parent_ua = world[self.parent[ua]][1]

        to_tgt = v_sub(target_pos_w, p_ua)
        dist = v_len(to_tgt)
        max_reach = (l1 + l2) * 0.985  # Preserve >= 10 deg natural elbow bend (never hyperextend!)
        min_reach = abs(l1 - l2) + 8.0
        clamped_dist = max(min_reach, min(max_reach, dist))
        dir_tgt = v_norm(to_tgt)
        eff_tgt = v_add(p_ua, v_scale(dir_tgt, clamped_dist))

        cos_a = max(-1.0, min(1.0, (l1*l1 + clamped_dist*clamped_dist - l2*l2) / (2.0 * l1 * clamped_dist)))
        sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
        pole_v = v_sub(pole_w, p_ua)
        bend_dir = v_sub(pole_v, v_scale(dir_tgt, v_dot(pole_v, dir_tgt)))
        if v_len(bend_dir) < 1e-4:
            bend_dir = self.vec(1.0 if side == "r" else -1.0, -0.25, -0.65)
        bend_dir = v_norm(bend_dir)
        p_elbow = v_add(p_ua, v_add(v_scale(dir_tgt, l1 * cos_a), v_scale(bend_dir, l1 * sin_a)))

        d_u = v_norm(v_sub(p_elbow, p_ua))
        d_l = v_norm(v_sub(eff_tgt, p_elbow))
        elbow_flex = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(d_u, d_l)))))
        spine_up = v_norm(v_sub(world["spine_05"][0], world["spine_01"][0]))
        arm_elev = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(d_u, v_scale(spine_up, -1.0))))))

        h_raw = v_cross(d_u, d_l)
        h_w = v_norm(h_raw) if v_len(h_raw) > 1e-4 else v_norm(v_cross(d_u, v_scale(bend_dir, -1.0)))
        in_u = v_norm(v_cross(h_w, d_u))
        in_l = v_norm(v_cross(h_w, d_l))

        new_ua_wrot = q_norm(q_mul(q_from_basis(d_u, in_u, h_w), q_inv(info["q_local_u"])))
        new_la_wrot = q_norm(q_mul(q_from_basis(d_l, in_l, h_w), q_inv(info["q_local_l"])))

        lp_ua, _, ls_ua = local_map[ua]
        local_map[ua] = (lp_ua, q_norm(q_mul(q_inv(r_parent_ua), new_ua_wrot)), ls_ua)
        lp_la, _, ls_la = local_map[la]
        local_map[la] = (lp_la, q_norm(q_mul(q_inv(new_ua_wrot), new_la_wrot)), ls_la)

        # Exact wrist local rotation targeting `target_rot_w`
        raw_hd_local = q_norm(q_mul(q_inv(new_la_wrot), target_rot_w))
        q_wrist_delta = q_norm(q_mul(raw_hd_local, q_inv(info["idle_hd_local_r"])))
        q_sw, _, tw_deg = q_swing_twist(q_wrist_delta, info["l_ldir"])
        sw_deg = q_angle_deg(q_sw)

        if enforce_exact_wrist:
            final_hd_local = raw_hd_local
        else:
            q_tw_c = q_axis_angle(info["l_ldir"], max(-82.0, min(82.0, tw_deg)))
            q_sw_c, _ = q_clamp_angle(q_sw, 54.0)
            final_hd_local = q_norm(q_mul(q_mul(q_sw_c, q_tw_c), info["idle_hd_local_r"]))

        lp_hd, _, ls_hd = local_map[hd]
        local_map[hd] = (lp_hd, final_hd_local, ls_hd)

        # Apply exact cylinder-wrapped FitShaft fingers!
        for bn, btf in self.grip_finger_locals[side].items():
            local_map[bn] = btf

        world = self.compute_fk(local_map)
        reach_err = v_len(v_sub(world[hd][0], target_pos_w))
        # Measure actual anatomical forearm-to-hand bend angle
        dl_actual = v_norm(v_sub(world[hd][0], world[la][0]))
        df_actual = v_norm(v_sub(world[f"middle_01_{side}"][0], world[hd][0]))
        wrist_bend = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(dl_actual, df_actual)))))
        return dict(
            reach_err=reach_err,
            elbow_flex=elbow_flex,
            arm_elev=arm_elev,
            wrist_twist=abs(tw_deg),
            wrist_swing=sw_deg,
            wrist_bend=wrist_bend,
        )

    def solve_leg_grounded(self, local_map, side, foot_target_w, knee_pole_w, toe_out_deg=14.0, heel_lift_deg=0.0):
        info = self.leg_info[side]
        th, cf, ft = info["th"], info["cf"], info["ft"]
        l1, l2 = info["l1"], info["l2"]

        world = self.compute_fk(local_map)
        p_hip = world[th][0]
        r_pelvis = world[self.parent[th]][1]
        to_ft = v_sub(foot_target_w, p_hip)
        dist = max(abs(l1 - l2) + 8.0, min((l1 + l2) * 0.990, v_len(to_ft)))
        dir_ft = v_norm(to_ft)
        eff_ft = v_add(p_hip, v_scale(dir_ft, dist))

        cos_a = max(-1.0, min(1.0, (l1*l1 + dist*dist - l2*l2) / (2.0 * l1 * dist)))
        sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
        pv = v_sub(knee_pole_w, p_hip)
        bend = v_sub(pv, v_scale(dir_ft, v_dot(pv, dir_ft)))
        bend = v_norm(bend if v_len(bend) > 1e-4 else (0.0, 1.0, 0.0))
        p_knee = v_add(p_hip, v_add(v_scale(dir_ft, l1 * cos_a), v_scale(bend, l1 * sin_a)))

        d_u = v_norm(v_sub(p_knee, p_hip))
        d_l = v_norm(v_sub(eff_ft, p_knee))
        knee_flex = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(d_u, d_l)))))
        h_raw = v_cross(d_u, d_l)
        h_w = v_norm(h_raw) if v_len(h_raw) > 1e-4 else v_norm(v_cross(d_u, v_scale(bend, -1.0)))
        in_u = v_norm(v_cross(h_w, d_u))
        in_l = v_norm(v_cross(h_w, d_l))

        new_th_w = q_norm(q_mul(q_from_basis(d_u, in_u, h_w), q_inv(info["q_local_u"])))
        new_cf_w = q_norm(q_mul(q_from_basis(d_l, in_l, h_w), q_inv(info["q_local_l"])))

        lp_th, _, ls_th = local_map[th]
        local_map[th] = (lp_th, q_norm(q_mul(q_inv(r_pelvis), new_th_w)), ls_th)
        lp_cf, _, ls_cf = local_map[cf]
        local_map[cf] = (lp_cf, q_norm(q_mul(q_inv(new_th_w), new_cf_w)), ls_cf)

        side_sgn = 1.0 if side == "r" else -1.0
        foot_w = q_norm(q_mul(q_axis_angle((0.0, 0.0, 1.0), -side_sgn * toe_out_deg * self.right_sign), self.bench_world[ft][1]))
        if abs(heel_lift_deg) > 0.01:
            # Subtle rear-foot heel roll forward during deep lunge follow-through
            foot_w = q_norm(q_mul(q_axis_angle((1.0, 0.0, 0.0), -heel_lift_deg), foot_w))
        lp_ft, _, ls_ft = local_map[ft]
        local_map[ft] = (lp_ft, q_norm(q_mul(q_inv(new_cf_w), foot_w)), ls_ft)
        return knee_flex

    def bake_sequence(self, name, fps, num_frames, frames_local, description):
        lib.make_directory(LM_ANIMS)
        dest_path = f"{LM_ANIMS}/{name}"
        if lib.does_asset_exist(dest_path):
            lib.delete_asset(dest_path)

        factory = ue.AnimSequenceFactory()
        factory.set_editor_property("target_skeleton", self.skeleton)
        factory.set_editor_property("preview_skeletal_mesh", self.body)
        clip = asset_tools.create_asset(name, LM_ANIMS, ue.AnimSequence, factory)
        if not clip:
            raise RuntimeError("Failed creating AnimSequence: " + name)

        all_frames = list(frames_local) + [frames_local[0]]
        tracks = sorted(frames_local[0].keys())

        ctl = clip.get_editor_property("controller")
        ctl.open_bracket(description, False)
        try:
            ctl.set_frame_rate(ue.FrameRate(fps, 1), False)
            ctl.set_number_of_frames(ue.FrameNumber(num_frames), False)
            for bn in tracks:
                ps, rs, ss = [], [], []
                prev_q = None
                for fdict in all_frames:
                    p, r, s = fdict[bn]
                    if prev_q is not None and (prev_q[0]*r[0] + prev_q[1]*r[1] + prev_q[2]*r[2] + prev_q[3]*r[3]) < 0.0:
                        r = (-r[0], -r[1], -r[2], -r[3])
                    prev_q = r
                    ps.append(ue.Vector(p[0], p[1], p[2]))
                    rs.append(ue.Quat(r[0], r[1], r[2], r[3]))
                    ss.append(ue.Vector(s[0], s[1], s[2]))
                ctl.add_bone_curve(bn, False)
                if not ctl.set_bone_track_keys(bn, ps, rs, ss, False):
                    raise RuntimeError(f"{name}: failed setting keys for bone {bn}")
        finally:
            ctl.close_bracket(False)

        clip.set_editor_property("enable_root_motion", False)
        clip.set_editor_property("force_root_lock", True)
        clip.set_editor_property("root_motion_root_lock", ue.RootMotionRootLock.REF_POSE)
        if not lib.save_loaded_asset(clip, False):
            raise RuntimeError("Save failed: " + clip.get_path_name())
        return clip


def apply_torso_wave(rig: RigSessionR60, loc, drop, shift_r, shift_f, yaw_r, lean_f, lean_r, upper_chest_lag_f=0.0):
    """Natural kinetic spine articulation with optional upper-thoracic lag (chest opens at overhead apex!)."""
    pp, pr, ps = loc["pelvis"]
    shift_w = rig.pt(shift_r, shift_f, -drop)
    loc["pelvis"] = ((pp[0] + shift_w[0], pp[1] + shift_w[1], pp[2] + shift_w[2]), pr, ps)
    rig.turn_yaw_right(loc, "pelvis", yaw_r * 0.28)
    rig.turn_pitch_fwd(loc, "pelvis", lean_f * 0.22)
    rig.turn_lean_right(loc, "pelvis", lean_r * 0.16)

    for sp, w_y, w_f, w_s, w_lag in (
        ("spine_01", 0.14, 0.17, 0.16, 0.00),
        ("spine_02", 0.18, 0.19, 0.20, 0.12),
        ("spine_03", 0.20, 0.20, 0.22, 0.26),
        ("spine_04", 0.18, 0.17, 0.22, 0.32),
        ("spine_05", 0.12, 0.12, 0.20, 0.30),
    ):
        if sp in loc:
            rig.turn_yaw_right(loc, sp, yaw_r * w_y)
            rig.turn_pitch_fwd(loc, sp, lean_f * w_f + upper_chest_lag_f * w_lag)
            rig.turn_lean_right(loc, sp, lean_r * w_s)


def build_axe_world_tf(rig: RigSessionR60, grip_mid_rfu, pitch_from_fwd_deg, yaw_right_deg, roll_right_deg):
    """Construct exact world transform of SM_BattleAxe from semantic woodcutter control coordinates:
      - `grip_mid_rfu`: midpoint between upper & lower wooden grip centers (Right, Fwd, Up cm)
      - `pitch_from_fwd_deg`: shaft pitch in vertical cleave plane:
           0 deg = horizontal straight forward (+Y, blade pointing straight DOWN -Z)
         +90 deg = vertical straight UP (+Z, blade pointing FORWARD +Y)
        +140 deg = angled BACK OVER HEAD (-Y/+Z, blade pointing UP/FWD)
         -18 deg = downward cleave into firewood billet (+Y/-Z, blade pointing DOWN/FWD!)
      - `yaw_right_deg`: subtle lateral swing angle (positive rotates axe toward worker's right)
      - `roll_right_deg`: subtle blade bank during S-arc gather/recovery (strictly 0 deg at cleave & impact!)
    """
    pr = math.radians(pitch_from_fwd_deg)
    # In vertical forward cleave plane (right=0):
    #   shaft_0 (+Z_axe) = (0, cos(pr), sin(pr))
    #   blade_0 (+X_axe) = (0, sin(pr), -cos(pr))  -> check: pr=0 => shaft=+Y, blade=-Z (down!); pr=90 => shaft=+Z, blade=+Y (fwd!)
    ez = (0.0, math.cos(pr), math.sin(pr))
    ex = (0.0, math.sin(pr), -math.cos(pr))

    # Apply subtle yaw around world Z (positive yaw_right rotates +Y toward worker's right = -X)
    if abs(yaw_right_deg) > 1e-4:
        qy = q_axis_angle((0.0, 0.0, 1.0), -yaw_right_deg * rig.right_sign)
        ez = q_rot(qy, ez)
        ex = q_rot(qy, ex)

    # Apply subtle roll around shaft axis ez during S-arc gather/recovery
    if abs(roll_right_deg) > 1e-4:
        qr = q_axis_angle(ez, roll_right_deg * rig.right_sign)
        ex = q_rot(qr, ex)

    ez = v_norm(ez)
    ex = v_norm(v_sub(ex, v_scale(ez, v_dot(ex, ez))))
    ey = v_norm(v_cross(ez, ex))
    q_axe = q_from_basis(ex, ey, ez)

    # Anchor SM_BattleAxe origin so the midpoint of the two real curved wood grips (`P_mid_local`)
    # sits EXACTLY at `grip_mid_w`!
    p_mid_loc = v_lerp(BattleAxeGeometry.GRIP_L_LOCAL, BattleAxeGeometry.GRIP_R_LOCAL, 0.5)
    grip_mid_w = rig.pt(*grip_mid_rfu)
    axe_pos_w = v_sub(grip_mid_w, q_rot(q_axe, p_mid_loc))
    return (axe_pos_w, q_axe, (1.0, 1.0, 1.0))


# ==============================================================================
# R60 MASTERPIECE: A_LJ_SplitLog_Loop (48f @ 30fps = 1.60s)
# ==============================================================================
def author_split_log_r60(rig: RigSessionR60):
    """Fluid, powerful, realistic firewood-splitting overhead cleave onto chopping stump billet:
      - Periodic C1 PCHIP curves across all channels (ZERO stop-start stiffness!)
      - Phase-shifted kinetic chain: hips & torso drop/drive 2.5 frames BEFORE hands whip down!
      - Genuine high overhead lift (hands Z ~ 166 cm, blade head soaring to Z ~ 218 cm!)
      - Wide extended mid-downswing power arc (elbows extend smoothly to ~30..45 deg!)
      - Exact impact on integer frame f=24 (u=0.500): steel blade edge splits billet dead-center
        at (X=0.0, Fwd=100.0, Z=82.5 cm) with downward -16 deg shaft cleave!
      - Heavy impact absorption (f=24..27), settled wood-bite hold, hip-led pry-out, and elliptical S-arc recovery!
    """
    fps, n = 30, 48

    # Athletic split woodcutter stance (planted firmly on yard earth Z=8.6 cm)
    foot_l_tgt = rig.pt(-22.0,  14.0, 8.6)
    foot_r_tgt = rig.pt( 24.0, -13.0, 8.6)
    knee_l_pole = rig.pt(-26.0, 46.0, 48.0)
    knee_r_pole = rig.pt( 29.0, 22.0, 48.0)

    # Phase-shifted periodic PCHIP channels (every value continuous C1 across u=1.0 -> 0.0!)
    # Notice: Pelvis/Torso peak at u=0.30 & ALREADY initiate downward crunch at u=0.35..0.46,
    # while the axe head hangs back overhead until u=0.38 then whips explosively to impact at u=0.50!
    torso_ch = {
        "drop":    [(0.00, 5.5), (0.14, 3.8), (0.30, 1.5), (0.36, 3.0), (0.44, 10.0), (0.50, 14.5), (0.55, 16.5), (0.63, 14.0), (0.76, 8.8), (0.88, 6.5)],
        "shift_r": [(0.00, 2.0), (0.14, 5.5), (0.30, 6.0), (0.37, 4.0), (0.45,  0.0), (0.50, -1.5), (0.56, -2.0), (0.66,  0.0), (0.80, 3.0), (0.90, 2.5)],
        # Stay at athletic reach distance so BOTH arms extend cleanly with 0.00 cm reach clamp across ALL 48 frames!
        "shift_f": [(0.00, 1.5), (0.14,-2.5), (0.30,-4.5), (0.37,-2.5), (0.45,  2.0), (0.50,  2.5), (0.56,  3.0), (0.65,  2.2), (0.78, 2.2), (0.90, 1.8)],
        "yaw_r":   [(0.00, 9.0), (0.14,17.0), (0.30,20.0), (0.37,14.0), (0.45,  0.0), (0.50, -7.5), (0.56, -8.5), (0.66, -2.5), (0.80, 6.5), (0.90, 8.5)],
        "lean_f":  [(0.00, 9.5), (0.14, 1.5), (0.30,-7.5), (0.36,-4.5), (0.44,  9.0), (0.50, 16.5), (0.55, 19.0), (0.64, 15.5), (0.78,12.0), (0.90,10.2)],
        "lean_r":  [(0.00, 1.5), (0.14, 4.5), (0.30, 4.8), (0.37, 3.0), (0.45, -0.5), (0.50, -2.0), (0.56, -2.2), (0.68,  0.5), (0.82, 2.0), (0.90, 1.8)],
        # Thoracic chest lag: stays arched open slightly while lower hips begin firing down (real whip!)
        "chest_lag": [(0.00, 0.0), (0.28, -4.0), (0.38, -7.0), (0.45, -3.0), (0.50, 2.5), (0.56, 3.8), (0.72, 1.0), (0.88, 0.0)],
        # Subtle rear right heel lift at deep impact lunge
        "heel_r":  [(0.00, 0.0), (0.34, 0.0), (0.46, 4.0), (0.52, 8.5), (0.60, 5.5), (0.74, 1.0), (0.88, 0.0)],
    }

    # Axe grip-midpoint (Right, Fwd, Up cm) & shaft pitch/yaw/roll (calibrated to lower-handle leverage Z=-27.5/-7.5!):
    # Exact impact (u=0.500, f=24):
    #   grip_mid = (0.0, 53.5, 99.0), pitch = -3.0 deg (realistic horizontal woodsplitting cleave at waist height!) ->
    #   blade_world = (0.0, 100.0, 80.8) cm (DEAD CENTER deep in oak billet!), extended arms (E_r~38, E_l~85), neutral wrists (W<=32 deg)!
    # Exact overhead apex (u=0.35..0.37):
    #   grip_mid = (5.0, 24.5, 164.0), pitch = +138 deg -> high overhead arch (blade Z ~ 212 cm, arm_elev <= 125 deg!)
    # Exact mid-downswing extended power arc (u=0.43..0.44):
    #   grip_mid = (2.5, 49.0, 142.0), pitch = +60 deg -> wide sweeping convex cleave arc!
    axe_ch = {
        "gr_r":  [(0.00,  5.0), (0.14, 11.5), (0.28,  8.5), (0.36,  5.0), (0.43,  2.5), (0.50,  0.0), (0.55, -0.3), (0.63,  0.5), (0.74,  7.5), (0.86,  6.5)],
        "gr_f":  [(0.00, 43.0), (0.14, 37.5), (0.28, 25.0), (0.36, 24.5), (0.43, 45.5), (0.50, 53.5), (0.55, 54.0), (0.63, 51.5), (0.74, 44.0), (0.86, 43.0)],
        "gr_u":  [(0.00,104.0), (0.14,132.0), (0.28,158.0), (0.36,164.0), (0.43,140.0), (0.50, 99.0), (0.55, 95.8), (0.63, 97.5), (0.74, 97.5), (0.86,100.5)],
        # Pitch lags behind hip/hand drop at u=0.37 (+138 deg -> whips explosively through +60 deg -> -3 deg -> -6.5 deg wood bite!)
        "pitch": [(0.00, 32.0), (0.14, 62.0), (0.28,118.0), (0.37,138.0), (0.44, 58.0), (0.50, -3.0), (0.55, -6.5), (0.63, -4.5), (0.75, 10.0), (0.88, 23.0)],
        "yaw":   [(0.00,  6.0), (0.14, 15.0), (0.28, 11.0), (0.36,  5.0), (0.44,  1.5), (0.50,  0.0), (0.55,  0.0), (0.64,  2.0), (0.76, 10.0), (0.88,  8.0)],
        "roll":  [(0.00,  6.0), (0.14, 14.0), (0.28,  8.0), (0.36,  3.0), (0.44,  0.0), (0.50,  0.0), (0.55,  0.0), (0.64,  2.0), (0.76, 10.0), (0.88,  8.0)],
    }

    frames = []
    visual_samples = []
    stats = dict(
        max_reach_err_r=0.0, max_reach_err_l=0.0,
        min_elbow_r=180.0, max_elbow_r=0.0, min_elbow_l=180.0, max_elbow_l=0.0,
        max_arm_elev=0.0, max_wrist_bend_r=0.0, max_wrist_bend_l=0.0,
        max_hand_r_z=0.0, min_hand_r_z=999.0, max_blade_z=0.0,
        max_left_grip_err_cm=0.0,
    )
    impact_info = {}

    inspect_frames = {0, 7, 17, 21, 24, 27, 36}
    for fi in range(n):
        u = fi / float(n)
        tc = eval_channels(torso_ch, u)
        ac = eval_channels(axe_ch, u)

        loc = dict(rig.idle_local)
        apply_torso_wave(rig, loc, tc["drop"], tc["shift_r"], tc["shift_f"], tc["yaw_r"], tc["lean_f"], tc["lean_r"], tc["chest_lag"])

        # Eyes stay locked onto the firewood billet on the stump (head counter-rotates smoothly!)
        rig.turn_yaw_right(loc, "neck_01", -tc["yaw_r"] * 0.36)
        rig.turn_yaw_right(loc, "head", -tc["yaw_r"] * 0.44)
        # Subtle gaze down toward stump top at impact, slight glance up only at highest wind-up
        head_pitch = -tc["lean_f"] * 0.50 + 10.0
        rig.turn_pitch_fwd(loc, "neck_01", head_pitch * 0.40)
        rig.turn_pitch_fwd(loc, "head", head_pitch * 0.60)

        # Grounded athletic legs with subtle rear-heel weight drive
        fr_tgt = (foot_r_tgt[0], foot_r_tgt[1], foot_r_tgt[2] + tc["heel_r"] * 0.22)
        rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=14.0, heel_lift_deg=0.0)
        rig.solve_leg_grounded(loc, "r", fr_tgt, knee_r_pole, toe_out_deg=22.0, heel_lift_deg=tc["heel_r"])

        # Build exact rigid SM_BattleAxe world transform & derive BOTH hands directly from the curved handle!
        axe_tf = build_axe_world_tf(rig, (ac["gr_r"], ac["gr_f"], ac["gr_u"]), ac["pitch"], ac["yaw"], ac["roll"])
        hand_r_tf = tf_mul(axe_tf, rig.hand_in_axe["r"])
        hand_l_tf = tf_mul(axe_tf, rig.hand_in_axe["l"])

        # Natural outward-down elbow poles following the hand height (overhead -> elbows forward-out!)
        lift_frac = max(0.0, min(1.0, (ac["gr_u"] - 115.0) / 50.0))
        pole_r = rig.pt(max(28.0, ac["gr_r"] + 28.0), ac["gr_f"] - 18.0 + 36.0 * lift_frac, ac["gr_u"] - 26.0 + 8.0 * lift_frac)
        pole_l = rig.pt(min(-26.0, ac["gr_r"] - 28.0), ac["gr_f"] - 16.0 + 34.0 * lift_frac, ac["gr_u"] - 28.0 + 8.0 * lift_frac)

        mr = rig.solve_arm_to_exact_hand_tf(loc, "r", hand_r_tf, pole_r, enforce_exact_wrist=True)
        ml = rig.solve_arm_to_exact_hand_tf(loc, "l", hand_l_tf, pole_l, enforce_exact_wrist=True)

        fw = rig.compute_fk(loc)
        # Recompute EXACT runtime axe transform from solved `hand_r` (identical to C++ `AxeInHandR * HandRWorld`!)
        rt_axe_tf = tf_mul(fw["hand_r"], rig.axe_in_hand_r)
        blade_w = tf_point(rt_axe_tf, BattleAxeGeometry.BLADE_EDGE_LOCAL)
        grip_l_expected_w = tf_point(rt_axe_tf, rig.hand_in_axe["l"][0])
        left_err = v_len(v_sub(fw["hand_l"][0], grip_l_expected_w))

        stats["max_reach_err_r"] = max(stats["max_reach_err_r"], mr["reach_err"])
        stats["max_reach_err_l"] = max(stats["max_reach_err_l"], ml["reach_err"])
        stats["min_elbow_r"] = min(stats["min_elbow_r"], mr["elbow_flex"])
        stats["max_elbow_r"] = max(stats["max_elbow_r"], mr["elbow_flex"])
        stats["min_elbow_l"] = min(stats["min_elbow_l"], ml["elbow_flex"])
        stats["max_elbow_l"] = max(stats["max_elbow_l"], ml["elbow_flex"])
        stats["max_arm_elev"] = max(stats["max_arm_elev"], mr["arm_elev"], ml["arm_elev"])
        stats["max_wrist_bend_r"] = max(stats["max_wrist_bend_r"], mr["wrist_bend"])
        stats["max_wrist_bend_l"] = max(stats["max_wrist_bend_l"], ml["wrist_bend"])
        stats["max_hand_r_z"] = max(stats["max_hand_r_z"], fw["hand_r"][0][2])
        stats["min_hand_r_z"] = min(stats["min_hand_r_z"], fw["hand_r"][0][2])
        stats["max_blade_z"] = max(stats["max_blade_z"], blade_w[2])
        stats["max_left_grip_err_cm"] = max(stats["max_left_grip_err_cm"], left_err)

        if fi == 24:
            shaft_w = q_rot(rt_axe_tf[1], BattleAxeGeometry.shaft_dir_grip_pair())
            impact_info = {
                "frame": fi, "u": round(u, 4),
                "blade_world": [round(x, 2) for x in blade_w],
                "blade_right_cm": round(blade_w[0] * rig.right_sign, 2),
                "blade_fwd_cm": round(blade_w[1], 2),
                "blade_z_cm": round(blade_w[2], 2),
                "shaft_pitch_deg": round(math.degrees(math.asin(max(-1.0, min(1.0, shaft_w[2])))), 2),
                "elbow_r": round(mr["elbow_flex"], 1),
                "elbow_l": round(ml["elbow_flex"], 1),
                "wrist_bend_r": round(mr["wrist_bend"], 1),
                "wrist_bend_l": round(ml["wrist_bend"], 1),
                "left_grip_err_cm": round(left_err, 3),
            }

        if fi in inspect_frames:
            dump_bones = [
                "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "head",
                "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
                "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
                "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
            ]
            for s in ("l", "r"):
                for dg in ("thumb", "index", "middle", "ring", "pinky"):
                    for ji in (1, 2, 3):
                        bn = f"{dg}_0{ji}_{s}"
                        if bn in fw:
                            dump_bones.append(bn)
            visual_samples.append({
                "frame": fi, "u": round(u, 3),
                "axe_pos": [round(x, 3) for x in rt_axe_tf[0]],
                "axe_quat": [round(x, 6) for x in rt_axe_tf[1]],
                "blade_w": [round(x, 2) for x in blade_w],
                "bones": {b: [round(x, 2) for x in fw[b][0]] for b in dump_bones if b in fw},
                "metrics": {
                    "elbow_r": round(mr["elbow_flex"], 1), "elbow_l": round(ml["elbow_flex"], 1),
                    "elev_r": round(mr["arm_elev"], 1), "elev_l": round(ml["arm_elev"], 1),
                    "wrist_r": round(mr["wrist_bend"], 1), "wrist_l": round(ml["wrist_bend"], 1),
                    "left_err_cm": round(left_err, 3),
                },
            })

        frames.append(loc)

    clip = rig.bake_sequence(
        "A_LJ_SplitLog_Loop", fps, n, frames,
        "R60 fluid PCHIP overhead firewood split (rigid SM_BattleAxe curved-handle grip, kinetic whip, billet cleave)"
    )
    return dict(
        path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3),
        impact=impact_info,
        **{k: round(v, 3) for k, v in stats.items()}
    ), visual_samples


# ==============================================================================
# R60 SYNCED: A_LJ_ChopTree_Loop (48f @ 30fps = 1.60s) using IDENTICAL rigid AxeInHandR!
# ==============================================================================
def author_chop_tree_r60(rig: RigSessionR60):
    """Standing tree-felling diagonal cleave sharing the EXACT same rigid `AxeInHandR` contract
    so Role 0 transitions seamlessly between Stump SplitLog and Standing Tree ChopTree!"""
    fps, n = 30, 48
    foot_l_tgt = rig.pt(-22.0,  16.0, 8.6)
    foot_r_tgt = rig.pt( 25.0, -14.0, 8.6)
    knee_l_pole = rig.pt(-28.0, 46.0, 48.0)
    knee_r_pole = rig.pt( 30.0, 18.0, 48.0)

    torso_ch = {
        "drop":    [(0.00, 5.0), (0.26, 7.5), (0.36, 8.5), (0.46, 12.5), (0.52, 13.5), (0.64, 10.5), (0.80, 6.5)],
        "shift_r": [(0.00, 2.5), (0.28, 9.5), (0.36, 8.0), (0.46, -4.5), (0.52, -5.0), (0.66, -1.0), (0.82, 2.0)],
        "shift_f": [(0.00, 1.5), (0.28,-3.0), (0.36,-1.0), (0.46,  8.0), (0.52,  8.5), (0.66,  5.0), (0.82, 2.0)],
        "yaw_r":   [(0.00,14.0), (0.28,40.0), (0.36,36.0), (0.46,-20.0), (0.52,-22.0), (0.66, -4.0), (0.82,10.0)],
        "lean_f":  [(0.00, 9.0), (0.28, 4.0), (0.36, 6.0), (0.46, 18.0), (0.52, 19.0), (0.66, 14.0), (0.82,10.0)],
        "lean_r":  [(0.00, 2.0), (0.28, 8.0), (0.36, 7.0), (0.46, -6.0), (0.52, -6.5), (0.66, -1.5), (0.82, 1.5)],
        "chest_lag":[(0.00,0.0), (0.28,-4.0), (0.38,-6.0), (0.46,  2.5), (0.54,  3.0), (0.76,  0.5)],
    }
    # Diagonal chopping arc into standing trunk ahead (impact at u=0.46, f=22 -> blade at Fwd~98cm, Z~108cm!)
    axe_ch = {
        "gr_r":  [(0.00, 11.0), (0.28, 25.0), (0.36, 23.0), (0.46, -5.0), (0.54, -4.5), (0.70,  4.0), (0.84,  9.5)],
        "gr_f":  [(0.00, 42.0), (0.28, 24.0), (0.36, 30.0), (0.46, 52.0), (0.54, 51.0), (0.70, 45.0), (0.84, 43.0)],
        "gr_u":  [(0.00,112.0), (0.28,136.0), (0.36,138.0), (0.46,110.0), (0.54,109.0), (0.70,107.0), (0.84,110.0)],
        "pitch": [(0.00, 42.0), (0.28, 84.0), (0.37, 94.0), (0.46,  8.0), (0.54,  6.0), (0.70, 22.0), (0.84, 34.0)],
        "yaw":   [(0.00, 24.0), (0.28, 56.0), (0.37, 52.0), (0.46,-14.0), (0.54,-12.0), (0.70,  8.0), (0.84, 20.0)],
        "roll":  [(0.00, 32.0), (0.28, 48.0), (0.37, 46.0), (0.46, 58.0), (0.54, 56.0), (0.70, 42.0), (0.84, 34.0)],
    }

    frames = []
    stats = dict(max_reach_err_r=0.0, max_reach_err_l=0.0, max_left_grip_err_cm=0.0, max_arm_elev=0.0, max_wrist_bend_r=0.0)
    for fi in range(n):
        u = fi / float(n)
        tc = eval_channels(torso_ch, u)
        ac = eval_channels(axe_ch, u)
        loc = dict(rig.idle_local)
        apply_torso_wave(rig, loc, tc["drop"], tc["shift_r"], tc["shift_f"], tc["yaw_r"], tc["lean_f"], tc["lean_r"], tc["chest_lag"])
        rig.turn_yaw_right(loc, "neck_01", -tc["yaw_r"] * 0.42)
        rig.turn_yaw_right(loc, "head", -tc["yaw_r"] * 0.42)
        rig.turn_pitch_fwd(loc, "head", -tc["lean_f"] * 0.45)

        rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=14.0)
        rig.solve_leg_grounded(loc, "r", foot_r_tgt, knee_r_pole, toe_out_deg=20.0)

        axe_tf = build_axe_world_tf(rig, (ac["gr_r"], ac["gr_f"], ac["gr_u"]), ac["pitch"], ac["yaw"], ac["roll"])
        hand_r_tf = tf_mul(axe_tf, rig.hand_in_axe["r"])
        hand_l_tf = tf_mul(axe_tf, rig.hand_in_axe["l"])

        pole_r = rig.pt(max(28.0, ac["gr_r"] + 26.0), ac["gr_f"] - 18.0, ac["gr_u"] - 22.0)
        pole_l = rig.pt(min(-24.0, ac["gr_r"] - 26.0), ac["gr_f"] - 16.0, ac["gr_u"] - 24.0)

        mr = rig.solve_arm_to_exact_hand_tf(loc, "r", hand_r_tf, pole_r, enforce_exact_wrist=True)
        ml = rig.solve_arm_to_exact_hand_tf(loc, "l", hand_l_tf, pole_l, enforce_exact_wrist=True)
        fw = rig.compute_fk(loc)
        rt_axe_tf = tf_mul(fw["hand_r"], rig.axe_in_hand_r)
        left_err = v_len(v_sub(fw["hand_l"][0], tf_point(rt_axe_tf, rig.hand_in_axe["l"][0])))

        stats["max_reach_err_r"] = max(stats["max_reach_err_r"], mr["reach_err"])
        stats["max_reach_err_l"] = max(stats["max_reach_err_l"], ml["reach_err"])
        stats["max_left_grip_err_cm"] = max(stats["max_left_grip_err_cm"], left_err)
        stats["max_arm_elev"] = max(stats["max_arm_elev"], mr["arm_elev"], ml["arm_elev"])
        stats["max_wrist_bend_r"] = max(stats["max_wrist_bend_r"], mr["wrist_bend"])
        frames.append(loc)

    clip = rig.bake_sequence(
        "A_LJ_ChopTree_Loop", fps, n, frames,
        "R60 fluid PCHIP tree felling cleave (synced rigid SM_BattleAxe curved-handle grip)"
    )
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 3) for k, v in stats.items()})


def extract_battleaxe_preview_mesh():
    """Extract subsampled SM_BattleAxe LOD0 vertices & triangles for 3D visual contact-sheet verification."""
    sm = ue.load_asset(SM_BATTLE_AXE)
    dyn = ue.new_object(ue.DynamicMesh)
    opts = ue.GeometryScriptCopyMeshFromAssetOptions()
    lod = ue.GeometryScriptMeshReadLOD()
    lod.lod_type = ue.GeometryScriptLODType.RENDER_DATA
    lod.lod_index = 2  # Clean lightweight ~2k-tri LOD for fast crystal-clear visual audit
    ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, opts, lod)
    nv = int(ue.GeometryScript_MeshQueries.get_vertex_count(dyn))
    verts = []
    for vid in range(nv):
        v, ok = ue.GeometryScript_MeshQueries.get_vertex_position(dyn, vid)
        verts.append([round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)] if ok else [0.0, 0.0, 0.0])
    nt = int(dyn.get_triangle_count()) if hasattr(dyn, "get_triangle_count") else int(ue.GeometryScript_MeshQueries.get_num_triangle_ids(dyn))
    tris = []
    for tid in range(nt):
        t, ok = ue.GeometryScript_MeshQueries.get_triangle_indices(dyn, tid)
        if ok:
            tris.append([int(t.x), int(t.y), int(t.z)])
    return {"verts": verts, "tris": tris}


def main():
    body = ue.load_asset(SK_SMITH_BODY)
    if not body:
        raise RuntimeError(f"Cannot load {SK_SMITH_BODY}")
    rig = RigSessionR60(body)

    split_report, visual_samples = author_split_log_r60(rig)
    chop_report = author_chop_tree_r60(rig)
    axe_mesh = extract_battleaxe_preview_mesh()

    ap, aq, _ = rig.axe_in_hand_r
    receipt = {
        "batch": "LumberMillOps-R60",
        "axe_in_hand_r": {
            "pos_cm": [round(x, 4) for x in ap],
            "quat_xyzw": [round(x, 6) for x in aq],
            "scale": BattleAxeGeometry.SCALE,
            "grip_r_axe_local": list(BattleAxeGeometry.GRIP_R_LOCAL),
            "grip_l_axe_local": list(BattleAxeGeometry.GRIP_L_LOCAL),
            "blade_edge_axe_local": list(BattleAxeGeometry.BLADE_EDGE_LOCAL),
        },
        "animations": {
            "A_LJ_SplitLog_Loop": split_report,
            "A_LJ_ChopTree_Loop": chop_report,
        },
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    VISUAL_DUMP_PATH.write_text(json.dumps({
        "right_sign": rig.right_sign,
        "axe_mesh": axe_mesh,
        "samples": visual_samples,
    }), encoding="utf-8")
    ue.log(f"[R60-DONE] SplitLog={split_report}")
    ue.log(f"[R60-DONE] ChopTree={chop_report}")


if __name__ == "__main__":
    main()
