"""Save all three glove detail families, preserving the native rig and LODs.

Run with the project authoring mutex commandlet or the existing editor bridge.
The original assets and black V4 stay intact. No PIE or runtime tests are run.
"""
import json,shutil,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GloveCompanionDetail20260928'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from import_tailored_fingerless_candidate import load,save
ROOT='/Game/Characters/ModularOutfit20260924/GloveCompanionDetail20260928'
SPECS={
 'Fingerless':('ue_field_gloves',['Shared','Body','DW715_l']),
 'Tactical':('ue_original_gloves',['M4','Body']),
 'Steel':('ue_steel_gauntlets',['Plates','Mail'])}
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def material(family,group):
 leather=family!='Steel';folder=ROOT+'/'+family+'/Materials/'+group;E.make_directory(folder)
 textures={}
 for channel in ['BaseColor','ORM','Normal']+(['Relief'] if leather else []):
  name='T_'+family+'_'+group+'_'+channel;task=u.AssetImportTask();task.filename=str(R/family/'Textures'/group/(name+'.png'))
  task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(folder+'/'+name)
  tex.set_editor_property('srgb',channel=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
  tex.set_editor_property('flip_green_channel',channel=='Normal');tex.set_editor_property('never_stream',False)
  tex.set_editor_property('max_texture_size',1024 if group=='Mail' else 2048 if group=='Body' else 4096)
  address=u.TextureAddress.TA_WRAP if group=='Mail' else u.TextureAddress.TA_CLAMP
  tex.set_editor_property('address_x',address);tex.set_editor_property('address_y',address);save(tex);textures[channel]=tex
 name='M_'+family+'_'+group+'_Detail';mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
 if not L.get_material_expressions(mat):
  mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH if leather else u.MaterialShadingModel.MSM_DEFAULT_LIT)
  mat.set_editor_property('tangent_space_normal',True)
  L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
  def node(cls):return L.create_material_expression(mat,cls)
  def wire(a,b,pin,output=''):
   if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)
  def prop(a,output,p):
   if not L.connect_material_property(a,output,p):raise RuntimeError('Cannot connect property '+str(p))
  def scalar(name,v):
   n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',v);return n
  uv=node(u.MaterialExpressionTextureCoordinate)
  if leather:
   mat.set_editor_property('use_material_attributes',True)
   pos=node(u.MaterialExpressionWorldPosition);pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
   inputs={'UV':uv,'Position':pos,'Camera':node(u.MaterialExpressionCameraPositionWS),'VertexNormal':node(u.MaterialExpressionVertexNormalWS),
     'DepthCm':scalar('LeatherReliefDepthCm',.06),'TextureSize':scalar('AtlasResolution',2048 if group=='Body' else 4096),'FuzzAmount':scalar('ShortFiberFuzz',.22)}
   for channel,pin in [('BaseColor','ColorTex'),('Normal','NormalTex'),('ORM','ORMTex'),('Relief','ReliefTex')]:
    n=node(u.MaterialExpressionTextureObjectParameter);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',textures[channel])
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);inputs[pin]=n
   shader=node(u.MaterialExpressionCustom)
   shader.set_editor_property('code',(P/'Tools/ModularOutfit/black_leather_relief.ush').read_text().replace('clamp(orm.g,.48,.96)','clamp(orm.g,.32,.96)'))
   shader.set_editor_property('description','Native skinned UV relief; high sculpt bake; bounded shared parallax and local seam nap')
   shader.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
   pins=[]
   for key in inputs:p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
   shader.set_editor_property('inputs',pins)
   for key,value in inputs.items():wire(value,shader,key)
   outputs=[]
   for key,width in [('NormalTangent',3),('AO',1),('Fuzz',1)]:
    o=u.CustomOutput();o.set_editor_property('output_name',key);o.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));outputs.append(o)
   shader.set_editor_property('additional_outputs',outputs)
   attrs=node(u.MaterialExpressionMakeMaterialAttributes);prop(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
   for channels,pin in [('rgb','BaseColor'),('a','Roughness')]:
    mask=node(u.MaterialExpressionComponentMask)
    for c in 'rgba':mask.set_editor_property(c,c in channels)
    wire(shader,mask,'')
    if channels=='rgb':
     tint=node(u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','SurfaceTint');tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
     multiply=node(u.MaterialExpressionMultiply);wire(mask,multiply,'A');wire(tint,multiply,'B','RGB');wire(multiply,attrs,pin)
    else:wire(mask,attrs,pin)
   for output,pin in [('NormalTangent','Normal'),('AO','AmbientOcclusion'),('Fuzz','ClearCoat')]:wire(shader,attrs,pin,output)
   wire(scalar('LeatherSpecular',.42),attrs,'Specular');wire(scalar('NonMetal',0.),attrs,'Metallic')
   fuzz=node(u.MaterialExpressionVectorParameter);fuzz.set_editor_property('parameter_name','FiberFuzzColor');fuzz.set_editor_property('default_value',u.LinearColor(.085,.052,.028,1));wire(fuzz,attrs,'SubsurfaceColor')
  else:
   if group=='Mail':uv.set_editor_property('u_tiling',.25/.0056);uv.set_editor_property('v_tiling',.25/.0048)
   for ch in ('BaseColor','ORM','Normal'):
    tex=node(u.MaterialExpressionTextureSampleParameter2D);tex.set_editor_property('parameter_name',ch);tex.set_editor_property('texture',textures[ch]);tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);wire(uv,tex,'UVs')
    if ch=='ORM':
     for output,p in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:prop(tex,output,p)
    else:prop(tex,'RGB',u.MaterialProperty.MP_BASE_COLOR if ch=='BaseColor' else u.MaterialProperty.MP_NORMAL)
   prop(scalar('SteelSpecular',.5),'',u.MaterialProperty.MP_SPECULAR)
  L.layout_material_expressions(mat)
 errors=L.recompile_material(mat)
 if errors:raise RuntimeError('Material compile failed '+family+' '+group+': '+str(errors))
 save(mat);return mat

def group_for(family,profile):
 if family=='Fingerless':
  manifest=read(P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1/manifest.json')
  return next(r['material_group'] for r in manifest if r['profile']==profile)
 return 'Body' if profile=='Body' else 'M4'

def duplicate(source,destination):
 E.make_directory(destination.rsplit('/',1)[0])
 return u.load_asset(destination) or E.duplicate_asset(source,destination) or load(destination)

def mesh(family,profile,source,materials,skin=False):
 suffix='_Skin' if skin else '';dest=ROOT+'/'+family+'/'+profile+'/SK_'+profile+'_'+family+'_Detail'+suffix
 obj=duplicate(source,dest);slots=list(obj.get_editor_property('materials'));changed=0
 for i,slot in enumerate(slots):
  old=slot.material_interface.get_path_name() if slot.material_interface else ''
  if skin and '/TailoredFingerlessV1/Materials/' not in old:continue
  mat=materials['Mail' if i==0 else 'Plates'] if family=='Steel' else materials[group_for(family,profile)]
  slot.material_interface=mat;slots[i]=slot;changed+=1
 if not changed:raise RuntimeError('No glove material slot found in '+source)
 obj.set_editor_property('materials',slots);E.set_metadata_tag(obj,'EquipmentDefinition',SPECS[family][0]);E.set_metadata_tag(obj,'DetailSource',source);save(obj)
 return dict(profile=profile,mesh=obj.get_path_name(),source=source,skin=skin,geometry_changed=False,weights_changed=False,lods_preserved=True)

def pickup(family,materials,before):
 obj=duplicate(before['item']['world_mesh'],ROOT+'/'+family+'/Pickups/SM_'+family+'_Detail_Pickup')
 slots=list(obj.get_editor_property('static_materials'))
 for i,slot in enumerate(slots):
  mat=materials['Mail' if i==0 else 'Plates'] if family=='Steel' else materials['Shared' if family=='Fingerless' else 'M4']
  if family=='Tactical' and i>0:
   # Preserve the current empty-shell lining's darker colour in world drops.
   folder=ROOT+'/'+family+'/Materials';name='MI_Tactical_Interior_Detail';instance=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
   L.set_material_instance_parent(instance,mat);L.set_material_instance_vector_parameter_value(instance,'SurfaceTint',u.LinearColor(.55,.55,.55,1));save(instance);mat=instance
  slot.material_interface=mat;slots[i]=slot
 obj.set_editor_property('static_materials',slots);E.set_metadata_tag(obj,'EquipmentDefinition',SPECS[family][0]);save(obj);return obj

def publish(family,materials):
 item_id,groups=SPECS[family];folder=R/family;before=read(folder/'before.json')
 cfgpath=P/'Content/ColdSteelData/modular_outfits.json';ipath=P/'Content/ColdSteelData/items.json';cfg=read(cfgpath);items=read(ipath)
 current=cfg['items'][item_id]
 if current!=before['recipe'] and current.get('appearance_family')!=family+'Detail20260928':raise RuntimeError('This glove recipe changed during production: '+item_id)
 # Gameplay fields are taken fresh at publication; only asset references move.
 receipt={p:read(folder/'Saved'/(p+'.json')) for p in before['recipe']['rig_meshes']}
 recipe=dict(current,appearance_family=family+'Detail20260928',material='',rig_meshes={p:r['mesh'] for p,r in receipt.items()})
 if 'skin_meshes' in before['recipe']:
  recipe['skin_meshes']={p:read(folder/'Saved'/(p+'_Skin.json'))['mesh'] for p in before['recipe']['skin_meshes']}
 world=pickup(family,materials,before);icon='Icons/GloveCompanionDetail20260928/'+item_id+'.png';path=P/'Content/ColdSteelData'/icon;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/(item_id+'.png'),path)
 definition=dict(items[item_id]);definition.update(ue_icon=icon,world_mesh=world.get_path_name(),world_material='')
 cfg['items'][item_id]=recipe;items[item_id]=definition;write(cfgpath,cfg);write(ipath,items)
 write(folder/'published.json',dict(item=item_id,recipe=recipe,item_definition=definition,appearance={k:definition[k] for k in ('ue_icon','world_mesh','world_material')},profiles=receipt,materials={g:m.get_path_name() for g,m in materials.items()},pickup=world.get_path_name(),icon=str(path),stats_changed=False,new_animations=0,runtime_tested=False))
 print('COMPANION_FAMILY_PUBLISHED',family,len(receipt),flush=True)

def main(families=None,names=None,import_materials=True,publish_result=True):
 commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
 subsystem=None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if subsystem and subsystem.get_game_world():raise RuntimeError('PIE is running; glove mesh saves require ending that play session')
 for family in families or list(SPECS):
  item_id,groups=SPECS[family];folder=R/family;read(folder/'artwork.json');before=read(folder/'before.json')
  materials={g:material(family,g) if import_materials else load(ROOT+'/'+family+'/Materials/'+g+'/M_'+family+'_'+g+'_Detail') for g in groups}
  for profile,source in before['recipe']['rig_meshes'].items():
   if names is not None and profile not in names:continue
   row=mesh(family,profile,source,materials);write(folder/'Saved'/(profile+'.json'),row)
   if profile in before['recipe'].get('skin_meshes',{}):
    row=mesh(family,profile,before['recipe']['skin_meshes'][profile],materials,True);write(folder/'Saved'/(profile+'_Skin.json'),row)
   print('COMPANION_NATIVE_SAVED',family,profile,flush=True)
  if publish_result:publish(family,materials)
 print('COMPANION_BATCH_SAVED',families,names,flush=True)

if __name__=='__main__':main()
