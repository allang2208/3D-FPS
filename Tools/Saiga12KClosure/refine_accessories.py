"""Fix Saiga-authored adapter faces and coat the original per-pixel metal areas."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018';D='/Game/Weapons/Saiga12K/Closure20261018'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;AT=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
R=json.loads((O/'Receipts/assets.json').read_text());audit={'adapters':{},'mixed_materials':{}}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
def custom(mat,name,code,inputs,kind):
 values=[]
 for x in inputs:
  item=u.CustomInput();item.set_editor_property('input_name',x);values.append(item)
 n=L.create_material_expression(mat,u.MaterialExpressionCustom);n.set_editor_property('description',name);n.set_editor_property('code',code);n.set_editor_property('output_type',kind);n.set_editor_property('inputs',values);return n
def coated(source):
 base=source.get_base_material();suffix=hashlib.sha256(base.get_path_name().encode()).hexdigest()[:12];name='M_Saiga12K_MixedCoat_'+suffix;path=D+'/Materials/'+name;ip=D+'/Materials/MI_Saiga12K_MixedCoat_'+suffix
 if path in audit['mixed_materials']:return u.load_asset(ip)
 mat=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(base.get_path_name(),path)
 if E.get_metadata_tag(mat,'SaigaMixedCoat')!='Closure20261018':
  bc=L.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);rough=L.get_material_property_input_node(mat,u.MaterialProperty.MP_ROUGHNESS);metal=L.get_material_property_input_node(mat,u.MaterialProperty.MP_METALLIC)
  if not isinstance(bc,u.MaterialExpressionCustom) or not isinstance(rough,u.MaterialExpressionCustom) or not metal:raise RuntimeError('Unsupported mixed material graph '+base.get_path_name())
  b=L.get_inputs_for_material_expression(mat,bc)[0];r=L.get_inputs_for_material_expression(mat,rough)[0]
  cp=L.create_material_expression(mat,u.MaterialExpressionVectorParameter);cp.set_editor_property('parameter_name','SaigaCoatColor');cp.set_editor_property('default_value',u.LinearColor(.029,.030,.032,1.))
  rp=L.create_material_expression(mat,u.MaterialExpressionScalarParameter);rp.set_editor_property('parameter_name','SaigaCoatRoughness');rp.set_editor_property('default_value',.36)
  c=custom(mat,'Clean Saiga metal only','return lerp(Base.rgb,Coat.rgb*(.9+.1*saturate(dot(Base.rgb,float3(.21,.72,.07))*3)),saturate(Metal.r));',['Base','Metal','Coat'],u.CustomMaterialOutputType.CMOT_FLOAT3)
  n=custom(mat,'Preserve polymer and authored roughness structure','return lerp(Base.r,saturate(Rough+(Base.r-.5)*.08),saturate(Metal.r));',['Base','Metal','Rough'],u.CustomMaterialOutputType.CMOT_FLOAT1)
  bo='RGB' if isinstance(b,u.MaterialExpressionTextureSample) else '';ro='RGB' if isinstance(r,u.MaterialExpressionTextureSample) else '';mo='R' if isinstance(metal,u.MaterialExpressionTextureSample) else ''
  for src,out,dst,pin in [(b,bo,c,'Base'),(metal,mo,c,'Metal'),(cp,'',c,'Coat'),(c,'',bc,'Base'),(r,ro,n,'Base'),(metal,mo,n,'Metal'),(rp,'',n,'Rough'),(n,'',rough,'Base')]:
   if not L.connect_material_expressions(src,out,dst,pin):raise RuntimeError('Failed mixed coat connection '+pin)
  L.recompile_material(mat);E.set_metadata_tag(mat,'SaigaMixedCoat','Closure20261018');save(mat)
 mi=u.load_asset(ip) if E.does_asset_exist(ip) else AT.create_asset('MI_Saiga12K_MixedCoat_'+suffix,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,mat);L.update_material_instance(mi);save(mi)
 audit['mixed_materials'][path]={'instance':mi.get_path_name(),'source':base.get_path_name(),'metal_color':[.029,.030,.032],'metal_roughness':.36,'source_metal_mask_normal_paint_and_single_wet_layer_preserved':True};return mi
for key in list(R['bindings']):
 if key in ('native','ext12'):continue
 mesh=u.load_asset(D+'/Attachments/SM_Saiga12K_'+key);slots=list(mesh.static_materials);dm,st=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,ts,_=Q.get_all_triangle_indices(dm,False);ts=list(LS.convert_triangle_list_to_array(ts));indices=[]
 for ti in range(len(ts)):
  mid,_=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
  if str(slots[mid].material_slot_name).startswith('Saiga12K_Interface'):indices.append(ti)
 if indices and E.get_metadata_tag(mesh,'SaigaAdapterWinding')!='Closure20261018':
  _,sel=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,indices,u.GeometryScriptMeshSelectionType.TRIANGLES);u.GeometryScript_Normals.flip_triangle_selection_normals(dm,sel,True,False)
  _,st=G.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
  if st!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Adapter write '+key)
  E.set_metadata_tag(mesh,'SaigaAdapterWinding','Closure20261018')
 if indices:audit['adapters'][key]={'triangles_flipped':len(indices),'borrowed_geometry_unchanged':True}
 for i,slot in enumerate(slots):
  if i==0 and (key in ('eoth_holographic','holographic') or key.startswith(('laser_','flashlight_'))):
   original=json.loads((O/'Reports/baseline.json').read_text())['assets'][key]['slots'][i]['material'];slot.material_interface=coated(u.load_asset(original));slots[i]=slot
 mesh.set_editor_property('static_materials',slots)
 for li in range(SM.get_lod_count(mesh)):
  bs=SM.get_lod_build_settings(mesh,li)
  original_mesh=u.load_asset(json.loads((O/'Reports/baseline.json').read_text())['assets'][key]['path'])
  wanted={'recompute_normals':False,'recompute_tangents':True,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True,'remove_degenerates':SM.get_lod_build_settings(original_mesh,li).remove_degenerates}
  if any(getattr(bs,n)!=v for n,v in wanted.items()):
   for n,v in wanted.items():setattr(bs,n,v)
   SM.set_lod_build_settings(mesh,li,bs)
 save(mesh);R['bindings'][key]={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials if s.material_interface}
 (O/'Receipts/assets.json').write_text(json.dumps(R,indent=2));(O/'Reports/accessories-repair.json').write_text(json.dumps(audit,indent=2))
print('ACCESSORY_WINDING_AND_MIXED_COAT_SAVED',len(audit['adapters']),len(audit['mixed_materials']))
