"""Headless UE 5.8 authoring pipeline for LumberMillOps-R52 (Ergonomic R55 Upgrade):
  Part A: Import 5 modular Timber Wagon & Horse Harness FBX assets into
          /Game/ForestPathStudy/VillageRegion/LumberMill/Transport/
          using 100% resident PBR materials (+0.00 MB VRAM!), smart LOD/Nanite,
          and exact KBoxElem simple collisions.
  Part B: Author 5 anatomically accurate, ergonomic 3P Lumberjack AnimSequences on
          SK_Smith_Body (SKM_Jason_body_Skeleton) into
          /Game/ForestPathStudy/VillageRegion/LumberMill/Animations/:
            - Exact measured coordinate handedness (+X = LEFT, -X = RIGHT, +Y = FWD, +Z = UP)
            - True anatomical hinge-plane 2-bone IK (calibrated from flexed rest elbows & bench knees;
              ZERO elbow/knee roll twist or candy-wrapper distortion!)
            - Clavicle elevation/protraction follow-through
            - Jason V9 forearm & upperarm twist bone distribution (lowerarm_twist_01/02, upperarm_twist_01)
            - Non-linear anticipation / explosive cleave / impact recoil easing
            - Hard ergonomic & 3D log-vs-head/torso zero-clipping clearance audit!
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal as ue

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
sys.path.insert(0, str(TOOLS))

lib = ue.EditorAssetLibrary
asset_tools = ue.AssetToolsHelpers.get_asset_tools()
mesh_sub = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)

LM_BASE = "/Game/ForestPathStudy/VillageRegion/LumberMill"
LM_TRANSPORT = LM_BASE + "/Transport"
LM_ANIMS = LM_BASE + "/Animations"
LM_MATS = LM_BASE + "/Materials"

FBX_DIR = Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/TransportFBX")
RECEIPT_PATH = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R52/authored-ops-r52.json")

RESIDENT_TRANSPORT_MATS = {
    "Oak": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak",
    "OiledOak": "/Game/WorldGeneration/VillageTavern/Furniture/M_TavernOiledOak",
    "DarkWood": "/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelTimber",
    "Sawn": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSawn",
    "Endgrain": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterCut",
    "Bark": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBark",
    "ScaleIron": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_SmithScaleIron",
    "Iron": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron",
    "Steel": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSteel",
    "Brass": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBrass",
    "Rope": "/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/Materials/M_StableWeatheredRope",
    "LeatherMain": "/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/Materials/M_StableSaddleLeather",
    "LeatherDark": "/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/Materials/M_StableHarnessLeather",
}

SK_SMITH_BODY = "/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Body"
BASE_IDLE = "/Game/Characters/JasonPlayer20261003/Animations/J_MM_Idle"
BASE_WALK = "/Game/Characters/JasonPlayer20261003/Animations/J_MF_Unarmed_Walk_Fwd"
BASE_BENCH = "/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/RefineV2/A_Rest_Bench_Idle"
SK_WARHORSE = "/Game/WorldGeneration/TemperateHills/VillageStable/Horses/SK_StableWarhorse"


def save_asset(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError("Save failed: " + asset.get_path_name())


# ==============================================================================
# PART A: IMPORT 5 MODULAR TIMBER WAGON & HORSE HARNESS FBX ASSETS
# ==============================================================================
def configure_transport_mesh(mesh: ue.StaticMesh, colliders: list, enable_nanite: bool):
    mesh_sub.remove_collisions(mesh)
    body = mesh.get_editor_property("body_setup")
    if body and colliders:
        agg = body.get_editor_property("agg_geom")
        boxes = []
        for col in colliders:
            box = ue.KBoxElem()
            box.set_editor_property("center", ue.Vector(*col["center"]))
            box.set_editor_property("x", float(col["size"][0]))
            box.set_editor_property("y", float(col["size"][1]))
            box.set_editor_property("z", float(col["size"][2]))
            yaw = float(col.get("yaw", 0.0))
            if abs(yaw) > 0.01:
                box.set_editor_property("rotation", ue.Rotator(pitch=0.0, yaw=yaw, roll=0.0))
            boxes.append(box)
        agg.set_editor_property("box_elems", boxes)
        body.set_editor_property("agg_geom", agg)
        body.set_editor_property("collision_trace_flag", ue.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        mesh.set_editor_property("body_setup", body)
        cooked = ue.GeometryScript_Collision.get_simple_collision_from_static_mesh(mesh)
        ue.GeometryScript_Collision.set_simple_collision_of_static_mesh(
            cooked, mesh, ue.GeometryScriptSetSimpleCollisionOptions()
        )

    ns = mesh.get_editor_property("nanite_settings")
    ns.set_editor_property("enabled", bool(enable_nanite))
    mesh.set_editor_property("nanite_settings", ns)

    if enable_nanite:
        ue.ForestVillageRegion.build_scenery_nanite_mesh(mesh, None)
    else:
        try:
            lod_opts = ue.StaticMeshReductionOptions()
            r0 = ue.StaticMeshReductionSettings(); r0.percent_triangles = 1.0; r0.screen_size = 1.0
            r1 = ue.StaticMeshReductionSettings(); r1.percent_triangles = 0.50; r1.screen_size = 0.25
            r2 = ue.StaticMeshReductionSettings(); r2.percent_triangles = 0.22; r2.screen_size = 0.08
            lod_opts.reduction_settings = [r0, r1, r2]
            lod_opts.auto_compute_lod_screen_size = False
            mesh_sub.set_lods(mesh, lod_opts)
        except Exception as ex:
            ue.log_warning(f"[WAGON-LOD] {mesh.get_name()}: {ex}")
    save_asset(mesh)


def import_transport_meshes():
    manifest_path = FBX_DIR / "transport-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Missing transport-manifest.json at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split_manifest = FBX_DIR / "splitlog-manifest.json"
    if split_manifest.is_file():
        manifest = manifest + json.loads(split_manifest.read_text(encoding="utf-8"))
    if os.environ.get("FPS_LUMBER_SPLITLOG_ONLY") == "1":
        manifest = [e for e in manifest if e["name"].startswith("SM_LM_SplitLog_")]
    lib.make_directory(LM_TRANSPORT)

    mat_cache = {}
    for key, mpath in RESIDENT_TRANSPORT_MATS.items():
        local_res = f"{LM_MATS}/M_LM_Res_{key}"
        mat = ue.load_asset(local_res) if lib.does_asset_exist(local_res) else ue.load_asset(mpath)
        if not mat:
            raise RuntimeError(f"Missing resident transport material {key}: {mpath}")
        mat_cache[key] = mat

    imported = {}
    for entry in manifest:
        name = entry["name"]
        fbx_path = Path(entry["lods"][0]["file"])
        dest_asset = f"{LM_TRANSPORT}/{name}"

        opts = ue.FbxImportUI()
        opts.import_mesh = True
        opts.import_as_skeletal = False
        opts.import_materials = False
        opts.import_textures = False
        opts.automated_import_should_detect_type = False
        opts.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
        sm_data = opts.static_mesh_import_data
        sm_data.combine_meshes = True
        sm_data.auto_generate_collision = False
        sm_data.generate_lightmap_u_vs = False
        sm_data.vertex_color_import_option = ue.VertexColorImportOption.REPLACE
        sm_data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        sm_data.import_uniform_scale = 1.0

        task = ue.AssetImportTask()
        task.filename = str(fbx_path)
        task.destination_path = LM_TRANSPORT
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = opts
        asset_tools.import_asset_tasks([task])

        mesh = ue.load_asset(dest_asset)
        if not isinstance(mesh, ue.StaticMesh):
            raise RuntimeError(f"Failed importing transport FBX {name}")

        slots = list(mesh.get_editor_property("static_materials"))
        assigned = []
        for idx, slot in enumerate(slots):
            sname = str(slot.get_editor_property("imported_material_slot_name") or slot.get_editor_property("material_slot_name"))
            base_key = sname.split(".")[0]
            mat = mat_cache.get(base_key) or mat_cache["Oak"]
            mesh.set_material(idx, mat)
            assigned.append(f"{base_key}->{mat.get_name()}")

        use_nanite = name in ("SM_LM_TimberWagon_TimberLoad",)
        configure_transport_mesh(mesh, entry.get("colliders", []), enable_nanite=use_nanite)

        box = mesh.get_bounding_box()
        sz = box.max - box.min
        imported[name] = {
            "mesh": mesh.get_path_name(),
            "size_cm": [round(float(sz.x), 1), round(float(sz.y), 1), round(float(sz.z), 1)],
            "min_cm": [round(float(box.min.x), 1), round(float(box.min.y), 1), round(float(box.min.z), 1)],
            "max_cm": [round(float(box.max.x), 1), round(float(box.max.y), 1), round(float(box.max.z), 1)],
            "colliders": len(entry.get("colliders", [])),
            "nanite": bool(mesh.get_editor_property("nanite_settings").enabled),
            "materials": assigned,
        }
        ue.log(f"[R52-MESH] {name:30s} | sz={imported[name]['size_cm']} | col={imported[name]['colliders']} | mats={len(assigned)}")
    return imported


# ==============================================================================
# PART B: ANATOMICAL HINGE-PLANE 2-BONE IK + TWIST-BONE + NON-LINEAR EASING
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


def q_inv(q):
    return (-q[0], -q[1], -q[2], q[3])


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


def q_angle_deg(q):
    q = q_norm(q)
    w = max(-1.0, min(1.0, abs(q[3])))
    return math.degrees(2.0 * math.acos(w))


def q_from_basis(ex, ey, ez):
    """Build quaternion from orthonormal right-handed columns (ex, ey, ez)."""
    # Ensure exact right-handed basis
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
    """Decompose q = q_swing * q_twist where q_twist is pure rotation around unit `axis`."""
    q = q_norm(q)
    if q[3] < 0.0:
        q = (-q[0], -q[1], -q[2], -q[3])
    ax = v_norm(axis)
    proj = q[0]*ax[0] + q[1]*ax[1] + q[2]*ax[2]
    tw = q_norm((ax[0]*proj, ax[1]*proj, ax[2]*proj, q[3]))
    sw = q_norm(q_mul(q, q_inv(tw)))
    # Signed twist angle in degrees around `ax`
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


def apply_ease(t, kind="smooth"):
    t = max(0.0, min(1.0, t))
    if kind == "strike_heavy":
        # Explosive continuous downward whip into axe cleave impact (crisp heavy chopping power!)
        return t ** 2.8
    if kind == "strike":
        # Non-linear explosive acceleration into impact (heavy mass feel!)
        return t * t * t
    if kind == "recoil":
        # Fast deceleration cushion right after impact
        return 1.0 - (1.0 - t) ** 3
    if kind == "windup":
        # Slow gather, gentle ease-out to peak anticipation
        return 1.0 - (1.0 - t) * (1.0 - t)
    # Default smooth cubic S-curve
    return t * t * (3.0 - 2.0 * t)


def lerp_nested(a, b, t):
    if isinstance(a, tuple):
        return tuple(lerp_nested(a[k], b[k], t) for k in range(len(a)))
    return a + (b - a) * t


def eval_keyed_curve(keys, u):
    """Evaluate cyclic piecewise non-linear keyframe table [(u_i, ease_to_next, val_i), ...] for u in [0, 1]."""
    u = u % 1.0
    n = len(keys)
    for i in range(n):
        u0, ease_kind, v0 = keys[i]
        u1, _, v1 = keys[(i + 1) % n]
        span = (u1 - u0) if (i + 1 < n) else (1.0 - u0 + u1)
        rel = (u - u0) % 1.0
        if rel <= span + 1e-7:
            t = apply_ease(rel / max(1e-6, span), ease_kind)
            return lerp_nested(v0, v1, t)
    return keys[0][2]


def point_to_segment_dist(p, a, b):
    ab = v_sub(b, a)
    l2 = v_dot(ab, ab)
    if l2 < 1e-8:
        return v_len(v_sub(p, a))
    t = max(0.0, min(1.0, v_dot(v_sub(p, a), ab) / l2))
    proj = v_add(a, v_scale(ab, t))
    return v_len(v_sub(p, proj))


class RigSession:
    """Anatomically calibrated FK + Hinge-Plane 2-Bone IK + Twist-Bone solver on SK_Smith_Body."""

    def __init__(self, body_mesh):
        self.body = body_mesh
        self.skeleton = body_mesh.skeleton
        self.opts = ue.AnimPoseEvaluationOptions()
        self.opts.optional_skeletal_mesh = body_mesh
        self.opts.evaluation_type = ue.AnimDataEvalType.RAW
        self.opts.should_retarget = False

        idle_clip = ue.load_asset(BASE_IDLE)
        bench_clip = ue.load_asset(BASE_BENCH)
        if not idle_clip or not bench_clip:
            raise RuntimeError(f"Cannot load base clips: {BASE_IDLE}, {BASE_BENCH}")
        self.idle_clip = idle_clip
        self.bench_clip = bench_clip

        pose = ue.AnimPoseExtensions.get_anim_pose_at_time(idle_clip, 0.0, self.opts)
        self.bone_names = [str(n) for n in ue.AnimPoseExtensions.get_bone_names(pose)]
        self._resolve_parents(pose)
        self.idle_local, self.idle_world = self.sample_clip_frame(idle_clip, 0.0)
        self.bench_local, self.bench_world = self.sample_clip_frame(bench_clip, 0.0)

        # Measure exact lateral handedness from SK_Smith_Body! (Verified: upperarm_l.X > 0, upperarm_r.X < 0 -> right_sign = -1!)
        sh_l_x = self.idle_world["upperarm_l"][0][0]
        sh_r_x = self.idle_world["upperarm_r"][0][0]
        self.right_sign = -1.0 if (sh_r_x < sh_l_x) else 1.0
        ue.log(f"[RIG-CAL] SK_Smith_Body handedness: upperarm_l.X={sh_l_x:.2f}, upperarm_r.X={sh_r_x:.2f} => right_sign={self.right_sign:+.0f} (+Y=FWD, +Z=UP)")

        # Mathematically assert all 3 world-turn conventions before authoring a single frame!
        v_fwd_test = q_rot(q_axis_angle((1.0, 0.0, 0.0), -10.0), (0.0, 0.0, 1.0))
        assert v_fwd_test[1] > 0.15, f"Forward lean axis mismatch: {v_fwd_test}"
        v_rlean_test = q_rot(q_axis_angle((0.0, 1.0, 0.0), 10.0 * self.right_sign), (0.0, 0.0, 1.0))
        assert v_rlean_test[0] * self.right_sign > 0.15, f"Right lean axis mismatch: {v_rlean_test}"
        v_ryaw_test = q_rot(q_axis_angle((0.0, 0.0, 1.0), -10.0 * self.right_sign), (0.0, 1.0, 0.0))
        assert v_ryaw_test[0] * self.right_sign > 0.15, f"Right yaw axis mismatch: {v_ryaw_test}"

        self._calibrate_limbs()

    def pt(self, right_cm, fwd_cm, up_cm):
        """Semantic body-space point: +right_cm is worker's RIGHT, +fwd_cm is FORWARD (+Y), +up_cm is UP (+Z)."""
        return (right_cm * self.right_sign, fwd_cm, up_cm)

    def vec(self, right, fwd, up):
        return v_norm((right * self.right_sign, fwd, up))

    def _resolve_parents(self, pose):
        locals_map = {b: tf_from_ue(ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.LOCAL)) for b in self.bone_names}
        worlds_map = {b: tf_from_ue(ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD)) for b in self.bone_names}
        known_parents = {
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
                    known_parents[meta] = f"hand_{side}"
                    known_parents[j1] = meta
                else:
                    known_parents[j1] = f"hand_{side}"
                known_parents[j2] = j1
                known_parents[j3] = j2
            for tw in ("upperarm_twist_01", "upperarm_twist_02", "lowerarm_twist_01", "lowerarm_twist_02"):
                base = "upperarm" if "upperarm" in tw else "lowerarm"
                known_parents[f"{tw}_{side}"] = f"{base}_{side}"
            for tw in ("thigh_twist_01", "thigh_twist_02", "calf_twist_01", "calf_twist_02"):
                base = "thigh" if "thigh" in tw else "calf"
                known_parents[f"{tw}_{side}"] = f"{base}_{side}"

        self.parent = {}
        for b in self.bone_names:
            cand = known_parents.get(b)
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

    def _calibrate_chain_frame(self, world_pose, b_u, b_l, b_e):
        """Measure exact orthonormal anatomical flexion frame (dir, inner_bend, hinge) in local space of b_u and b_l."""
        p_u, r_u, _ = world_pose[b_u]
        p_l, r_l, _ = world_pose[b_l]
        p_e, _, _ = world_pose[b_e]
        v_u = v_sub(p_l, p_u)
        v_l = v_sub(p_e, p_l)
        l1, l2 = v_len(v_u), v_len(v_l)
        u_dir_w = v_norm(v_u)
        l_dir_w = v_norm(v_l)
        h_raw = v_cross(u_dir_w, l_dir_w)
        assert v_len(h_raw) > 0.15, f"Calibration chain {b_u}->{b_l}->{b_e} too straight (sin={v_len(h_raw):.3f})"
        hinge_w = v_norm(h_raw)
        # Inner flexion side in plane of triangle (points toward inner elbow / back of knee)
        u_in_w = v_norm(v_cross(hinge_w, u_dir_w))
        l_in_w = v_norm(v_cross(hinge_w, l_dir_w))

        # Local orthonormal basis frames Q_local so Q_world * inv(Q_local) yields exact bone world rotation!
        u_ldir = v_norm(q_rot(q_inv(r_u), u_dir_w))
        u_lin = v_norm(q_rot(q_inv(r_u), u_in_w))
        u_lh = v_norm(q_rot(q_inv(r_u), hinge_w))
        l_ldir = v_norm(q_rot(q_inv(r_l), l_dir_w))
        l_lin = v_norm(q_rot(q_inv(r_l), l_in_w))
        l_lh = v_norm(q_rot(q_inv(r_l), hinge_w))

        q_local_u = q_from_basis(u_ldir, u_lin, u_lh)
        q_local_l = q_from_basis(l_ldir, l_lin, l_lh)
        # Verify exact round-trip reconstruction on calibration pose!
        q_w_u_check = q_norm(q_mul(q_from_basis(u_dir_w, u_in_w, hinge_w), q_inv(q_local_u)))
        err_u = q_angle_deg(q_mul(q_inv(r_u), q_w_u_check))
        assert err_u < 0.5, f"Frame round-trip error on {b_u}: {err_u:.2f} deg"

        return dict(
            l1=l1, l2=l2,
            u_ldir=u_ldir, l_ldir=l_ldir,
            q_local_u=q_local_u, q_local_l=q_local_l,
        )

    def _calibrate_limbs(self):
        self.arm_info = {}
        self.leg_info = {}
        for side in ("l", "r"):
            ua, la, hd = f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"
            # J_MM_Idle has clean 24..28 deg anatomical elbow flexion!
            chain = self._calibrate_chain_frame(self.idle_world, ua, la, hd)

            # Calibrate exact palm frame at wrist (X=fingers, Z=palm_outward_normal, Y=Z x X)
            p_hd, r_hd, _ = self.idle_world[hd]
            idx_b, mid_b, pnk_b = f"index_01_{side}", f"middle_01_{side}", f"pinky_01_{side}"
            v_idx = v_sub(self.idle_world[idx_b][0], p_hd)
            v_pnk = v_sub(self.idle_world[pnk_b][0], p_hd)
            fingers = v_norm(v_sub(self.idle_world[mid_b][0], p_hd))
            # Verify palm normal points INWARD toward body centerline in J_MM_Idle (relaxed arms at sides)!
            palm = v_norm(v_cross(v_idx, v_pnk))
            to_center_x = -self.idle_world[hd][0][0]
            if palm[0] * to_center_x < 0.0:
                palm = v_scale(palm, -1.0)
            ey = v_norm(v_cross(palm, fingers))
            ez = v_norm(v_cross(fingers, ey))
            q_palm_world = q_from_basis(fingers, ey, ez)
            palm_to_wrist = q_norm(q_mul(q_inv(q_palm_world), r_hd))
            ue.log(f"[RIG-CAL] hand_{side} palm_rest=({palm[0]:+.2f},{palm[1]:+.2f},{palm[2]:+.2f}) fingers=({fingers[0]:+.2f},{fingers[1]:+.2f},{fingers[2]:+.2f})")

            # Store rest twist bone rotations relative to parent so twist distribution preserves exact bind alignment
            self.arm_info[side] = dict(
                ua=ua, la=la, hd=hd,
                palm_to_wrist=palm_to_wrist,
                idle_hd_local_r=self.idle_local[hd][1],
                idle_ua_local_r=self.idle_local[ua][1],
                **chain,
            )

            # A_Rest_Bench_Idle has clean 92 deg anatomical knee flexion!
            th, cf, ft = f"thigh_{side}", f"calf_{side}", f"foot_{side}"
            leg_chain = self._calibrate_chain_frame(self.bench_world, th, cf, ft)
            self.leg_info[side] = dict(th=th, cf=cf, ft=ft, **leg_chain)

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
        """Positive deg_fwd leans upper part FORWARD toward +Y."""
        self.apply_world_turn(local_map, bone, (1.0, 0.0, 0.0), -deg_fwd, world_cache)

    def turn_lean_right(self, local_map, bone, deg_right, world_cache=None):
        """Positive deg_right tilts upper part toward worker's RIGHT (-X)."""
        self.apply_world_turn(local_map, bone, (0.0, 1.0, 0.0), deg_right * self.right_sign, world_cache)

    def turn_yaw_right(self, local_map, bone, deg_right, world_cache=None):
        """Positive deg_right twists chest to face worker's RIGHT (-X)."""
        self.apply_world_turn(local_map, bone, (0.0, 0.0, 1.0), -deg_right * self.right_sign, world_cache)

    def drive_clavicle(self, local_map, side, target_hand_w):
        """Gentle anatomical shoulder-girdle follow-through (capped <= 8 deg so MetaHuman workwear collars/armpits NEVER tear)."""
        clav = f"clavicle_{side}"
        if clav not in local_map:
            return
        w = self.compute_fk(local_map)
        sh = w[f"upperarm_{side}"][0]
        # Subtle elevation only when hand rises above shoulder height (max 8 deg -> lets ABP_Smith_R4_Correctives stay pristine!)
        elev = max(0.0, min(8.0, (target_hand_w[2] - sh[2] + 4.0) * 0.22))
        # Subtle protraction when reaching far forward (max 7 deg)
        prot = max(-4.0, min(7.0, (target_hand_w[1] - sh[1] - 20.0) * 0.16))
        side_sgn = 1.0 if side == "r" else -1.0
        self.turn_lean_right(local_map, clav, -side_sgn * elev)
        self.turn_yaw_right(local_map, clav, -side_sgn * prot)

    def wrist_from_grip(self, grip_w, grip_fingers_dir_w, grip_palm_dir_w, palm_forward_cm=6.5, palm_inward_cm=3.0):
        """Convert exact closed-fist handle center `grip_w` into exact `hand_l/r` wrist joint position!
        Eliminates 100% of wrist/palm/blade clipping because the wooden shaft sits inside the curled fingers, NOT through the wrist bone!
        """
        fx = v_norm(grip_fingers_dir_w)
        pz = v_sub(grip_palm_dir_w, v_scale(fx, v_dot(grip_palm_dir_w, fx)))
        pz = v_norm(pz if v_len(pz) > 1e-4 else (0.0, 0.0, -1.0))
        return v_sub(v_sub(grip_w, v_scale(fx, palm_forward_cm)), v_scale(pz, palm_inward_cm))

    def solve_arm_grip_ik(self, local_map, side, grip_w, pole_w, haft_dir_w, fallback_fingers_w, palm_hint_w,
                          palm_forward_cm=6.5, palm_inward_cm=3.0, forearm_align_blend=0.88, drive_clav=True):
        """R59 Pronated-Forearm Anatomical Power-Grip Solver:
        Chooses the unique palm normal around the cylindrical handle (`haft_dir_w`) that is SIMULTANEOUSLY
        orthogonal to `haft_dir_w` AND orthogonal to the real forearm vector `dl` (`palm ~ ±(dl x haft)`).
        Result: natural pronated woodcutter power-grip with wrist_bend <= 18 deg (ZERO 55 deg wrist hook!),
        natural forearm pronation, and exact 0.0 cm alignment of the closed-fist cavity onto `grip_w`!
        """
        info = self.arm_info[side]
        ua = info["ua"]
        l1, l2 = info["l1"], info["l2"]
        haft_u = v_norm(haft_dir_w)
        hint_o = v_sub(palm_hint_w, v_scale(haft_u, v_dot(palm_hint_w, haft_u)))
        hint_o = v_norm(hint_o if v_len(hint_o) > 1e-4 else (0.0, 0.0, -1.0))

        def proj_ortho(vec_w, normal_w):
            pr = v_sub(vec_w, v_scale(normal_w, v_dot(vec_w, normal_w)))
            if v_len(pr) > 0.15:
                return v_norm(pr)
            fb = v_sub(fallback_fingers_w, v_scale(normal_w, v_dot(fallback_fingers_w, normal_w)))
            return v_norm(fb if v_len(fb) > 1e-4 else (0.0, 1.0, 0.0))

        pz = hint_o
        fx = proj_ortho(fallback_fingers_w, pz)
        world0 = self.compute_fk(local_map)
        p_ua = world0[ua][0]
        for _ in range(3):
            hr_est = self.wrist_from_grip(grip_w, fx, pz, palm_forward_cm, palm_inward_cm)
            to_tgt = v_sub(hr_est, p_ua)
            dist = max(abs(l1 - l2) + 9.0, min((l1 + l2) * 0.980, v_len(to_tgt)))
            dir_tgt = v_norm(to_tgt)
            eff_tgt = v_add(p_ua, v_scale(dir_tgt, dist))
            cos_a = max(-1.0, min(1.0, (l1*l1 + dist*dist - l2*l2) / (2.0 * l1 * dist)))
            sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
            pv = v_sub(pole_w, p_ua)
            bend = v_sub(pv, v_scale(dir_tgt, v_dot(pv, dir_tgt)))
            bend = v_norm(bend if v_len(bend) > 1e-4 else self.vec(1.0 if side == "r" else -1.0, -0.3, -0.6))
            p_elbow = v_add(p_ua, v_add(v_scale(dir_tgt, l1 * cos_a), v_scale(bend, l1 * sin_a)))
            dl_est = v_norm(v_sub(eff_tgt, p_elbow))

            # Ideal zero-bend palm normal is perpendicular to BOTH forearm `dl_est` AND shaft `haft_u`!
            cross_pn = v_cross(dl_est, haft_u)
            clen = v_len(cross_pn)
            if clen > 0.18:
                pn_ideal = v_norm(cross_pn)
                if v_dot(pn_ideal, hint_o) < 0.0:
                    pn_ideal = v_scale(pn_ideal, -1.0)
                w_ideal = min(0.88, clen)
                pz_raw = v_add(v_scale(pn_ideal, w_ideal), v_scale(hint_o, 1.0 - w_ideal))
                pz = v_norm(v_sub(pz_raw, v_scale(haft_u, v_dot(pz_raw, haft_u))))
            else:
                pz = hint_o

            dl_p = proj_ortho(dl_est, pz)
            fb_p = proj_ortho(fallback_fingers_w, pz)
            fx = proj_ortho(v_add(v_scale(dl_p, forearm_align_blend), v_scale(fb_p, 1.0 - forearm_align_blend)), pz)

        hr_w = self.wrist_from_grip(grip_w, fx, pz, palm_forward_cm, palm_inward_cm)
        return self.solve_arm_ik(local_map, side, hr_w, pole_w, fx, pz, drive_clav=drive_clav)

    def measure_fist_cavity(self, world, side):
        """Exact runtime-matched closed-fist cavity center (identical to ALumberMillWorker::ComputePalmGripCenter!)."""
        hd = world[f"hand_{side}"][0]
        m1 = world[f"middle_01_{side}"][0]
        m2 = world[f"middle_02_{side}"][0]
        m3 = world[f"middle_03_{side}"][0]
        i1 = world[f"index_01_{side}"][0]
        p1 = world[f"pinky_01_{side}"][0]
        t2 = world[f"thumb_02_{side}"][0]
        fingers = v_norm(v_sub(m1, hd))
        vi = v_sub(i1, hd)
        vp = v_sub(p1, hd)
        raw_n = v_cross(vp, vi) if side == "r" else v_cross(vi, vp)
        palm_in = v_norm(v_sub(raw_n, v_scale(fingers, v_dot(raw_n, fingers))))
        analytic = v_add(v_add(hd, v_scale(fingers, 6.5)), v_scale(palm_in, 3.0))
        palm_pad = v_add(v_scale(m1, 0.55), v_scale(hd, 0.45))
        ring_c = v_add(v_add(v_scale(palm_pad, 0.30), v_scale(m2, 0.25)), v_add(v_scale(m3, 0.25), v_scale(t2, 0.20)))
        return v_lerp(analytic, ring_c, 0.50)

    def solve_arm_ik(self, local_map, side, target_hand_w, pole_w, grip_fingers_dir_w, grip_palm_dir_w, drive_clav=True):
        """Exact anatomical hinge-plane 2-bone arm IK + clamped wrist.
        CRITICAL (R58): Preserve native MetaHuman twist & corrective bone rest transforms so
        SK_Smith_Body's native ABP_Smith_R4_Correctives PostProcess RBF solver drives armpits,
        deltoids & forearm twist cleanly with ZERO sleeve tearing/streaking!
        """
        if drive_clav:
            self.drive_clavicle(local_map, side, target_hand_w)

        info = self.arm_info[side]
        ua, la, hd = info["ua"], info["la"], info["hd"]
        l1, l2 = info["l1"], info["l2"]

        world = self.compute_fk(local_map)
        p_ua = world[ua][0]
        r_parent_ua = world[self.parent[ua]][1]

        to_tgt = v_sub(target_hand_w, p_ua)
        dist = v_len(to_tgt)
        # Keep slight minimum elbow bend (~10 deg) so arm never snaps straight/hyperextends!
        max_reach = (l1 + l2) * 0.985
        min_reach = abs(l1 - l2) + 9.0
        clamped_dist = max(min_reach, min(max_reach, dist))
        dir_tgt = v_norm(to_tgt)
        eff_tgt = v_add(p_ua, v_scale(dir_tgt, clamped_dist))

        cos_a = max(-1.0, min(1.0, (l1*l1 + clamped_dist*clamped_dist - l2*l2) / (2.0 * l1 * clamped_dist)))
        sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
        pole_v = v_sub(pole_w, p_ua)
        bend_dir = v_sub(pole_v, v_scale(dir_tgt, v_dot(pole_v, dir_tgt)))
        if v_len(bend_dir) < 1e-4:
            bend_dir = self.vec(1.0 if side == "r" else -1.0, -0.3, -0.6)
        bend_dir = v_norm(bend_dir)
        p_elbow = v_add(p_ua, v_add(v_scale(dir_tgt, l1 * cos_a), v_scale(bend_dir, l1 * sin_a)))

        # Build exact anatomical hinge-plane world frames for upperarm & lowerarm!
        d_u = v_norm(v_sub(p_elbow, p_ua))
        d_l = v_norm(v_sub(eff_tgt, p_elbow))
        elbow_flex_deg = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(d_u, d_l)))))
        # Measure upper-arm elevation relative to torso down axis (-Z_spine) to enforce zero armpit tear!
        spine_up = v_norm(v_sub(world["spine_05"][0], world["spine_01"][0]))
        arm_elev_deg = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(d_u, v_scale(spine_up, -1.0))))))

        h_raw = v_cross(d_u, d_l)
        h_w = v_norm(h_raw) if v_len(h_raw) > 1e-4 else v_norm(v_cross(d_u, v_scale(bend_dir, -1.0)))
        in_u = v_norm(v_cross(h_w, d_u))
        in_l = v_norm(v_cross(h_w, d_l))

        new_ua_wrot = q_norm(q_mul(q_from_basis(d_u, in_u, h_w), q_inv(info["q_local_u"])))
        new_la_wrot = q_norm(q_mul(q_from_basis(d_l, in_l, h_w), q_inv(info["q_local_l"])))

        lp_ua, _, ls_ua = local_map[ua]
        new_ua_local = q_norm(q_mul(q_inv(r_parent_ua), new_ua_wrot))
        local_map[ua] = (lp_ua, new_ua_local, ls_ua)

        lp_la, _, ls_la = local_map[la]
        new_la_local = q_norm(q_mul(q_inv(new_ua_wrot), new_la_wrot))
        local_map[la] = (lp_la, new_la_local, ls_la)

        # Orient hand cleanly from desired fingers & palm normal, then clamp anatomical wrist range!
        fx = v_norm(grip_fingers_dir_w)
        pz = v_sub(grip_palm_dir_w, v_scale(fx, v_dot(grip_palm_dir_w, fx)))
        if v_len(pz) < 1e-4:
            pz = (0.0, 0.0, -1.0)
        pz = v_norm(pz)
        ey = v_norm(v_cross(pz, fx))
        ez = v_norm(v_cross(fx, ey))
        q_palm = q_from_basis(fx, ey, ez)
        des_hd_wrot = q_norm(q_mul(q_palm, info["palm_to_wrist"]))
        raw_hd_local = q_norm(q_mul(q_inv(new_la_wrot), des_hd_wrot))

        # Swing-twist decomposition in lowerarm space around forearm longitudinal axis (info["l_ldir"])
        q_wrist_delta = q_norm(q_mul(raw_hd_local, q_inv(info["idle_hd_local_r"])))
        q_sw, _, tw_deg = q_swing_twist(q_wrist_delta, info["l_ldir"])
        clamped_tw_deg = max(-74.0, min(74.0, tw_deg))
        q_tw_clamped = q_axis_angle(info["l_ldir"], clamped_tw_deg)
        q_sw_clamped, sw_deg = q_clamp_angle(q_sw, 46.0)
        final_hd_local = q_norm(q_mul(q_mul(q_sw_clamped, q_tw_clamped), info["idle_hd_local_r"]))
        lp_hd, _, ls_hd = local_map[hd]
        local_map[hd] = (lp_hd, final_hd_local, ls_hd)

        # Keep MetaHuman twist/corrective bones at exact idle bind pose so ABP_Smith_R4_Correctives
        # solves armpits, upperarm_twist_01/02, and lowerarm_twist_01/02 cleanly without double-rotation!
        world = self.compute_fk(local_map)
        ik_err = v_len(v_sub(world[hd][0], eff_tgt))
        return dict(ik_err=ik_err, elbow_flex=elbow_flex_deg, arm_elev=arm_elev_deg, wrist_twist=abs(clamped_tw_deg), wrist_swing=sw_deg)

    def curl_fingers(self, local_map, side, curl_strength=1.0):
        if curl_strength <= 0.01:
            return
        world = self.compute_fk(local_map)
        hd = f"hand_{side}"
        if hd not in world:
            return
        info = self.arm_info[side]
        q_palm = q_norm(q_mul(world[hd][1], q_inv(info["palm_to_wrist"])))
        palm_n = q_rot(q_palm, (0.0, 0.0, 1.0))
        finger_fwd = q_rot(q_palm, (1.0, 0.0, 0.0))
        # Verify curl moves fingertip toward palm_n: (finger_fwd x flex_axis) should align with +palm_n -> flex_axis = palm_n x finger_fwd!
        #Wait: rotating `finger_fwd` by +deg around `axis` moves it in direction `(axis x finger_fwd)`.
        # So we want `axis x finger_fwd = +palm_n` => `axis = finger_fwd x palm_n`? Check: (f x p) x f = p*(f.f) - f*(p.f) = +p!! YES!
        flex_axis_w = v_norm(v_cross(finger_fwd, palm_n))
        for digit, degs in (
            ("index",  (62.0, 74.0, 48.0)),
            ("middle", (66.0, 78.0, 52.0)),
            ("ring",   (66.0, 76.0, 50.0)),
            ("pinky",  (62.0, 72.0, 46.0)),
        ):
            for ji, deg in enumerate(degs, start=1):
                bn = f"{digit}_0{ji}_{side}"
                if bn in local_map:
                    world = self.compute_fk(local_map)
                    self.apply_world_turn(local_map, bn, flex_axis_w, deg * curl_strength, world_cache=world)
        # Thumb wraps anatomically OVER index/middle knuckles closing the fist 360 deg around the handle!
        world = self.compute_fk(local_map)
        t1_b, t2_b, m2_b = f"thumb_01_{side}", f"thumb_02_{side}", f"middle_02_{side}"
        if t1_b in world and t2_b in world and m2_b in world:
            p_t1, p_t2, p_m2 = world[t1_b][0], world[t2_b][0], world[m2_b][0]
            t_dir = v_norm(v_sub(p_t2, p_t1))
            # Aim thumb tip cleanly over the outer-front knuckle of middle_02 so thumb locks around handle
            aim_pt = v_add(p_m2, v_scale(palm_n, -1.2))
            to_aim = v_norm(v_sub(aim_pt, p_t1))
            t_axis = v_cross(t_dir, to_aim)
            if v_len(t_axis) > 1e-3:
                t_axis = v_norm(t_axis)
                for ji, deg in enumerate((26.0, 34.0, 28.0), start=1):
                    bn = f"thumb_0{ji}_{side}"
                    if bn in local_map:
                        world = self.compute_fk(local_map)
                        self.apply_world_turn(local_map, bn, t_axis, deg * curl_strength, world_cache=world)

    def solve_leg_grounded(self, local_map, side, foot_target_w, knee_pole_w, toe_out_deg=12.0):
        """Anatomical hinge-plane 2-bone leg IK keeping feet flat on ground with ZERO knee twist."""
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
        knee_flex_deg = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(d_u, d_l)))))
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

        # Keep foot flat on ground using bench_world foot (pure straight-forward flat foot!) + natural toe-out!
        side_sgn = 1.0 if side == "r" else -1.0
        foot_w = q_norm(q_mul(q_axis_angle((0.0, 0.0, 1.0), -side_sgn * toe_out_deg * self.right_sign), self.bench_world[ft][1]))
        lp_ft, _, ls_ft = local_map[ft]
        local_map[ft] = (lp_ft, q_norm(q_mul(q_inv(new_cf_w), foot_w)), ls_ft)
        return knee_flex_deg

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
        save_asset(clip)
        return clip


