"""Sprint43: remove the forearm surface distortion in the PKM tactical sprint.

The tactical sprint for every weapon is the same three clips
(sprint_enter / sprint_loop / sprint_exit - see UM4TacticalSprintComponent::Configure).
Rendered across the transition the PKM left forearm shows banding that runs around
the arm plus a hard rim, and a jagged silhouette around f18: the surface roll is
oscillating band to band, exactly the defect Elbow42 fixed on the idle by
optimising the correction against the measured surface profile instead of forcing
the bones onto a straight line.

This script re-points the Elbow42 optimiser at the three sprint clips.  It starts
from the shipped Elbow41 edits, so nothing that already shipped is thrown away.
Only lowerarm_l / lowerarm_twist_02_l / lowerarm_twist_01_l are twisted, about the
live forearm axis through each bone's own head; descendants' local channels are
re-derived from their preserved world matrices, so the hand, fingers and grip
cannot move.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Sprint43'
EXPORT = HERE / 'Exports'
EDIT = HERE / 'Edit'
for d in (EXPORT, EDIT):
    d.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

RAMPED = ('lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l')
ORDER = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
GRID = np.arange(-45.0, 45.1, 5.0)
TV_WEIGHT = 0.02

CLIPS = (
    ('sprint_enter', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_enter_Elbow41.blend',
     'PKM_sprint_enter_Elbow41', 120, EXPORT / 'A_PKM_sprint_enter.fbx',
     'PKM_sprint_enter_Sprint43'),
    ('sprint_loop', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_loop_Elbow41.blend',
     'PKM_sprint_loop_Elbow41', 120, EXPORT / 'A_PKM_sprint_loop.fbx',
     'PKM_sprint_loop_Sprint43'),
    ('sprint_exit', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_exit_Elbow41.blend',
     'PKM_sprint_exit_Elbow41', 120, EXPORT / 'A_PKM_sprint_exit.fbx',
     'PKM_sprint_exit_Sprint43'),
)

# forward model: how much of each band's surface each ramped bone owns
RAMP_IDX = [E.V7_BONES.index(n) for n in RAMPED]
Wn = np.zeros((E.NB, len(RAMPED)))
for b in range(E.NB):
    sel = E.BIN == b
    tot = E.TW[sel].sum()
    if tot <= 0:
        continue
    for bi, bone_idx in enumerate(RAMP_IDX):
        m = sel[:, None] & (E.TI == bone_idx)
        Wn[b, bi] = E.TW[m].sum() / tot

COMBOS = np.array(np.meshgrid(GRID, GRID, GRID, indexing='ij')).reshape(3, -1).T


def cost(vals, cols):
    d = np.diff(vals[cols])
    return float(np.clip(d, 0.0, None).max()) + TV_WEIGHT * float(np.abs(d).sum())


def repair(blend, action_name, fps, dest, edit_name):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    source = bpy.data.actions[action_name]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0

    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rest_local = {b.name: (rest[b.parent.name].inverted() @ rest[b.name])
                  if b.parent else rest[b.name] for b in rig.data.bones}
    PARENT = {n: rig.data.bones[n].parent.name for n in ORDER}
    start, end = map(int, source.frame_range)

    sampled = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sampled.append({b.name: b.matrix.copy() for b in rig.pose.bones})

    action = source.copy()
    action.name = edit_name
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
        cols = np.where(E.BIN_OK & ~np.isnan(cur))[0]

        fv = Vector(f.tolist())

        def build(dd):
            skin = np.copy(base_skin)
            for name, ang in zip(RAMPED, dd):
                if abs(ang) < 1e-9:
                    continue
                h = pose[name].translation
                skin[E.V7_BONES.index(name)] = np.array(
                    Matrix.Translation(h) @ Matrix.Rotation(math.radians(ang), 4, fv)
                    @ Matrix.Translation(-h) @ delta[name])
            return skin

        if len(cols) >= 3:
            pred = cur[cols][None, :] + COMBOS @ Wn[cols].T
            d = np.diff(pred, axis=1)
            model = np.clip(d, 0.0, None).max(axis=1) + TV_WEIGHT * np.abs(d).sum(axis=1)
            cand = COMBOS[int(np.argmin(model))]
        else:
            cand = np.zeros(3)

        # accept only if the real surface profile actually improves
        base_cost = cost(cur, cols)
        best_dd, best_cost, best_prof = np.zeros(3), base_cost, cur
        trial = E.roll_profile(E.deform_arm(build(cand)), e, u, f)
        if cost(trial, cols) < base_cost:
            best_dd, best_cost, best_prof = cand, cost(trial, cols), trial
        corr = np.zeros(3)
        for name, ang in zip(RAMPED, best_dd):
            pass
        corr = best_dd

        world = {}
        for name in ORDER:
            m = pose[name].copy()
            if name in RAMPED:
                ang = float(corr[RAMPED.index(name)])
                if abs(ang) > 1e-9:
                    h = pose[name].translation
                    m = (Matrix.Translation(h)
                         @ Matrix.Rotation(math.radians(ang), 4, fv)
                         @ Matrix.Translation(-h) @ m)
            world[name] = m

        for name in ORDER:
            pm = (world[PARENT[name]] if PARENT[name] in world
                  else pose[PARENT[name]])
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
                       'corr': {n: round(float(a), 2) for n, a in zip(RAMPED, corr)},
                       'cost_before': round(base_cost, 2),
                       'cost_after': round(best_cost, 2)})
        if frame % 40 == 0:
            print('SPRINT43 %s f%d corr %s  cost %.1f -> %.1f'
                  % (action_name, frame,
                     {n: round(float(a), 1) for n, a in zip(RAMPED, corr)},
                     base_cost, best_cost), flush=True)

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
        filepath=str(dest), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(EDIT / (edit_name + '.blend')))
    return {'frames': len(sampled), 'fps': fps, 'action': action.name,
            'max_hand_drift': max_hand_drift, 'report': report}


results = {}
for label, blend, action_name, fps, dest, edit_name in CLIPS:
    print('\n=== %s (%s) ===' % (label, action_name), flush=True)
    res = repair(blend, action_name, fps, dest, edit_name)
    before = max(r['cost_before'] for r in res['report'])
    after = max(r['cost_after'] for r in res['report'])
    results[label] = {
        'source_blend': str(blend), 'action': res['action'], 'fps': fps,
        'frames': res['frames'], 'max_hand_drift': res['max_hand_drift'],
        'worst_cost_before': round(before, 2), 'worst_cost_after': round(after, 2),
        'export': str(dest), 'edit': str(EDIT / (edit_name + '.blend')),
        'report': res['report'],
    }
    print('EXPORTED %s frames %d  max hand drift %.9f  worst cost %.1f -> %.1f'
          % (dest.name, res['frames'], res['max_hand_drift'], before, after), flush=True)

(HERE / 'authoring_sprint43.json').write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nSPRINT43_AUTHOR_DONE')