"""Save library-derived M07 casting and height-matched melee reach."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'LibraryCastV28'
MANIFEST = OUT/'Motion/library_cast_manifest_v28.json'
REPORT = OUT/'ue_library_cast_delivery_v28.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsLibraryCastV28'
BP = DEST+'/BP_BlindSupplicantM07'
PROPS = {'magic_gather_clip':'MagicGather','magic_release_clip':'MagicRelease'}
LIB = u.EditorAssetLibrary
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 casting belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('M07_V28_PIE_PRESERVED: finish the play session before import.')
    if any(p.get_path_name() == BP or p.get_path_name().startswith(ANIM+'/')
           for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved casting or M07 Blueprint edits preserved.')
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
settings = dict(attack_range=manifest['base_attack_range_cm'],
               magic_release_contact_time=manifest['release_contact_seconds'])
retained = ('melee_left_clip','melee_right_clip','attack_clip','idle_clip','walk_clip','slow_walk_clip',
            'chase_clip','death_clip','wall_listen_clip')
report = dict(revision='LibraryCastV28',saved=False,assets=[],clips={},
    source=manifest['source_asset'],authoring_manifest=str(MANIFEST),
    previous_settings={p:defaults.get_editor_property(p) for p in settings},
    previous_references={p:defaults.get_editor_property(p).get_path_name() for p in PROPS},
    retained_action_references={p:defaults.get_editor_property(p).get_path_name() for p in retained},
    retained_charge_forward_offset_cm=defaults.get_editor_property('magic_charge_forward_offset_cm'),
    retained_magic_ranges={p:defaults.get_editor_property(p) for p in ('fireball_range','ice_column_range','lightning_range')},
    geometry_modified=False,weights_modified=False,native_code_modified=False,new_runtime_ik=False,
    tested=False,runtime_tested=False,rendered=False,user_review_pending=True)
def receipt():
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    name = asset.get_path_name()
    if not (name.split('.')[0] == BP or name.startswith(ANIM+'/')):
        raise RuntimeError('V28 save out of scope: '+name)
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('V28 package save failed: '+name)
    report['assets'].append(name)
    receipt()
receipt()
clips = {}
for role in PROPS.values():
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
        raise RuntimeError('V28 cast import failed: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale',1.)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',False)
    LIB.set_metadata_tag(clip,'CastingRevision','LibraryCastV28: native full-body source, continuous gather/release, grounded pelvis')
    save(clip)
    clips[role] = clip
    report['clips'][role] = dict(asset=clip.get_path_name(),duration_seconds=clip.get_play_length())
for prop,role in PROPS.items():
    defaults.set_editor_property(prop,clips[role])
for prop,value in settings.items():
    defaults.set_editor_property(prop,value)
LIB.set_metadata_tag(blueprint,'CastingRevision','LibraryCastV28')
save(blueprint)
report.update(saved=True,settings=settings,effective_melee_range_cm=manifest['effective_melee_range_cm'],
    melee_activation_distance_cm=manifest['effective_melee_range_cm']-15.,
    melee_stopping_distance_cm=manifest['effective_melee_range_cm']-30.,
    stage='Two casting clips and existing AI/F6 Blueprint saved; accepted melee animations retained')
receipt()
manifest.update(ue_imported=True,ue_saved=True,ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename in ('production_status.json','gameplay_delivery.json'):
    record_path = ROOT/filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(casting_revision='LibraryCastV28',casting_delivery=str(REPORT),
        casting_assets={r:c.get_path_name() for r,c in clips.items()},
        casting_release_contact_seconds=settings['magic_release_contact_time'],
        melee_base_attack_range_cm=settings['attack_range'],
        melee_effective_attack_range_cm=manifest['effective_melee_range_cm'],
        tested=False,runtime_tested=False,user_review_pending=True)
    record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V28_LIBRARY_CAST_SAVED '+str(REPORT))
