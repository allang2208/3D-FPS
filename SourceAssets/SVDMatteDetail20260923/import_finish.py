"""SVD-only matte coating and matched wet partners, preserving source regions."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/SVDDragunov20260922';DEST=P+'/MatteDetail20260923'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
project=Path(u.Paths.project_dir()).resolve()
source=json.loads((O/'material_inputs.json').read_text())
attachment=json.loads((O.parent/'SVDAttachments20260923/import_receipt.json').read_text())
tablepath=P+'/Accessories20260923/DA_SVD_AttachmentWetMaterials'
receipt={'materials':{},'textures':{},'meshes':[],'game_tested':False}
record_path=O/'finish_receipt.json'
if record_path.exists():receipt=json.loads(record_path.read_text())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active PIE; preserve assets')
targets={x['asset'].split('.')[0] for x in source['meshes']}|{tablepath}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in targets or p.startswith(DEST+'/') for p in dirty):raise RuntimeError('Unsaved SVD finish target')

def record():record_path.write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(a):
 package=a.get_path_name().split('.')[0];f=project/'Content'/(package.removeprefix('/Game/')+'.uasset')
 dest=O/'Before'/f.relative_to(project/'Content')
 if f.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(src,target,pin):
 n,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(n,out,target,pin):raise RuntimeError('Cannot connect '+pin)
def output(src,name):
 n,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Cannot output '+name)
def constant(m,v):
 return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1)) if isinstance(v,tuple) else node(m,u.MaterialExpressionConstant,r=v)
def previous(m,name,default):
 prop=getattr(u.MaterialProperty,'MP_'+name);n=L.get_material_property_input_node(m,prop)
 return (n,L.get_material_property_input_node_output_name(m,prop)) if n else constant(m,default)
def custom(m,code,inputs,size,label):
 n=node(m,u.MaterialExpressionCustom,code=code,description=label,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,value in inputs.items():link(value,n,name)
 return n
def clone(a,path):
 result=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(a.get_path_name(),path)
 if not result:raise RuntimeError('Copy failed '+path)
 return result
def flatten_instance(original,base,path):
 if not isinstance(original,u.MaterialInstanceConstant):return base
 result=clone(original,path);L.set_material_instance_parent(result,base)
 for kind in ['scalar','vector','texture','static_switch']:
  for name in getattr(L,'get_'+kind+'_parameter_names')(original.get_base_material()):
   value=getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,name)
   if value is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,name,value)
 L.update_material_instance(result);save(result);return result
def finish(m):
 L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 errors=[str(v) for v in L.recompile_material(m)]
 if errors:raise RuntimeError('Material compile failed '+m.get_path_name()+str(errors))
 save(m)
def vertex(m,cls):
 n=node(m,u.MaterialExpressionVertexInterpolator);link(node(m,cls),n,'VS');return n

textures={}
for kind in ['BaseColor','ORM','Normal']:
 name='T_SVD_Magazine_'+kind;path=DEST+'/Textures/'+name
 if name in receipt['textures']:textures[kind]=u.load_asset(path);continue
 task=u.AssetImportTask();task.filename=str(O/'Textures'/(name+'.png'));task.destination_path=DEST+'/Textures';task.destination_name=name
 task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task])
 tex=u.load_asset(path)
 if not tex or not task.imported_object_paths:raise RuntimeError('Texture import '+name)
 tex.set_editor_property('srgb',kind=='BaseColor')
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_BC7)
 if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
 tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('max_texture_size',4096);tex.set_editor_property('lod_bias',0)
 save(tex);textures[kind]=tex;receipt['textures'][name]=tex.get_path_name();record()

micro=(O/'MicroFinish.hlsl').read_text();rough=(O/'MatteRoughness.hlsl').read_text();color=(O/'MatteColor.hlsl').read_text()
beads=(O.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text().replace('return float4(slope,beads,saturate(Wet));','float coverage=saturate(Wet*20.0); return float4(slope*coverage,beads*coverage,saturate(Wet));')
paths={s['material'] for row in source['meshes'] for s in row['slots'] if s['material'] and s['material'].startswith(P+'/')}
replacements={}
for path in sorted(paths):
 if path in receipt['materials']:
  replacements[path]=u.load_asset(receipt['materials'][path]['dry']);continue
 original=u.load_asset(path);base=original.get_base_material();name=original.get_name()
 info=attachment['materials'].get(path.split('.')[0],{})
 if info.get('coating')=='protected material identity' or base.blend_mode not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:continue
 if L.get_material_property_input_node(base,u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Unexpected substrate source '+path)
 drybase=clone(base,DEST+'/Materials/M_'+name+'_Matte')
 # A material interrupted before its receipt is saved can be resumed cleanly.
 tagged=E.get_metadata_tag(drybase,'SVDMatteDetail')=='20260923'
 if not tagged:
  values={p:previous(drybase,p,v) for p,v in [('BASE_COLOR',(.03,.034,.04)),('ROUGHNESS',.3),('METALLIC',0.),('NORMAL',(0,0,1))]}
  metalregion=custom(drybase,'return smoothstep(.25,.72,Metal);',{'Metal':values['METALLIC']},1,'SVD metal only')
  optical=any(k in name for k in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring'])
  weather_region=constant(drybase,1.)
  if optical:
   root=values['BASE_COLOR'][0] if isinstance(values['BASE_COLOR'],tuple) else values['BASE_COLOR']
   if not isinstance(root,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Missing existing optical-region Lerp '+path)
   alpha=L.get_inputs_for_material_expression(drybase,root)[2]
   if not alpha:raise RuntimeError('Missing optical shell mask '+path)
   mask=(alpha,'R') if isinstance(alpha,u.MaterialExpressionVertexColor) else alpha
   weather_region=mask
   metalregion=custom(drybase,'return Metal*Shell;',{'Metal':metalregion,'Shell':mask},1,'SVD optical interior protection')
  if 'laser_0' in name:
   weather_region=custom(drybase,'return 1-saturate(max(Emission.r,max(Emission.g,Emission.b)));',{'Emission':previous(drybase,'EMISSIVE_COLOR',(0,0,0))},1,'SVD laser aperture protection')
  region=custom(drybase,'return Value;',{'Value':weather_region},1,'SVDMatte WeatherRegion')
  detail=custom(drybase,micro,{'P':vertex(drybase,u.MaterialExpressionPreSkinnedPosition),'N':vertex(drybase,u.MaterialExpressionPreSkinnedNormal)},4,'SVDMatte physical micro finish')
  strength=node(drybase,u.MaterialExpressionScalarParameter,parameter_name='SVD_MicroScratchStrength',default_value=.30)
  for prop,code,size in [('BASE_COLOR',color,3),('ROUGHNESS',rough,1)]:
   output(custom(drybase,code,{'Base':values[prop],'Detail':detail,'Strength':strength,'Region':metalregion},size,'SVDMatte '+prop),prop)
  E.set_metadata_tag(drybase,'SVDMatteDetail','20260923')
  finish(drybase)
 dry=flatten_instance(original,drybase,DEST+'/Materials/MI_'+name+'_Matte')
 if name=='MI_SVD_Magazine':
  for param,kind in [('Tex_basecolor','BaseColor'),('Tex_orm','ORM'),('Tex_normal','Normal')]:
   L.set_material_instance_texture_parameter_value(dry,param,textures[kind])
  L.update_material_instance(dry);save(dry)
 wetbase=clone(drybase,DEST+'/Materials/M_'+name+'_Matte_Wet')
 if E.get_metadata_tag(wetbase,'SVDMatteWet')!='20260923':
  vals={p:previous(wetbase,p,v) for p,v in [('BASE_COLOR',(.03,.034,.04)),('ROUGHNESS',.6),('NORMAL',(0,0,1))]}
  region=next(n for n in L.get_material_expressions(wetbase) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='SVDMatte WeatherRegion')
  amount=node(wetbase,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
  amount=custom(wetbase,'return saturate(Wet)*Region;',{'Wet':amount,'Region':region},1,'SVDMatte wet coverage')
  data=custom(wetbase,beads,{'UV':node(wetbase,u.MaterialExpressionTextureCoordinate),'Wet':amount},4,'SVDMatte rain')
  output(custom(wetbase,'return Base*(1-Data.a*.065);',{'Base':vals['BASE_COLOR'],'Data':data},3,'SVDMatte water film'),'BASE_COLOR')
  output(custom(wetbase,'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',{'Base':vals['ROUGHNESS'],'Data':data},1,'SVDMatte wet roughness'),'ROUGHNESS')
  output(custom(wetbase,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',{'Base':vals['NORMAL'],'Data':data},3,'SVDMatte water beads'),'NORMAL')
  E.set_metadata_tag(wetbase,'SVDMatteWet','20260923');finish(wetbase)
 wet=flatten_instance(dry,wetbase,DEST+'/Materials/MI_'+name+'_Matte_Wet')
 replacements[path]=dry
 receipt['materials'][path]={'dry':dry.get_path_name(),'wet':wet.get_path_name(),'saved':True,'source_normal_preserved':name!='MI_SVD_Magazine'};record()
 print('SVD_MATTE_MATERIAL_SAVED',name,flush=True)

table=u.load_asset(tablepath);backup(table)
mapping=dict(table.get_editor_property('wet_materials'))
for value in receipt['materials'].values():mapping[value['dry']]=u.load_asset(value['wet'])
table.set_editor_property('wet_materials',mapping);save(table)
receipt['wet_table']=table.get_path_name();record()
# Attachment meshes keep their geometry and UVs; only SVD-owned metal surfaces
# receive new private materials. Main skeletal mesh is bound after reimport.
for row in source['meshes']:
 mesh=u.load_asset(row['asset'])
 if isinstance(mesh,u.SkeletalMesh):continue
 backup(mesh);slots=mesh.static_materials
 for slot in row['slots']:
  old=slot['material']
  if old in replacements:
   s=slots[slot['index']];s.material_interface=replacements[old];slots[slot['index']]=s
 mesh.set_editor_property('static_materials',slots);save(mesh)
 receipt['meshes'].append({'asset':mesh.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'saved':True});record()
receipt['saved']=True;record()
print('SVD_MATTE_FINISH_SAVED',len(receipt['materials']),flush=True)
