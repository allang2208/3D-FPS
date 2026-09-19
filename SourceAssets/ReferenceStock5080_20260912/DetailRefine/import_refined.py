import unreal as u,json
from pathlib import Path
R=Path(__file__).parent;D='/Game/Weapons/ReferenceStock5080/Refined';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def simple(name,color,rough):
 mat=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
 c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(*color,1);assert M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
 n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.r=rough;assert M.connect_material_property(n,'',u.MaterialProperty.MP_ROUGHNESS)
 M.recompile_material(mat);assert L.save_loaded_asset(mat,False);return mat
poly=simple('M_StockPolymer',(.021,.024,.027),.49);rubber=simple('M_StockRubber',(.008,.009,.010),.83)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
report={}
for key,path in [('m4','/Game/Weapons/M4InfimaV3/Body_001'),('akm','/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR')]:
 body=u.load_asset(path);assert body
 import os
 target=('/Game/Weapons/ReferenceStock5080'+('/AKM' if key=='akm' else '')) if os.environ.get('STOCK_PUBLISH')=='1' else D+'/'+key.upper()
 t=u.AssetImportTask();t.filename=str(R/key/'SM_SkeletonStock.fbx');t.destination_path=target;t.destination_name='SM_SkeletonStock';t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t])
 stock=u.load_asset(t.destination_path+'/SM_SkeletonStock');assert stock
 slots=[]
 for i,s in enumerate(stock.static_materials):
  name=str(s.material_slot_name);mat=poly if 'Polymer' in name else rubber if 'Rubber' in name else body;stock.set_material(i,mat);slots.append({'slot':name,'material':mat.get_path_name()})
 assert len(slots)==3 and sum('StockMetal' in s['slot'] for s in slots)==1
 assert L.save_loaded_asset(stock,False)
 size=stock.get_bounding_box().max-stock.get_bounding_box().min
 report[key]={'asset':stock.get_path_name(),'triangles':stock.get_num_triangles(0),'dimensions_cm':[size.x,size.y,size.z],'slots':slots,'body_material_identical':stock.get_material(stock.get_material_index('StockMetal'))==body}
 assert report[key]['body_material_identical'] and 22.8<size.x<23.3 and 10.9<size.z<11.5
(R/('publish_report.json' if os.environ.get('STOCK_PUBLISH')=='1' else 'import_report.json')).write_text(json.dumps(report,indent=2));u.log('REFINED_STOCK_IMPORT_PASS '+json.dumps(report))
