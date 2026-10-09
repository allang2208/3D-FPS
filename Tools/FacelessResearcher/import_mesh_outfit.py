"""Background import into an independent security namespace; no game/preview tests."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
DEST='/Game/Monsters/FacelessResearcher'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is active; researcher import not started')

report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8')) if (ROOT/'ue_delivery.json').exists() else {'stage':'importing','saved':[],'runtime_tested':False}
def record():
    (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
def copy_asset(source,name):
    path=DEST+'/'+name
    asset=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Copy source unavailable: '+source)
    return asset
def import_one(file,folder,name,options=None):
    path=folder+'/'+name
    if LIB.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed '+path)
    return asset
def connect(source,output,dest,pin):
    names=MEL.get_material_expression_input_names(dest)
    normalize=lambda s:''.join(c.lower() for c in str(s) if c.isalnum())
    match=next((p for p in names if normalize(p)==normalize(pin)),None)
    if match is None:match=next((p for p in names if normalize(p).startswith(normalize(pin))),None)
    if match is None or not MEL.connect_material_expressions(source,output,dest,match):raise RuntimeError('Material pin '+pin+' in '+str(names))

skeleton=u.load_asset(DEST+'/SKEL_FacelessResearcher')
physics=u.load_asset(DEST+'/PA_FacelessResearcher')
materials={'Researcher_'+f:u.load_asset(DEST+'/Materials/M_FRS1_'+f) for f in ['Skin','Coat','Trousers','Trim','Hardware','Leather']}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.set_editor_property('import_morph_targets',True)
meshes={}
for role,name in [('outfit', 'SK_FacelessResearcher_V01')]:
    mesh=import_one(ROOT/'Delivery'/(name+'.fbx'),DEST,name,options)
    slots=list(mesh.materials)
    for slot in slots:
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        chosen=next((mat for key,mat in materials.items() if imported.startswith(key)),None)
        if not chosen:raise RuntimeError('Unknown material slot '+imported)
        slot.material_interface=chosen
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'Source','User reduced Meshy female GLB; independent fitted lab coat and trousers; original Nurse skeleton')
    LIB.set_metadata_tag(mesh,'Status','Saved V01 candidate; not rendered or gameplay tested')
    save(mesh);meshes[role]=mesh

print('RESEARCHER_MESH_SAVED '+'outfit',flush=True)
