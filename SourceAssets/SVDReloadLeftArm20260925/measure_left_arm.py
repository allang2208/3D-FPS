"""Measure the support (left) arm in the SVD reload tails against the game camera anchor.

Read-only diagnosis: no asset is modified. Numbers only; the camera model matches
the one used by SVDChargeGrasp20260924 (eye 10 cm behind / 5 cm above the origin,
+Z up, -Y muzzle, 75 deg vertical FOV, 5 mm near clip).
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
JOB = ARGS[0]
OUT = Path(ARGS[1]) if len(ARGS) > 1 else Path(__file__).parent / 'measure'
OUT.mkdir(parents=True, exist_ok=True)

CONFIG = {
    'svd_base_reload': dict(
        blend=r'D:\FPS3D\FPSGAME\SourceAssets\SVDThumbUp20260923\SVD_base_Editable.blend',
        action='A_SVD_reload', frames=list(range(300, 401, 2)) + [400],
        armature='SK_M4_Infima', mesh='SK_Manny_Arms_Export'),
    'svd_base_reload_empty': dict(
        blend=r'D:\FPS3D\FPSGAME\SourceAssets\SVDChargeGrasp20260924\SVD_base_Grasp.blend',
        action='A_SVD_reload_empty', frames=list(range(400, 516, 2)) + [515],
        armature='SK_M4_Infima', mesh='SK_Manny_Arms_Export'),
    'svd_base_idle': dict(
        blend=r'D:\FPS3D\FPSGAME\SourceAssets\SVDHandRepair20260923\SVD_base_Editable.blend',
        action='A_SVD_idle', frames=[0, 1, 2, 3, 4],
        armature='SK_M4_Infima', mesh='SK_Manny_Arms_Export'),
}
CFG = CONFIG[JOB]

bpy.ops.wm.open_mainfile(filepath=CFG['blend'], use_scripts=False)
rig = bpy.data.objects[CFG['armature']]
arms = bpy.data.objects[CFG['mesh']]
act = bpy.data.actions[CFG['action']]
scene = bpy.context.scene

# --- game camera anchor (same model as the SVD charge review) ---
cam = bpy.data.objects.new('ProbeCam', bpy.data.cameras.new('ProbeCam'))
scene.collection.objects.link(cam)
cam.location = (0.0, -0.10, 0.05)
cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
cam.data.clip_start = 0.005
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 24
cam.data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
bpy.context.view_layer.update()
TO_CAM = cam.matrix_world.inverted()
CAM_FORWARD = -cam.matrix_world.to_3x3().col[2].normalized()   # -Z in world
VFOV = math.radians(75.0)

LEFT_PREFIX = ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l',
               'upperarm_twist_01_l', 'upperarm_twist_02_l',
               'lowerarm_twist_01_l', 'lowerarm_twist_02_l')
LEFT_GROUPS = {g.index for g in arms.vertex_groups
               if g.name in LEFT_PREFIX or g.name.endswith('_l')}
left_ids = {v.index for v in arms.data.vertices
            if sum(g.weight for g in v.groups if g.group in LEFT_GROUPS)
            / max(1e-8, sum(g.weight for g in v.groups)) > 0.90}

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
BONES = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l']


def sample(frame):
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


rows = []
for f in CFG['frames']:
    sample(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arms.evaluated_get(dg)
    mw = ev.matrix_world
    pts = [TO_CAM @ (mw @ ev.data.vertices[i].co) for i in left_ids]
    dists = [p.length for p in pts]
    fwd = [-p.z for p in pts]
    near = [p for p in pts if 0.005 < -p.z < 0.12]
    vfov_hits = [p for p in near
                 if abs(math.atan2(p.y, -p.z)) < VFOV * 0.75
                 and abs(math.atan2(p.x, -p.z)) < math.radians(70)]
    world = {n: rig.matrix_world @ rig.pose.bones[n].matrix.translation for n in BONES}
    local = {n: rig.pose.bones[n].matrix.translation - rest[n].translation for n in BONES}
    scales = {n: list(rig.pose.bones[n].scale) for n in BONES}
    seg = {
        'shoulder_elbow': (world['lowerarm_l'] - world['upperarm_l']).length * 100,
        'elbow_wrist': (world['hand_l'] - world['lowerarm_l']).length * 100,
        'clav_shoulder': (world['upperarm_l'] - world['clavicle_l']).length * 100,
    }
    rows.append(dict(
        frame=f,
        min_eye_dist_mm=round(min(dists) * 1000, 2),
        min_forward_mm=round(min(fwd) * 1000, 2),
        near_verts=len(near), near_in_frustum=len(vfov_hits),
        closest_forward_mm=round(min(fwd) * 1000, 2),
        world_cm={n: [round(v * 100, 2) for v in world[n]] for n in BONES},
        wrist_shoulder_cm=round((world['hand_l'] - world['upperarm_l']).length * 100, 2),
        seg_cm={k: round(v, 3) for k, v in seg.items()},
        pose_scales={n: [round(x, 5) for x in scales[n]] for n in BONES},
        local_shift_cm={n: round(local[n].length * 100, 3) for n in BONES},
    ))

rest_seg = dict(
    shoulder_elbow=(rest['lowerarm_l'].translation - rest['upperarm_l'].translation).length * 100,
    elbow_wrist=(rest['hand_l'].translation - rest['lowerarm_l'].translation).length * 100,
    clav_shoulder=(rest['upperarm_l'].translation - rest['clavicle_l'].translation).length * 100,
)

# last frame of the clip vs the accepted idle pose, per left-arm bone
idle = CONFIG['svd_base_idle']
bpy.ops.wm.open_mainfile(filepath=idle['blend'], use_scripts=False)
rig2 = bpy.data.objects[idle['armature']]
rig2.animation_data.action = bpy.data.actions[idle['action']]
rig2.animation_data.action_slot = bpy.data.actions[idle['action']].slots[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
idle_world = {n: rig2.matrix_world @ rig2.pose.bones[n].matrix.translation for n in BONES}

last = rows[-1]['world_cm']
delta = {n: round(((Vector([c / 100 for c in last[n]]) - idle_world[n]).length) * 100, 3)
         for n in BONES}

report = dict(job=JOB, blend=CFG['blend'], action=CFG['action'],
              left_vertices=len(left_ids),
              rest_segments_cm={k: round(v, 3) for k, v in rest_seg.items()},
              last_vs_idle_bone_delta_cm=delta,
              frames=rows)
(OUT / (JOB + '.json')).write_text(json.dumps(report, indent=1))
print('SVD_LEFT_ARM', JOB, 'verts', len(left_ids),
      'last_min_eye_mm', rows[-1]['min_eye_dist_mm'],
      'last_min_fwd_mm', rows[-1]['min_forward_mm'],
      'near_verts_max', max(r['near_verts'] for r in rows),
      'vs_idle', json.dumps(delta), flush=True)
