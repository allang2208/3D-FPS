"""Locate which part of the support arm enters the camera volume, and when.

Camera model: the game action anchor used by the accepted SVD reviews
(eye at (0,-0.10,0.05) m, +Y view axis, +Z up, 5 mm near clip), with the 82 deg
protected cone used for the accepted charging-hand repair plus the real 75 deg /
2.39:1 frame for on-screen depth.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP = ARGS[0]
FRAMES = [int(v) for v in ARGS[1:]]
JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')

CLIPS = {
    'reload': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDThumbUp20260923\SVD_base_Editable.blend', 'A_SVD_reload'),
    'reload_empty': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDChargeGrasp20260924\SVD_base_Grasp.blend', 'A_SVD_reload_empty'),
    'idle': (r'D:\FPS3D\FPSGAME\SourceAssets\SVDHandRepair20260923\SVD_base_Editable.blend', 'A_SVD_idle'),
}
blend, action = CLIPS[CLIP]
bpy.ops.wm.open_mainfile(filepath=blend, use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[action]
scene = bpy.context.scene

GROUPS = {
    'clavicle': ('clavicle_l',),
    'upperarm': ('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l'),
    'lowerarm': ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l'),
    'hand': ('hand_l',),
    'fingers': tuple(n for n in (g.name for g in arms.vertex_groups)
                     if n.endswith('_l') and n.split('_')[0] in
                     ('thumb', 'index', 'middle', 'ring', 'pinky')),
}
NAME_TO_GROUP = {n: g for g, names in GROUPS.items() for n in names}
GROUP_IDS = {g: {arms.vertex_groups[n].index for n in names if n in arms.vertex_groups}
             for g, names in GROUPS.items()}

# dominant left-side group per vertex
vertex_group = {}
for v in arms.data.vertices:
    best, share = None, 0.0
    total = sum(g.weight for g in v.groups) or 1.0
    for g in v.groups:
        name = arms.vertex_groups[g.group].name
        if name in NAME_TO_GROUP and g.weight / total > share:
            best, share = name, g.weight / total
    if best:
        vertex_group[v.index] = NAME_TO_GROUP[best]
left_ids = list(vertex_group)
print('LEFT_VERTICES', len(left_ids), {g: sum(1 for i in left_ids if vertex_group[i] == g) for g in GROUPS},
      flush=True)

CAM = Vector((0.0, -0.10, 0.05))
TV = math.tan(math.radians(82 / 2))
TH = TV * 16 / 9
TV75 = math.tan(math.radians(75 / 2))
TH75 = TV75 * (2109 / 883)


def frame_probe(f):
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arms.evaluated_get(dg)
    mw = ev.matrix_world
    rows = {}
    onscreen_depth = []
    group_depth = {g: None for g in GROUPS}
    for i in left_ids:
        p = (mw @ ev.data.vertices[i].co) - CAM
        x, depth, z = p.x, p.y, p.z
        pen = min(depth - 0.005, TH * depth - x, TH * depth + x, TV * depth - z, TV * depth + z) + 0.006
        g = vertex_group[i]
        best = rows.get(g)
        if best is None or pen > best:
            rows[g] = pen
        if depth > 0.006 and abs(x) <= TH75 * depth and abs(z) <= TV75 * depth:
            onscreen_depth.append(depth)
            if group_depth[g] is None or depth < group_depth[g]:
                group_depth[g] = depth
    wrist = (rig.matrix_world @ rig.pose.bones['hand_l'].matrix.translation) - CAM
    elbow = (rig.matrix_world @ rig.pose.bones['lowerarm_l'].matrix.translation) - CAM
    shoulder = (rig.matrix_world @ rig.pose.bones['upperarm_l'].matrix.translation) - CAM
    return dict(
        frame=f,
        pen={g: round(rows.get(g, -9.0) * 100, 1) for g in GROUPS},
        group_onscreen_depth_mm={g: (None if group_depth[g] is None else round(group_depth[g] * 1000, 1))
                                 for g in GROUPS},
        onscreen_min_depth_mm=round(min(onscreen_depth) * 1000, 1) if onscreen_depth else None,
        onscreen_vertices=len(onscreen_depth),
        wrist=[round(v * 100, 1) for v in wrist],
        elbow=[round(v * 100, 1) for v in elbow],
        shoulder=[round(v * 100, 1) for v in shoulder],
    )


out = [frame_probe(f) for f in FRAMES]
(JOB / f'diagnose_{CLIP}.json').write_text(json.dumps(out, indent=1))
for r in out:
    print('DIAG', CLIP, r['frame'], 'pen', r['pen'],
          'depth_mm', r['group_onscreen_depth_mm'], 'onscreen', r['onscreen_min_depth_mm'],
          'shoulder_cm', r['shoulder'], 'elbow_cm', r['elbow'], 'wrist_cm', r['wrist'], flush=True)
