"""Install PKM-specific geometry and semantic coating variants. No game tests."""
import unreal as u,json,sys
from pathlib import Path
O=Path(__file__).parent;R=O.parent;P='/Game/Weapons/PKMLowpoly20260922';D=P+'/Accessories14'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before importing PKM accessories')
auth=json.loads((O/'authoring.json').read_text());coat=json.loads((O/'coating.json').read_text())
receipt=json.loads((O/'geometry_import.json').read_text()) if (O/'geometry_import.json').exists() else {'meshes':{},'materials':{},'game_tested':False}
def record():(O/'geometry_import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def clone(a,p):
 m=u.load_asset(p) if E.does_asset_exist(p) else E.duplicate_asset(a.get_path_name(),p)
 if not m:raise RuntimeError('Cannot duplicate '+p)
 return m
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(a,pin,b,target):
 if target=='Input':
  names=list(map(str,L.get_material_expression_input_names(b)))
  if target not in names:target=names[0]
 if not L.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material connection failed '+target)
def output(n,pin,prop):
 if not L.connect_material_property(n,pin,prop):raise RuntimeError('Material output failed '+str(prop))
textures={}
for channel,file in coat['textures'].items():
 t=u.AssetImportTask();t.filename=file;t.destination_path=D+'/Textures';t.destination_name=Path(file).stem;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
 if not tex:raise RuntimeError(file)
 tex.srgb=channel=='BaseColor';tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
 tex.set_editor_property('address_x',u.TextureAddress.TA_MIRROR);tex.set_editor_property('address_y',u.TextureAddress.TA_MIRROR)
 if channel=='Normal':tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;tex.flip_green_channel=True
 elif channel=='ORM':tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
 save(tex);textures[channel]=tex
props={name:getattr(u.MaterialProperty,'MP_'+name) for name in ['BASE_COLOR','ROUGHNESS','METALLIC','SPECULAR']}
def samples(m):
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=2)
 tx={}
 for c in ['BaseColor','ORM']:
  tx[c]=node(m,u.MaterialExpressionTextureSample,texture=textures[c],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if c=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  link(uv,'',tx[c],'UVs')
 sp=node(m,u.MaterialExpressionConstant,r=.5)
 return {'BASE_COLOR':(tx['BaseColor'],'RGB'),'ROUGHNESS':(tx['ORM'],'G'),'METALLIC':(tx['ORM'],'B'),'SPECULAR':(sp,'')}
interface=u.load_asset(D+'/Materials/M_PKM14_Interface')
if not interface:
 interface=A.create_asset('M_PKM14_Interface',D+'/Materials',u.Material,u.MaterialFactoryNew())
 for k,(n,pin) in samples(interface).items():output(n,pin,props[k])
 uv=node(interface,u.MaterialExpressionTextureCoordinate,coordinate_index=2)
 nt=node(interface,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);link(uv,'',nt,'UVs');output(nt,'RGB',u.MaterialProperty.MP_NORMAL)
 L.recompile_material(interface);save(interface)

def finish(key,info):
 path=info['path'];label=info['source_slot'].lower();index=info['index']
 if path=='PKM_INTERFACE':return interface
 if key=='laser' and index==0:path='/Game/Weapons/TacticalDevices20260913/AKM/laser/M_AKM_laser_Body_OpticalV2'
 if key=='flashlight' and index==0:path='/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/M_AKM_flashlight_Body_MetalTail'
 original=u.load_asset(path)
 if not original:raise RuntimeError('Missing source material '+path)
 if any(word in label for word in ['reticle','glass','red_dot','rubber','polymer','titanium','recess','interior']):return original
 if key=='stable_antislip_reargrip' and index==0:return original
 dest=D+'/Materials/M_PKM14_'+key+'_'+str(index)
 if dest in receipt['materials']:
  ready=u.load_asset(dest)
  if ready:return ready
 if isinstance(original,u.MaterialInstanceConstant):
  base=original.get_base_material();m=clone(base,dest+'_Graph');result=clone(original,dest)
  params={k:{str(n):getattr(L,'get_material_instance_'+k+'_parameter_value')(original,n) for n in getattr(L,'get_'+k+'_parameter_names')(base)} for k in ['scalar','vector','texture','static_switch']}
  L.set_material_instance_parent(result,m)
  for k,values in params.items():
   for n,v in values.items():
    if v is not None:getattr(L,'set_material_instance_'+k+'_parameter_value')(result,n,v)
 else:m=clone(original,dest);result=m
 prior={k:(L.get_material_property_input_node(m,p),L.get_material_property_input_node_output_name(m,p)) for k,p in props.items()}
 coating=samples(m)
 # Earlier shared finish assets already encode metallic regions, white marks
 # and optical interiors in their outer lerp. Replace that coating input only.
 semantic=all(isinstance(prior[k][0],u.MaterialExpressionLinearInterpolate) for k in ['BASE_COLOR','ROUGHNESS','METALLIC'])
 if key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring'] and not semantic:
  raise RuntimeError('Optic semantic coating mask not found: '+key)
 if semantic:
  for k,(n,pin) in coating.items():
   if isinstance(prior[k][0],u.MaterialExpressionLinearInterpolate):link(n,pin,prior[k][0],'B')
   else:output(n,pin,props[k])
  mode='Reuse original coating alpha (material regions, markings, optical inner wall)'
 else:
  mask=None;bc,bcp=prior['BASE_COLOR']
  if key in ['laser','flashlight','tactical_vertical'] and index==0:
   metal,mp=prior['METALLIC']
   if not metal:raise RuntimeError('Mixed material needs original metallic region: '+key)
   mask=node(m,u.MaterialExpressionSmoothStep,const_min=.20,const_max=.50);link(metal,mp,mask,'Value')
  if bc:
   lum=node(m,u.MaterialExpressionDesaturation);link(bc,bcp,lum,'Input');c=node(m,u.MaterialExpressionConstant,r=1);link(c,'',lum,'Fraction')
   white=node(m,u.MaterialExpressionSmoothStep,const_min=.55,const_max=.82);link(lum,'',white,'Value');marks=node(m,u.MaterialExpressionOneMinus);link(white,'',marks,'Input')
   if mask:
    both=node(m,u.MaterialExpressionMultiply);link(mask,'',both,'A');link(marks,'',both,'B');mask=both
   else:mask=marks
  for k,(n,pin) in coating.items():
   old,oldpin=prior[k]
   if mask and old:
    blend=node(m,u.MaterialExpressionLinearInterpolate);link(old,oldpin,blend,'A');link(n,pin,blend,'B');link(mask,'',blend,'Alpha');output(blend,'',props[k])
   else:output(n,pin,props[k])
  mode='Explicit metal slots / original mixed-metal mask; retain white marks'
 E.set_metadata_tag(m,'WeaponFinishReference',coat['reference']);E.set_metadata_tag(m,'WeaponFinishUV','UV2 physical 5cm; donor UV0 normal and AO retained');E.set_metadata_tag(m,'PKM14_Regions',mode)
 L.recompile_material(m);save(m)
 if result!=m:L.update_material_instance(result);save(result)
 receipt['materials'][dest]={'source':path,'mask':mode,'saved':True};record();return result

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in auth['meshes'].items():
  if key in receipt['meshes']:continue
  bindings={name:finish(key,desc) for name,desc in info['materials'].items()}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
  d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  t=u.AssetImportTask();t.filename=str(O/'Exports'/(info['name']+'.fbx'));t.destination_path=D+'/Meshes';t.destination_name=info['name'];t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(t.destination_path+'/'+t.destination_name)
  if not mesh or not t.imported_object_paths:raise RuntimeError('Import failed '+key)
  slots=mesh.static_materials
  for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  for name,p in info.get('sockets',{}).items():
   socket=mesh.find_socket(name)
   if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
   socket.relative_location=u.Vector(*p)
  E.set_metadata_tag(mesh,'WeaponFinishReference',coat['reference']);E.set_metadata_tag(mesh,'PKM14_Source',info['source']);save(mesh)
  b=mesh.get_bounds();receipt['meshes'][key]={'asset':mesh.get_path_name(),'size_cm':list((b.box_extent*2).to_tuple()),'materials':{str(v.material_slot_name):v.material_interface.get_path_name() for v in mesh.static_materials},'saved':True};record()
 if 'body' not in receipt['meshes']:
  old=u.load_asset(P+'/SK_PKM_Manny');skeleton=old.skeleton
  sys.path.insert(0,str(R/'Belt08'));from material_binding import capture_bindings,bind_materials
  bindings=capture_bindings(old)
  for name,source in auth['factory_slots'].items():bindings[name]=bindings[source]
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
  d=opt.skeletal_mesh_import_data;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
  t=u.AssetImportTask();t.filename=str(O/'Exports/SK_PKM_Manny_Modular.fbx');t.destination_path=D;t.destination_name='SK_PKM_Manny_Modular';t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(D+'/SK_PKM_Manny_Modular')
  if not t.imported_object_paths or not mesh:raise RuntimeError('PKM modular mesh import failed')
  mapping=bind_materials(mesh,{},bindings);save(mesh)
  receipt['meshes']['body']={'asset':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'materials':mapping,'saved':True};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['status']='saved';record();print('PKM14_GEOMETRY_AND_MATERIALS_SAVED')