# ==============================================================================
# PART C: AUTHOR ALL 5 ERGONOMIC 3P LUMBERJACK ANIMATIONS (SEMANTIC RIGHT/FWD/UP)
# ==============================================================================
def _apply_torso(rig: RigSession, loc, pelvis_drop, shift_right, shift_fwd, yaw_right, lean_fwd, lean_right):
    pp, pr, ps = loc["pelvis"]
    shift_w = rig.pt(shift_right, shift_fwd, -pelvis_drop)
    loc["pelvis"] = ((pp[0] + shift_w[0], pp[1] + shift_w[1], pp[2] + shift_w[2]), pr, ps)
    rig.turn_yaw_right(loc, "pelvis", yaw_right * 0.30)
    rig.turn_pitch_fwd(loc, "pelvis", lean_fwd * 0.25)

    for sp, w_y, w_f, w_s in (
        ("spine_01", 0.14, 0.18, 0.16),
        ("spine_02", 0.18, 0.20, 0.20),
        ("spine_03", 0.20, 0.20, 0.22),
        ("spine_04", 0.18, 0.16, 0.22),
        ("spine_05", 0.12, 0.10, 0.20),
    ):
        if sp in loc:
            rig.turn_yaw_right(loc, sp, yaw_right * w_y)
            rig.turn_pitch_fwd(loc, sp, lean_fwd * w_f)
            rig.turn_lean_right(loc, sp, lean_right * w_s)


