import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';lib=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
old=u.load_asset('/Game/Weapons/AKMIntegration/WalnutFab/SK_AKM_MannyNative');assert old
bindings={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('materials')}
textures={}
for kind in ['Base_color','Metallic','Roughness','Mixed_AO','Normal_OpenGL']:
 t=u.AssetImportTask();t.filename=str(O/'Source/ak47fbx_extracted/textures'/f'AK_{kind}.png');t.destination_path=P+'/Textures';t.destination_name='T_AKM_'+kind;t.automated=True;t.save=True;t.replace_existing=True;assets.import_asset_tasks([t]);tex=u.load_asset(t.imported_object_paths[0]);tex.set_editor_property('srgb',kind=='Base_color')
 if kind=='Normal_OpenGL':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
 elif kind!='Base_color':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
 assert u.EditorAssetLibrary.save_loaded_asset(tex,False);textures[kind]=tex
m=assets.create_asset('M_AKM_Soviet_PBR',P,u.Material,u.MaterialFactoryNew()) if not u.EditorAssetLibrary.does_asset_exist(P+'/M_AKM_Soviet_PBR') else u.load_asset(P+'/M_AKM_Soviet_PBR')
lib.delete_all_material_expressions(m);lib.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
props={'Base_color':u.MaterialProperty.MP_BASE_COLOR,'Metallic':u.MaterialProperty.MP_METALLIC,'Roughness':u.MaterialProperty.MP_ROUGHNESS,'Mixed_AO':u.MaterialProperty.MP_AMBIENT_OCCLUSION,'Normal_OpenGL':u.MaterialProperty.MP_NORMAL}
for kind,tex in textures.items():
 n=lib.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
 if kind=='Normal_OpenGL':n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 elif kind!='Base_color':n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
 assert lib.connect_material_property(n,'RGB' if kind in ['Base_color','Normal_OpenGL'] else 'R',props[kind])
lib.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m,False)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=old.skeleton
t=u.AssetImportTask();t.filename=str(O/'SK_AKM_MannyNative.fbx');t.destination_path=P;t.destination_name='SK_AKM_MannyNative';t.automated=True;t.replace_existing=True;t.save=True;t.options=opt;assets.import_asset_tasks([t]);mesh=u.load_asset(P+'/SK_AKM_MannyNative');assert mesh and mesh.skeleton==old.skeleton
slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):
 name=str(s.material_slot_name);s.material_interface=m if name=='M_AKM_Soviet_PBR' else bindings[name];slots[i]=s
mesh.set_editor_property('materials',slots);assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in slots],'normal_green_flipped':textures['Normal_OpenGL'].get_editor_property('flip_green_channel')},indent=2));u.log('SOVIET_IMPORT_PASS')
