"""Probe ASH-12 clips: skin stretch per group, bone pops and camera-space placement."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP = ARGS[0]
FRAMES = [int(v) for v in ARGS[1:] if v.lstrip('-').isdigit()]
S = HERE.parent
CLIPS = {
    'reload_empty': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn', 198),
    'quick_melee': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base', 54),
    'reload': (S / 'ASH12ReloadRefine20260919/ASH12_Reload_Reference_Editable.blend',
               'ASH12_Reference_reload', 150),
    'idle': (S / 'ASH1220260917/ASH12_Editable.blend', 'ASH12_idle', 5),
}
CAM = dict(eye=Vector((0.0, -0.10, 0.05)), right=Vector((1, 0, 0)),
           forward=Vector((0, 1, 0)), up=Vector((0, 0, 1)))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883

blend, action_name, LAST = CLIPS[CLIP]
bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[action_name]
scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.type == 'MESH' and ob is not arms:
        ob.hide_viewport = True
        ob.hide_render = True

surface = SkinSurface(rig, arms)
print('SURFACE', len(surface.ids), 'edges', len(surface.edges),
      {g: int((surface.groups == g).sum()) for g in set(surface.groups)}, flush=True)


def cam_space(point):
    d = Vector(point) - CAM['eye']
    return [round(d.dot(CAM[k]) * 100, 1) for k in ('right', 'forward', 'up')]


rows = []
for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(f))
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    ratio, growth = surface.stretch(pose)
    worst = int(np.argmax(ratio))
    a, b = surface.edges[worst]
    groups = {}
    for g in ('upperarm', 'lowerarm', 'hand', 'fingers'):
        for s in ('l', 'r'):
            sel = ratio[(surface.groups[surface.edges[:, 0]] == g) &
                        (surface.sides[surface.edges[:, 0]] == s)]
            gro = growth[(surface.groups[surface.edges[:, 0]] == g) &
                         (surface.sides[surface.edges[:, 0]] == s)]
            groups[f'{s}_{g}'] = round(float(sel.max()), 3) if sel.size else None
            groups[f'{s}_{g}_mm'] = round(float(gro.max()) * 1000, 1) if gro.size else None
    row = dict(frame=f, max_stretch=round(float(ratio.max()), 3),
               max_growth_mm=round(float(growth.max()) * 1000, 1),
               p999=round(float(np.percentile(ratio, 99.9)), 3),
               over15=int((ratio > 1.5).sum()), over2=int((ratio > 2.0).sum()),
               worst=dict(group=list(surface.group_of(a)), side=list(surface.group_of(b)),
                          rest_mm=round(float(surface.rest_len[worst]) * 1000, 2)),
               groups=groups)
    for bone in ('hand_l', 'lowerarm_l', 'upperarm_l', 'hand_r', 'lowerarm_r', 'upperarm_r'):
        row[bone] = cam_space(rig.matrix_world @ rig.pose.bones[bone].matrix.translation)
    # grip check: hand position in the receiver's own space (does the support hand stay put?)
    root = rig.matrix_world @ pose['WPN_root']
    inv = root.inverted()
    for bone in ('hand_l', 'hand_r'):
        p = inv @ (rig.matrix_world @ pose[bone].translation)
        row[bone + '_root'] = [round(v * 100, 1) for v in p]
    # closest skinned surface to the camera, and how far in front of the eye it is
    pts = surface.positions(pose)
    local = np.array([[v.x, v.y, v.z] for v in
                      (rig.matrix_world @ b.matrix.translation for b in rig.pose.bones.values())])
    eye = np.array([CAM['eye'].x, CAM['eye'].y, CAM['eye'].z])
    rel = pts - eye
    fwd = rel @ np.array([CAM['forward'].x, CAM['forward'].y, CAM['forward'].z])
    right = rel @ np.array([CAM['right'].x, CAM['right'].y, CAM['right'].z])
    up = rel @ np.array([CAM['up'].x, CAM['up'].y, CAM['up'].z])
    onscreen = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    if onscreen.any():
        idx = np.flatnonzero(onscreen)[int(np.argmin(fwd[onscreen]))]
        row['closest'] = dict(forward_cm=round(float(fwd[idx]) * 100, 1),
                              right_cm=round(float(right[idx]) * 100, 1),
                              up_cm=round(float(up[idx]) * 100, 1),
                              group=[str(surface.groups[idx]), str(surface.sides[idx])])
    else:
        row['closest'] = None
    row['onscreen_under_20cm'] = int(((fwd > 0.006) & (fwd < 0.20) & onscreen).sum())
    rows.append(row)

(HERE / f'probe_{CLIP}.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print('ASH12', CLIP, r['frame'], 'growth_mm', r['max_growth_mm'], 'p999', r['p999'],
          'closest', r['closest'], 'under20', r['onscreen_under_20cm'],
          'hand_l_root', r['hand_l_root'], 'hand_l', r['hand_l'], 'hand_r', r['hand_r'], flush=True)