def author_chop_tree_loop(rig: RigSession):
    """A_LJ_ChopTree_Loop (45f @ 30fps = 1.50s): snappy two-handed diagonal tree-felling swing!
    R59 Upgrade: forearm-aligned neutral power-grip (wrist_bend <= 25 deg), explosive strike_heavy whip,
    athletic elbow flexion (55..125 deg), upperarm elevation <= 90 deg, and closed-fist shaft audit.
    Impact at u = 0.44.
    """
    fps, n = 30, 45
    foot_l_tgt = rig.pt(-22.0,  16.0, 8.6)
    foot_r_tgt = rig.pt( 24.0, -14.0, 8.6)
    knee_l_pole = rig.pt(-28.0, 44.0, 48.0)
    knee_r_pole = rig.pt( 28.0, 18.0, 48.0)

    keys = [
        # 0.00: Balanced woodcutter ready guard facing standing trunk
        (0.00, "windup",       ( 5.0,  2.0,  2.0,  14.0, 10.0,  2.0, ( 20.0, 48.0, 114.0), (  2.0, 46.0, 102.0))),
        # 0.28: Deep coiled right-shoulder wind-up
        (0.28, "smooth",       ( 7.5,  8.0, -2.0,  36.0,  6.0,  8.0, ( 36.0, 24.0, 134.0), ( 18.0, 36.0, 120.0))),
        # 0.34: Brief loaded apex poise before explosive whip
        (0.34, "strike_heavy", ( 8.0,  8.0, -1.5,  37.0,  6.5,  8.0, ( 35.0, 26.0, 134.0), ( 17.0, 37.0, 120.0))),
        # 0.44: IMPACT! Crisp extended diagonal cleave biting into standing tree trunk directly ahead!
        (0.44, "recoil",       (11.0, -4.0,  8.0, -18.0, 18.5, -6.0, (  2.0, 62.0, 108.0), (-14.0, 50.0,  99.0))),
        # 0.54: Bite-in recoil hold (wood shock absorption)
        (0.54, "smooth",       (10.0, -3.0,  7.0, -16.0, 17.0, -4.5, (  4.0, 60.0, 107.5), (-12.0, 49.0,  98.5))),
        # 0.76: Wrench blade free from kerf back to ready
        (0.76, "smooth",       ( 6.5,  0.5,  3.5,   4.0, 12.0,  0.0, ( 15.0, 52.0, 112.0), ( -2.0, 48.0, 101.0))),
    ]

    frames = []
    stats = dict(max_ik_err=0.0, min_elbow=180.0, max_elbow=0.0, max_arm_elev=0.0, max_wrist_tw=0.0, max_wrist_sw=0.0, max_wrist_bend=0.0, max_grip_err=0.0)
    for fi in range(n):
        u = fi / n
        drop, sr, sf, yr, lf, lr, gr_s, gl_s = eval_keyed_curve(keys, u)
        loc = dict(rig.idle_local)
        _apply_torso(rig, loc, drop, sr, sf, yr, lf, lr)

        rig.turn_yaw_right(loc, "neck_01", -yr * 0.42)
        rig.turn_yaw_right(loc, "head", -yr * 0.42)
        rig.turn_pitch_fwd(loc, "head", -lf * 0.45)

        rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=14.0)
        rig.solve_leg_grounded(loc, "r", foot_r_tgt, knee_r_pole, toe_out_deg=18.0)

        gr_w = rig.pt(*gr_s)
        gl_w = rig.pt(*gl_s)
        haft_w = v_norm(v_sub(gr_w, gl_w))
        blade_fwd = v_norm(v_sub((0.0, 1.0, 0.0), v_scale(haft_w, v_dot((0.0, 1.0, 0.0), haft_w))))
        palm_hint_r = rig.vec(-0.55, 0.0, -0.83)
        palm_hint_l = rig.vec( 0.55, 0.0, -0.83)
        pole_r = rig.pt(max(28.0, gr_s[0] + 24.0), gr_s[1] - 20.0, gr_s[2] - 22.0)
        pole_l = rig.pt(min(-22.0, gl_s[0] - 24.0), gl_s[1] - 18.0, gl_s[2] - 24.0)

        sr_m = rig.solve_arm_grip_ik(loc, "r", gr_w, pole_r, haft_w, blade_fwd, palm_hint_r)
        sl_m = rig.solve_arm_grip_ik(loc, "l", gl_w, pole_l, haft_w, blade_fwd, palm_hint_l)
        for m in (sr_m, sl_m):
            stats["max_ik_err"] = max(stats["max_ik_err"], m["ik_err"])
            stats["min_elbow"] = min(stats["min_elbow"], m["elbow_flex"])
            stats["max_elbow"] = max(stats["max_elbow"], m["elbow_flex"])
            stats["max_arm_elev"] = max(stats["max_arm_elev"], m["arm_elev"])
            stats["max_wrist_tw"] = max(stats["max_wrist_tw"], m["wrist_twist"])
            stats["max_wrist_sw"] = max(stats["max_wrist_sw"], m["wrist_swing"])

        rig.curl_fingers(loc, "r", 0.96)
        rig.curl_fingers(loc, "l", 0.96)

        fw = rig.compute_fk(loc)
        for side, tgt_g in (("r", gr_w), ("l", gl_w)):
            dl = v_norm(v_sub(fw[f"hand_{side}"][0], fw[f"lowerarm_{side}"][0]))
            df = v_norm(v_sub(fw[f"middle_01_{side}"][0], fw[f"hand_{side}"][0]))
            wb = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(dl, df)))))
            stats["max_wrist_bend"] = max(stats["max_wrist_bend"], wb)
            stats["max_grip_err"] = max(stats["max_grip_err"], v_len(v_sub(rig.measure_fist_cavity(fw, side), tgt_g)))
        frames.append(loc)

    clip = rig.bake_sequence("A_LJ_ChopTree_Loop", fps, n, frames, "R59 ergonomic tree felling chop loop (neutral wrist power-grip, snappy strike_heavy)")
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 2) for k, v in stats.items()})


