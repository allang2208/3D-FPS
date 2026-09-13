"""Install only the accepted balanced grip and per-rifle phantom finish variants."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent/'HunyuanV3'; D='/Game/Weapons/TacticalDevices20260913/HunyuanV3'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
# Reuse the current receiver graph helpers, without executing that job's imports.
source=(O.parent.parent/'WeaponAttachmentFinish20260913/import_finish.py').read_text()
exec(source[source.index('def save('):source.index('def is_target(')])
auth=json.loads((O/'authoring.json').read_text());bakes=json.loads((O/'coating.json').read_text())
profiles=json.loads((O.parent.parent/'WeaponAttachmentFinish20260913/profiles.json').read_text())
refs={k:v['reference_material'] for k,v in profiles.items()}
refs['QBZ191']='/Game/Weapons/QBZ191/Attachments20260913/Materials/M_QBZ191_Unified_M_QBZ191_Wear_Body_metal'

def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a

def texture(file, color):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=D+'/Textures';t.destination_name=Path(file).stem;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);a=load(t.destination_path+'/'+t.destination_name)
 a.srgb=color;a.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS
 a.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;save(a);return a

source_maps={k:(texture(O/k/('T_'+k+'_BaseColor.png'),True),texture(O/k/('T_'+k+'_MetalRough.png'),False)) for k in ['laser','flashlight'] if (O/k/('T_'+k+'_BaseColor.png')).exists()}
metaltex={
 'M4':{k:load('/Game/Weapons/AttachmentFinish20260913/M4/Textures/T_M4_Receiver_'+k) for k in ['BaseColor','Roughness']},
 'AKM':{k:load('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+suffix) for k,suffix in [('BaseColor','Base_color'),('Metallic','Metallic'),('Roughness','Roughness')]}}

def sample(m,tex,uv,color):
 n=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if color else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 link(uv,'',n,'UVs');return n

def material(key,info,collar):
 family=info['family'];kind=info['kind'];path=D+'/'+family+'/'+kind+'/M_'+key+('_Collar' if collar else '_Body')
 existing=u.load_asset(path)
 if existing and E.get_metadata_tag(existing,'TacticalFinishReady')=='1':return existing
 if kind=='phantom' and not collar:
  m=clone(phantom.get_path_name(),path)
 else:
  m=u.load_asset(path) or A.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
  if not collar:
   uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
   c=sample(m,base,uv,True);r=sample(m,mr,uv,False)
   output(c,'RGB',u.MaterialProperty.MP_BASE_COLOR);output(r,'G',u.MaterialProperty.MP_ROUGHNESS)
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
 if family=='QBZ191':
  maps={k:texture(v,k=='BaseColor') for k,v in bakes[key]['textures'].items()}
  c=sample(m,maps['BaseColor'],uv,True);r=sample(m,maps['ORM'],uv,False)
  coat={u.MaterialProperty.MP_BASE_COLOR:(c,'RGB'),u.MaterialProperty.MP_ROUGHNESS:(r,'G'),u.MaterialProperty.MP_METALLIC:(r,'B')}
 elif family=='M4':
  c=sample(m,metaltex[family]['BaseColor'],uv,True);r=sample(m,metaltex[family]['Roughness'],uv,True)
  fn=node(m,u.MaterialExpressionMaterialFunctionCall,material_function=load('/InterchangeAssets/Functions/MF_PhongToMetalRoughness'))
  link(c,'RGB',fn,'DiffuseColor');link(r,'R',fn,'Shininess')
  link(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.2,.2,.2,1)),'',fn,'SpecularColor')
  link(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1)),'',fn,'AmbientColor')
  coat={p:(fn,o) for p,o in [(u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(u.MaterialProperty.MP_METALLIC,'Metallic'),(u.MaterialProperty.MP_SPECULAR,'Specular')]}
 else:
  samples={}
  for k,t in metaltex[family].items():
   sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if k=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
   n=node(m,u.MaterialExpressionTextureSample,texture=t,sampler_type=sampler);link(uv,'',n,'UVs');samples[k]=n
  coat={p:(samples[k],out) for p,k,out in [(u.MaterialProperty.MP_BASE_COLOR,'BaseColor','RGB'),(u.MaterialProperty.MP_ROUGHNESS,'Roughness','R'),(u.MaterialProperty.MP_METALLIC,'Metallic','R')]}
 mask=node(m,u.MaterialExpressionVertexColor)
 for prop,(n,out) in coat.items():
  if collar:output(n,out,prop);continue
  old=L.get_material_property_input_node(m,prop);oldout=L.get_material_property_input_node_output_name(m,prop)
  if prop==u.MaterialProperty.MP_METALLIC:old=constant(m,0);oldout=''
  if not old:old=constant(m,.5 if prop==u.MaterialProperty.MP_SPECULAR else 0);oldout=''
  blend=node(m,u.MaterialExpressionLinearInterpolate);link(old,oldout,blend,'A');link(n,out,blend,'B');link(mask,'R',blend,'Alpha');output(blend,'',prop)
 E.set_metadata_tag(m,'WeaponFinishReference',refs[family]);E.set_metadata_tag(m,'WeaponFinishRegion','metal frame/collar; polymer preserved on UV0')
 E.set_metadata_tag(m,'TacticalFinishReady','1');L.recompile_material(m);save(m);return m

normaltex=texture(O/'flashlight/T_flashlight_Normal.png',False)
normaltex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;normaltex.srgb=False;save(normaltex)
report={}
for key,info in auth.items():
 base,mr=source_maps[info['kind']]
 body=material(key,info,False);collar=material(key,info,True)
 n=node(body,u.MaterialExpressionTextureSample,texture=normaltex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);uv=node(body,u.MaterialExpressionTextureCoordinate,coordinate_index=0);link(uv,'',n,'UVs');output(n,'RGB',u.MaterialProperty.MP_NORMAL);L.recompile_material(body);save(body)
 path=D+'/'+info['family']+'/'+info['kind']+'/'+info['mesh_name']
 t=u.AssetImportTask();t.filename=bakes[key]['file'] if key in bakes else info['fbx'];t.destination_path=path.rsplit('/',1)[0];t.destination_name=info['mesh_name'];t.automated=True;t.replace_existing=True;t.save=False
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opt
 A.import_asset_tasks([t]);mesh=load(path);slots=mesh.static_materials
 for i,slot in enumerate(slots):
  slot.material_interface=collar if 'Collar' in str(slot.material_slot_name) else body;slots[i]=slot
 mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'WeaponFinishReference',refs[info['family']]);E.set_metadata_tag(mesh,'WeaponFinishUV','1');save(mesh)
 report[key]={'mesh':path,'reference':refs[info['family']],'coating_uv':1,'polymer_uv':0,'sockets':{str(x.socket_name):str(x.relative_location) for x in [mesh.find_socket('Emitter'),mesh.find_socket('AimGuide')] if x},'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
 (O/'installed.json').write_text(json.dumps(report,indent=2));u.log('TACTICAL_DEVICE_INSTALLED '+key)
u.log('TACTICAL_DEVICE_COMPLETE')
