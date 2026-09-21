"""Import the recovery revision and publish only its tail into live V5 clips.

Run under the project's UE batch mutex. No PIE, preview or validation run.
Existing live animation keys through the spin boundary are copied directly;
notifies, runtime paths and the material border fix remain on their assets.
"""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).parent
L = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
NORMAL = '/Game/Weapons/AzureRunesword20260913'
LONG = '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'
NAME = 'A_RuneSword_WhirlwindRecoverV6'
INFO = json.loads((P/'authoring.json').read_text(encoding='utf-8'))

u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
if not L.does_asset_exist(NORMAL+'/'+NAME):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = u.load_asset(NORMAL+'/SK_AzureRunesword_Manny').skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', INFO['fps'])
    task = u.AssetImportTask()
    task.filename = str(P/'Export'/(NAME+'.fbx'))
    task.destination_path = NORMAL
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = options
    TOOLS.import_asset_tasks([task])
    clip = u.load_asset(NORMAL+'/'+NAME)
    if not task.imported_object_paths or not clip:
        raise RuntimeError('Recovery FBX import did not create the animation')
    compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:
        clip.set_editor_property('bone_compression_settings', compression)
    if not L.save_loaded_asset(clip, False):
        raise RuntimeError('Could not save the recovery animation')

if not L.does_asset_exist(LONG+'/'+NAME):
    script = P/'author_long_grip.py'
    exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), {'__file__': str(script)})

mesh = u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh = mesh
receipts = []
for folder in [NORMAL, LONG]:
    active_path = folder+'/A_RuneSword_WhirlwindV5'
    revision_path = folder+'/'+NAME
    backup_path = folder+'/A_RuneSword_WhirlwindV5_BeforeRecoverV6'
    active = u.load_asset(active_path)
    revision = u.load_asset(revision_path)
    if L.get_metadata_tag(active, 'Whirlwind.RecoverRevision') == 'OutwardRecoverV6':
        receipts.append({'asset': active_path, 'revision': revision_path, 'saved': True, 'already_published': True})
        continue
    # Backup first. The live object is not replaced, so runtime references,
    # asset-level settings and authored notify tracks survive publication.
    backup = u.load_asset(backup_path) if L.does_asset_exist(backup_path) else L.duplicate_asset(active_path, backup_path)
    if not backup or not L.save_loaded_asset(backup, False):
        raise RuntimeError('Unable to retain the pre-recovery animation '+active_path)
    intervals = u.AnimationLibrary.get_num_frames(active)
    seconds = active.get_play_length()
    if intervals != INFO['intervals'] or abs(seconds-INFO['intervals']/INFO['fps']) > .001:
        raise RuntimeError('Animation timing changed during authoring; preserve the live asset '+active_path)
    tracks = {name: ([], [], []) for name in INFO['affected_bones']}
    last_quats = {}
    for frame in range(intervals+1):
        seconds_at_frame = frame/INFO['fps']
        source = active if seconds_at_frame <= INFO['recover_start_seconds'] else revision
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(source, seconds_at_frame, options)
        for name, (positions, rotations, scales) in tracks.items():
            transform = u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)
            q = transform.rotation
            if name in last_quats:
                prev = last_quats[name]
                if q.x*prev.x+q.y*prev.y+q.z*prev.z+q.w*prev.w < 0:
                    q = u.Quat(-q.x, -q.y, -q.z, -q.w)
            positions.append(transform.translation)
            rotations.append(q)
            scales.append(transform.scale3d)
            last_quats[name] = q
    controller = active.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(active.get_editor_property('data_model_interface'))
    controller.open_bracket('Whirlwind outward extension and return in existing recover window', False)
    try:
        for name, (positions, rotations, scales) in tracks.items():
            if not controller.set_bone_track_keys(name, positions, rotations, scales, False):
                raise RuntimeError('Unable to write recovery bone '+name)
    finally:
        controller.close_bracket(False)
    L.set_metadata_tag(active, 'Whirlwind.RecoverRevision', 'OutwardRecoverV6')
    L.set_metadata_tag(active, 'Whirlwind.RecoverSource', revision_path)
    if not L.save_loaded_asset(active, False):
        raise RuntimeError('Unable to save active recovery '+active_path)
    receipts.append({'asset': active_path, 'revision': revision_path, 'backup': backup_path,
        'saved': True, 'recover_start_seconds': INFO['recover_start_seconds'],
        'recover_seconds': INFO['recover_seconds'], 'prefix_source': 'existing live source keys', 'tested': False})
    (P/'import_receipt.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    u.log('WHIRLWIND_RECOVER_PUBLISHED '+active_path)
(P/'import_receipt.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
u.log('WHIRLWIND_RECOVER_ASSETS_SAVED')
