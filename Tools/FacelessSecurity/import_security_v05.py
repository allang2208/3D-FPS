"""Import V05 clothing/body/walk and save the existing guard entry."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V05')
DEST='/Game/Monsters/FacelessSecurity';LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; no asset changes made')
manifest=json.loads((ROOT/'motion_manifest.json').read_text(encoding='utf-8'))
bp=u.load_asset(DEST+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
old=cdo.get_editor_property('visual_mesh');skeleton=old.get_editor_property('skeleton');physics=old.get_editor_property('physics_asset')
component=cdo.get_editor_property('mesh');old_location=component.get_editor_property('relative_location')
report={'stage':'importing','previous_mesh':old.get_path_name(),'meshes':{},'saved':[],
    'previous_clips':{p:cdo.get_editor_property(p+'_clip').get_path_name() for p in ['idle','walk','attack']},
    'previous_mesh_location':[old_location.x,old_location.y,old_location.z],
    'game_tested':False,'rendered':False,'cpp_modified':False}

def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

record();u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role,name in [('outfit','SK_FacelessSecurity_V05'),('clothing','SK_FacelessSecurity_Clothing_V05'),('body','SK_FacelessSecurity_Body_V05')]:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
    data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(ROOT/'Delivery'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not mesh or not task.imported_object_paths:raise RuntimeError('Mesh import failed '+name)
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        family=str(slot.get_editor_property('imported_material_slot_name')).removeprefix('Security_').split('.')[0]
        material=u.load_asset(DEST+'/Materials/M_FS1_'+family)
        if not material:raise RuntimeError('Missing material '+family)
        slot.material_interface=material
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'SecurityGeometryRevision','V05 independent torso and sleeves; same-side arm weights; smooth crotch transition; intact hands and boots')
    report['meshes'][role]=mesh.get_path_name();save(mesh)

mesh=u.load_asset(report['meshes']['outfit']);entry=manifest['clips']['walk'];name='A_Security_Male_V05_walk';anim_path=DEST+'/Animations/V05'
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',manifest['fps'])
data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
data.set_editor_property('preserve_local_transform',True)
task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=anim_path;task.destination_name=name
task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory()
AT.import_asset_tasks([task]);clip=u.load_asset(anim_path+'/'+name)
if not clip or not task.imported_object_paths:raise RuntimeError('Walk import failed')
clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('rate_scale',entry['rate_scale'])
for prop in ['enable_root_motion','force_root_lock']:
    if clip.get_editor_property(prop):clip.set_editor_property(prop,False)
LIB.set_metadata_tag(clip,'SecurityMotionRevision','V05 Zombie Walk_B; 3 degree shoulder clearance; outsole support and fixed-length leg correction')
LIB.set_metadata_tag(clip,'SourceAction',entry['source_asset']);save(clip)

cdo.set_editor_property('visual_mesh',mesh);component.set_skeletal_mesh_asset(mesh);cdo.set_editor_property('walk_clip',clip)
# CharacterMovement deliberately floats the capsule 1.9-2.4 cm above a flat
# floor. The common monster component smooths stairs only; it does not cancel
# that gap. Apply the midpoint to this guard's mesh, preserving its capsule.
capsule=cdo.get_editor_property('capsule_component')
half_height=capsule.get_unscaled_capsule_half_height()
mesh_z=-half_height-manifest['mesh_floor_gap_compensation_cm']
component.set_editor_property('relative_location',u.Vector(old_location.x,old_location.y,mesh_z))
LIB.set_metadata_tag(bp,'UniformRevision','V05 separate overlapping sleeves; remove pelvis influence from arms')
LIB.set_metadata_tag(bp,'MotionRevision','V05 Walk_B; V03 idle and attack retained; capsule floor gap compensated')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),walk={'asset':clip.get_path_name(),'source':entry['source_asset'],
    'duration':clip.get_play_length(),'rate_scale':entry['rate_scale'],'speed_cm_s':cdo.get_editor_property('walk_speed')},
    mesh_location_cm=[old_location.x,old_location.y,mesh_z],capsule_half_height_cm=half_height,
    preserved='V03 idle and attack, combat timing, hands/fingers and boots, materials, skeleton, physics, capsule, AI, F6 entry',
    grounding=manifest['grounding'])
record();print('SECURITY_V05_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
