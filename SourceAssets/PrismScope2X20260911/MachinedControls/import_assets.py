import unreal,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/PrismScope2XMachined';lib=unreal.MaterialEditingLibrary;assets=unreal.AssetToolsHelpers.get_asset_tools()
unreal.EditorAssetLibrary.make_directory(D)
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;o.import_as_skeletal=False;o.import_materials=False;o.import_textures=False;o.static_mesh_import_data.combine_meshes=True;o.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
t=unreal.AssetImportTask();t.filename=str(P/'SM_PrismScope2X.fbx');t.destination_path=D;t.destination_name='SM_PrismScope2X';t.automated=True;t.replace_existing=True;t.save=True;t.options=o;assets.import_asset_tasks([t]);mesh=unreal.load_asset(D+'/SM_PrismScope2X');assert mesh
textures={}
for name in ['BaseColor','Roughness','Metallic','Normal']:
 t=unreal.AssetImportTask();t.filename=str(P/('T_Scope2X_'+name+'.png'));t.destination_path=D;t.automated=True;t.replace_existing=True;t.save=True;assets.import_asset_tasks([t]);tex=unreal.load_asset(D+'/T_Scope2X_'+name);assert tex
 if name!='BaseColor':tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if name=='Normal' else unreal.TextureCompressionSettings.TC_MASKS)
 if name=='Normal':tex.set_editor_property('flip_green_channel',True)
 unreal.EditorAssetLibrary.save_loaded_asset(tex);textures[name]=tex
def material(name):
 m=unreal.load_asset(D+'/'+name) or assets.create_asset(name,D,unreal.Material,unreal.MaterialFactoryNew());lib.delete_all_material_expressions(m);return m
def constant(m,value,prop):
 if isinstance(value,tuple):n=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);n.constant=unreal.LinearColor(*value,1)
 else:n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=value
 lib.connect_material_property(n,'',prop)
body=material('M_Scope2X_Body')
for name,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS),('Metallic',unreal.MaterialProperty.MP_METALLIC),('Normal',unreal.MaterialProperty.MP_NORMAL)]:
 n=lib.create_material_expression(body,unreal.MaterialExpressionTextureSample);n.texture=textures[name]
 if name!='BaseColor':n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if name=='Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
 lib.connect_material_property(n,'RGB' if name in ['BaseColor','Normal'] else 'R',prop)
glass=material('M_Scope2X_Glass');glass.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);glass.set_editor_property('two_sided',True)
constant(glass,(.14,.25,.28),unreal.MaterialProperty.MP_BASE_COLOR);constant(glass,.07,unreal.MaterialProperty.MP_OPACITY);constant(glass,.08,unreal.MaterialProperty.MP_ROUGHNESS);constant(glass,.15,unreal.MaterialProperty.MP_METALLIC)
reticle=material('M_Scope2X_Reticle');reticle.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);reticle.set_editor_property('two_sided',True);constant(reticle,(40,.04,.006),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
for m in [body,glass,reticle]:lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
for i,s in enumerate(mesh.static_materials):
 name=str(s.material_slot_name);mesh.set_material(i,glass if 'Glass' in name else reticle if 'Reticle' in name else body)
assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
b=mesh.get_bounding_box();size=b.max-b.min;assert 12.8<size.x<13.2 and 3<size.y<6 and 5<size.z<9,str(size)
report={'asset':mesh.get_path_name(),'bounds_cm':[str(b.min),str(b.max)],'triangles':mesh.get_num_triangles(0),'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]}
(P/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('SCOPE2X_IMPORT_PASS '+json.dumps(report))
