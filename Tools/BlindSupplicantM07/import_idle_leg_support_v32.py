"""Import and save only the two idle-calibrated melee clips and AI/F6 refs."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'IdleLegSupportV32'
MANIFEST = OUT/'Motion/idle_leg_support_manifest_v32.json'
REPORT = OUT/'ue_idle_leg_support_delivery_v32.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsIdleLegSupportV32'
BP = DEST+'/BP_BlindSupplicantM07'
PROPS = {'melee_left_clip':'SweepLeft','melee_right_clip':'SweepRight','attack_clip':'SweepLeft'}
LIB = u.EditorAssetLibrary

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 animations belong to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('M07_V32_PIE_PRESERVED: finish the play session before import.')
    if any(p.get_path_name() == BP or p.get_path_name().startswith(ANIM+'/')
           for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 animations or Blueprint edits preserved.')
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
backup = OUT/'Before/BP_BlindSupplicantM07.uasset'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.uasset',backup)
blueprint = u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(blueprint)
defaults = u.get_default_object(blueprint.generated_class())
mesh = defaults.get_editor_property('visual_mesh')
skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV11')
retained = ('idle_clip','walk_clip','slow_walk_clip','chase_clip','wall_listen_clip',
            'death_clip','magic_gather_clip','magic_release_clip')
report = dict(revision='IdleLegSupportV32',saved=False,assets=[],clips={},
    authoring_manifest=str(MANIFEST),
    previous_references={p:defaults.get_editor_property(p).get_path_name() for p in PROPS},
    retained_action_references={p:defaults.get_editor_property(p).get_path_name() for p in retained},
    retained_directional_deaths=[c.get_path_name() for c in defaults.get_editor_property('directional_death_clips')],
    retained_settings={p:defaults.get_editor_property(p) for p in ('attack_range','left_contact_time',
        'right_contact_time','contact_window_seconds','melee_playback_rate')},
    idle_reference=manifest['idle_reference_asset'],geometry_modified=False,weights_modified=False,
    native_code_modified=False,new_runtime_ik=False,tested=False,runtime_tested=False,
    rendered=False,user_review_pending=True)


def receipt():
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def save(asset):
    path = asset.get_path_name()
    if not (path.split('.')[0] == BP or path.startswith(ANIM+'/')):
        raise RuntimeError('V32 save out of scope: '+path)
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('V32 package save failed: '+path)
    report['assets'].append(path)
    receipt()


receipt()
clips = {}
for role in ('SweepLeft','SweepRight'):
    entry = manifest['clips'][role]
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = options.import_materials = options.import_textures = options.create_physics_asset = False
    options.import_animations = True
    options.skeleton = skeleton
    data = options.anim_sequence_import_data
    data.convert_scene = data.convert_scene_unit = True
    data.set_editor_property('preserve_local_transform',True)
    data.import_uniform_scale = 1.
    data.set_editor_property('use_default_sample_rate',False)
    data.set_editor_property('custom_sample_rate',manifest['fps'])
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task = u.AssetImportTask()
    task.filename,task.destination_name,task.destination_path = entry['file'],'A_M07_'+role,ANIM
    task.automated,task.save = True,False
    task.replace_existing = task.replace_existing_settings = True
    task.options,task.factory = options,u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(ANIM+'/A_M07_'+role)
    if not clip or not task.imported_object_paths or clip.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('V32 animation import failed: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale',1.)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',False)
    LIB.set_metadata_tag(clip,'MotionRevision','IdleLegSupportV32: idle knee plane, single calf hinge, grounded claws')
    save(clip)
    clips[role] = clip
    report['clips'][role] = dict(asset=clip.get_path_name(),duration_seconds=clip.get_play_length())
for prop,role in PROPS.items():
    defaults.set_editor_property(prop,clips[role])
LIB.set_metadata_tag(blueprint,'MeleeLegRevision','IdleLegSupportV32')
save(blueprint)
report.update(saved=True,stage='Two melee animations and existing AI/F6 Blueprint saved')
receipt()
manifest.update(ue_imported=True,ue_saved=True,ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename in ('production_status.json','gameplay_delivery.json'):
    record_path = ROOT/filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(melee_leg_revision='IdleLegSupportV32',melee_leg_delivery=str(REPORT),
        melee_assets={r:clips[r].get_path_name() for r in clips},
        tested=False,runtime_tested=False,user_review_pending=True)
    record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V32_IDLE_LEG_SUPPORT_SAVED '+str(REPORT))
