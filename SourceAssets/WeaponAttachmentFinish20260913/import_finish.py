"""Install per-rifle finish variants on current attachment meshes only."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/AttachmentFinish20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
sources=json.loads((O/'sources.json').read_text());auth=json.loads((O/'authoring.json').read_text());profiles=json.loads((O/'profiles.json').read_text())
report={}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(a,out,b,pin):
 if pin=='Input':
  names=list(map(str,L.get_material_expression_input_names(b)))
  if pin not in names:pin=names[0]
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(n,out,p):
 if not L.connect_material_property(n,out,p):raise RuntimeError('Cannot connect '+str(p))
def constant(m,v):return node(m,u.MaterialExpressionConstant,r=v)
def mul(m,a,b):
 n=node(m,u.MaterialExpressionMultiply);link(a,'',n,'A');link(b,'',n,'B');return n
def clone(path,dest):return u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(path,dest)
def is_target(family,key,label):
 label=label.lower()
 if key=='drum':return 'fastener' in label
 if key=='prism':return 'saddle' in label or (family=='AKM' and 'adaptersteel' in label)
 if key in ['suppressor','brake','titanium_brake']:return 'riflemetal' in label
 if key in ['vertical','canted']:return 'body' in label
 return 'body' in label or 'holosight' in label
textures={'M4':{},'AKM':{}}
for kind,file in profiles['M4']['textures'].items():
 name=Path(file).stem;t=u.AssetImportTask();t.filename=file;t.destination_path=D+'/M4/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+name)
 # The active M4 receiver uses legacy Phong conversion with an sRGB shininess
 # texture. Preserve that existing response; do not silently alter the rifle.
 tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_DEFAULT;tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
 tex.set_editor_property('address_x',u.TextureAddress.TA_MIRROR);tex.set_editor_property('address_y',u.TextureAddress.TA_MIRROR)
 save(tex);textures['M4'][kind]=tex
for key,kind in [('BaseColor','Base_color'),('Metallic','Metallic'),('Roughness','Roughness')]:
 textures['AKM'][key]=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+kind)
 if not textures['AKM'][key]:raise RuntimeError(kind)
def make_material(info,index,original,author):
 family,key=info['family'],info['key'];path=D+'/'+family+'/Materials/M_'+family+'_'+key+'_'+str(index)
 if isinstance(original,u.MaterialInstanceConstant):
  base=original.get_base_material();m=clone(base.get_path_name(),path+'_Graph');result=clone(original.get_path_name(),path)
  values={kind:{str(n):getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,n) for n in getattr(L,'get_'+kind+'_parameter_names')(base)} for kind in ['scalar','vector','texture','static_switch']}
  L.set_material_instance_parent(result,m)
  for kind,params in values.items():
   for name,value in params.items():
    if value is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,name,value)
 else:m=clone(original.get_path_name(),path);result=m
 if E.get_metadata_tag(m,'WeaponReceiverFinish')!='20260913':
  uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=author['uv_index'])
  samples={}
  for kind,tex in textures[family].items():
   sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if family=='M4' or kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
   sample=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler);link(uv,'',sample,'UVs');samples[kind]=sample
  profile={}
  if family=='M4':
   fn=node(m,u.MaterialExpressionMaterialFunctionCall,material_function=u.load_asset('/InterchangeAssets/Functions/MF_PhongToMetalRoughness'))
   link(samples['BaseColor'],'RGB',fn,'DiffuseColor');link(samples['Roughness'],'R',fn,'Shininess')
   c=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.2,.2,.2,1));link(c,'',fn,'SpecularColor')
   c=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1));link(c,'',fn,'AmbientColor')
   profile={u.MaterialProperty.MP_BASE_COLOR:(fn,'BaseColor'),u.MaterialProperty.MP_METALLIC:(fn,'Metallic'),u.MaterialProperty.MP_ROUGHNESS:(fn,'Roughness'),u.MaterialProperty.MP_SPECULAR:(fn,'Specular')}
  else:
   profile={u.MaterialProperty.MP_BASE_COLOR:(samples['BaseColor'],'RGB'),u.MaterialProperty.MP_METALLIC:(samples['Metallic'],'R'),u.MaterialProperty.MP_ROUGHNESS:(samples['Roughness'],'R'),u.MaterialProperty.MP_SPECULAR:(constant(m,.5),'')}
  bc=L.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);bco=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
  mask=None
  if key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']:
   metallic=L.get_material_property_input_node(m,u.MaterialProperty.MP_METALLIC);mo=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_METALLIC)
   mask=node(m,u.MaterialExpressionSmoothStep,const_min=.2,const_max=.4);link(metallic,mo,mask,'Value')
   if author['interior_vertex_mask']:
    vc=node(m,u.MaterialExpressionVertexColor);region=node(m,u.MaterialExpressionMultiply);link(mask,'',region,'A');link(vc,'R',region,'B');mask=region
  if bc:
   lum=node(m,u.MaterialExpressionDesaturation);link(bc,bco,lum,'Input');link(constant(m,1),'',lum,'Fraction')
   white=node(m,u.MaterialExpressionSmoothStep,const_min=.55,const_max=.82);link(lum,'',white,'Value')
   marks=node(m,u.MaterialExpressionOneMinus);link(white,'',marks,'Input');mask=mul(m,mask,marks) if mask else marks
  for prop,(sample,out) in profile.items():
   old=L.get_material_property_input_node(m,prop);oldout=L.get_material_property_input_node_output_name(m,prop)
   if mask:
    if not old:
     value=.5 if prop==u.MaterialProperty.MP_SPECULAR else 0.
     old=constant(m,value);oldout=''
    blend=node(m,u.MaterialExpressionLinearInterpolate);link(old,oldout,blend,'A');link(sample,out,blend,'B');link(mask,'',blend,'Alpha');output(blend,'',prop)
   else:output(sample,out,prop)
  # Original UV0 structural normal/AO and opacity/emissive paths are retained.
  E.set_metadata_tag(m,'WeaponReceiverFinish','20260913');E.set_metadata_tag(m,'WeaponFinishReference',profiles[family]['reference_material'])
  L.recompile_material(m)
 save(m)
 if result!=m:L.update_material_instance(result);save(result)
 return result
for ident,author in auth.items():
 info=sources[ident];path=D+'/'+info['family']+'/Meshes/'+info['path'].rsplit('/',1)[1];bindings={};aliases={};changed=[]
 for i,slot in enumerate(info['slots']):
  original=u.load_asset(slot['material']);target=is_target(info['family'],info['key'],slot['slot'])
  bindings[slot['slot']]=make_material(info,i,original,author) if target else original
  if target:changed.append(slot['slot'])
  exported=author['export_slots'][i];aliases[exported]=slot['slot'];aliases[exported.replace('.','_')]=slot['slot']
 t=u.AssetImportTask();t.filename=author['file'];t.destination_path=path.rsplit('/',1)[0];t.destination_name=path.rsplit('/',1)[1];t.automated=True;t.replace_existing=True;t.save=False
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opt
 A.import_asset_tasks([t]);mesh=u.load_asset(path);slots=mesh.static_materials
 for i,slot in enumerate(slots):
  exported=str(slot.material_slot_name);label=exported if exported in bindings else aliases[exported]
  slot.material_interface=bindings[label];slot.material_slot_name=u.Name(label);slots[i]=slot
 mesh.set_editor_property('static_materials',slots)
 E.set_metadata_tag(mesh,'WeaponFinishReference',profiles[info['family']]['reference_material']);E.set_metadata_tag(mesh,'WeaponFinishUV',str(author['uv_index']))
 save(mesh)
 report[ident]={'mesh':path,'previous_mesh':info['path'],'reference':profiles[info['family']]['reference_material'],'changed_slots':changed,'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'triangles':mesh.get_num_triangles(0),'uv_index':author['uv_index']}
 (O/'installed.json').write_text(json.dumps(report,indent=2));u.log('WEAPON_FINISH_INSTALLED '+ident)
u.log('WEAPON_FINISH_IMPORT_COMPLETE')
