"""Publish the complete unclothed body and repaired hand on the existing AI."""
import unreal as u,json,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];P=BASE/'V14BareBodyHand'
DEST='/Game/Monsters/NightWarden/V14BareBodyHand';ENTRY='/Game/Monsters/NightWarden/BP_NightWarden'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving the body and removing Warden clothing')
    if any(p.get_path_name().startswith('/Game/Monsters/NightWarden') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved Night Warden assets')
source=json.loads((P/'Records/authoring.json').read_text(encoding='utf-8'))
bp=u.load_asset(ENTRY)
skeleton=u.load_asset('/Game/Monsters/NightWarden/V07WaistStride/SK_NightWarden_WaistWrap_Skeleton')
material=u.load_asset('/Game/Monsters/NightWarden/V06Original/Materials/M_NW_Original')
clips={
    'idle':u.load_asset('/Game/Monsters/NightWarden/V08AIMovement/Animations/A_NightWarden_StandingIdle_V08'),
    'walk':u.load_asset('/Game/Monsters/NightWarden/V07WaistStride/CoupledLocomotionV18/Animations/A_NightWarden_CoupledStride_V18'),
    'attack':u.load_asset('/Game/Monsters/NightWarden/V09Melee/HundredEyeSweepV12/Animations/A_NightWarden_HundredEyeSweep_V12')}
if not all([bp,skeleton,material,*clips.values()]):raise RuntimeError('Preserved original body rig, material or motion asset missing')
backup=P/'Records/BP_NightWarden.before_v14.uasset'
if not backup.exists():shutil.copy2(BASE.parents[1]/'Content/Monsters/NightWarden/BP_NightWarden.uasset',backup)
cdo=u.get_default_object(bp.generated_class());component=cdo.get_editor_property('mesh')
oldmesh=component.get_skeletal_mesh_asset()
report={'stage':'importing_complete_body_hand_repair','complete':False,'saved':[],
    'previous_mesh':oldmesh.get_path_name(),'game_tested':False,'rendered':False}
def record():(P/'Records/ue_delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()
record();u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
d=options.skeletal_mesh_import_data;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=True;d.import_uniform_scale=1.
d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False)
d.set_editor_property('import_morph_targets',False)
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task=u.AssetImportTask();task.filename=source['fbx'];task.destination_path=DEST
task.destination_name='SK_NightWarden_BareBody_HandRepair_V14'
task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
mesh=u.load_asset(DEST+'/'+task.destination_name)
if not mesh:raise RuntimeError('Complete body import failed')
slots=list(mesh.materials)
for slot in slots:slot.material_interface=material
mesh.set_editor_property('materials',slots)
physics=oldmesh.get_editor_property('physics_asset')
if physics:mesh.set_editor_property('physics_asset',physics)
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
build=editor.get_lod_build_settings(mesh,0)
build.recompute_normals=False;build.recompute_tangents=False;build.use_full_precision_u_vs=True
editor.set_lod_build_settings(mesh,0,build)
E.set_metadata_tag(mesh,'NightWarden.Version','V14BareBodyHand')
E.set_metadata_tag(mesh,'NightWarden.Change','Complete source body restored; left finger thigh weights reassigned to original hand bones; no clothing')
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
save(mesh);save(skeleton)
bp.modify();cdo.modify();component.modify()
component.set_skeletal_mesh_asset(mesh);component.set_editor_property('override_materials',[])
component.set_editor_property('disable_cloth_simulation',True);component.set_editor_property('cloth_blend_weight',0.)
component.set_animation_mode(u.AnimationMode.ANIMATION_BLUEPRINT)
component.set_anim_instance_class(u.NightWardenAnimInstance)
component.set_editor_property('disable_post_process_blueprint',True)
component.set_editor_property('pause_anims',False);component.set_simulate_physics(False)
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
E.set_metadata_tag(bp,'NightWarden.Version','V14BareBodyHand')
E.set_metadata_tag(bp,'NightWarden.Stage','User rejected clothing: full bare body restored, left hand thigh contamination repaired; locomotion and Hundred-Eyed sweep retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
cdo=u.get_default_object(bp.generated_class())
yaw=cdo.get_editor_property('character_movement').get_editor_property('rotation_rate')
report.update(stage='bare_body_hand_repair_and_blueprint_saved',complete=True,
    mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),blueprint=bp.get_path_name(),
    animations={role:clip.get_path_name() for role,clip in clips.items()},
    clothing=False,cloth_simulation=False,repaired_left_hand_vertices=source['repaired_vertices'],
    complete_body_vertices=source['body_vertices'],body_animation_tracks_changed=False,
    source_walk_speed_cm_s=cdo.get_editor_property('source_walk_speed'),yaw_degrees_per_second=yaw.yaw,
    attack_contact_window=[cdo.get_editor_property('contact_start'),cdo.get_editor_property('contact_end')])
record();print('NW14_BARE_BODY_HAND_SAVED '+json.dumps(report),flush=True)
