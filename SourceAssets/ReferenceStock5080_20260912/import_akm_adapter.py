import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/ReferenceStock5080/AKM';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
t=u.AssetImportTask();t.filename=str(P/'AKM/SM_SkeletonStock.fbx');t.destination_path=D;t.destination_name='SM_SkeletonStock';t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);stock=u.load_asset(D+'/SM_SkeletonStock');assert stock
mat=u.load_asset(D+'/M_AKM_StockAdapter') or A.create_asset('M_AKM_StockAdapter',D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(.035,.044,.052);M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
for prop,val in [(u.MaterialProperty.MP_METALLIC,.85),(u.MaterialProperty.MP_ROUGHNESS,.55)]:
 n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.r=val;M.connect_material_property(n,'',prop)
M.recompile_material(mat);assert L.save_loaded_asset(mat,False)
stock.set_material(0,u.load_asset('/Game/Weapons/ReferenceStock5080/M_ReferenceStock5080'));stock.set_material(1,mat);assert L.save_loaded_asset(stock,False)
assert len(stock.static_materials)==2
r={'asset':stock.get_path_name(),'triangles':stock.get_num_triangles(0),'materials':2};(P/'import_akm_report.json').write_text(json.dumps(r,indent=2));u.log('REFERENCE_AKM_ADAPTER_PASS '+json.dumps(r))
