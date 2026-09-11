import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/OpticSteel';L=u.EditorAssetLibrary;E=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();slots=json.loads((O/'slots.json').read_text());geo=json.loads((O/'geometry.json').read_text());report={};mats={}
for k,entry in slots.items():
 for slot in entry['materials']:
  name=slot['slot']
  if not any(x in name for x in ('Body','Holosight')):continue
  source=slot['asset'];dest=P+'/M_AKM_'+name
  if source in mats:continue
  if L.does_asset_exist(dest):assert L.delete_asset(dest)
  m=L.duplicate_asset(source,dest)
  assert m
  props=[u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_ROUGHNESS]
  inputs=[(E.get_material_property_input_node(m,p),E.get_material_property_input_node_output_name(m,p)) for p in props];assert all(n for n,_ in inputs),(k,inputs)
  # Original metallic atlas identifies painted/rubber regions and metal hardware.
  sub=E.create_material_expression(m,u.MaterialExpressionSubtract);c=E.create_material_expression(m,u.MaterialExpressionConstant);c.set_editor_property('r',.2);E.connect_material_expressions(c,'',sub,'B');E.connect_material_expressions(inputs[1][0],inputs[1][1],sub,'A')
  mul=E.create_material_expression(m,u.MaterialExpressionMultiply);c=E.create_material_expression(m,u.MaterialExpressionConstant);c.set_editor_property('r',5.);E.connect_material_expressions(c,'',mul,'B');E.connect_material_expressions(sub,'',mul,'A')
  mask=E.create_material_expression(m,u.MaterialExpressionClamp);assert E.connect_material_expressions(mul,'',mask,'')
  uv=E.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('coordinate_index',1)
  for idx,kind in enumerate(('Base_color','Metallic','Roughness')):
   t=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+kind);assert t
   sample=E.create_material_expression(m,u.MaterialExpressionTextureSample);sample.texture=t
   if idx:sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
   E.connect_material_expressions(uv,'',sample,'UVs')
   blend=E.create_material_expression(m,u.MaterialExpressionLinearInterpolate)
   E.connect_material_expressions(inputs[idx][0],inputs[idx][1],blend,'A');E.connect_material_expressions(sample,'RGB' if idx==0 else 'R',blend,'B');E.connect_material_expressions(mask,'',blend,'Alpha');E.connect_material_property(blend,'',props[idx])
  E.recompile_material(m);assert L.save_loaded_asset(m,False);mats[source]=m
for k,entry in slots.items():
 f=O/geo[k]['fbx'];opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;opt.static_mesh_import_data.generate_lightmap_u_vs=False
 t=u.AssetImportTask();t.filename=str(f);t.destination_path=P;t.destination_name=f.stem;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True;A.import_asset_tasks([t]);m=u.load_asset(P+'/'+f.stem);assert m
 bindings={s['slot']:mats.get(s['asset']) or u.load_asset(s['asset']) for s in entry['materials']}
 for i,s in enumerate(m.static_materials):m.set_material(i,bindings[str(s.material_slot_name)])
 assert m.get_num_triangles(0)==entry['triangles'],(k,m.get_num_triangles(0),entry['triangles']);assert L.save_loaded_asset(m,False)
 report[k]={'mesh':m.get_path_name(),'triangles':m.get_num_triangles(0),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in m.static_materials}}
(O/'import.json').write_text(json.dumps(report,indent=2));u.log('AKM_OPTIC_STEEL_IMPORT_PASS')
