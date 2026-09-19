import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/ReferenceStock5080';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def task(file,name,opts=None):
 t=u.AssetImportTask();t.filename=str(P/file);t.destination_path=D;t.destination_name=name;t.options=opts;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);a=u.load_asset(D+'/'+name);assert a;return a
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
stock=task('SM_SkeletonStock.fbx','SM_SkeletonStock',opt)
tex={}
for key in ['BaseColor','MetalRough','Normal']:
 t=task('T_ReferenceStock_'+key+'.png','T_ReferenceStock_'+key)
 if key!='BaseColor':t.srgb=False;t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS
 if key=='Normal':t.flip_green_channel=True
 assert L.save_loaded_asset(t,False);tex[key]=t
mat=u.load_asset(D+'/M_ReferenceStock5080') or A.create_asset('M_ReferenceStock5080',D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
for key in tex:
 n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=tex[key]
 if key!='BaseColor':n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
 if key=='MetalRough':M.connect_material_property(n,'G',u.MaterialProperty.MP_ROUGHNESS);M.connect_material_property(n,'B',u.MaterialProperty.MP_METALLIC)
 else:M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL if key=='Normal' else u.MaterialProperty.MP_BASE_COLOR)
M.recompile_material(mat);assert L.save_loaded_asset(mat,False);stock.set_material(0,mat);assert L.save_loaded_asset(stock,False)
size=stock.get_bounding_box().max-stock.get_bounding_box().min
report={'asset':stock.get_path_name(),'triangles':stock.get_num_triangles(0),'dimensions_cm':[size.x,size.y,size.z],'material_slots':len(stock.static_materials),'textures':{k:v.get_path_name() for k,v in tex.items()}}
assert 45000<report['triangles']<51000 and 22.5<size.x<23.5 and 2.5<size.y<3.2 and 10.7<size.z<11.8
(P/'import_game_report.json').write_text(json.dumps(report,indent=2));u.log('REFERENCE_STOCK_IMPORT_PASS '+json.dumps(report))
