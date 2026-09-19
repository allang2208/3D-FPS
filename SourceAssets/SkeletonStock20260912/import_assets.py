import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/SkeletonStock';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def task(file,name,opts,dest=D):
 t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=dest;t.options=opts;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);o=u.load_asset(dest+'/'+name);assert o,name;return o
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
stock=task(P/'SM_SkeletonStock.fbx','SM_SkeletonStock',opt)
textures={}
for name in ['BaseColor','Roughness','Metallic','Normal']:
 tex=task(P/('T_SkeletonStock_'+name+'.png'),'T_SkeletonStock_'+name,None)
 if name!='BaseColor':tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if name=='Normal' else u.TextureCompressionSettings.TC_MASKS)
 if name=='Normal':tex.set_editor_property('flip_green_channel',True)
 L.save_loaded_asset(tex,False);textures[name]=tex
mat=u.load_asset(D+'/M_SkeletonStock') or A.create_asset('M_SkeletonStock',D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
for name,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Metallic',u.MaterialProperty.MP_METALLIC),('Normal',u.MaterialProperty.MP_NORMAL)]:
 n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=textures[name]
 if name!='BaseColor':n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
 M.connect_material_property(n,'RGB' if name in ['BaseColor','Normal'] else 'R',prop)
M.recompile_material(mat);assert L.save_loaded_asset(mat,False);stock.set_material(0,mat);assert L.save_loaded_asset(stock,False)
# Only material partition changes. Reuse the current asset's exact skeleton and current material bindings.
old=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative');assert old
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=old.skeleton
akm=task(P/'SK_AKM_StockReady.fbx','SK_AKM_MannyNative',opt,'/Game/Weapons/AKMIntegration/SovietFab/StockV2');bindings={str(s.material_slot_name):s.material_interface for s in old.materials};slots=akm.materials
for i,s in enumerate(slots):
 key=str(s.material_slot_name);s.material_interface=bindings['M_AKM_Soviet_PBR'] if key=='M_AKM_FactoryStock' else bindings[key];slots[i]=s
akm.set_editor_property('materials',slots);assert L.save_loaded_asset(akm,False)
u.log('STOCK_SECTIONS '+json.dumps({'old':list(bindings),'new':[str(s.material_slot_name) for s in slots]}))
assert set(bindings).issubset({str(s.material_slot_name) for s in slots}), 'Existing material sections lost'
report={'stock':stock.get_path_name(),'triangles':stock.get_num_triangles(0),'material_slots':len(stock.static_materials),'bounds_min_cm':str(stock.get_bounding_box().min),'bounds_max_cm':str(stock.get_bounding_box().max),'akm':akm.get_path_name(),'skeleton':akm.skeleton.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in akm.materials}}
assert len(stock.static_materials)==1 and stock.get_num_triangles(0)<19000
size=stock.get_bounding_box().max-stock.get_bounding_box().min;assert 22.5<size.x<23.5 and 4<size.y<5.5 and 12<size.z<13.2,str(size)
(P/'import_report.json').write_text(json.dumps(report,indent=2));u.log('SKELETON_STOCK_IMPORT_PASS '+json.dumps(report))
