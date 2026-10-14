"""Retarget the licensed full-body sword donors and save Jason-only clips."""
import json
import math
import re
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSwordFree20261005'
DEST = '/Game/Characters/JasonPlayer20261003/SwordFullBody20261005'
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
sources = json.loads((OUT/'imported-sources.json').read_text())
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
target = u.load_asset(cfg['body_mesh'])
chosen = {
    'Kevin': {'Attack2H01': 'Slash1', 'CombatIdle2H01': 'Idle'},
    'KayKit': {'Melee_2H_Attack_Chop': 'Overhead', 'Melee_2H_Attack_Slice': 'Slash2',
              'Melee_2H_Attack_Stab': 'Thrust', 'Melee_2H_Attack_Spin': 'Whirlwind',
              'Melee_Block_Attack': 'Pommel', 'Melee_Block': 'Guard', 'Melee_Block_Hit': 'GuardHit'},
}


def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())


def create(name, cls, factory):
    if lib.does_asset_exist(DEST+'/Rig/'+name):
        raise RuntimeError('Rig already exists: '+name)
    return assets.create_asset(name, DEST+'/Rig', cls, factory)


def rig(name, mesh, kind):
    ik = create(name, u.IKRigDefinition, u.IKRigDefinitionFactory())
    c = u.IKRigController.get_controller(ik)
    c.set_skeletal_mesh(mesh)
    names = {re.sub('[^a-z0-9]', '', str(n).lower()): str(n)
             for n in u.AnimPoseExtensions.get_bone_names(mesh.skeleton.get_reference_pose())}
    def bone(n):
        return names[re.sub('[^a-z0-9]', '', n.lower())]
    if kind == 'Jason':
        root = 'pelvis'
        chains = {'Spine': ('spine_01', 'spine_05'), 'Neck': ('neck_01', 'neck_02'), 'Head': ('head', 'head')}
        for s in ('l', 'r'):
            for label, start, end in [('Clavicle', 'clavicle', 'clavicle'), ('Arm', 'upperarm', 'hand'), ('Leg', 'thigh', 'foot'), ('Toe', 'ball', 'ball')]:
                chains[label+'_'+s] = (start+'_'+s, end+'_'+s)
            for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                chains[digit+'_'+s] = (digit+'_01_'+s, digit+'_03_'+s)
    elif kind == 'Kevin':
        root = 'B-hips'
        chains = {'Spine': ('B-spine', 'B-chest'), 'Neck': ('B-neck', 'B-neck'), 'Head': ('B-head', 'B-head')}
        for s in ('l', 'r'):
            for label, start, end in [('Clavicle', 'shoulder', 'shoulder'), ('Arm', 'upperArm', 'hand'), ('Leg', 'thigh', 'foot'), ('Toe', 'toe', 'toe')]:
                chains[label+'_'+s] = ('B-'+start+'.'+s, 'B-'+end+'.'+s)
            for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                stem = digit+'Finger' if digit in ('index', 'middle', 'ring') else digit
                chains[digit+'_'+s] = ('B-'+stem+'01.'+s, 'B-'+stem+'03.'+s)
    else:
        root = 'hips'
        chains = {'Spine': ('spine', 'chest'), 'Head': ('head', 'head')}
        for s in ('l', 'r'):
            # KayKit's hand is a simplified finger block. Wrist is the true
            # three-joint arm endpoint; handslot is the weapon attachment.
            for label, start, end in [('Arm', 'upperarm', 'wrist'), ('Leg', 'upperleg', 'foot'), ('Toe', 'toes', 'toes')]:
                chains[label+'_'+s] = (start+'.'+s, end+'.'+s)
    c.set_retarget_root(bone(root))
    for label, (start, end) in chains.items():
        c.add_retarget_chain(label, bone(start), bone(end), '')
    save(ik)
    return ik


