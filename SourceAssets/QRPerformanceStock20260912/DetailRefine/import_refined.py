"""Import the user-requested QR detail rebuild. No tests or asset audit."""
import unreal as u
from pathlib import Path
R=Path(__file__).parent;D='/Game/Weapons/QRPerformanceStock';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary

def surface(name,color,rough):
 path=D+'/Refined';mat=u.load_asset(path+'/'+name) or A.create_asset(name,path,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
 c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(*color,1);M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
 r=M.create_material_expression(mat,u.MaterialExpressionConstant);r.r=rough;M.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
 n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.r=0;M.connect_material_property(n,'',u.MaterialProperty.MP_METALLIC)
 M.recompile_material(mat);L.save_loaded_asset(mat,False);return mat

poly=surface('M_QR_RefinedPolymer',(.021,.024,.027),.58);rubber=surface('M_QR_RefinedRubber',(.008,.009,.010),.84)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
for key,path in [('M4','/Game/Weapons/M4InfimaV3/Body_001'),('AKM','/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR')]:
 body=u.load_asset(path)
 task=u.AssetImportTask();task.filename=str(R/key/'SM_QRPerformanceStock.fbx');task.destination_path=D+'/'+key;task.destination_name='SM_QRPerformanceStock';task.options=opt;task.automated=True;task.replace_existing=True;task.save=True;A.import_asset_tasks([task])
 mesh=u.load_asset(task.destination_path+'/SM_QRPerformanceStock')
 for index,slot in enumerate(mesh.static_materials):
  name=str(slot.material_slot_name);mesh.set_material(index,poly if 'Polymer' in name else rubber if 'Rubber' in name else body)
 L.save_loaded_asset(mesh,False);u.log('QR_REFINED_IMPORTED '+task.destination_path+'/SM_QRPerformanceStock')
u.log('QR refinement import completed. No validation or runtime tests executed.')
