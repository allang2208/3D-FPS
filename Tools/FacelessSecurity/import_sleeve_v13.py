"""Import one sleeve revision asset per bridge batch, then bind the existing BP."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V13')
DEST='/Game/Monsters/FacelessSecurity';LIB=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; no assets modified')
bp=u.load_asset(DEST+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
old=cdo.get_editor_property('visual_mesh')
if old.get_name() not in ['SK_FacelessSecurity_V11','SK_FacelessSecurity_V13']:raise RuntimeError('Security mesh changed outside this revision')
skeleton=old.get_editor_property('skeleton');physics=old.get_editor_property('physics_asset')
role=globals()['ROLE']
path=ROOT/'ue_delivery.json'
report=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
    'revision':'V13','previous_mesh':old.get_path_name(),'meshes':{},'saved':[],
    'game_tested':False,'rendered':False,'cpp_modified':False}
def record():path.write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
    record()
if role in ['outfit','clothing']:
    name='SK_FacelessSecurity_'+('Clothing_' if role=='clothing' else '')+'V13'
    if LIB.does_asset_exist(DEST+'/'+name):raise RuntimeError('V13 asset exists; inspect saved receipt before repeating this import')
    report['stage']='importing_'+role;record()
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
    opt.skeleton=skeleton;opt.create_physics_asset=False;opt.physics_asset=physics
    data=opt.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(ROOT/'Delivery'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False;task.options=opt;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not mesh or not task.imported_object_paths:raise RuntimeError('Import did not create '+name)
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        family=str(slot.get_editor_property('imported_material_slot_name')).removeprefix('Security_').split('.')[0]
        material=u.load_asset(DEST+'/Materials/M_FS1_'+family)
        if not material:raise RuntimeError('Missing material '+family)
        slot.material_interface=material
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'SecurityGeometryRevision','V13 long-sleeve skin coverage; forearm-bound cuff and wrist overlap; V11 sewn collar retained')
    report['meshes'][role]=mesh.get_path_name();save(mesh);report['stage']='saved_'+role;record()
elif role=='apply':
    def refs():
        result={p:cdo.get_editor_property(p+'_clip').get_path_name() for p in ['idle','walk','attack']}
        for group,names in [('combat',['hit_clip','dizzy_clip']),('knockdown',['fall_clip','get_up_clip','prone_get_up_clip'])]:
            obj=cdo.get_editor_property(group)
            for n in names:
                a=obj.get_editor_property(n);result[group+'.'+n]=a.get_path_name() if a else None
        return result
    before=refs()
    for required in ['outfit','clothing']:
        if not u.load_asset(report['meshes'][required]):raise RuntimeError('Missing imported '+required)
    mesh=u.load_asset(report['meshes']['outfit'])
    cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
    LIB.set_metadata_tag(bp,'UniformRevision','V13 covered forearm visibility and wrist cuff binding; V11 neck, cap and V12 states preserved')
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    after=refs()
    if before!=after:raise RuntimeError('Unexpected animation reference change')
    save(bp)
    report.update(stage='saved',blueprint=bp.get_path_name(),preserved_clips=after,
                  complete_body='Unmodified complete body retained in authoring and existing V09 asset',
                  cap='Existing independent V11 physical cap component retained',
                  pose_diagnosis='SourceAssets/FacelessSecurity20261008/V13/Diagnosis/sleeve_overlap.json')
    record()
else:raise RuntimeError('Unknown role '+str(role))
print('SECURITY_SLEEVE_V13 '+json.dumps(report),flush=True)
