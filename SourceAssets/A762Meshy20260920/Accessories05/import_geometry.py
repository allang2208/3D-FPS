"""Install fitted common parts, finishes and independent sight bases, no PIE."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/A762/Accessories05';R='/Game/Weapons/A762/Integrated20260920'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text());src=json.loads((O/'sources.json').read_text())
receipt=json.loads((O/'geometry_import.json').read_text()) if (O/'geometry_import.json').exists() else {'meshes':{},'materials':{},'backups':{},'tested':False}
def record(): (O/'geometry_import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def clone(source,path):return u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(a,pin,b,target):
 if not L.connect_material_expressions(a,pin,b,target):raise RuntimeError('Cannot connect '+target)
old=u.load_asset(R+'/SK_A762_Manny');skeleton=old.skeleton
existing={str(m.material_slot_name):m.material_interface for m in old.materials}
for rev in ['Refinement01','Refinement02','Refinement03','Refinement04']:
 info=json.loads((O.parent/rev/'authoring.json').read_text())
 for name in info['materials']:existing[name]=u.load_asset('/Game/Weapons/A762/'+rev+'/Materials/'+name)
steel=existing['M_A762_FactoryStock_Metal04']
for name in ['SK_A762_Manny','SM_A762_RearSight','SM_A762_FrontSight']:
 if name not in receipt['backups']:
  b=clone(R+'/'+name,P+'/Before/'+name);save(b);receipt['backups'][name]=b.get_path_name();record()
def finish(key,index,original):
 overrides=O/'finish_overrides.json'
 if overrides.exists():
  path=json.loads(overrides.read_text()).get(key+':'+str(index))
  if path:
   result=u.load_asset(path)
   if not result:raise RuntimeError('Missing authored finish override '+path)
   return result
 # Some donor FBXs contain extra adapter slots consolidated by their UE import.
 source_slots=src['meshes'][key]['materials'];info=source_slots[min(index,len(source_slots)-1)];label=info['slot'].lower()
 # Optical, rubber, polymer and titanium slots keep their own identity.
 if any(w in label for w in ['reticle','glass','red_dot','rubber','polymer','titanium','index']):return original
 if key.endswith('reargrip') and 'collar' not in label:return original
 if key=='tactical_vertical' and index==0:return original
 if key=='drum' and 'fastener' not in label:return original
 if 'recess' in label or 'interior' in label:return original
 path=P+'/Materials/M_A762_'+key+'_'+str(index)
 if E.does_asset_exist(path):return u.load_asset(path)
 # Copy the original graph and instance parameters so UV0 normal/opacity and
 # emissive paths stay intact; alter only the coating response.
 if isinstance(original,u.MaterialInstanceConstant):
  base=original.get_base_material();m=clone(base.get_path_name(),path+'_Graph');result=clone(original.get_path_name(),path)
  params={k:{str(n):getattr(L,'get_material_instance_'+k+'_parameter_value')(original,n) for n in getattr(L,'get_'+k+'_parameter_names')(base)} for k in ['scalar','vector','texture','static_switch']}
  L.set_material_instance_parent(result,m)
  for k,values in params.items():
   for n,v in values.items():
    if v is not None:getattr(L,'set_material_instance_'+k+'_parameter_value')(result,n,v)
 else:m=clone(original.get_path_name(),path);result=m
 mask=None
 if key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','laser','flashlight']:
  metallic=L.get_material_property_input_node(m,u.MaterialProperty.MP_METALLIC)
  if metallic:
   mask=node(m,u.MaterialExpressionSmoothStep,const_min=.2,const_max=.5)
   link(metallic,L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_METALLIC),mask,'Value')
 bc=node(m,u.MaterialExpressionVectorParameter,parameter_name='A762CoatingColor',default_value=u.LinearColor(.021,.028,.039,1))
 rough=node(m,u.MaterialExpressionScalarParameter,parameter_name='A762CoatingRoughness',default_value=.36)
 metal=node(m,u.MaterialExpressionScalarParameter,parameter_name='A762CoatingMetallic',default_value=.86)
 for prop,new in [(u.MaterialProperty.MP_BASE_COLOR,bc),(u.MaterialProperty.MP_ROUGHNESS,rough),(u.MaterialProperty.MP_METALLIC,metal)]:
  previous=L.get_material_property_input_node(m,prop);pin=L.get_material_property_input_node_output_name(m,prop)
  output=new
  if mask and previous:
   output=node(m,u.MaterialExpressionLinearInterpolate);link(previous,pin,output,'A');link(new,'',output,'B');link(mask,'',output,'Alpha')
  if not L.connect_material_property(output,'',prop):raise RuntimeError('Cannot apply coating')
 L.recompile_material(m);save(m)
 if result!=m:L.update_material_instance(result);save(result)
 receipt['materials'][path]=original.get_path_name();record();return result

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in auth['meshes'].items():
  if key in receipt['meshes']:continue
  bindings={}
  for label,path in info['materials'].items():
   if path=='EXISTING_A762':mat=existing[label]
   elif path=='A762_STEEL':mat=steel
   else:
    i=int(label.rsplit('_',1)[1]);original=u.load_asset(path)
    if key=='laser' and i==0:original=u.load_asset('/Game/Weapons/TacticalDevices20260913/AKM/laser/M_AKM_laser_Body_OpticalV2') or original
    if key=='flashlight' and i==0:original=u.load_asset('/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/M_AKM_flashlight_Body_MetalTail') or original
    mat=finish(key,i,original)
   if not mat:raise RuntimeError('Unresolved material '+label)
   bindings[label]=mat
  # Fresh sight packages avoid UE static-mesh reimport retaining the old head's
  # material-section layout despite reset_to_fbx_on_material_conflict.
  name=info['name'];dest=P+'/Meshes'
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
  d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  t=u.AssetImportTask();t.filename=str(O/'Exports'/(name+'.fbx'));t.destination_path=dest;t.destination_name=name;t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(dest+'/'+name)
  if not mesh or not t.imported_object_paths:raise RuntimeError('Import failed '+name)
  slots=mesh.static_materials
  for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  for name,loc in info.get('sockets',{}).items():
   socket=mesh.find_socket(name)
   if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
   socket.set_editor_property('relative_location',u.Vector(*loc))
  save(mesh);receipt['meshes'][key]=mesh.get_path_name();record()
 if 'body' not in receipt['meshes']:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
  opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
  opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
  d=opt.skeletal_mesh_import_data
  d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  t=u.AssetImportTask();t.filename=str(O/'Exports/SK_A762_Manny.fbx');t.destination_path=R;t.destination_name='SK_A762_Manny';t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(R+'/SK_A762_Manny')
  if not t.imported_object_paths:raise RuntimeError('A762 body import failed')
  slots=mesh.materials
  for i,slot in enumerate(slots):slot.material_interface=existing[str(slot.material_slot_name)];slots[i]=slot
  mesh.set_editor_property('materials',slots);save(mesh);receipt['meshes']['body']=mesh.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['status']='imported_and_saved';record();u.log('A762_ACCESSORY_GEOMETRY_IMPORTED_AND_SAVED')