def author_split_log_loop(rig: RigSession):
    """A_LJ_SplitLog_Loop (40f @ 30fps = 1.333s): snappy, powerful firewood-splitting cleave onto chopping stump!
    R59 Upgrade:
      - 30% faster cycle (1.33s @ 1.0x vs old 1.91s) with brief loaded apex poise (0.30..0.35) and
        one continuous 5-frame (0.167s) explosive `strike_heavy` (t^2.8) power cleave into exact impact frame 19 (u = 0.475)!
      - Pronated forearm-aligned power-grip (`solve_arm_grip_ik`) eliminates the 55 deg downward wrist hook
        (`wrist_bend <= 30 deg`), keeps BOTH elbows athletically flexed (55..128 deg, never stiff/straight),
        and locks the wooden axe shaft 0.0 cm dead-center inside BOTH tightly curled fists!
      - Downward impact shaft angle (-14..-16 deg, NOT +10 deg upward!) drives SM_BattleAxe cutting edge
        DEAD-CENTER into the upright oak billet (Z ~ 81..88 cm, lateral <= 2.5 cm, exact solved Fwd standoff)!
    """
    fps, n = 30, 40
    foot_l_tgt = rig.pt(-21.0,  10.0, 8.6)
    foot_r_tgt = rig.pt( 23.0,  -8.0, 8.6)
    knee_l_pole = rig.pt(-24.0, 40.0, 48.0)
    knee_r_pole = rig.pt( 26.0, 26.0, 48.0)

    # (u, ease, (drop, shift_f, lean_fwd, yaw_r, lean_r, gripR(R,F,U), gripL(R,F,U)))
    # Impact lands on EXACT integer frame fi=19 (u=19/40=0.475) after one continuous explosive downswing!
    keys = [
        # 0.000 (f=0): Balanced ready stance holding axe angled toward stump billet
        (0.000, "windup",       ( 5.5,  1.0, 12.0,   8.0,  2.0, (  4.5, 52.0, 108.0), ( -2.0, 38.0,  96.0))),
        # 0.150 (f=6): Brisk lift-up gather across right chest
        (0.150, "windup",       ( 4.0, -1.5,  2.0,  18.0,  4.0, ( 14.0, 42.0, 134.0), (  5.0, 40.0, 114.0))),
        # 0.300 (f=12): Athletic right-shoulder high wind-up (upperarms <= 90 deg; axe head arcs to Z~198 cm!)
        (0.300, "smooth",       ( 3.0, -4.0, -8.0,  24.0,  5.5, ( 19.0, 29.0, 148.0), (  9.0, 41.0, 127.0))),
        # 0.350 (f=14): Brief loaded apex poise (0.07s anticipation coil before single explosive 5-frame whip!)
        (0.350, "strike_heavy", ( 3.8, -3.5, -6.5,  25.0,  5.5, ( 18.5, 31.0, 149.0), (  8.5, 42.0, 128.0))),
        # 0.475 (f=19): IMPACT! Crisp downward (-15 deg) cleave splitting upright oak billet dead-center (X~0, Z~83cm)!
        (0.475, "recoil",       (14.5,  4.5, 22.0,  -4.0, -1.5, ( -0.7, 64.0, 106.0), ( -1.0, 46.0, 111.0))),
        # 0.575 (f=23): Heavy impact stop / wood-bite recoil cushion as split halves burst apart
        (0.575, "smooth",       (13.5,  4.0, 20.0,  -3.5, -1.0, ( -0.5, 63.0, 107.0), ( -1.2, 45.0, 112.0))),
        # 0.775 (f=31): Brisk athletic recovery back to ready as fresh billet seats on stump (u=0.84)
        (0.775, "smooth",       ( 7.5,  2.5, 15.0,   4.0,  1.0, (  3.5, 53.0, 106.0), ( -1.5, 39.0,  99.0))),
    ]

    frames = []
    stats = dict(
        max_ik_err=0.0, min_elbow=180.0, max_elbow=0.0, max_arm_elev=0.0,
        max_wrist_tw=0.0, max_wrist_sw=0.0, max_wrist_bend=0.0, max_grip_err=0.0,
        impact_haft_pitch=0.0, impact_blade_x=0.0, impact_blade_fwd=0.0, impact_blade_z=0.0,
    )
    impact_fi = 19  # exact u = 19/40 = 0.475!
    for fi in range(n):
        u = fi / n
        drop, sf, lf, yr, lr, gr_s, gl_s = eval_keyed_curve(keys, u)
        loc = dict(rig.idle_local)
        _apply_torso(rig, loc, drop, 0.0, sf, yr, lf, lr)

        # Eyes stay locked on the upright billet across wind-up and cleave
        rig.turn_yaw_right(loc, "neck_01", -yr * 0.40)
        rig.turn_yaw_right(loc, "head", -yr * 0.45)
        rig.turn_pitch_fwd(loc, "neck_01", 8.0 - lf * 0.20)
        rig.turn_pitch_fwd(loc, "head", 10.0 - lf * 0.25)

        rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=12.0)
        rig.solve_leg_grounded(loc, "r", foot_r_tgt, knee_r_pole, toe_out_deg=16.0)

        gr_w = rig.pt(*gr_s)
        gl_w = rig.pt(*gl_s)
        haft_w = v_norm(v_sub(gr_w, gl_w))
        # Cutting blade aims straight down-forward in the vertical cleave plane (exact match to LumberMillWorkerActor.cpp!)
        cleave_aim = v_norm((0.0, 0.35, -0.94))
        blade_fwd = v_sub(cleave_aim, v_scale(haft_w, v_dot(cleave_aim, haft_w)))
        if v_len(blade_fwd) < 1e-3:
            blade_fwd = v_sub((0.0, 1.0, 0.0), v_scale(haft_w, v_dot((0.0, 1.0, 0.0), haft_w)))
        blade_fwd = v_norm(blade_fwd)

        # Natural pronated woodcutter overhand grip hints: Right palm faces down-inward-left, Left palm faces down-inward-right
        palm_hint_r = rig.vec(-0.55, 0.0, -0.83)
        palm_hint_l = rig.vec( 0.55, 0.0, -0.83)

        # Wide outward-downward elbow poles -> natural athletic elbow bend (never straight/locked!)
        pole_r = rig.pt(max(30.0, gr_s[0] + 26.0), gr_s[1] - 14.0, gr_s[2] - 28.0)
        pole_l = rig.pt(min(-26.0, gl_s[0] - 26.0), gl_s[1] - 12.0, gl_s[2] - 28.0)

        sr_m = rig.solve_arm_grip_ik(loc, "r", gr_w, pole_r, haft_w, blade_fwd, palm_hint_r)
        sl_m = rig.solve_arm_grip_ik(loc, "l", gl_w, pole_l, haft_w, blade_fwd, palm_hint_l)
        for m in (sr_m, sl_m):
            stats["max_ik_err"] = max(stats["max_ik_err"], m["ik_err"])
            stats["min_elbow"] = min(stats["min_elbow"], m["elbow_flex"])
            stats["max_elbow"] = max(stats["max_elbow"], m["elbow_flex"])
            stats["max_arm_elev"] = max(stats["max_arm_elev"], m["arm_elev"])
            stats["max_wrist_tw"] = max(stats["max_wrist_tw"], m["wrist_twist"])
            stats["max_wrist_sw"] = max(stats["max_wrist_sw"], m["wrist_swing"])

        rig.curl_fingers(loc, "r", 0.96)
        rig.curl_fingers(loc, "l", 0.96)

        # Live 3D Hand-Axe Grip + Impact Blade-to-Billet Audit (1:1 mirror of LumberMillWorkerActor.cpp!)
        fw = rig.compute_fk(loc)
        fc_r = rig.measure_fist_cavity(fw, "r")
        fc_l = rig.measure_fist_cavity(fw, "l")
        for side, tgt_g, fc in (("r", gr_w, fc_r), ("l", gl_w, fc_l)):
            dl = v_norm(v_sub(fw[f"hand_{side}"][0], fw[f"lowerarm_{side}"][0]))
            df = v_norm(v_sub(fw[f"middle_01_{side}"][0], fw[f"hand_{side}"][0]))
            wb = math.degrees(math.acos(max(-1.0, min(1.0, v_dot(dl, df)))))
            stats["max_wrist_bend"] = max(stats["max_wrist_bend"], wb)
            stats["max_grip_err"] = max(stats["max_grip_err"], v_len(v_sub(fc, tgt_g)))

        if fi == impact_fi:
            h_rt = v_norm(v_sub(fc_r, fc_l))
            b_rt = v_norm(v_sub(cleave_aim, v_scale(h_rt, v_dot(cleave_aim, h_rt))))
            axe_pos = v_add(fc_l, v_scale(h_rt, 28.0))
            # SM_BattleAxe cutting edge midpoint at local (+11.5, 0, +29.5) * 1.06
            edge_mid = v_add(v_add(axe_pos, v_scale(h_rt, 29.5 * 1.06)), v_scale(b_rt, 11.5 * 1.06))
            stats["impact_haft_pitch"] = math.degrees(math.asin(max(-1.0, min(1.0, h_rt[2]))))
            stats["impact_blade_x"] = edge_mid[0] * rig.right_sign
            stats["impact_blade_fwd"] = edge_mid[1]
            stats["impact_blade_z"] = edge_mid[2]

        frames.append(loc)

    # Hard R59 Gates: neutral wrist, downward cleave angle, dead-center billet impact!
    if stats["max_wrist_bend"] > 34.0:
        raise RuntimeError(f"SPLITLOG WRIST HOOK GATE FAILED: max_wrist_bend={stats['max_wrist_bend']:.1f} deg > 34 deg")
    if stats["impact_haft_pitch"] > -6.0:
        raise RuntimeError(f"SPLITLOG CLEAVE ANGLE GATE FAILED: haft_pitch={stats['impact_haft_pitch']:+.1f} deg (must point downward < -6 deg!)")
    if abs(stats["impact_blade_x"]) > 4.0 or not (78.0 <= stats["impact_blade_z"] <= 94.0):
        raise RuntimeError(
            f"SPLITLOG BLADE BULLSEYE GATE FAILED: X={stats['impact_blade_x']:+.1f}cm, Fwd={stats['impact_blade_fwd']:.1f}cm, Z={stats['impact_blade_z']:.1f}cm"
        )

    clip = rig.bake_sequence("A_LJ_SplitLog_Loop", fps, n, frames, "R59 fast powerful firewood splitting loop (neutral wrist grip, dead-center downward cleave)")
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 2) for k, v in stats.items()})


