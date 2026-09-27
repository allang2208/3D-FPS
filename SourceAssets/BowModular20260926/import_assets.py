"""Import and save actual split meshes/materials; no gameplay or capture."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).parent;DEST='/Game/Weapons/DarkBow20260925/ModularV13'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'sources':{},'runtime_tested':False}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved packages '+str(dirty))
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    r['saved'][a.get_name()]=a.get_path_name();receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
def fresh(name):
    if name not in r['saved'] and E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Unowned asset '+name)
def scalar(m,v):
    n=L.create_material_expression(m,u.MaterialExpressionConstant);n.r=v;return n
for name,rgb,rough in [('M_Bow_GripLinen',(.105,.068,.038),.84),('M_Bow_FastString',(.17,.115,.06),.78)]:
    if name in r['saved']:continue
    fresh(name);m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*rgb,1)
    L.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
    L.connect_material_property(scalar(m,rough),'',u.MaterialProperty.MP_ROUGHNESS)
    L.connect_material_property(scalar(m,0),'',u.MaterialProperty.MP_METALLIC);L.recompile_material(m);save(m)
materials={
 'standardSurface2':u.load_asset('/Game/Weapons/DarkBow20260925/WoodLongbow20260925/M_WoodLongbow_PBR'),
 'ArrowRestWood':u.load_asset('/Game/Weapons/DarkBow20260925/WoodSightV12/M_Bow_CarvedWood'),
 'ArrowRestLeather':u.load_asset('/Game/Weapons/DarkBow20260925/WoodSightV12/M_Bow_WaxedLinen')}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in json.loads((P/'authoring.json').read_text())['assets']:
    source=P/'Export'/(name+'.fbx');sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if name in r['saved'] and r['sources'].get(name)==sha:continue
    fresh(name);opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.static_mesh_import_data.combine_meshes=True
    opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=name in r['saved'];task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Mesh import missing '+name)
    slots=list(asset.static_materials)
    for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
    asset.static_materials=slots;r['sources'][name]=sha;save(asset)
print('BOW_MODULAR_ASSETS_SAVED',json.dumps(r))
