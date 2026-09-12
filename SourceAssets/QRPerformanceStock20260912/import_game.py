"""Production import only. User performs game testing."""
import unreal as u
from pathlib import Path
R=Path(__file__).parent
D='/Game/Weapons/QRPerformanceStock'
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary

def texture(name,normal=False):
 t=u.AssetImportTask();t.filename=str(R/(name+'.png'));t.destination_path=D+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
 A.import_asset_tasks([t]);asset=u.load_asset(t.destination_path+'/'+name)
 asset.set_editor_property('srgb',not normal)
 if normal:
  asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
  asset.set_editor_property('flip_green_channel',True)
 L.save_loaded_asset(asset,False);return asset

base=texture('T_QRStock_BaseColor');normal=texture('T_QRStock_Normal',True)
def finish_material(name,color,rough,use_base):
 mat=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
 uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-700,0);uv.coordinate_index=1
 if use_base:
  c=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,-200);c.texture=base
  M.connect_material_expressions(uv,'',c,'UVs');M.connect_material_property(c,'RGB',u.MaterialProperty.MP_BASE_COLOR)
 else:
  c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-400,-200);c.constant=u.LinearColor(*color,1);M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
 n=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-400,100);n.texture=normal;n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL
 M.connect_material_expressions(uv,'',n,'UVs');M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)
 v=M.create_material_expression(mat,u.MaterialExpressionConstant,-250,300);v.r=rough;M.connect_material_property(v,'',u.MaterialProperty.MP_ROUGHNESS)
 z=M.create_material_expression(mat,u.MaterialExpressionConstant,-250,450);z.r=0;M.connect_material_property(z,'',u.MaterialProperty.MP_METALLIC)
 M.recompile_material(mat);L.save_loaded_asset(mat,False);return mat

poly=finish_material('M_QRStockPolymer',(.04,.042,.045),.57,True)
rubber=finish_material('M_QRStockRubber',(.008,.009,.010),.85,False)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
for key,path in [('M4','/Game/Weapons/M4InfimaV3/Body_001'),('AKM','/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR')]:
 body=u.load_asset(path)
 t=u.AssetImportTask();t.filename=str(R/key/'SM_QRPerformanceStock.fbx');t.destination_path=D+'/'+key;t.destination_name='SM_QRPerformanceStock';t.options=opt;t.automated=True;t.replace_existing=True;t.save=True
 A.import_asset_tasks([t]);stock=u.load_asset(t.destination_path+'/SM_QRPerformanceStock')
 for i,slot in enumerate(stock.static_materials):
  name=str(slot.material_slot_name);stock.set_material(i,poly if 'Polymer' in name else rubber if 'Rubber' in name else body)
 L.save_loaded_asset(stock,False)
 u.log('QR_STOCK_IMPORTED '+t.destination_path+'/SM_QRPerformanceStock')
u.log('QR stock production import completed; no game tests performed.')