def author_saw_log_loop(rig: RigSession):
    """A_LJ_SawLog_Loop (48f @ 30fps = 1.60s): athletic split-stance rhythmic crosscut sawing!
    R58 Upgrade:
      - Matched 1:1 to real vertical oak handle of SM_LM_TwoManCrosscutSaw (radius 2.4 cm, Z_saw=[14.5..44.5] cm,
        scale 0.90 -> teeth at Z=95 cm kerf height => handle center at Z_body = 123 cm!).
      - BOTH closed-fist centers stack collinearly on the SAME vertical handle axis X=0 (Right upper Z=128.5,
        Left lower Z=117.5 -> +6.4 cm clear above iron clamp, ZERO blade/clamp/wrist clipping!).
      - Natural 28 cm push-pull stroke with smooth hip/shoulder weight transfer & zero armpit distortion!
    """
    fps, n = 30, 48
    foot_l_tgt = rig.pt(-17.0,  22.0, 8.6)
    foot_r_tgt = rig.pt( 21.0, -22.0, 8.6)
    knee_l_pole = rig.pt(-20.0, 48.0, 48.0)
    knee_r_pole = rig.pt( 24.0,  4.0, 48.0)

    frames = []
    stats = dict(max_ik_err=0.0, min_elbow=180.0, max_elbow=0.0, max_arm_elev=0.0, max_wrist_tw=0.0, max_wrist_sw=0.0)
    for fi in range(n):
        phase = math.tau * fi / n
        # Authentic crosscut cadence: purposeful forward bite push, crisp draw stroke back
        stroke = math.sin(phase) + 0.12 * math.sin(2.0 * phase)
        loc = dict(rig.idle_local)

        drop = 7.5 + 2.6 * stroke
        shift_f = 7.0 * stroke
        lean_f = 15.0 + 7.5 * stroke
        yaw_r = 10.0 - 8.5 * stroke
        _apply_torso(rig, loc, drop, 1.5, shift_f, yaw_r, lean_f, 0.0)

        rig.turn_yaw_right(loc, "neck_01", -yaw_r * 0.45)
        rig.turn_yaw_right(loc, "head", -yaw_r * 0.45)
        rig.turn_pitch_fwd(loc, "neck_01", 6.0 - 2.0 * stroke)
        rig.turn_pitch_fwd(loc, "head", 7.0 - 1.5 * stroke)

        rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=10.0)
        rig.solve_leg_grounded(loc, "r", foot_r_tgt, knee_r_pole, toe_out_deg=20.0)

        # Both closed-fist centers stacked directly on the single vertical wooden oak handle (X=0, Y=saw_f)!
        # Height Z = 123 cm keeps curved steel teeth at Z ~ 95 cm dead-center inside SM_LM_SawbuckStation kerf!
        saw_f = 54.0 + 14.0 * stroke
        saw_z = 123.0 - 1.8 * stroke
        gr_w = rig.pt(0.0, saw_f, saw_z + 5.5)  # Upper hand on vertical handle
        gl_w = rig.pt(0.0, saw_f, saw_z - 5.5)  # Lower hand stacked directly below on same handle

        # Fingers wrap forward-inward horizontally around the vertical 4.8 cm oak handle post!
        fx_r = rig.vec(-0.22, 0.97, 0.0)
        pz_r = rig.vec(-0.97, -0.22, 0.0)
        fx_l = rig.vec( 0.22, 0.97, 0.0)
        pz_l = rig.vec( 0.97, -0.22, 0.0)

        hr_w = rig.wrist_from_grip(gr_w, fx_r, pz_r, palm_forward_cm=7.0, palm_inward_cm=3.3)
        hl_w = rig.wrist_from_grip(gl_w, fx_l, pz_l, palm_forward_cm=7.0, palm_inward_cm=3.3)

        pole_r = rig.pt( 28.0, saw_f - 28.0, saw_z - 16.0)
        pole_l = rig.pt(-28.0, saw_f - 28.0, saw_z - 20.0)

        sr_m = rig.solve_arm_ik(loc, "r", hr_w, pole_r, fx_r, pz_r, drive_clav=False)
        sl_m = rig.solve_arm_ik(loc, "l", hl_w, pole_l, fx_l, pz_l, drive_clav=False)
        for m in (sr_m, sl_m):
            stats["max_ik_err"] = max(stats["max_ik_err"], m["ik_err"])
            stats["min_elbow"] = min(stats["min_elbow"], m["elbow_flex"])
            stats["max_elbow"] = max(stats["max_elbow"], m["elbow_flex"])
            stats["max_arm_elev"] = max(stats["max_arm_elev"], m["arm_elev"])
            stats["max_wrist_tw"] = max(stats["max_wrist_tw"], m["wrist_twist"])
            stats["max_wrist_sw"] = max(stats["max_wrist_sw"], m["wrist_swing"])

        rig.curl_fingers(loc, "r", 0.96)
        rig.curl_fingers(loc, "l", 0.96)
        frames.append(loc)

    clip = rig.bake_sequence("A_LJ_SawLog_Loop", fps, n, frames, "R58 ergonomic crosscut sawing loop (collinear vertical-handle grip, kerf-aligned)")
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 2) for k, v in stats.items()})


