"""Install receiver-matched coating; preserve UV0 normals and non-metal inserts."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/QBZ191/MetalCoat20260913';A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
sources=json.loads((O/'sources.json').read_text());bakes=json.loads((O/'coating.json').read_text());report={}
def save(x):
 if not E.save_loaded_asset(x,False):raise RuntimeError('Save failed '+x.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(a,out,b,pin):
 pins=[str(x) for x in L.get_material_expression_input_names(b)]
 if pin=='Input' and pin not in pins:pin=pins[0]
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Connection failed '+pin)
def output(n,out,prop):
 if not L.connect_material_property(n,out,prop):raise RuntimeError('Output failed '+str(prop))
def constant(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def duplicate(src,path):return u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(src,path)
def is_coated(key,index):
 ss=sources[key]['source_slots'];label=ss[index]['slot'].lower() if index<len(ss) else 'adaptermetal'
 if any(t in label for t in ['glass','reticle','red_dot','recess','index','titanium','rubber','grip_default']):return False
 if key in ['skeleton','qr_performance'] and 'polymer' in label:return False
 return True
def make_material(key,index,original,textures):
 name='M_QBZ191_Receiver_'+key+'_'+str(index);path=D+'/Materials/'+name
 if isinstance(original,u.MaterialInstanceConstant):
  base=original.get_base_material();m=duplicate(base.get_path_name(),path+'_Graph');result=duplicate(original.get_path_name(),path)
  vals={kind:{str(n):getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,n) for n in getattr(L,'get_'+kind+'_parameter_names')(base)} for kind in ['scalar','vector','texture','static_switch']}
  L.set_material_instance_parent(result,m)
  for kind,values in vals.items():
   for n,v in values.items():
    if v is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,n,v)
 else:m=duplicate(original.get_path_name(),path);result=m
 if E.get_metadata_tag(m,'QBZReceiverCoating')!='20260913':
  uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1);maps={}
  for kind,tex in textures.items():
   t=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);link(uv,'',t,'UVs');maps[kind]=t
  oldbc=L.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);bcout=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
  mask=None
  if oldbc:
   lum=node(m,u.MaterialExpressionDesaturation);link(oldbc,bcout,lum,'Input');link(constant(m,1),'',lum,'Fraction')
   white=node(m,u.MaterialExpressionSmoothStep,const_min=.55,const_max=.82);link(lum,'',white,'Value')
   mask=node(m,u.MaterialExpressionOneMinus);link(white,'',mask,'Input')
   if key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']:
    recess=node(m,u.MaterialExpressionSmoothStep,const_min=.004,const_max=.016);link(lum,'',recess,'Value')
    mul=node(m,u.MaterialExpressionMultiply);link(mask,'',mul,'A');link(recess,'',mul,'B');mask=mul
  for prop,tex,out in [(u.MaterialProperty.MP_BASE_COLOR,maps['BaseColor'],'RGB'),(u.MaterialProperty.MP_ROUGHNESS,maps['ORM'],'G'),(u.MaterialProperty.MP_METALLIC,maps['ORM'],'B')]:
   old=L.get_material_property_input_node(m,prop);oldout=L.get_material_property_input_node_output_name(m,prop)
   if mask and old:
    blend=node(m,u.MaterialExpressionLinearInterpolate);link(old,oldout,blend,'A');link(tex,out,blend,'B');link(mask,'',blend,'Alpha');output(blend,'',prop)
   else:output(tex,out,prop)
  # Original normal and cavity inputs remain connected to their original UV0.
  E.set_metadata_tag(m,'QBZReceiverCoating','20260913');L.recompile_material(m)
 save(m)
 if result!=m:L.update_material_instance(result);save(result)
 return result
for key,info in bakes.items():
 textures={}
 for kind,file in info['textures'].items():
  name=Path(file).stem;task=u.AssetImportTask();task.filename=file;task.destination_path=D+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(D+'/Textures/'+name)
  tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if kind=='BaseColor' else u.TextureCompressionSettings.TC_MASKS);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('lod_bias',0);save(tex);textures[kind]=tex
 bindings={};aliases={};changed=[]
 for index,slot in enumerate(sources[key]['slots']):
  old=u.load_asset(slot['material']);coated=is_coated(key,index);mat=make_material(key,index,old,textures) if coated else old;bindings[slot['slot']]=mat
  exported=info['export_slots'][index];aliases[exported]=slot['slot'];aliases[exported.replace('.','_')]=slot['slot']
  if coated:changed.append(slot['slot'])
 path=sources[key]['path'];task=u.AssetImportTask();task.filename=info['file'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;task.options=opt
 A.import_asset_tasks([task]);mesh=u.load_asset(path)
 slots=mesh.static_materials
 for index,slot in enumerate(slots):
  exported=str(slot.material_slot_name);name=exported if exported in bindings else aliases[exported]
  slot.material_interface=bindings[name];slot.material_slot_name=u.Name(name);slots[index]=slot
 mesh.set_editor_property('static_materials',slots)
 save(mesh);report[key]={'mesh':path,'coated_slots':changed,'bindings':{n:m.get_path_name() for n,m in bindings.items()}}
 (O/'import.json').write_text(json.dumps(report,indent=2));u.log('QBZ_RECEIVER_COATING_INSTALLED '+key)
u.log('QBZ_RECEIVER_COATING_IMPORT_COMPLETE')
