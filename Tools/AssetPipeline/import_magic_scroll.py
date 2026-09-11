import unreal,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/MagicScroll5080_20260911/UE');D='/Game/Items/MagicScroll';tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
manifest=json.loads((P/'manifest.json').read_text());report={}
def imp(path,name,dest,options=None):
 t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=dest;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
 if options:t.options=options
 tools.import_asset_tasks([t]);return unreal.load_asset(dest+'/'+name)
for asset,data in manifest.items():
 dest=D+'/'+asset
 opts=unreal.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False;opts.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;opts.automated_import_should_detect_type=False
 opts.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.generate_lightmap_u_vs=True;opts.static_mesh_import_data.auto_generate_collision=False
 mesh=imp(P/(asset+'.fbx'),'SM_'+asset,dest,opts);assert isinstance(mesh,unreal.StaticMesh),asset
 materials={}
 for index,(name,v) in enumerate(data['materials'].items()):
  mn='M_'+asset+'_'+str(index);m=unreal.load_asset(dest+'/'+mn) or tools.create_asset(mn,dest,unreal.Material,unreal.MaterialFactoryNew())
  # UE 5.8 DeleteAll iterates the same collection it removes from; snapshot it first.
  for expression in list(lib.get_material_expressions(m)):lib.delete_material_expression(m,expression)
  assert lib.get_num_material_expressions(m)==0
  m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
  c=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.constant=unreal.LinearColor(*v['Base Color']);lib.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
  props={'Base Color':unreal.MaterialProperty.MP_BASE_COLOR,'Roughness':unreal.MaterialProperty.MP_ROUGHNESS,'Metallic':unreal.MaterialProperty.MP_METALLIC,'Normal':unreal.MaterialProperty.MP_NORMAL}
  for key,prop in props.items():
   spec=v.get('maps',{}).get(key)
   if spec:
    tex=imp(P/spec['file'],'T_'+asset+'_'+str(index)+'_'+key.replace(' ','_'),dest)
    tex.set_editor_property('srgb',key=='Base Color')
    if key=='Normal':
     tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
     tex.set_editor_property('flip_green_channel',True)
    elif key!='Base Color':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    unreal.EditorAssetLibrary.save_loaded_asset(tex)
    n=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample);n.texture=tex
    n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='Base Color' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    channel=spec['channel']
    if spec.get('factor',1)!=1:
     mul=lib.create_material_expression(m,unreal.MaterialExpressionMultiply);factor=lib.create_material_expression(m,unreal.MaterialExpressionConstant);factor.r=spec['factor'];lib.connect_material_expressions(factor,'',mul,'B');lib.connect_material_expressions(n,channel,mul,'A');n=mul;channel=''
    lib.connect_material_property(n,channel,prop)
   elif key in ['Roughness','Metallic']:
    n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=v[key];lib.connect_material_property(n,'',prop)
  if 'glass' in name.lower():
   m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING);m.set_editor_property('two_sided',True)
   m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
   thin=lib.create_material_expression(m,unreal.MaterialExpressionThinTranslucentMaterialOutput)
   tint=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);tint.constant=unreal.LinearColor(.96,.985,.99,1)
   inputs=lib.get_material_expression_input_names(thin)
   assert lib.connect_material_expressions(tint,'',thin,str(inputs[0]))
   # Thin transmission carries the glass; zero opacity removes the opaque diffuse coating.
   n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=0.;lib.connect_material_property(n,'',unreal.MaterialProperty.MP_OPACITY)
  lib.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m);materials[name]=m
 for i,slot in enumerate(mesh.static_materials):
  slot_name=str(slot.material_slot_name)
  name=next((n for n in materials if n.replace(' ','_').replace('.','_')==slot_name or n==slot_name),None)
  if name is None:raise RuntimeError('Unmapped material slot: '+asset+' '+slot_name+' '+str(list(materials)))
  mesh.set_material(i,materials[name])
 ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
 unreal.EditorAssetLibrary.save_loaded_asset(mesh);report[asset]={'mesh':mesh.get_path_name(),'slots':len(mesh.static_materials),'bounds':str(mesh.get_bounds())}
Path('D:/FPS3D/FPSGAME/Saved/MagicScrollImport.json').write_text(json.dumps(report,indent=2));unreal.log('MAGIC_SCROLL_IMPORT_PASS')