def author_carry_log_walk(rig: RigSession):
    """A_LJ_CarryLog_Walk: authentic J_MF_Unarmed_Walk_Fwd lower body + outer-right-shoulder log carry!
    Includes live 3D cylinder-vs-head/neck/chest clearance audit matching LumberMillWorkerActor.cpp!
    """
    walk_clip = ue.load_asset(BASE_WALK)
    if not walk_clip:
        raise RuntimeError("Cannot load base walk: " + BASE_WALK)
    play_len = float(walk_clip.get_play_length())
    fps = 30
    n = max(24, int(round(play_len * fps)))

    frames = []
    stats = dict(max_ik_err=0.0, min_elbow=180.0, max_elbow=0.0, max_wrist_tw=0.0, max_wrist_sw=0.0,
                 min_head_clear_cm=999.0, min_neck_clear_cm=999.0)
    for fi in range(n):
        t = (fi / n) * play_len
        phase = math.tau * fi / n
        loc, _ = rig.sample_clip_frame(walk_clip, t)

        bob = math.sin(2.0 * phase)
        sway = math.sin(phase)
        # Counter-lean gently LEFT (away from log on right shoulder) & slightly forward for realistic load weight!
        for sp, w in (("spine_01", 0.16), ("spine_02", 0.22), ("spine_03", 0.24), ("spine_04", 0.20), ("spine_05", 0.18)):
            if sp in loc:
                rig.turn_lean_right(loc, sp, (-6.5 + 1.2 * sway) * w)
                rig.turn_pitch_fwd(loc, sp, (5.5 + 1.0 * bob) * w)

        # Tilt head slightly left & away from the outer-shoulder timber log!
        rig.turn_lean_right(loc, "neck_01", -6.0)
        rig.turn_lean_right(loc, "head", -5.0)
        rig.turn_yaw_right(loc, "head", -4.0)

        cur_w = rig.compute_fk(loc)
        sh_r = cur_w["upperarm_r"][0]
        sh_l = cur_w["upperarm_l"][0]
        rs = rig.right_sign  # -1.0 -> +right moves toward -X!

        # Right hand reaches OUTWARD-UP-FORWARD cleanly supporting the underside-front of the log barrel
        # resting at SeatCenter = sh_r + Right*9.0 + Up*11.5 + Fwd*5.0 (log radius = 8.55 cm -> underside at sh_r.z + 3 cm)!
        hr_w = (sh_r[0] + rs * 11.0, sh_r[1] + 27.0, sh_r[2] + 6.0 + 1.0 * bob)
        pole_r = (sh_r[0] + rs * 28.0, sh_r[1] + 8.0, sh_r[2] - 24.0)
        sr_m = rig.solve_arm_ik(loc, "r", hr_w, pole_r, rig.vec(0.15, 0.20, 0.97), rig.vec(-0.95, 0.0, 0.30), drive_clav=False)
        rig.curl_fingers(loc, "r", 0.85)

        # Left arm swings naturally OUTWARD on LEFT side (-rs) as a relaxed counterweight!
        hl_w = (sh_l[0] - rs * 10.0, sh_l[1] + 8.0 - 11.0 * sway, sh_l[2] - 43.0 + 1.5 * abs(sway))
        pole_l = (sh_l[0] - rs * 22.0, sh_l[1] - 14.0, sh_l[2] - 20.0)
        sl_m = rig.solve_arm_ik(loc, "l", hl_w, pole_l, rig.vec(0.0, 0.85, -0.52), rig.vec(1.0, 0.0, 0.0), drive_clav=False)
        rig.curl_fingers(loc, "l", 0.30)

        for m in (sr_m, sl_m):
            stats["max_ik_err"] = max(stats["max_ik_err"], m["ik_err"])
            stats["min_elbow"] = min(stats["min_elbow"], m["elbow_flex"])
            stats["max_elbow"] = max(stats["max_elbow"], m["elbow_flex"])
            stats["max_wrist_tw"] = max(stats["max_wrist_tw"], m["wrist_twist"])
            stats["max_wrist_sw"] = max(stats["max_wrist_sw"], m["wrist_swing"])

        # 3D LOG-VS-BODY CLEARANCE AUDIT (exact mirror of ALumberMillWorker::UpdateDynamicToolTransform!)
        fw = rig.compute_fk(loc)
        sh_r_f = fw["upperarm_r"][0]
        hr_f = fw["hand_r"][0]
        seat_c = (sh_r_f[0] + rs * 9.0, sh_r_f[1] + 5.0, sh_r_f[2] + 11.5)
        hand_rel_z = max(-4.0, min(6.0, (hr_f[2] - seat_c[2]) * 0.25))
        log_dir = v_norm((0.0, 40.0, 5.5 + hand_rel_z))
        # Log length 96 cm (half=48 cm), radius 8.55 cm
        log_a = v_sub(seat_c, v_scale(log_dir, 48.0))
        log_b = v_add(seat_c, v_scale(log_dir, 48.0))
        head_center = v_add(fw["head"][0], (0.0, 0.0, 8.0))
        neck_center = fw["neck_01"][0]
        head_clear = point_to_segment_dist(head_center, log_a, log_b) - (8.55 + 10.0)
        neck_clear = point_to_segment_dist(neck_center, log_a, log_b) - (8.55 + 6.0)
        stats["min_head_clear_cm"] = min(stats["min_head_clear_cm"], head_clear)
        stats["min_neck_clear_cm"] = min(stats["min_neck_clear_cm"], neck_clear)

        frames.append(loc)

    if stats["min_head_clear_cm"] < 2.0 or stats["min_neck_clear_cm"] < 2.0:
        raise RuntimeError(f"CARRY LOG CLIPPING AUDIT FAILED: head_clear={stats['min_head_clear_cm']:.2f}cm, neck_clear={stats['min_neck_clear_cm']:.2f}cm")

    clip = rig.bake_sequence("A_LJ_CarryLog_Walk", fps, n, frames, "Ergonomic lumberjack outer-shoulder log carry walk")
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 2) for k, v in stats.items()})


