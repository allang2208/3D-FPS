import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/PhantomRearGrip'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
collar=u.load_asset(D+'/M_PhantomRearGrip_Collar') or A.create_asset('M_PhantomRearGrip_Collar',D,u.Material,u.MaterialFactoryNew())
M.delete_all_material_expressions(collar)
c=M.create_material_expression(collar,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(.014,.017,.019,1);M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
for prop,value in [(u.MaterialProperty.MP_METALLIC,.35),(u.MaterialProperty.MP_ROUGHNESS,.48)]:
    n=M.create_material_expression(collar,u.MaterialExpressionConstant);n.r=value;M.connect_material_property(n,'',prop)
M.recompile_material(collar);E.save_loaded_asset(collar,False)
result={}
for family in ['M4','AKM','QBZ191']:
    path=D+'/'+family+'/ReceiverFit/SM_PhantomRearGrip';old=u.load_asset(D+'/'+family+'/SM_PhantomRearGrip')
    # Keep any per-weapon finish that has been applied by other project work.
    base=old.get_material(0) if old else u.load_asset(D+'/M_PhantomRearGrip')
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_as_skeletal=False;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(P/family/'SM_PhantomRearGrip.fbx');task.destination_path=D+'/'+family+'/ReceiverFit';task.destination_name='SM_PhantomRearGrip'
    task.options=opts;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed: '+family)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,collar if 'Collar' in str(slot.material_slot_name) else base)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed: '+family)
    result[family]=mesh.get_path_name()
(P/'import_results.json').write_text(json.dumps(result,indent=2));u.log('PHANTOM_RECEIVER_FIT_IMPORTED')
