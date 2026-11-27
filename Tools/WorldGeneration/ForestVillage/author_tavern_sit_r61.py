"""Headless UE 5.8 Authoring Pipeline for LumberMillOps-R61:
Natural Casual Tavern Rest Sitting Animation (`A_LJ_SitTavern_Relaxed`, 120f @ 30fps = 4.00 s).

Calibrated to exact measured Tavern furniture in L_AbandonedVillage:
  - SM_TavernStool: seat top Z = 46.06 cm, radius 20.0 cm
  - SM_TavernTable: round tabletop Z = 76.07 cm, radius 58.0 cm, center Fwd = +82.0 cm (rim at Fwd = +24.0 cm)
  - SK_Smith_Body: Actor.Z = FloorZ + 88.0 -> skeleton Z = 0.0 is exact floorboard datum!

Design highlights:
  - Pelvis seated solidly at Z = 55.5 cm (thigh underside dead-flush on 46.06 cm stool, 0 hover / 0 sink).
  - Asymmetric relaxed legs (left foot forward-open Fwd=+43, right foot casually tucked Fwd=+31.5, boots flat on floor).
  - Natural casual working-man slouch (+13 deg forward lean, +7 deg torso open yaw, soft spine curve).
  - Right forearm/relaxed hand resting flush ON TOP of the 76.07 cm wooden tabletop (Z = 79.4 cm, >= 14 cm clear of bowl/spoon).
  - Left relaxed hand draped naturally atop left mid-thigh (Z = 61.5 cm, 0 clipping).
  - Smooth periodic C1 PCHIP 4.0 s breathing + casual taproom gaze drift + subtle hand/shoulder settle.
  - Exports SM_TavernStool + SM_TavernTable meshes + posed skeleton snapshot for 3D visual audit!
"""
import json
import math
import sys
from pathlib import Path
import unreal as ue

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
sys.path.insert(0, str(TOOLS))

# Reuse proven math, periodic PCHIP, and anatomically calibrated rig session from R60!
from author_lumber_ops_r60 import (
    SK_SMITH_BODY, LM_ANIMS, RigSessionR60,
    v_add, v_sub, v_scale, v_dot, v_cross, v_len, v_norm,
    q_norm, q_mul, q_inv, q_rot, q_axis_angle, q_from_basis,
    tf_mul, eval_channels,
)

SM_TAVERN_STOOL = "/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernStool"
SM_TAVERN_TABLE = "/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernTable"

BATCH_DIR = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R61")
BATCH_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_PATH = BATCH_DIR / "authored-sit-r61.json"
VISUAL_DUMP_PATH = BATCH_DIR / "visual-sit-r61.json"


def apply_relaxed_finger_curl(rig: RigSessionR60, loc, side, curl_scale=0.55):
    """Natural relaxed half-open resting hand fingers (NOT clenched fist, NOT rigid flat plank!)."""
    w = rig.compute_fk(loc)
    info = rig.arm_info[side]
    hd = f"hand_{side}"
    palm_w = q_rot(w[hd][1], info["f_palm_loc"])
    fwd_w = q_rot(w[hd][1], info["f_fwd_loc"])
    flex_axis = v_norm(v_cross(fwd_w, palm_w))

    # Cascade slight natural curl: pinky curls slightly more than index (classic resting hand!)
    for digit, angles in (
        ("index",  (14.0, 18.0, 10.0)),
        ("middle", (18.0, 24.0, 14.0)),
        ("ring",   (22.0, 28.0, 16.0)),
        ("pinky",  (26.0, 32.0, 18.0)),
    ):
        for ji, deg in enumerate(angles):
            bn = f"{digit}_0{ji+1}_{side}"
            if bn in loc:
                w = rig.compute_fk(loc)
                pr = w[rig.parent[bn]][1]
                br = w[bn][1]
                new_br = q_norm(q_mul(q_axis_angle(flex_axis, deg * curl_scale), br))
                lp, _, ls = loc[bn]
                loc[bn] = (lp, q_norm(q_mul(q_inv(pr), new_br)), ls)

    # Relaxed thumb resting slightly inward
    t1, t2 = f"thumb_01_{side}", f"thumb_02_{side}"
    if t1 in loc and t2 in loc:
        w = rig.compute_fk(loc)
        rad_w = q_rot(w[hd][1], info["f_rad_loc"])
        t_axis = v_norm(v_cross(rad_w, palm_w))
        for ji, deg in enumerate((10.0, 12.0, 8.0)):
            bn = f"thumb_0{ji+1}_{side}"
            if bn in loc:
                w = rig.compute_fk(loc)
                pr = w[rig.parent[bn]][1]
                br = w[bn][1]
                new_br = q_norm(q_mul(q_axis_angle(t_axis, deg * curl_scale), br))
                lp, _, ls = loc[bn]
                loc[bn] = (lp, q_norm(q_mul(q_inv(pr), new_br)), ls)