def author_drive_wagon_idle(rig: RigSession):
    """A_LJ_DriveWagon_Idle (90f @ 30fps = 3.00s): seated coachman matched 1:1 to R56 TimberWagon cockpit!
    Wagon datums (build_lumber_wagon_r52.py + LumberMillTimberWagon.cpp):
      - DriverSeatAnchor = Wagon (108, 0, 136), Capsule offset = (-6, 0, 37) => BodyMesh origin = Wagon (102, 0, 85)
      - Seat bench top = Wagon Z 136.0 cm => buttocks Z_body = 51.0 cm (pelvis Z_body = 61.5 cm, flush on bench!)
      - Footboard top  = Wagon Z  94.0 cm => sole Z_body = 9.0 cm => foot_l/r ankle Z_body = 17.6 cm (0.0 cm sink!)
      - SeatFrontBox   = Wagon X 124.4 cm, FrontDashboard inner face = Wagon X 154.5 (bottom) .. 165.0 (knee)
      - Feet planted solidly on oak footboard at Wagon X=135 cm (toes <= 150 cm, >= 5 cm clear of dashboard!)
    """
    fps, n = 30, 90
    base_loc, base_wld = rig.bench_local, rig.bench_world
    mid_sh_z = 0.5 * (base_wld["upperarm_r"][0][2] + base_wld["upperarm_l"][0][2])
    mid_sh_y = 0.5 * (base_wld["upperarm_r"][0][1] + base_wld["upperarm_l"][0][1])

    # Exact Wagon-to-BodyMesh constants (BodyMesh origin at Wagon X=102.0, Z=85.0)
    WAGON_BODY_X = 102.0
    WAGON_BODY_Z = 85.0
    FOOTBOARD_TOP_WAGON_Z = 94.0
    DASH_INNER_TOE_X = 155.0
    SEAT_FRONT_X = 124.4
    ANKLE_TO_SOLE_CM = 8.6

    # Plant both boots cleanly on footboard: ankle Z_body = (94.0 - 85.0) + 8.6 = 17.6 cm, fwd = 32.5 cm (Wagon X=134.5)!
    foot_up_body = (FOOTBOARD_TOP_WAGON_Z - WAGON_BODY_Z) + ANKLE_TO_SOLE_CM  # 17.6 cm
    foot_l_tgt = rig.pt(-14.5, 32.5, foot_up_body)
    foot_r_tgt = rig.pt( 14.5, 32.5, foot_up_body)
    knee_l_pole = rig.pt(-17.5, 58.0, 58.0)
    knee_r_pole = rig.pt( 17.5, 58.0, 58.0)

    frames = []
    stats = dict(
        max_ik_err=0.0, min_elbow=180.0, max_elbow=0.0, max_wrist_tw=0.0, max_wrist_sw=0.0,
        min_knee=180.0, max_knee=0.0, min_sole_wagon_z=999.0, max_toe_wagon_x=-999.0,
        max_knee_wagon_x=-999.0, min_calf_wagon_x=999.0,
    )
    for fi in range(n):
        phase = math.tau * fi / n
        jolt = 0.65 * math.sin(3.0 * phase) + 0.35 * math.sin(6.0 * phase + 0.9)
        sway = math.sin(phase) + 0.35 * math.sin(2.0 * phase - 0.5)
        rein_tug = 0.5 * math.sin(2.0 * phase + 0.4)
        head_scan = 12.0 * math.sin(phase - 0.4)

        loc = dict(base_loc)
        # Solve both legs onto the real oak footboard with anatomical hinge-plane IK (ZERO sink, ZERO dashboard clip!)
        kl_deg = rig.solve_leg_grounded(loc, "l", foot_l_tgt, knee_l_pole, toe_out_deg=10.0)
        kr_deg = rig.solve_leg_grounded(loc, "r", foot_r_tgt, knee_r_pole, toe_out_deg=10.0)
        stats["min_knee"] = min(stats["min_knee"], kl_deg, kr_deg)
        stats["max_knee"] = max(stats["max_knee"], kl_deg, kr_deg)

        for sp, w in (("spine_01", 0.16), ("spine_02", 0.22), ("spine_03", 0.24), ("spine_04", 0.20), ("spine_05", 0.18)):
            if sp in loc:
                rig.turn_pitch_fwd(loc, sp, (6.0 - 1.4 * jolt) * w)
                rig.turn_lean_right(loc, sp, (2.2 * sway) * w)

        rig.turn_yaw_right(loc, "neck_01", head_scan * 0.45)
        rig.turn_yaw_right(loc, "head", head_scan * 0.55)
        rig.turn_pitch_fwd(loc, "head", -4.0 + 1.0 * jolt)

        # Right hand on RIGHT side (+14.5 semantic), Left hand on LEFT side (-14.5 semantic), aligned cleanly toward brass ReinTerrets!
        hr_w = rig.pt( 14.5 + 0.7 * sway, mid_sh_y + 32.0 + 2.0 * rein_tug, mid_sh_z - 19.0 + 1.3 * jolt)
        hl_w = rig.pt(-14.5 + 0.7 * sway, mid_sh_y + 32.0 - 1.8 * rein_tug, mid_sh_z - 19.0 + 1.3 * jolt)
        pole_r = rig.pt( 28.0, mid_sh_y + 4.0, mid_sh_z - 30.0)
        pole_l = rig.pt(-28.0, mid_sh_y + 4.0, mid_sh_z - 30.0)

        sr_m = rig.solve_arm_ik(loc, "r", hr_w, pole_r, rig.vec(0.0, 1.0, 0.0), rig.vec(-1.0, 0.0, 0.0), drive_clav=False)
        sl_m = rig.solve_arm_ik(loc, "l", hl_w, pole_l, rig.vec(0.0, 1.0, 0.0), rig.vec(1.0, 0.0, 0.0), drive_clav=False)
        for m in (sr_m, sl_m):
            stats["max_ik_err"] = max(stats["max_ik_err"], m["ik_err"])
            stats["min_elbow"] = min(stats["min_elbow"], m["elbow_flex"])
            stats["max_elbow"] = max(stats["max_elbow"], m["elbow_flex"])
            stats["max_wrist_tw"] = max(stats["max_wrist_tw"], m["wrist_twist"])
            stats["max_wrist_sw"] = max(stats["max_wrist_sw"], m["wrist_swing"])

        rig.curl_fingers(loc, "r", 0.95)
        rig.curl_fingers(loc, "l", 0.95)

        # Live Wagon Cockpit Geometric Clearance Audit (BodyMesh +Y = Wagon +X, +Z = Wagon +Z)
        fw = rig.compute_fk(loc)
        for side in ("l", "r"):
            ft_p = fw[f"foot_{side}"][0]
            bl_p = fw[f"ball_{side}"][0]
            cf_p = fw[f"calf_{side}"][0]
            sole_wagon_z = WAGON_BODY_Z + min(ft_p[2] - ANKLE_TO_SOLE_CM, bl_p[2] - 2.0)
            toe_wagon_x = WAGON_BODY_X + bl_p[1] + 5.0  # +5 cm boot toe tip ahead of ball joint
            knee_wagon_x = WAGON_BODY_X + cf_p[1] + 5.5  # +5.5 cm kneecap ahead of knee joint
            calf_wagon_x = WAGON_BODY_X + min(cf_p[1], ft_p[1])
            stats["min_sole_wagon_z"] = min(stats["min_sole_wagon_z"], sole_wagon_z)
            stats["max_toe_wagon_x"] = max(stats["max_toe_wagon_x"], toe_wagon_x)
            stats["max_knee_wagon_x"] = max(stats["max_knee_wagon_x"], knee_wagon_x)
            stats["min_calf_wagon_x"] = min(stats["min_calf_wagon_x"], calf_wagon_x)

        frames.append(loc)

    # Hard Driver Cockpit Clearance Gates!
    if stats["min_sole_wagon_z"] < FOOTBOARD_TOP_WAGON_Z - 0.8:
        raise RuntimeError(f"DRIVER FOOTBOARD CLIP: min_sole_wagon_z={stats['min_sole_wagon_z']:.2f} < {FOOTBOARD_TOP_WAGON_Z}")
    if stats["max_toe_wagon_x"] > DASH_INNER_TOE_X - 1.5:
        raise RuntimeError(f"DRIVER DASHBOARD TOE CLIP: max_toe_wagon_x={stats['max_toe_wagon_x']:.2f} > {DASH_INNER_TOE_X}")
    if stats["max_knee_wagon_x"] > 158.0 or stats["min_calf_wagon_x"] < SEAT_FRONT_X + 1.0:
        raise RuntimeError(f"DRIVER KNEE/CALF CLIP: knee_x={stats['max_knee_wagon_x']:.2f}, calf_x={stats['min_calf_wagon_x']:.2f}")
    if stats["min_knee"] < 40.0 or stats["max_knee"] > 125.0:
        raise RuntimeError(f"DRIVER KNEE ANGLE OUT OF RANGE: [{stats['min_knee']:.1f}, {stats['max_knee']:.1f}]")

    clip = rig.bake_sequence("A_LJ_DriveWagon_Idle", fps, n, frames, "Ergonomic R56 wagon driver seated footboard IK + rein loop")
    return dict(path=clip.get_path_name(), frames=n, fps=fps, duration=round(n / fps, 3), **{k: round(v, 2) for k, v in stats.items()})


