"""Replace only the two V18 gaits baked with the rig in REST position."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'BodyMotionV18'
MANIFEST = OUT / 'Move/body_gait_manifest_v18.json'
REPORT = OUT / 'ue_locomotion_export_repair_v18.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST + '/AnimationsBodyMotionV18'
BP = DEST + '/BP_BlindSupplicantM07'
LIB = u.EditorAssetLibrary

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not level_editor or level_editor.is_in_play_in_editor():
        raise RuntimeError('M07 gait replacement requires an editing context; existing PIE preserved.')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
skeleton = u.load_asset(DEST + '/SK_M07_ReferenceOriginalV11')
bp = u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
mesh = defaults.get_editor_property('visual_mesh')
report = {'revision': 'BodyMotionV18PoseBakeRepair', 'saved': False, 'assets': [],
          'cause': 'The gait producer loaded the V17 skin rig in REST and baked constant reference-pose FBX tracks.',
          'repair': 'Reauthor and bake both existing V18 gait actions in POSE position; replace only the two gait assets and save existing AI/F6 Blueprint references.',
          'mesh': mesh.get_path_name(), 'skeleton': skeleton.get_path_name(),
          'native_rebuild_required': False, 'runtime_tested': False,
          'visual_tested': False, 'tested': False, 'user_review_pending': True,
          'source_manifest': str(MANIFEST), 'clips': {}}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 gait package could not save: ' + asset.get_path_name())
    report['assets'].append(asset.get_path_name())
    receipt()


clips = {}
for role in ('SlowWalk', 'Chase'):
    entry = manifest['clips'][role]
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = options.import_textures = options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.anim_sequence_import_data
    data.convert_scene = data.convert_scene_unit = True
    data.import_uniform_scale = 1.
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', 30)
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    task = u.AssetImportTask()
    task.filename = entry['file']
    task.destination_name = 'A_M07_' + role
    task.destination_path = ANIM
    task.automated = True
    task.save = False
    task.replace_existing = task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(ANIM + '/A_M07_' + role)
    if not clip or not task.imported_object_paths:
        raise RuntimeError('M07 gait import failed: ' + role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'LocomotionExportRepair', 'V18: POSE evaluation restored for animation baking; user test pending')
    save(clip)
    clips[role] = clip
    report['clips'][role] = {'asset': clip.get_path_name(), 'source_fbx': entry['file'],
                             'duration_s': clip.get_play_length()}

defaults.set_editor_property('slow_walk_clip', clips['SlowWalk'])
defaults.set_editor_property('chase_clip', clips['Chase'])
defaults.set_editor_property('walk_clip', clips['Chase'])
LIB.set_metadata_tag(bp, 'LocomotionExportRepair', 'V18 POSE baking repair: existing AI/F6, mesh, cloth, weights and other actions retained')
save(bp)
report.update(saved=True, blueprint=bp.get_path_name(),
              stage='Corrected walk/run assets and existing AI/F6 references actually saved')
receipt()
manifest.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT),
                runtime_tested=False, tested=False, user_review_pending=True)
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for filename in ('ue_body_motion_delivery_v18.json', 'source_delivery_v18.json'):
    record_path = OUT / filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(locomotion_export_repair_saved=True, locomotion_export_repair_receipt=str(REPORT),
                  animation_export_pose_position='POSE', runtime_tested=False,
                  visual_tested=False, tested=False, user_review_pending=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT / filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(locomotion_export_repair_saved=True, locomotion_export_repair_receipt=str(REPORT),
                  stage='V18 with corrected POSE-baked walk/run assets and existing AI/F6 references saved',
                  runtime_tested=False, visual_tested=False, tested=False, user_review_pending=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('M07_V18_POSE_BAKED_WALK_RUN_REPAIR_SAVED ' + str(REPORT), flush=True)