target_rig = rig('IK_Jason_Sword', target, 'Jason')
saved = {}
for kind, selections in chosen.items():
    source = u.load_asset(sources[kind]['mesh'])
    source_rig = rig('IK_'+kind+'_Sword', source, kind)
    rtg = create('RTG_'+kind+'_Jason_Sword', u.IKRetargeter, u.IKRetargetFactory())
    c = u.IKRetargeterController.get_controller(rtg)
    c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, source_rig)
    c.set_ik_rig(u.RetargetSourceOrTarget.TARGET, target_rig)
    c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, source)
    c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
    c.add_default_ops()
    c.auto_map_chains(u.AutoMapChainType.EXACT, True)
    pose = c.create_retarget_pose('Jason_Sword_Aligned', u.RetargetSourceOrTarget.TARGET)
    c.set_current_retarget_pose(pose, u.RetargetSourceOrTarget.TARGET)
    c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
    save(rtg)
    paths = {label: next(p for n, p in sources[kind]['clips'].items() if n.endswith(suffix))
             for suffix, label in selections.items()}
    inputs = u.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget = [lib.find_asset_data(p) for p in paths.values()]
    inputs.source_mesh = source
    inputs.target_mesh = target
    inputs.ik_retarget_asset = rtg
    inputs.prefix = 'J_'
    inputs.target_path = DEST+'/Animations'
    inputs.include_referenced_assets = False
    inputs.overwrite_existing_files = False
    outputs = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
    for data in outputs:
        clip = data.get_asset()
        if not isinstance(clip, u.AnimSequence):
            continue
        original = clip.get_name().removeprefix('J_')
        label = next(k for k, p in paths.items() if p.split('.')[-1] == original)
        clip.set_preview_skeletal_mesh(target)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', True)
        clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.ANIM_FIRST_FRAME)
        save(clip)
        saved[label] = clip

# Derive an upward stroke from the full-body downward stroke, including its
# hips, chest and both complete arms. No first-person hand curves are baked.
upper = lib.duplicate_asset(saved['Overhead'].get_path_name(), DEST+'/Animations/J_Sword_Uppercut')
count = upper.get_editor_property('data_model_interface').get_number_of_keys()
duration = upper.get_play_length()
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = target
options.evaluation_type = u.AnimDataEvalType.SOURCE
poses = [u.AnimPoseExtensions.get_anim_pose_at_time(saved['Overhead'], duration*(1-i/(count-1)), options) for i in range(count)]
controller = upper.get_editor_property('controller')
controller.open_bracket('Full-body reverse stroke for upward sword attack', False)
try:
    for name in u.AnimPoseExtensions.get_bone_names(poses[0]):
        keys = [u.AnimPoseExtensions.get_bone_pose(p, name, u.AnimPoseSpaces.LOCAL) for p in poses]
        controller.set_bone_track_keys(name, [t.translation for t in keys], [t.rotation for t in keys], [t.scale3d for t in keys], False)
finally:
    controller.close_bracket(False)
saved['Uppercut'] = upper

timings = {}
for label, clip in saved.items():
    # Authored marker placement from donor hand motion; these retime only the
    # displayed clip, never the weapon's contact or damage schedule.
    length = clip.get_play_length()
    count = max(3, int(round(length*60))+1)
    points = []
    for i in range(count):
        p = u.AnimPoseExtensions.get_anim_pose_at_time(clip, length*i/(count-1), options)
        hand = u.AnimPoseExtensions.get_bone_pose(p, 'hand_r', u.AnimPoseSpaces.WORLD)
        points.append(hand.translation)
    indices = range(max(1, int(count*.18)), min(count-1, int(count*.78)))
    peak = max(indices, key=lambda i: (points[i+1]-points[i-1]).length())
    contact = peak/(count-1)
    release = min(.88, contact+.16)
    if label == 'Thrust':
        peak = max(indices, key=lambda i: points[i].y)
        contact = peak/(count-1)
        release = min(.88, contact+.10)
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    u.AnimationLibrary.add_animation_notify_track(clip, 'SwordTiming')
    for name, fraction in [('Contact', contact), ('Release', release)]:
        u.AnimationLibrary.add_animation_sync_marker(clip, name, fraction*length, 'SwordTiming')
    lib.set_metadata_tag(clip, 'ThirdPersonSource', 'Free author full-body donor; not FPS hands')
    save(clip)
    timings[label] = {'length': length, 'contact': contact, 'release': release}

mapping = {'Melee.FullBody.'+k: a.get_path_name() for k, a in saved.items()}
mapping['Melee.FullBody.HeavyRelease'] = mapping['Melee.FullBody.Slash1']
mapping['Melee.FullBody.Charge'] = mapping['Melee.FullBody.Slash1']
mapping['Melee.FullBody.GuardBreak'] = mapping['Melee.FullBody.GuardHit']
bp = u.load_asset('/Game/AsianMale_Jason/Demo/MetaHumans/Common/Face/ABP_Face_PostProcess')
head_ik = u.get_default_object(bp.generated_class()).get_editor_property('EnableHeadMovementIK')
(OUT/'assets-saved.json').write_text(json.dumps({'runtime_clips': mapping, 'timings': timings,
    'head_postprocess_default_EnableHeadMovementIK': head_ik}, indent=2), encoding='utf-8')
print('SWORD_FULLBODY_SAVED '+json.dumps(mapping))
