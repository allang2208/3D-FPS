"""Save only the changed render assembly and attack recovery; retain V09 clothing."""
from pathlib import Path
import unreal as u
source_bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');source_cdo=u.get_default_object(source_bp.generated_class())
if source_cdo.get_editor_property('visual_mesh').get_name()!='SK_FacelessSecurity_V09':raise RuntimeError('Source mesh changed from V09')
if source_cdo.get_editor_property('attack_clip').get_name()!='A_Security_Male_V06_attack':raise RuntimeError('Source attack changed from V06')
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_security_v05.py').read_text(encoding='utf-8')
prefix=src.split("mesh=u.load_asset(report['meshes']['outfit']);entry=")[0].replace('V05','V10')
prefix=prefix.replace("[('outfit','SK_FacelessSecurity_V10'),('clothing','SK_FacelessSecurity_Clothing_V10'),('body','SK_FacelessSecurity_Body_V10')]","[('outfit','SK_FacelessSecurity_V10')]")
prefix=prefix.replace('independent torso and sleeves; same-side arm weights; smooth crotch transition; intact hands and boots',
    'Boot-compatible visible ankle binding; closed-boot skin visibility mask; V09 clothing and complete body preserved')
exec(compile(prefix,'security_v10_mesh_import','exec'))
old_attack=cdo.get_editor_property('attack_clip');old_recovery=cdo.get_editor_property('recovery_time')
cycle=old_attack.get_play_length()+old_recovery
entry=manifest['clips']['attack'];name='A_Security_Male_V10_attack';anim_path=DEST+'/Animations/V10'
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',manifest['fps'])
data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('preserve_local_transform',True)
task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=anim_path;task.destination_name=name
task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory()
AT.import_asset_tasks([task]);clip=u.load_asset(anim_path+'/'+name)
if not clip or not task.imported_object_paths:raise RuntimeError('Recovery animation import did not produce an asset')
mesh=u.load_asset(report['meshes']['outfit']);clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('rate_scale',1.)
for prop in ['enable_root_motion','force_root_lock']:clip.set_editor_property(prop,False)
LIB.set_metadata_tag(clip,'SecurityMotionRevision','V10 continuous whole-body recovery after 1.10 s; complete-arm curves; same ready endpoint')
LIB.set_metadata_tag(clip,'SourceAction',entry['source_asset']);save(clip)
cdo.set_editor_property('visual_mesh',mesh);component.set_skeletal_mesh_asset(mesh);cdo.set_editor_property('attack_clip',clip)
cdo.set_editor_property('recovery_time',max(0.,cycle-clip.get_play_length()))
LIB.set_metadata_tag(bp,'UniformRevision','V10 boot skin mask and matching ankle binding; V09 uniform retained')
LIB.set_metadata_tag(bp,'MotionRevision','V10 continuous recovery; preserved V06 idle/walk, hit window and attack cycle')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),clips={p:cdo.get_editor_property(p+'_clip').get_path_name() for p in ['idle','walk','attack']},
    attack_seconds=clip.get_play_length(),recovery_time=cdo.get_editor_property('recovery_time'),attack_cycle_seconds=cycle,
    contact_time=cdo.get_editor_property('contact_time'),contact_end=cdo.get_editor_property('contact_end'),
    preserved='V09 separate complete body and clothing assets, materials, skeleton, physics, V06 idle/walk, ground offset, movement and combat values')
record();print('SECURITY_V10_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
