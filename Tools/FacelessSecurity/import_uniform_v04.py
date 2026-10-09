"""Import only the revised clothes/assembly and preserve the V03 motions."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V04')
DEST='/Game/Monsters/FacelessSecurity';LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; no asset changes made')
bp=u.load_asset(DEST+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
old=cdo.get_editor_property('visual_mesh');skeleton=old.get_editor_property('skeleton');physics=old.get_editor_property('physics_asset')
report={'stage':'importing','previous_mesh':old.get_path_name(),'meshes':{},'saved':[],'clips':{p:cdo.get_editor_property(p+'_clip').get_path_name() for p in ['idle','walk','attack']},'game_tested':False,'rendered':False,'cpp_modified':False}
def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved'].append(a.get_path_name());record()
record();u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role,name in [('outfit','SK_FacelessSecurity_V04'),('clothing','SK_FacelessSecurity_Clothing_V04')]:
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
    LIB.set_metadata_tag(mesh,'SecurityGeometryRevision','V04 torso-only belt; no side pouches; front-only collar panels; continuous garment and trim weights')
    report['meshes'][role]=mesh.get_path_name();save(mesh)
mesh=u.load_asset(report['meshes']['outfit']);cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
LIB.set_metadata_tag(bp,'UniformRevision','V04 waist protrusion and garment spike repair; V03 zombie motions retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),animation_and_combat_timing='Preserved existing V03 references and values',complete_body='Existing intact V03 body asset retained')
record();print('SECURITY_UNIFORM_V04_SAVED '+json.dumps(report),flush=True)