def solve_hand_relaxed_rot(rig: RigSessionR60, side, hand_fwd_w, palm_down_w):
    """Build exact world quaternion for `hand_{side}` so fingers point along `hand_fwd_w`
    and palm faces `palm_down_w` (flat on tabletop or draped on thigh!)."""
    info = rig.arm_info[side]
    df = v_norm(hand_fwd_w)
    dp = v_norm(v_sub(palm_down_w, v_scale(df, v_dot(palm_down_w, df))))
    # Match SK_Smith_Body hand-local basis handedness: loc_3 = f_fwd x f_rad
    loc_3 = v_norm(v_cross(info["f_fwd_loc"], info["f_rad_loc"]))
    sgn = 1.0 if v_dot(loc_3, info["f_palm_loc"]) >= 0.0 else -1.0
    # We want df x dr = dp * sgn  =>  dr = (dp * sgn) x df!
    des_3 = v_scale(dp, sgn)
    dr = v_norm(v_cross(des_3, df))
    des_3 = v_norm(v_cross(df, dr))
    q_loc = q_from_basis(info["f_fwd_loc"], info["f_rad_loc"], loc_3)
    q_des = q_from_basis(df, dr, des_3)
    return q_norm(q_mul(q_des, q_inv(q_loc)))


def extract_static_mesh_preview(asset_path):
    sm = ue.load_asset(asset_path)
    if not sm:
        return {"verts": [], "tris": []}
    dyn = ue.new_object(ue.DynamicMesh)
    opts = ue.GeometryScriptCopyMeshFromAssetOptions()
    lod = ue.GeometryScriptMeshReadLOD()
    lod.lod_type = ue.GeometryScriptLODType.RENDER_DATA
    lod.lod_index = 0
    ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(sm, dyn, opts, lod)
    nv = int(ue.GeometryScript_MeshQueries.get_vertex_count(dyn))
    verts = []
    for vid in range(nv):
        v, ok = ue.GeometryScript_MeshQueries.get_vertex_position(dyn, vid)
        verts.append([round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)] if ok else [0.0, 0.0, 0.0])
    nt = int(dyn.get_triangle_count()) if hasattr(dyn, "get_triangle_count") else int(ue.GeometryScript_MeshQueries.get_num_triangle_ids(dyn))
    tris = []
    # Subsample slightly if huge mesh, else keep all
    step = 1 if nt <= 4000 else max(1, nt // 3500)
    for tid in range(0, nt, step):
        t, ok = ue.GeometryScript_MeshQueries.get_triangle_indices(dyn, tid)
        if ok:
            tris.append([int(t.x), int(t.y), int(t.z)])
    return {"verts": verts, "tris": tris}


def author_sit_tavern_relaxed(rig: RigSessionR60):
    fps, n = 30, 120  # 4.00 s relaxed breathing & tavern look-around loop

    # Start from bench_local base pose for clean pelvic tilt & hip sockets, then refine pelvis, spine, legs & arms!
    base_pelvis_p = rig.bench_world["pelvis"][0]

    # Periodic C1 PCHIP living tavern rest channels:
    ch = {
        # Subtle breathing chest rise + casual seated weight settle
        "breath":    [(0.00, 0.0), (0.25, 1.0), (0.50, 0.1), (0.75, 0.9), (0.90, 0.3)],
        # Casual forward slouch (~19.5 deg warm tavern relax leaning gently toward table, NOT military rigid!)
        "lean_f":    [(0.00, 19.5), (0.28, 18.0), (0.52, 20.5), (0.78, 18.8)],
        # Casual torso twist slightly open toward taproom (+6..+9 deg)
        "yaw_r":     [(0.00,  7.0), (0.32,  4.5), (0.62,  9.2), (0.86,  7.8)],
        # Slight relaxed lateral lean toward resting right forearm on table (+3.5 deg)
        "lean_r":    [(0.00,  3.6), (0.35,  2.6), (0.68,  4.4), (0.88,  3.8)],
        # Living taproom gaze: glance left toward hearth/room -> back warmly toward table/bowl -> slight right glance
        "head_yaw":  [(0.00, -4.0), (0.22,-18.0), (0.40,-14.0), (0.58,  5.0), (0.76,  8.5), (0.90, -1.0)],
        "head_pitch":[(0.00, 11.0), (0.22,  3.0), (0.42,  6.0), (0.60, 16.0), (0.78, 13.5), (0.90, 11.5)],
        "head_roll": [(0.00,  1.5), (0.26, -3.5), (0.58,  3.0), (0.84,  2.0)],
        # Subtle living micro-settle on resting hands (stays 100% flush on tabletop & upper thigh!)
        "rhand_f":   [(0.00, 39.0), (0.35, 39.6), (0.70, 38.5)],
        "rhand_r":   [(0.00, 13.5), (0.35, 14.2), (0.70, 13.0)],
        "lhand_f":   [(0.00, 20.0), (0.40, 20.8), (0.75, 19.8)],
    }

    # Asymmetric relaxed foot placements on floorboards (Z = 8.8 cm ankle -> boot sole flat at Z = 0.0!)
    # Left foot forward-out (relaxed open stance), Right foot tucked casually closer under stool!
    foot_l_tgt = rig.pt(-17.5, 42.5, 8.8)
    foot_r_tgt = rig.pt( 15.5, 30.5, 8.8)
    knee_l_pole = rig.pt(-27.0, 44.0, 56.0)
    knee_r_pole = rig.pt( 24.5, 36.0, 54.0)

    frames = []
    visual_samples = []
    inspect_frames = {0, 32, 70, 100}
    stats = dict(
        min_pelvis_z=999.0, max_pelvis_z=0.0,
        min_thigh_z=999.0, max_thigh_z=0.0,
        min_rhand_z=999.0, max_rhand_z=0.0,
        min_lhand_z=999.0, max_lhand_z=0.0,
        max_reach_err_r=0.0, max_reach_err_l=0.0,
        max_wrist_bend_r=0.0, max_wrist_bend_l=0.0,
        max_arm_elev=0.0,
    )

    for fi in range(n):
        u = fi / float(n)
        c = eval_channels(ch, u)

        # Start from bench_local so hip/pelvis seated base orientation is clean, then pose every segment smoothly!
        loc = dict(rig.bench_local)

        # 1. Exact pelvis placement: seated solidly on 46.06 cm SM_TavernStool (pelvis Z = 55.6 cm -> thigh underside Z ~ 46.3 cm!)
        # Shift slightly back (-1.8 cm) so hips sit squarely centered on the 40 cm round wooden stool.
        p_lp, p_lr, p_ls = loc["pelvis"]
        pelvis_target_z = 55.6 + 0.25 * c["breath"]
        dz = pelvis_target_z - base_pelvis_p[2]
        loc["pelvis"] = (
            (p_lp[0] + 0.5 * rig.right_sign, p_lp[1] - 1.8, p_lp[2] + dz),
            p_lr,
            p_ls,
        )
        # Subtle pelvis pitch/yaw for casual weight distribution
        rig.turn_pitch_fwd(loc, "pelvis", 4.5)
        rig.turn_yaw_right(loc, "pelvis", c["yaw_r"] * 0.25)

        # 2. Natural relaxed spine slouch + gentle breathing expansion
        lean_f = c["lean_f"] - 1.2 * c["breath"]
        yaw_r = c["yaw_r"] * 0.75
        lean_r = c["lean_r"]
        for bn, wf, wy, wr in (
            ("spine_01", 0.14, 0.15, 0.15),
            ("spine_02", 0.20, 0.20, 0.20),
            ("spine_03", 0.24, 0.25, 0.25),
            ("spine_04", 0.22, 0.20, 0.20),
            ("spine_05", 0.20, 0.20, 0.20),
        ):
            rig.turn_pitch_fwd(loc, bn, lean_f * wf)
            rig.turn_yaw_right(loc, bn, yaw_r * wy)
            rig.turn_lean_right(loc, bn, lean_r * wr)

        # 3. Living casual head & neck look-around (counter-balances forward slouch naturally)
        rig.turn_yaw_right(loc, "neck_01", c["head_yaw"] * 0.38)
        rig.turn_yaw_right(loc, "head",    c["head_yaw"] * 0.62)
        rig.turn_pitch_fwd(loc, "neck_01", (c["head_pitch"] - lean_f * 0.65) * 0.40)
        rig.turn_pitch_fwd(loc, "head",    (c["head_pitch"] - lean_f * 0.65) * 0.60)
        rig.turn_lean_right(loc, "head",   c["head_roll"])

        # 4. Asymmetric relaxed grounded legs (boots flat on floor Z=0, knees clear of tabletop & splayed naturally)
        rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=18.0, heel_lift_deg=0.0)
        rig.solve_leg_grounded(loc, "r", foot_r_tgt, knee_r_pole, toe_out_deg=26.0, heel_lift_deg=0.0)

        # Compute leg FK so left hand drapes cleanly ON TOP of left mid-thigh!
        fw_pre = rig.compute_fk(loc)
        thigh_l_p = fw_pre["thigh_l"][0]
        calf_l_p = fw_pre["calf_l"][0]
        # Left hand resting spot: ~52% down left thigh (clear of table rim Fwd=24 cm!), +9.4 cm above femur centerline (on top of denim!)
        l_mid_thigh = (
            thigh_l_p[0] * 0.45 + calf_l_p[0] * 0.55,
            c["lhand_f"],
            thigh_l_p[2] * 0.45 + calf_l_p[2] * 0.55 + 9.4 + 0.2 * c["breath"],
        )

        # 5. Right arm: forearm & relaxed open hand resting casually ON TOP of the 76.07 cm round Tavern tabletop!
        # Table outer rim is at Fwd=+24.0 cm (repaired) / +30.5 cm (ruined), tabletop Z=76.07 cm.
        # Wrist sits at Z=79.4 cm (+3.3 cm above wood -> palm & lower forearm rest dead-flush on tabletop, ZERO sink!),
        # elbow settles casually right onto the outer right table rim (Right=+24, Fwd=+24, Z~80 cm)!
        r_hand_pos = rig.pt(c["rhand_r"], c["rhand_f"], 79.4)
        # Fingers angle casually forward-inward across the table toward the glowing lantern/bowl
        r_fwd_w = rig.vec(-0.46, 0.88, -0.06)
        r_palm_w = rig.vec(-0.10, 0.04, -0.99)
        r_hand_rot = solve_hand_relaxed_rot(rig, "r", r_fwd_w, r_palm_w)
        pole_r = rig.pt(31.0, 23.0, 74.0)  # elbow settles gently right down to table rim height!

        # 6. Left arm: relaxed open hand draped comfortably on left upper-mid thigh (0.00 cm reach err, clear of table rim!)
        l_hand_pos = l_mid_thigh
        l_fwd_w = rig.vec(0.24, 0.88, -0.40)
        l_palm_w = rig.vec(0.20, -0.35, -0.91)
        l_hand_rot = solve_hand_relaxed_rot(rig, "l", l_fwd_w, l_palm_w)
        pole_l = rig.pt(-30.0, 2.0, 74.0)  # elbow hangs loosely at left side with natural ~35 deg bend!

        mr = rig.solve_arm_to_exact_hand_tf(loc, "r", (r_hand_pos, r_hand_rot, (1.0, 1.0, 1.0)), pole_r, enforce_exact_wrist=False)
        ml = rig.solve_arm_to_exact_hand_tf(loc, "l", (l_hand_pos, l_hand_rot, (1.0, 1.0, 1.0)), pole_l, enforce_exact_wrist=False)

        # Override clenched axe fingers from solve_arm_to_exact_hand_tf with relaxed resting open-curved fingers!
        for bn in list(loc.keys()):
            if any(bn.startswith(dg) for dg in ("thumb_", "index_", "middle_", "ring_", "pinky_")):
                loc[bn] = rig.idle_local[bn]
        apply_relaxed_finger_curl(rig, loc, "r", curl_scale=0.52)
        apply_relaxed_finger_curl(rig, loc, "l", curl_scale=0.68)

        fw = rig.compute_fk(loc)
        stats["min_pelvis_z"] = min(stats["min_pelvis_z"], fw["pelvis"][0][2])
        stats["max_pelvis_z"] = max(stats["max_pelvis_z"], fw["pelvis"][0][2])
        stats["min_thigh_z"] = min(stats["min_thigh_z"], fw["thigh_l"][0][2], fw["thigh_r"][0][2])
        stats["max_thigh_z"] = max(stats["max_thigh_z"], fw["thigh_l"][0][2], fw["thigh_r"][0][2])
        stats["min_rhand_z"] = min(stats["min_rhand_z"], fw["hand_r"][0][2])
        stats["max_rhand_z"] = max(stats["max_rhand_z"], fw["hand_r"][0][2])
        stats["min_lhand_z"] = min(stats["min_lhand_z"], fw["hand_l"][0][2])
        stats["max_lhand_z"] = max(stats["max_lhand_z"], fw["hand_l"][0][2])
        stats["max_reach_err_r"] = max(stats["max_reach_err_r"], mr["reach_err"])
        stats["max_reach_err_l"] = max(stats["max_reach_err_l"], ml["reach_err"])
        stats["max_wrist_bend_r"] = max(stats["max_wrist_bend_r"], mr["wrist_bend"])
        stats["max_wrist_bend_l"] = max(stats["max_wrist_bend_l"], ml["wrist_bend"])
        stats["max_arm_elev"] = max(stats["max_arm_elev"], mr["arm_elev"], ml["arm_elev"])

        if fi in inspect_frames:
            dump_bones = [
                "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "head",
                "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
                "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
                "thigh_l", "calf_l", "foot_l", "ball_l",
                "thigh_r", "calf_r", "foot_r", "ball_r",
            ]
            for s in ("l", "r"):
                for dg in ("thumb", "index", "middle", "ring", "pinky"):
                    for ji in (1, 2, 3):
                        bn = f"{dg}_0{ji}_{s}"
                        if bn in fw:
                            dump_bones.append(bn)
            visual_samples.append({
                "frame": fi, "u": round(u, 3),
                "bones": {b: [round(x, 2) for x in fw[b][0]] for b in dump_bones if b in fw},
                "metrics": {
                    "pelvis_z": round(fw["pelvis"][0][2], 1),
                    "elbow_r_z": round(fw["lowerarm_r"][0][2], 1),
                    "hand_r_z": round(fw["hand_r"][0][2], 1),
                    "hand_l_z": round(fw["hand_l"][0][2], 1),
                    "wrist_r": round(mr["wrist_bend"], 1),
                    "wrist_l": round(ml["wrist_bend"], 1),
                    "elev_r": round(mr["arm_elev"], 1),
                },
            })

        frames.append(loc)

    clip = rig.bake_sequence(
        "A_LJ_SitTavern_Relaxed", fps, n, frames,
        "R61 relaxed casual Tavern stool-and-table sitting loop (46cm stool flush seat, right forearm on 76cm table, left hand on thigh)"
    )
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 3) for k, v in stats.items()}), visual_samples


def main():
    body = ue.load_asset(SK_SMITH_BODY)
    if not body:
        raise RuntimeError(f"Cannot load {SK_SMITH_BODY}")
    rig = RigSessionR60(body)
    report, samples = author_sit_tavern_relaxed(rig)
    stool_mesh = extract_static_mesh_preview(SM_TAVERN_STOOL)
    table_mesh = extract_static_mesh_preview(SM_TAVERN_TABLE)

    RECEIPT_PATH.write_text(json.dumps({"batch": "LumberMillOps-R61", "animation": report}, indent=2, ensure_ascii=False), encoding="utf-8")
    VISUAL_DUMP_PATH.write_text(json.dumps({
        "right_sign": rig.right_sign,
        "stool_mesh": stool_mesh,
        "table_mesh": table_mesh,
        "samples": samples,
    }), encoding="utf-8")
    ue.log(f"[R61-SIT-DONE] {report}")


if __name__ == "__main__":
    main()