def inspect_warhorse_ref_bounds():
    try:
        horse = ue.load_asset(SK_WARHORSE)
        if not horse:
            return {}
        bounds = horse.get_imported_bounds() if hasattr(horse, "get_imported_bounds") else horse.get_bounds()
        return dict(
            origin=[round(float(bounds.origin.x), 1), round(float(bounds.origin.y), 1), round(float(bounds.origin.z), 1)],
            extent=[round(float(bounds.box_extent.x), 1), round(float(bounds.box_extent.y), 1), round(float(bounds.box_extent.z), 1)],
        )
    except Exception as ex:
        return {"note": str(ex)}


def main():
    ue.log("=== LumberMillOps-R52 (Ergonomic R55) Headless UE5 Authoring Start ===")
    anims_only = os.environ.get("FPS_LUMBER_ANIMS_ONLY") == "1"
    if anims_only and RECEIPT_PATH.is_file():
        prev = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        transport = prev.get("transport", {})
    else:
        transport = import_transport_meshes()

    body = ue.load_asset(SK_SMITH_BODY)
    if not body:
        raise RuntimeError("Missing SK_Smith_Body: " + SK_SMITH_BODY)
    rig = RigSession(body)

    anims = {}
    for key, fn in (
        ("A_LJ_ChopTree_Loop", author_chop_tree_loop),
        ("A_LJ_SplitLog_Loop", author_split_log_loop),
        ("A_LJ_SawLog_Loop", author_saw_log_loop),
        ("A_LJ_CarryLog_Walk", author_carry_log_walk),
        ("A_LJ_DriveWagon_Idle", author_drive_wagon_idle),
    ):
        info = fn(rig)
        anims[key] = info
        if info["max_ik_err"] > 0.5:
            raise RuntimeError(f"ERGONOMIC GATE FAILED on {key}: max_ik_err={info['max_ik_err']}cm")
        if info["min_elbow"] < 6.0 or info["max_elbow"] > 142.0:
            raise RuntimeError(f"ERGONOMIC GATE FAILED on {key}: elbow range [{info['min_elbow']}, {info['max_elbow']}]")
        if info.get("max_arm_elev", 0.0) > 108.0:
            raise RuntimeError(f"ARMPIT TEAR GATE FAILED on {key}: max_arm_elev={info['max_arm_elev']} deg > 108 deg!")
        ue.log(
            f"[R59-ANIM] {key:22s} | f={info['frames']:3d} ({info['duration']:.2f}s) | ik={info['max_ik_err']:.2f}cm | "
            f"elbow=[{info['min_elbow']:.1f},{info['max_elbow']:.1f}] | elev={info.get('max_arm_elev', 0.0):.1f}deg | "
            f"wrist_bend={info.get('max_wrist_bend', 0.0):.1f}deg | grip_err={info.get('max_grip_err', 0.0):.2f}cm"
        )

    receipt = dict(
        batch="LumberMillOps-R52-R55Ergonomic",
        transport=transport,
        animations=anims,
        warhorse_bounds=inspect_warhorse_ref_bounds(),
    )
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    ue.log(f"LUMBER_OPS_R55_OK: {len(transport)} transport meshes + {len(anims)} ergonomic 3P AnimSequences authored -> {RECEIPT_PATH}")


if __name__ == "__main__":
    main()
