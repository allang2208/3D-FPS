"""Author a continuous 0.5 s pull-load-release on the accepted two-hand rig."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

P = Path(__file__).parent
ROOT = P.parents[1]
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(P))

sys.path.append(str(ROOT / 'MeleePommelAttack20260916'))
from arm_solver import ArmSolver          # noqa: E402
from whirlwind_motion import *               # noqa: E402

bpy.context.preferences.filepaths.save_version = 0

# Grasp matrices come from the same donor and fit record that authored the
# accepted diagonal slashes and the thrust: the hilt contacts must not move.
donor = ROOT / 'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor))
bpy.context.scene.frame_set(0)
r = bpy.data.objects['SK_M4_Infima']
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
pose = {b.name: b.matrix.copy() for b in r.pose.bones}
fit = json.loads((ROOT / 'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
G = pose['WPN_root'] @ Matrix(fit['grip_in_root'])
S = Matrix.Diagonal((-1, 1, 1, 1))
GR = S @ G @ S
leftnames = [b.name for b in r.pose.bones
             if b.name.endswith('_l') and any(b.name.startswith(x) for x in
                                              ['index', 'middle', 'ring', 'pinky', 'thumb'])]
left_rel = {n: pose['hand_l'].inverted() @ pose[n] for n in leftnames}
mirrored = {n[:-1] + 'r': S @ (pose[n] @ rest[n].inverted()) @ S @ rest[n[:-1] + 'r']
            for n in ['hand_l'] + leftnames}
right_rel = {n: mirrored['hand_r'].inverted() @ m for n, m in mirrored.items() if n != 'hand_r'}
HL = Matrix.Translation((0, 0, .06)) @ G.inverted() @ pose['hand_l']
HR = Matrix.Translation((0, 0, .06)) @ GR.inverted() @ mirrored['hand_r']
for grasp in [HL, HR]:
    radial = Vector((grasp.translation.x, grasp.translation.y, 0))
    if radial.length > .0025:
        grasp.translation -= radial.normalized() * .0025

# The current accepted state of this sword lives in the charged-hold revision.
source = ROOT / 'RuneSword20260913/ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
r = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
localrest = {n: (rest[r.data.bones[n].parent.name].inverted() @ m if r.data.bones[n].parent else m)
             for n, m in rest.items()}
solver = ArmSolver(rest, {'l': HL, 'r': HR}, {'l': left_rel, 'r': right_rel})
solver.ready_pose(READY)
s.render.fps = FPS
s.render.fps_base = 1

paired = [poses(f / FPS) for f in range(round(ATTACK_END * FPS) + 1)]
frames = [p[0] for p in paired]
hold = (0, 0)  # The reused arm separator expects an explicit one-frame endpoint hold.
print('WHIRLWIND_SOLVING_GRASP', flush=True)
grasps = solver.fit_path(frames, False, hold)
supports = solver.fit_support(frames, grasps, hold)
supports = solver.separate_arms(frames, grasps, supports, hold)
print('WHIRLWIND_SOLVING_BONES', flush=True)
r.animation_data.action = None
baked = []
for f, (gf, sf) in enumerate(paired):
    p = {n: m.copy() for n, m in rest.items()}
    for side in ['l', 'r']:
        solver.apply_arm(p, side, solver.hand(side, gf, grasps[side][f]), supports[side][f])
    p['WPN_root'] = sf
    for n in ['Blade_Base', 'Blade_Tip']:
        local = rest['WPN_root'].inverted() @ rest[n]
        local.translation *= .8
        p[n] = sf @ local
    localpose = {}
    for b in r.pose.bones:
        basis = localrest[b.name].inverted() @ (p[b.parent.name].inverted() @ p[b.name] if b.parent else p[b.name])
        localpose[b.name] = basis.decompose()
    baked.append(localpose)


def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


action = bpy.data.actions.new('A_RuneSword_WhirlwindV4')
action.use_fake_user = True
r.animation_data.action = action
s.frame_start = 0
s.frame_end = len(baked) - 1
previous = {}
for f, localpose in enumerate(baked):
    s.frame_set(f)
    for b in r.pose.bones:
        loc, q, scale = localpose[b.name]
        q = q.copy()
        if b.name in previous and q.dot(previous[b.name]) < 0:
            q.negate()
        b.rotation_mode = 'QUATERNION'
        b.location = loc
        b.rotation_quaternion = q
        b.scale = scale
        previous[b.name] = q.copy()
        b.keyframe_insert('location', frame=f, group=b.name)
        b.keyframe_insert('rotation_quaternion', frame=f, group=b.name)
        b.keyframe_insert('scale', frame=f, group=b.name)
select(r)
bpy.ops.export_scene.fbx(filepath=str(OUT / 'A_RuneSword_WhirlwindV4.fbx'), use_selection=True,
                         object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
                         add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
print('WHIRLWIND_ANIMATION_EXPORTED', flush=True)


r.animation_data.action=action
r.animation_data.action_slot=action.slots[0]
s.frame_start=0;s.frame_end=len(baked)-1;s.frame_set(0)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Whirlwind_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'clip':'A_RuneSword_WhirlwindV4','fps':FPS,'seconds':ATTACK_END,'ready':READY_END,'spin_end':SPIN_END,'loop':False,'source':str(source),'donor':str(donor),'camera_turn_degrees':T['turnDegrees'],'camera_turn_in_runtime':True,'knots_seconds':KNOTS,'windup_curve':'C2 quintic Hermite with shared velocity; continuous pull/load/drive through the release boundary','runtime_entry_seconds':.1},indent=2),encoding='utf-8')
print('WHIRLWIND_AUTHORED',flush=True)
