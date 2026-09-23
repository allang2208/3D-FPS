"""Save the SVD modular mesh, fitted attachments, per-host finishes and animations."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/SVDDragunov20260922/Accessories20260923'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
src=json.loads((O/'sources.json').read_text());geo=json.loads((O/'authoring.json').read_text())
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {'materials':{},'meshes':{},'animations':{},'textures':{},'tests_run':False}
if any(p.get_path_name().startswith(P) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved SVD target packages; preserve state')
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
 if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+str(a))
def clone(original,path):
 a=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(original.get_path_name(),path)
 if not a:raise RuntimeError('Duplicate failed '+path)
 return a
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(value,target,pin):
 n,out=value if isinstance(value,tuple) else (value,'')
 if not L.connect_material_expressions(n,out,target,pin):raise RuntimeError('Cannot connect '+pin)
def output(m,value,prop):
 n,out=value if isinstance(value,tuple) else (value,'')
 if not L.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
def const(m,v):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1)) if isinstance(v,(tuple,list)) else node(m,u.MaterialExpressionConstant,r=v)
def previous(m,prop,default):
 p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
 return (n,L.get_material_property_input_node_output_name(m,p)) if n else const(m,default)
def custom(m,code,inputs,size,label):
 n=node(m,u.MaterialExpressionCustom,code=code,description=label,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for name in inputs:
  item=u.CustomInput();item.set_editor_property('input_name',name);pins.append(item)
 n.set_editor_property('inputs',pins)
 for name,value in inputs.items():link(value,n,name)
 return n
def graphcopy(original,path):
 result=clone(original,path)
 if isinstance(original,u.MaterialInstanceConstant):
  m=clone(original.get_base_material(),path+'_Graph');base=original.get_base_material()
  L.set_material_instance_parent(result,m)
  for kind in ['scalar','vector','texture','static_switch']:
   for name in getattr(L,'get_'+kind+'_parameter_names')(base):
    v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,name)
    if v is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,name,v)
 else:m=result
 return m,result
def finish(m,result):
 L.recompile_material(m);save(m)
 if result!=m:L.update_material_instance(result);save(result)
def texture(path,srgb):
 t=u.AssetImportTask();t.filename=str(path);t.destination_path=P+'/Textures';t.destination_name=path.stem;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);a=u.load_asset(P+'/Textures/'+path.stem)
 if not a or not t.imported_object_paths:raise RuntimeError('Texture import '+str(path))
 a.set_editor_property('srgb',srgb);a.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);save(a)
 receipt['textures'][path.stem]=a.get_path_name();record();return a
coatbc=texture(O/'Textures/T_SVD_AttachmentCoat_BaseColor.png',True)
coato=texture(O/'Textures/T_SVD_AttachmentCoat_ORM.png',False)
beads=(O.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text().replace('return float4(slope,beads,saturate(Wet));','float coverage=saturate(Wet*20.0); return float4(slope*coverage,beads*coverage,saturate(Wet));')
wetmap={}
def addwet(dry,inner_mask=False):
 path=P+'/Materials/'+dry.get_name()+'_Wet'
 if dry.get_path_name() in receipt.get('wet_materials',{}):
  wetmap[dry.get_path_name()]=u.load_asset(receipt['wet_materials'][dry.get_path_name()]);return
 m,result=graphcopy(dry,path)
 base=previous(m,'BASE_COLOR',(.027,.034,.041));rough=previous(m,'ROUGHNESS',.31);normal=previous(m,'NORMAL',(0,0,1))
 amount=node(m,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
 if inner_mask:amount=custom(m,'return saturate(Wet)*Region;',{'Wet':amount,'Region':(node(m,u.MaterialExpressionVertexColor),'R')},1,'Preserve dry optical interior')
 data=custom(m,beads,{'UV':node(m,u.MaterialExpressionTextureCoordinate),'Wet':amount},4,'SVD attachment rain')
 output(m,custom(m,'return Base*(1-Data.a*.065);',{'Base':base,'Data':data},3,'Water film'),'BASE_COLOR')
 output(m,custom(m,'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',{'Base':rough,'Data':data},1,'Wet roughness'),'ROUGHNESS')
 output(m,custom(m,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',{'Base':normal,'Data':data},3,'Water beads'),'NORMAL')
 finish(m,result);wetmap[dry.get_path_name()]=result;receipt.setdefault('wet_materials',{})[dry.get_path_name()]=result.get_path_name();record()
def coating(m):
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=2)
 bc=node(m,u.MaterialExpressionTextureSample,texture=coatbc,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 orm=node(m,u.MaterialExpressionTextureSample,texture=coato,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 link(uv,bc,'UVs');link(uv,orm,'UVs')
 return {'BASE_COLOR':(bc,'RGB'),'METALLIC':(orm,'B'),'ROUGHNESS':(orm,'G'),'SPECULAR':const(m,.5)}
def fitted_material(key,label,original,index):
 source_label=src['meshes'][key]['materials'][index]['slot'].lower() if key in src['meshes'] else ''
 if any(n in source_label for n in ['reticle','glass','red_dot']):return original
 path=P+'/Materials/M_'+label
 if path in receipt['materials']:
  result=u.load_asset(path);addwet(result,key in ['prism_scope_2x','lpvo_1_6x','lpvo_ring']);return result
 m,result=graphcopy(original,path)
 protected=any(n in source_label for n in ['polymer','rubber','recess','titanium']) or (key in ['vertical','canted'] and index==0)
 if not protected:
  coat=coating(m)
  # Modern optic bodies already have a semantic coating Lerp: retain its
  # source UV0, markings, metallic mask and inner-wall vertex exclusion.
  optical=key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']
  if optical:
   for prop,value in coat.items():
    prior=L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+prop))
    if not isinstance(prior,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Optic coating graph changed '+key+' '+prop)
    link(value,prior,'B')
  else:
   mixed=key in ['laser','flashlight','angled','tactical_vertical'] and index==0
   mask=None
   if mixed:
    metallic=previous(m,'METALLIC',.84)
    mask=node(m,u.MaterialExpressionSmoothStep,const_min=.20,const_max=.55);link(metallic,mask,'Value')
   for prop,value in coat.items():
    if mask:
     old=previous(m,prop,(.027,.034,.041) if prop=='BASE_COLOR' else .5)
     blend=node(m,u.MaterialExpressionLinearInterpolate);link(old,blend,'A');link(value,blend,'B');link(mask,blend,'Alpha');value=blend
    output(m,value,prop)
 E.set_metadata_tag(m,'WeaponFinishReference','SVD Surface20260923 / Receiver')
 E.set_metadata_tag(m,'WeaponFinishUV','SVD physical coating UV2, 0.05 m tile; source UV0 structure/normal retained')
 finish(m,result);receipt['materials'][path]={'source':original.get_path_name(),'saved':True,'coating':'protected material identity' if protected else 'SVD receiver'};record()
 addwet(result,key in ['prism_scope_2x','lpvo_1_6x','lpvo_ring']);return result

steelpath=P+'/Materials/M_SVD_InterfaceSteel';steel=u.load_asset(steelpath)
if not steel:
 steel=A.create_asset('M_SVD_InterfaceSteel',P+'/Materials',u.Material,u.MaterialFactoryNew())
 for prop,value in coating(steel).items():output(steel,value,prop)
 finish(steel,steel)
addwet(steel)
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in geo['meshes'].items():
  if key in receipt['meshes']:continue
  bindings={}
  for label,path in info['materials'].items():
   if path=='SVD_STEEL':bindings[label]=steel;continue
   original=u.load_asset(path)
   if not original:raise RuntimeError('Source material '+path)
   bindings[label]=fitted_material(key,label,original,info['source_slot_indices'][label])
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opts.import_materials=False;opts.import_textures=False;opts.import_animations=False;opts.set_editor_property('reset_to_fbx_on_material_conflict',True)
  d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  t=u.AssetImportTask();t.filename=str(O/'Exports'/(info['name']+'.fbx'));t.destination_path=P+'/Meshes';t.destination_name=info['name'];t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(P+'/Meshes/'+info['name'])
  if not mesh or not t.imported_object_paths:raise RuntimeError('Static import '+key)
  slots=mesh.static_materials
  for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  for name,loc in info['sockets'].items():
   socket=mesh.find_socket(name)
   if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
   socket.set_editor_property('relative_location',u.Vector(*loc))
  save(mesh);b=mesh.get_bounds();receipt['meshes'][key]={'asset':mesh.get_path_name(),'saved':True,'size_cm':[v*2 for v in b.box_extent.to_tuple()],'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'sockets':info['sockets']};record()
  u.log('SVD_ATTACH_MESH_SAVED '+key)
 sk=u.load_asset(src['svd']['skeleton'])
 if 'body' not in receipt['meshes']:
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opts.import_as_skeletal=True
  opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=sk;opts.set_editor_property('reset_to_fbx_on_material_conflict',True)
  d=opts.skeletal_mesh_import_data;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True);d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  t=u.AssetImportTask();t.filename=str(O/'Exports/SK_SVD_Modular.fbx');t.destination_path=P;t.destination_name='SK_SVD_Modular';t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(P+'/SK_SVD_Modular')
  if not mesh or not t.imported_object_paths:raise RuntimeError('SVD body import')
  slots=mesh.materials
  for i,slot in enumerate(slots):slot.material_interface=u.load_asset(geo['body_materials'][str(slot.material_slot_name)]);slots[i]=slot
  mesh.set_editor_property('materials',slots);save(mesh)
  receipt['meshes']['body']={'asset':mesh.get_path_name(),'saved':True,'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}};record()
 for key,info in json.loads((O/'animations.json').read_text()).items():
  if key in receipt['animations']:continue
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.skeleton=sk;opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
  d=opts.anim_sequence_import_data;d.set_editor_property('use_default_sample_rate',False);d.set_editor_property('custom_sample_rate',120)
  t=u.AssetImportTask();t.filename=str(O/'Animations'/(info['name']+'.fbx'));t.destination_path=P+'/Animations';t.destination_name=info['name'];t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False
  A.import_asset_tasks([t]);a=u.load_asset(P+'/Animations/'+info['name'])
  if not a or not t.imported_object_paths:raise RuntimeError('Animation import '+key)
  base=u.load_asset('/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'+key.split('/')[1])
  a.set_editor_property('bone_compression_settings',base.get_editor_property('bone_compression_settings'));save(a)
  receipt['animations'][key]={'asset':a.get_path_name(),'saved':True,'seconds':a.get_play_length()};record();u.log('SVD_ATTACH_ANIMATION_SAVED '+key)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
# Include already-finished dry/wet pairs when resuming a partial import.
for dry,path in receipt.get('wet_materials',{}).items():wetmap[dry]=u.load_asset(path)
da=u.load_asset(P+'/DA_SVD_AttachmentWetMaterials')
if not da:
 factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
 da=A.create_asset('DA_SVD_AttachmentWetMaterials',P,u.WeatherPresentationAssets,factory)
da.set_editor_property('wet_materials',wetmap);save(da)
receipt['status']='imported_and_saved';record();u.log('SVD_ATTACH_IMPORT_COMPLETE')
