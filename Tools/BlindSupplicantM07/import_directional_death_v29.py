"""Import/save only M07's impact-away death set and its existing Blueprint."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'DirectionalDeathV29'
MANIFEST = OUT/'Motion/directional_death_manifest_v29.json'
REPORT = OUT/'ue_directional_death_delivery_v29.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsDirectionalDeathV29'
BP = DEST+'/BP_BlindSupplicantM07'
LIB = u.EditorAssetLibrary
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 death assets belong to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('M07_V29_PIE_PRESERVED: finish the play session before import.')
    if any(p.get_path_name() == BP or p.get_path_name().startswith(ANIM+'/')
           for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 death or Blueprint edits preserved.')
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
backup = OUT/'Before/BP_BlindSupplicantM07.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.uasset', backup)
blueprint = u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(blueprint)
defaults = u.get_default_object(blueprint.generated_class())
# Reading the new field makes a stale native binary fail before any imports.
defaults.get_editor_property('directional_death_clips')
mesh = defaults.get_editor_property('visual_mesh')
skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV11')
retained = ('melee_left_clip','melee_right_clip','attack_clip','idle_clip','walk_clip','slow_walk_clip',
            'chase_clip','wall_listen_clip','magic_gather_clip','magic_release_clip')
report = dict(revision='DirectionalDeathV29',saved=False,assets=[],clips={},
    authoring_manifest=str(MANIFEST),previous_death=defaults.get_editor_property('death_clip').get_path_name(),
    retained_action_references={p:defaults.get_editor_property(p).get_path_name() for p in retained},
    handoff_seconds=manifest['handoff_seconds'],handoff_fraction=manifest['handoff_fraction'],
    geometry_modified=False,weights_modified=False,native_code_modified=True,new_runtime_ik=False,
    tested=False,runtime_tested=False,rendered=False,user_review_pending=True)


def receipt():
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def save(asset):
    path = asset.get_path_name()
    if not (path.split('.')[0] == BP or path.startswith(ANIM+'/')):
        raise RuntimeError('Death save out of scope: '+path)
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('Death package save failed: '+path)
    report['assets'].append(path)
    receipt()


receipt()
clips = {}
for role, entry in manifest['clips'].items():
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
        raise RuntimeError('Death animation import failed: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale',1.)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',False)
    LIB.set_metadata_tag(clip,'DeathRevision','DirectionalDeathV29: impact-away, preserve facing, whole-body fall')
    save(clip)
    clips[role] = clip
    report['clips'][role] = dict(asset=clip.get_path_name(),duration_seconds=clip.get_play_length())
defaults.set_editor_property('death_clip',clips['DeathAway000'])
defaults.set_editor_property('directional_death_clips',list(clips.values()))
LIB.set_metadata_tag(blueprint,'DeathRevision','DirectionalDeathV29')
save(blueprint)
report.update(saved=True,stage='Eight directional death clips and existing AI/F6 Blueprint saved')
receipt()
manifest.update(ue_imported=True,ue_saved=True,ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename in ('production_status.json','gameplay_delivery.json'):
    record_path = ROOT/filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(death_revision='DirectionalDeathV29',death_delivery=str(REPORT),
        death_assets={r:c.get_path_name() for r,c in clips.items()},
        death_handoff_seconds=manifest['handoff_seconds'],tested=False,runtime_tested=False,user_review_pending=True)
    record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V29_DIRECTIONAL_DEATH_SAVED '+str(REPORT))
