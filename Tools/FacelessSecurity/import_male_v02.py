"""Save only the new male actions and current security Blueprint references."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V02')
DEST='/Game/Monsters/FacelessSecurity';ANIM=DEST+'/Animations/V02'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve loaded session')
manifest=json.loads((ROOT/'motion_manifest.json').read_text(encoding='utf-8'))
bp=u.load_asset(DEST+'/BP_FacelessSecurity');u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh');skeleton=mesh.get_editor_property('skeleton')
report={'stage':'importing','saved':[],'clips':{},'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),'tested':False,'rendered':False,'native_code_modified':False}
def receipt():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
    receipt()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
clips={}
for role,entry in manifest['clips'].items():
    name='A_Security_Male_V02_'+role
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
    data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',manifest['fps'])
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform',True)
    task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=ANIM;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task])
    clip=u.load_asset(ANIM+'/'+name)
    if not clip or not task.imported_object_paths:raise RuntimeError('Animation import failed '+role)
    clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('rate_scale',entry['rate_scale'])
    if clip.get_editor_property('enable_root_motion'):clip.set_editor_property('enable_root_motion',False)
    if clip.get_editor_property('force_root_lock'):clip.set_editor_property('force_root_lock',False)
    LIB.set_metadata_tag(clip,'SecurityMotionRevision','V02 male sources, native retarget, tailored stance, grounded boots and authored strike timing')
    LIB.set_metadata_tag(clip,'SourceAction',entry['source_asset']);save(clip);clips[role]=clip
    report['clips'][role]={'asset':clip.get_path_name(),'duration':clip.get_play_length(),'rate_scale':entry['rate_scale'],'source_asset':entry['source_asset']}
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
settings={'walk_speed':manifest['walk_speed_cm_s'],'contact_time':manifest['contact_time'],'contact_end':manifest['contact_end'],'recovery_time':manifest['recovery_time']}
for prop,value in settings.items():cdo.set_editor_property(prop,value)
LIB.set_metadata_tag(bp,'MotionRevision','V02 Male guard: Jason idle/walk, ZombieAnimationPack Attack_D weighted strike')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),settings=settings,
    walk_rate_contract={'controller_denominator_cm_s':26.,'source_foot_speed_cm_s':manifest['walk_source_speed_cm_s'],'asset_rate_scale':manifest['walk_rate_scale']},
    preserved='V01 body, clothing, materials, skeleton, skin weights, physics, AI and F6 entry; only action references and matching movement/contact timing updated')
receipt();print('SECURITY_MALE_V02_UE_SAVED '+json.dumps({'saved_count':len(report['saved']),'settings':settings,'clips':report['clips']}),flush=True)
