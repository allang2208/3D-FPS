"""PKM idle left forearm: remove the residual crease Elbow39 left behind.

Elbow39 put the three forearm bones on a straight pronation line, which cut the
worst surface step from 32.8 deg to 9.0.  What is left is a 14 deg backward bump
centred at t=0.33 of the forearm, where `lowerarm_l` and `lowerarm_twist_02_l`
cross over: the surface roll at t is the weight-weighted mean of the bone rolls,
so it reads the ramp at the *local weight centroid* rather than at t, and the
centroid lags ~0.10 behind t there.  Forcing the bones onto a line therefore
cannot flatten the bump -- it only moves it.

This round therefore optimises instead of assuming.  For every frame it searches
small world-space twists of the same three forearm bones (about the live forearm
axis through each bone's own head) for the one that minimises the worst backward
step and the total variation of that frame's own surface roll profile, using the
measured weight of each bone in each band as the forward model.  The winner is
applied exactly, descendants' local channels are re-derived from their unchanged
world matrices, so the hand, grip, contacts and wrist cannot move.
"""
import importlib.util
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow42'
HERE.mkdir(parents=True, exist_ok=True)
(HERE / 'Exports').mkdir(exist_ok=True)
(HERE / 'Edit').mkdir(exist_ok=True)

spec = importlib.util.spec_from_file_location(
    'elbow39_author', ROOT / 'Elbow39' / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

SRC = ROOT / 'Elbow39' / 'Edit' / 'PKM_idle_Elbow39.blend'
ACTION_IN = 'PKM_idle_Elbow39'
DEST = HERE / 'Exports' / 'A_PKM_idle.fbx'
EDIT_NAME = 'PKM_idle_Elbow42'
FPS = 60

RAMPED = ('lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l')
ORDER = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
GRID = np.arange(-45.0, 45.1, 5.0)
TV_WEIGHT = 0.02

# ---- forward model: how much of each band's surface each ramped bone owns ----
RAMP_IDX = [E.V7_BONES.index(n) for n in RAMPED]
NB = E.NB
Wn = np.zeros((NB, len(RAMPED)))
for b in range(NB):
    sel = E.BIN == b
    tot = E.TW[sel].sum()
    if tot <= 0:
        continue
    for bi, bone_idx in enumerate(RAMP_IDX):
        m = sel[:, None] & (E.TI == bone_idx)
        Wn[b, bi] = E.TW[m].sum() / tot
print('band ownership of the ramped bones (t, lowerarm / lo_twist_02 / lo_twist_01):')
for b in range(NB):
    if any(Wn[b] > 0.02):
        print('  t %+.3f  %.3f  %.3f  %.3f' % (E.BIN_T[b], Wn[b, 0], Wn[b, 1], Wn[b, 2]))

bpy.ops.wm.open_mainfile(filepath=str(SRC))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
source = bpy.data.actions[ACTION_IN]
rig.animation_data.action = source
rig.animation_data.action_slot = source.slots[0]
scene.render.fps = FPS
scene.render.fps_base = 1.0

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
rest_local = {b.name: (rest[b.parent.name].inverted() @ rest[b.name])
              if b.parent else rest[b.name] for b in rig.data.bones}
PARENT = {n: rig.data.bones[n].parent.name for n in ORDER}
print('parents:', PARENT)

start, end = map(int, source.frame_range)
sampled = []
for frame in range(start, end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    sampled.append({b.name: b.matrix.copy() for b in rig.pose.bones})

action = source.copy()
action.name = EDIT_NAME
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in list(bag.fcurves):
                if any('"%s"' % n in curve.data_path for n in ORDER):
                    bag.fcurves.remove(curve)

previous = {}
report = []
max_hand_drift = 0.0
for frame, pose in enumerate(sampled, start):
    s, e, w = (np.array(pose['upperarm_l'].translation),
               np.array(pose['lowerarm_l'].translation),
               np.array(pose['hand_l'].translation))
    u = (e - s) / np.linalg.norm(e - s)
    f = (w - e) / np.linalg.norm(w - e)
    delta = {n: pose[n] @ E.AU_REST_M[E.AU_INDEX[n]].inverted() for n in E.AU_BONES}

    base_skin = np.tile(np.eye(4), (len(E.V7_BONES), 1, 1))
    for i, n in enumerate(E.V7_BONES):
        if n in delta:
            base_skin[i] = np.array(delta[n])
    cur = E.roll_profile(E.deform_arm(base_skin), e, u, f)

    col = E.BIN_OK & ~np.isnan(cur)
    cols = np.where(col)[0]
    c = cur[cols]

    # score every candidate correction with the same forward model
    combos = np.array(np.meshgrid(GRID, GRID, GRID, indexing='ij')).reshape(3, -1).T
    pred = c[None, :] + combos @ Wn[cols].T
    d = np.diff(pred, axis=1)
    cost = np.clip(d, 0.0, None).max(axis=1) + TV_WEIGHT * np.abs(d).sum(axis=1)
    best = int(np.argmin(cost))
    delta_deg = combos[best]

    def build(dd):
        skin = np.copy(base_skin)
        fv = Vector(f.tolist())
        for name, ang in zip(RAMPED, dd):
            if abs(ang) < 1e-9:
                continue
            h = pose[name].translation
            skin[E.V7_BONES.index(name)] = np.array(
                Matrix.Translation(h) @ Matrix.Rotation(math.radians(ang), 4, fv)
                @ Matrix.Translation(-h) @ delta[name])
        return skin

    before = E.backward(cur)
    chosen_skin = build(delta_deg)
    after_prof = E.roll_profile(E.deform_arm(chosen_skin), e, u, f)
    after = E.backward(after_prof)

    fv = Vector(f.tolist())
    world = {}
    for name in ORDER:
        m = pose[name].copy()
        if name in RAMPED:
            ang = float(delta_deg[RAMPED.index(name)])
            if abs(ang) > 1e-9:
                h = pose[name].translation
                m = (Matrix.Translation(h) @ Matrix.Rotation(math.radians(ang), 4, fv)
                     @ Matrix.Translation(-h) @ m)
        world[name] = m

    parent_world = {n: pose[PARENT[n]] for n in ORDER}
    for name in ORDER:
        pm = (world[PARENT[name]] if PARENT[name] in world
              else parent_world[name])
        loc, quat, scale_v = E.local_channels(world[name], pm, rest_local[name])
        if name in previous and quat.dot(previous[name]) < 0.0:
            quat.negate()
        previous[name] = quat.copy()
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        bone.location = loc
        bone.rotation_quaternion = quat
        bone.scale = scale_v
        for ch in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(ch, frame=frame, group=name)

    drift = (world['hand_l'].translation - pose['hand_l'].translation).length
    orient = world['hand_l'].to_quaternion().rotation_difference(
        pose['hand_l'].to_quaternion()).angle
    max_hand_drift = max(max_hand_drift, drift, orient)
    report.append({'frame': frame,
                   'corr': {n: round(float(a), 2) for n, a in zip(RAMPED, delta_deg)},
                   'worst_before': round(before, 2), 'worst_after': round(after, 2)})
    if frame % 20 == 0:
        print('ELBOW42', frame, 'corr',
              {n: round(float(a), 1) for n, a in zip(RAMPED, delta_deg)},
              'worst %.1f -> %.1f' % (before, after), flush=True)

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if any('"%s"' % n in curve.data_path for n in ORDER):
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'

scene.frame_start, scene.frame_end = start, end
scene.frame_set(start)
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=str(DEST), use_selection=True, object_types={'ARMATURE'},
    axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'Edit' / (EDIT_NAME + '.blend')))

worst_before = max(r['worst_before'] for r in report)
worst_after = max(r['worst_after'] for r in report)
print('\nEXPORTED %s frames %d  max hand drift %.9f' % (DEST.name, len(report), max_hand_drift))
print('worst backward step over the clip: %.1f -> %.1f' % (worst_before, worst_after))
(HERE / 'authoring_elbow42.json').write_text(json.dumps({
    'source': str(SRC), 'action': EDIT_NAME, 'fps': FPS, 'frames': len(report),
    'max_hand_drift': max_hand_drift, 'ramped': list(RAMPED),
    'worst_before': worst_before, 'worst_after': worst_after, 'report': report,
}, indent=2), encoding='utf-8')
print('ELBOW42_AUTHOR_DONE')