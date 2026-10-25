"""Save fitted chair clips and native Kaitlin counterparts in new packages."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
REVISION = globals().get('FURNITURE_REVISION', 'ChairReuse20261024')
OUT = ROOT/'SourceAssets/FurnitureRest20261022'/REVISION
DEST = '/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/'+REVISION
FEMALE_DEST = '/Game/Characters/KaitlinPlayer20261023/'+REVISION
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
data = read(OUT/'authored.json')
source_hash = hashlib.sha256((OUT/'authored.json').read_bytes()).hexdigest()
baseline = read(OUT/'baseline_routes.json')
mesh = u.load_asset(data['mesh'])
if not mesh:
    raise RuntimeError('Missing native chair authoring mesh.')
E = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
factory = u.AnimSequenceFactory()
factory.target_skeleton = mesh.skeleton
factory.preview_skeletal_mesh = mesh
receipt_path = OUT/'assets_saved.json'
receipt = read(receipt_path) if receipt_path.exists() else {'source_sha256': source_hash, 'default': {}, 'variants': {}}
if receipt['source_sha256'] != source_hash:
    raise RuntimeError('Authored source changed after saving; use a new package revision.')

def record():
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


for role, take in data['clips'].items():
    if role not in data.get('changed_roles', data['clips']):
        continue
    if role in receipt['default']:
        continue
    name = 'A_' + role.replace('.', '_')
    if E.does_asset_exist(DEST+'/'+name):
        raise RuntimeError('Preserve unreceipted package: '+name)
    clip = assets.create_asset(name, DEST, u.AnimSequence, factory)
    ctl = clip.get_editor_property('controller')
    frames = take['frames']
    ctl.open_bracket('Reuse relaxed furniture seating', False)
    try:
        ctl.set_frame_rate(u.FrameRate(take['rate'], 1), False)
        ctl.set_number_of_frames(u.FrameNumber(len(frames)-1), False)
        for i, bone in enumerate(data['names']):
            ctl.add_bone_curve(bone, False)
            keys = [frame[i] for frame in frames]
            if not ctl.set_bone_track_keys(bone, [u.Vector(*k[:3]) for k in keys],
                                           [u.Quat(*k[3:7]) for k in keys],
                                           [u.Vector(*k[7:]) for k in keys], False):
                raise RuntimeError('Track failed: '+bone)
    finally:
        ctl.close_bracket(False)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Animation compilation failed: '+role)
    if not E.save_loaded_asset(clip, False):
        raise RuntimeError('Animation save failed: '+role)
    receipt['default'][role] = clip.get_path_name()
    record()
    print('CHAIR_SAVED', role, flush=True)

if 'kaitlin' in baseline['variants']:
    target = u.load_asset(baseline['variants']['kaitlin']['mesh'])
    rtg = u.load_asset('/Game/Characters/KaitlinPlayer20261023/Motion/Rig/RTG_Jason_Kaitlin.RTG_Jason_Kaitlin')
    if not target or not rtg:
        raise RuntimeError('Missing existing Jason-to-Kaitlin retarget assets.')
    female = receipt['variants'].setdefault('kaitlin', {})
    for role, path in receipt['default'].items():
        if role in female:
            continue
        clip = u.load_asset(path)
        name = 'K_'+clip.get_name()
        if E.does_asset_exist(FEMALE_DEST+'/'+name):
            raise RuntimeError('Preserve unreceipted female package: '+name)
        if globals().get('NATIVE_REVERSE_EXITS',False) and role.endswith('.Exit'):
            entry = u.load_asset(female[role[:-5]+'.Enter'])
            output = E.duplicate_asset(entry.get_path_name(),FEMALE_DEST+'/'+name)
            opt = u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=target
            opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
            rate=data['clips'][role]['rate'];count=len(data['clips'][role]['frames'])
            poses=[u.AnimPoseExtensions.get_anim_pose_at_time(entry,max(0.,entry.get_play_length()-j/rate),opt) for j in range(count)]
            controller=output.get_editor_property('controller');controller.open_bracket('Reverse the native bed entry',False)
            try:
                controller.set_frame_rate(u.FrameRate(rate,1),False);controller.set_number_of_frames(u.FrameNumber(count-1),False)
                for bone in u.AnimationLibrary.get_animation_track_names(entry):
                    keys=[u.AnimPoseExtensions.get_bone_pose(p,bone,u.AnimPoseSpaces.LOCAL) for p in poses]
                    if not controller.set_bone_track_keys(bone,[k.translation for k in keys],[k.rotation for k in keys],[k.scale3d for k in keys],False):raise RuntimeError('Native reversed track: '+str(bone))
            finally:controller.close_bracket(False)
        else:
            inputs = u.IKRetargetBatchOperationInputs()
            inputs.assets_to_retarget = [E.find_asset_data(path)]
            inputs.source_mesh = mesh
            inputs.target_mesh = target
            inputs.ik_retarget_asset = rtg
            inputs.prefix = 'K_'
            inputs.target_path = FEMALE_DEST
            inputs.include_referenced_assets = False
            inputs.overwrite_existing_files = False
            results = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
            clips = [a.get_asset() for a in results if str(a.asset_class_path.asset_name) == 'AnimSequence']
            if len(clips) != 1:
                raise RuntimeError('Expected one female chair clip: '+role)
            output = clips[0]
        for key in ('enable_root_motion', 'force_root_lock', 'root_motion_root_lock', 'rate_scale'):
            output.set_editor_property(key, clip.get_editor_property(key))
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(output):
            raise RuntimeError('Female animation compilation failed: '+role)
        if not E.save_loaded_asset(output, False):
            raise RuntimeError('Female animation save failed: '+role)
        female[role] = output.get_path_name()
        record()
        print('CHAIR_KAITLIN_SAVED', role, flush=True)

lengths = {}
for variant, routes in [('default', receipt['default']), *receipt['variants'].items()]:
    lengths[variant] = {}
    for role, asset in routes.items():
        length = u.load_asset(asset).get_play_length()
        if abs(length-data['clips'][role]['duration']) > .001:
            raise RuntimeError('Saved timing differs from furniture phase: '+variant+'/'+role)
        lengths[variant][role] = length
(OUT/'save_complete.json').write_text(json.dumps({
    'authored_sha256': source_hash,
    'default_clips': len(receipt['default']),
    'variant_clips': {k: len(v) for k, v in receipt['variants'].items()},
    'saved': True, 'runtime_published': False,
    'saved_durations': lengths,
}, indent=2))
print('CHAIR_SAVE_COMPLETE', flush=True)
