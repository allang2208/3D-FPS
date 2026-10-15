"""Two diagonal warhammer cuts on the accepted bare-arm author rig.

Only the weapon's swing plane is redirected. Each shoulder stays on its own
side, both hands retain the source handle contacts, and complete arm chains
are solved with their original segment lengths and distributed axial twist.
"""
import ast, copy, json, math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
OUT = P/'Export'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'SprintDragV1/RigSource/SteelWarhammer_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_RusticPickaxe_Rig']
rig.data.pose_position = 'POSE'
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions['A_RusticPickaxe_Idle']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
finger_basis = {b.name: b.matrix_basis.copy() for b in rig.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
CFG = json.loads((ROOT/'SourceAssets/PickaxeSightline20260919/motion.json').read_text())
STATIONS = json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
SHOULDER_OVERRIDES = {}
module = ast.parse((ROOT/'SourceAssets/PickaxeSightline20260919/author_attack.py').read_text(encoding='utf-8'))
for function in module.body:
    if isinstance(function, ast.FunctionDef) and function.name == 'solve_arm':
        for i, node in enumerate(function.body):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'shoulder' for t in node.targets):
                function.body[i+1:i+1] = ast.parse('shoulder = SHOULDER_OVERRIDES[side]').body
                break
ast.fix_missing_locations(module)
names = {'unwrap','axial_delta','frame_rotation','solve_arm'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<shared_arm_solver>','exec'))
# Reuse baking and local hierarchy conversion without running the sprint job.
module = ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
names = {'ease','apply_pose','new_action','bake'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<warhammer_bake>','exec'))

FPS = 150
source = {}
for clip, duration in (('Swing', .68), ('HitRecover', .44)):
    name = 'A_RusticPickaxe_'+clip
    if bpy.data.actions.get(name):
        bpy.data.actions[name].name = 'REF_PreSightline_'+clip
    with bpy.data.libraries.load(str(ROOT/'SourceAssets/PickaxeSightline20260919/Pickaxe_Sightline_Editable.blend'),link=False) as (_, loaded):
        loaded.actions = [name]
    action = loaded.actions[0]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    source[clip] = []
    for frame in range(round(duration*FPS)+1):
        scene.frame_set(frame*2)  # accepted source is authored at 300 fps
        source[clip].append({b.name: b.matrix.copy() for b in rig.pose.bones})

def diagonal_pose(original, degrees, weight, state):
    if weight < 1e-7:
        return copy.deepcopy(original)
    roll = Quaternion((0,1,0), math.radians(degrees)*weight)
    wpn = roll.to_matrix().to_4x4()@original['WPN_root']
    grips = {s: original['WPN_root'].inverted()@original['hand_'+s] for s in ('l','r')}
    # Move the complete grip group into the two arms' common reachable volume.
    # No individual wrist is translated away from the handle and no bone scales.
    for side in ('l','r'):
        SHOULDER_OVERRIDES[side] = original['upperarm_'+side].translation.copy()
    for _ in range(8):
        for side in ('l','r'):
            upper, fore, hand = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
            reach = (wpn@grips[side]).translation-SHOULDER_OVERRIDES[side]
            limit = ((rest[fore].translation-rest[upper].translation).length+(rest[hand].translation-rest[fore].translation).length)*.985
            if reach.length > limit:
                wpn.translation -= reach.normalized()*(reach.length-limit)
    pose = copy.deepcopy(idle)
    for side in ('l','r'):
        upper, fore, wrist = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
        hand = wpn@grips[side]
        shoulder = SHOULDER_OVERRIDES[side]
        axis = (hand.translation-shoulder).normalized()
        source_axis = (original[wrist].translation-original[upper].translation).normalized()
        radial = original[fore].translation-original[upper].translation
        radial = (radial-source_axis*radial.dot(source_axis)).normalized()
        # Transport the accepted elbow plane, then support the palm within a
        # bounded circle arc. Unwrap that arc before interpolation to avoid flips.
        guide = (roll@source_axis).rotation_difference(axis)@(roll@radial)
        rest_fore = (rest[wrist].translation-rest[fore].translation).normalized()
        neutral = hand.to_quaternion()@rest[wrist].to_quaternion().inverted()@rest_fore
        desired = -neutral+axis*neutral.dot(axis)
        if desired.length > 1e-5:
            desired.normalize()
            angle = unwrap(math.atan2(axis.dot(guide.cross(desired)),guide.dot(desired)),state.get(side+'_palm_support'))
            state[side+'_palm_support'] = angle
            guide = Quaternion(axis,max(-math.pi/4,min(math.pi/4,angle))*weight)@guide
        pole = [guide.x*(1 if side=='r' else -1),guide.y,guide.z]
        CFG['elbow_pole_top'][side] = pole
        CFG['elbow_pole_impact'][side] = pole
        solve_arm(pose,side,hand,weight,1.,0.,state)
    pose['WPN_root'] = wpn
    return pose

clips = []
for stage, degrees in ((1,45.),(2,-45.)):
    state = {}
    swing = []
    contact_state = None
    for i, original in enumerate(source['Swing']):
        t = i/FPS
        w = ease(t/.09)*(1-ease((t-.53)/.15))
        swing.append(diagonal_pose(original,degrees,w,state))
        if i == round(.24*FPS):
            contact_state = copy.deepcopy(state)
    state = contact_state
    recovery = [diagonal_pose(original,degrees,1-ease((i/FPS-.30)/.14),state) for i,original in enumerate(source['HitRecover'])]
    recovery[0] = copy.deepcopy(swing[round(.24*FPS)])
    for suffix, poses in ((f'Slash{stage}',swing),(f'Slash{stage}Recover',recovery)):
        name = 'A_Warhammer_'+suffix
        bake(name,poses,FPS)
        clips.append({'name':name,'seconds':(len(poses)-1)/FPS,'frames':len(poses)})
rig.animation_data.action = bpy.data.actions['A_Warhammer_Slash1']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Combo_Editable.blend'))
receipt = {'clips':clips,'fps':FPS,'source_contact_seconds':.24,'third_clip':'A_RusticPickaxe_Swing','third_damage_multiplier':1.25,'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
