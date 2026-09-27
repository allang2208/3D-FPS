"""Retarget the original DW715 inspect, preserving its timing and trajectories.

Animation-only FBX; M1911's own grip, mechanical rest and empty slide are retained.
No spin choreography, procedural flourishes, renders or game tests are added.
"""
import ast
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent
SOURCES = OUT.parent
sys.path.insert(0, str(OUT))
import author_support as support
RATE = 120
DONOR = SOURCES / 'DanWesson715Upgrade20260914/DanWesson715_Upgrade_Editable.blend'
TARGET = SOURCES / 'M1911RearRain20260913/M1911_RearFinish_Editable.blend'

def open_blend(path):
    bpy.context.preferences.filepaths.save_version = 0
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
    except RuntimeError as e:
        if 'Missing library override hierarchy root data' not in str(e):
            raise

def select_action(rig, name):
    action = bpy.data.actions[name]
    rig.animation_data_create(); rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    return action

def sample(rig, frame):
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}

open_blend(DONOR)
rig = bpy.data.objects['SK_DW715_Manny']
select_action(rig, 'DW715V2_idle'); source_idle = sample(rig, 0)
action = select_action(rig, 'DW715V2_inspect')
first, last = action.frame_range
fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
duration = (last - first) / fps
source_rows = [sample(rig, first + i / RATE * fps) for i in range(round(duration * RATE) + 1)]
source_parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
source_grips = {s: source_idle['WPN_root'].inverted() @ source_idle['hand_' + s] for s in ('r', 'l')}
landmarks = []
for fraction in (0, .15, .3, .5, .7, .85, 1):
    p = source_rows[round((len(source_rows) - 1) * fraction)]
    landmarks.append({'time': duration * fraction,
        'gun': list(p['WPN_root'].translation),
        'right_hand': list(p['hand_r'].translation), 'left_hand': list(p['hand_l'].translation)})

open_blend(TARGET)
scene = bpy.context.scene; scene.render.fps = 60
rig = bpy.data.objects['SK_M1911_Manny']; rig.data.pose_position = 'POSE'
skin = support.install_bare_arms(rig, 'M1911')
names = [b.name for b in rig.data.bones]
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}
tree = ast.parse((SOURCES / 'DualPistolQuickCombat20260920/VideoRefV3/author_actions.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
    and n.name == 'solve_arm'], type_ignores=[]), 'native_arm_solver', 'exec'), globals())

support.DURATION = duration
(OUT / 'Animations').mkdir(exist_ok=True)
clips = {}; actions = {}
for empty in (False, True):
    suffix = '_empty' if empty else ''
    idle_name = 'M1911_Contact_idle' + suffix
    select_action(rig, idle_name); idle = sample(rig, 0)
    # Constant donor-to-target gun-space registration places both idles exactly
    # together, while all subsequent motion comes from the original clip.
    mapping = idle['WPN_root'] @ source_idle['WPN_root'].inverted()
    rotation = mapping.to_quaternion()
    grips = {s: idle['WPN_root'].inverted() @ idle['hand_' + s] for s in ('r', 'l')}
    mechanical = {n: idle['WPN_root'].inverted() @ idle[n] for n in names if n.startswith('WPN_')}
    frames = []; rows = []; previous = {}
    for i, donor in enumerate(source_rows):
        t = i / RATE
        p = {n: m.copy() for n, m in idle.items()}
        gun = mapping @ donor['WPN_root']
        for side in ('r', 'l'):
            hand_name = 'hand_' + side
            # Preserve the donor hand's movement relative to its grip, applying
            # that movement to M1911's own grip rather than the revolver handle.
            relative_motion = donor['WPN_root'].inverted() @ donor[hand_name] @ source_grips[side].inverted()
            hand = gun @ relative_motion @ grips[side]
            upper, lower = 'upperarm_' + side, 'lowerarm_' + side
            shoulder = idle[upper].translation + rotation @ (donor[upper].translation - source_idle[upper].translation)
            pole = idle[lower].translation + rotation @ (donor[lower].translation - source_idle[lower].translation)
            solve_arm(p, idle, side, hand, shoulder, pole, names)
            for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                for joint in (1, 2, 3):
                    n = f'{finger}_{joint:02d}_{side}'
                    if n not in donor or n not in p:
                        continue
                    dp = source_parents[n]; parent = parents[n]
                    source_start = (source_idle[dp].inverted() @ source_idle[n]).to_quaternion()
                    source_now = (donor[dp].inverted() @ donor[n]).to_quaternion()
                    loc, q, scale = (idle[parent].inverted() @ idle[n]).decompose()
                    p[n] = p[parent] @ Matrix.LocRotScale(loc, q @ source_start.inverted() @ source_now, scale)
        for n, local in mechanical.items():
            p[n] = gun @ local
        # Keep the source's central performance; only hand off the very start
        # and end to M1911's exact native idle, without a second runtime recenter.
        edge = min(1., t / .12, (duration - t) / .18)
        edge = max(0., edge); edge = edge * edge * (3. - 2. * edge)
        row = {}
        for n in names:
            local = p[parents[n]].inverted() @ p[n] if parents[n] else p[n]
            base = idle[parents[n]].inverted() @ idle[n] if parents[n] else idle[n]
            if edge < 1.:
                local = Matrix.LocRotScale(base.translation.lerp(local.translation, edge),
                    base.to_quaternion().slerp(local.to_quaternion(), edge), base.to_scale().lerp(local.to_scale(), edge))
            loc, q, scale = (local_rest[n].inverted() @ local).decompose()
            if n in previous and previous[n].dot(q) < 0: q.negate()
            previous[n] = q.copy(); row[n] = (loc, q, scale)
        rows.append(row); frames.append(t * 60)
    kind = 'inspect' + suffix
    action = support.bake_action(rig, scene, 'M1911_Revolver_' + kind, rows, frames)
    bpy.ops.object.select_all(action='DESELECT'); rig.hide_set(False); rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = OUT / 'Animations' / f'A_M1911_{kind}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_step=.5, bake_anim_simplify_factor=0)
    actions[kind] = action; clips[kind] = {'fbx': str(fbx), 'idle': idle_name}
    print('M1911_ORIGINAL_REVOLVER_INSPECT_EXPORTED', kind, flush=True)
rig.animation_data.action = actions['inspect']; rig.animation_data.action_slot = actions['inspect'].slots[0]
scene.frame_set(0)
blend = OUT / 'M1911_RevolverInspect_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
(OUT / 'authoring.json').write_text(json.dumps({'source_blend': str(DONOR), 'source_action': 'DW715V2_inspect',
    'source_ue_animation': '/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_inspect',
    'duration': duration, 'sample_rate': RATE, 'source_landmarks': landmarks,
    'target': str(TARGET), 'skin': skin, 'blend': str(blend), 'clips': clips,
    'testing': 'Not performed; user testing'}, indent=2), encoding='utf8')
print('M1911_REVOLVER_INSPECT_AUTHOR_COMPLETE', duration, flush=True)
