"""Private 201 coating family; preserve regional identity and source detail maps."""
import unreal as u
import json, hashlib
from pathlib import Path

O=Path(__file__).parent; S=O.parent; P='/Game/Weapons/LMG201/FitFinish37'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools(); M=u.MaterialEditingLibrary
COLOR=(.010960,.014444,.017642); ROUGH=.60; METAL=0.; SPEC=.28
COATING={'linear_color':COLOR,'roughness':ROUGH,'metallic':METAL,'specular':SPEC,
         'wet_color_multiplier':.90,'wet_roughness_multiplier':.85,'wet_roughness_floor':.48}
receipt={'status':'building','recipe':COATING,'materials':{},'adapted':{},'preserved':{}}
if (O/'materials.json').exists():receipt=json.loads((O/'materials.json').read_text())
def record():(O/'materials.json').write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def node(mat,cls,**props):
 n=M.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,dst,pin):
 n,ch=src if isinstance(src,tuple) else (src,'')
 if not M.connect_material_expressions(n,ch,dst,pin):raise RuntimeError('Cannot connect '+pin)
def output(src,prop):
 n,ch=src if isinstance(src,tuple) else (src,'')
 if not M.connect_material_property(n,ch,prop):raise RuntimeError('Cannot connect output '+str(prop))
def parameter(mat,name,value,vector=False):
 cls=u.MaterialExpressionVectorParameter if vector else u.MaterialExpressionScalarParameter
 n=next((n for n in M.get_material_expressions(mat) if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==name),None)
 if n is None:n=node(mat,cls,parameter_name=name)
 n.set_editor_property('default_value',u.LinearColor(*value,1) if vector else value)
 return n
def custom(mat,label,code,inputs,vector=False):
 n=node(mat,u.MaterialExpressionCustom,description=label,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3 if vector else u.CustomMaterialOutputType.CMOT_FLOAT1)
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n
def sampled(mat,tex,kind):
 return node(mat,u.MaterialExpressionTextureSample,texture=tex,sampler_type={'color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'mask':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind])
def upstream(mat,prop):
 return (M.get_material_property_input_node(mat,prop),M.get_material_property_input_node_output_name(mat,prop))
def fine_roughness(mat,rough):
 inputs={'Base':rough}
 for label,cls in [('P',u.MaterialExpressionPreSkinnedPosition),('N',u.MaterialExpressionPreSkinnedNormal)]:
  bridge=node(mat,u.MaterialExpressionVertexInterpolator);wire(node(mat,cls),bridge,'VS');inputs[label]=bridge
 inputs['FinishTex']=node(mat,u.MaterialExpressionTextureObject,texture=load('/Game/Weapons/LMG201/Material21/Textures/T_LMG201_FineFinish'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
 inputs['Amplitude']=parameter(mat,'LMG201MicroRoughness',.016)
 return custom(mat,'F37 shared 5 cm roughness grain',(S/'Material21/FineRoughness.hlsl').read_text(),inputs)
def wet_film(mat,base,rough,region=None):
 wet=parameter(mat,'WeaponWetness',0)
 amount=custom(mat,'F37 wet amount','return saturate(Wet)*saturate(Region);',{'Wet':wet,'Region':region or node(mat,u.MaterialExpressionConstant,r=1.)})
 for src,prop,code in [(base,u.MaterialProperty.MP_BASE_COLOR,'return Base*(1-Wet*.10);'),(rough,u.MaterialProperty.MP_ROUGHNESS,'return lerp(Base,max(.48,Base*.85),Wet);')]:
  output(custom(mat,'F37 unified wet film',code,{'Base':src,'Wet':amount},prop==u.MaterialProperty.MP_BASE_COLOR),prop)
def compile_save(mat):
 errors=M.recompile_material(mat)
 if errors:raise RuntimeError('Compile failed '+mat.get_path_name()+' '+str(errors))
 E.set_metadata_tag(mat,'201FinishRevision','FitFinish37: shared coated body recipe, individual UV0 normal/AO, regional nonmetal identity, common WeaponWetness film')
 save(mat)
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing source '+path)
 return a

# The new lid alone gets these maps; other UV layouts must not sample them.
cover={}
for kind in ['Normal','AO']:
 src=O/'Textures'/('T_LMG201_F37_Cover_'+kind+'.png');t=u.AssetImportTask();t.filename=str(src);t.destination_path=P+'/Textures';t.destination_name=src.stem;t.automated=True;t.replace_existing=True;t.save=False
 tex=u.load_asset(t.destination_path+'/'+src.stem)
 if not tex:A.import_asset_tasks([t]);tex=load(t.destination_path+'/'+src.stem)
 tex.set_editor_property('srgb',False);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS)
 if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
 save(tex);cover[kind]=tex

for role in ['Surface','Receiver','Coat','Satin','Interior','Sight','Cover','CoverInterior','CoverSatin']:
 if role in receipt['materials'] and receipt.get('family_recipe_version')==2:continue
 name='M_LMG201_F37_'+role;mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);mat.set_editor_property('used_with_skeletal_mesh',True);mat.set_editor_property('automatically_set_usage_in_editor',False);mat.set_editor_property('two_sided',False)
 inside=role in ['Interior','CoverInterior'];satin=role in ['Satin','CoverSatin']
 rgb=tuple(v*(.78 if inside else 1.65 if satin else .82 if role=='Sight' else 1.) for v in COLOR)
 base=parameter(mat,'FinishColor',rgb,True);rough=parameter(mat,'DryRoughness',.70 if inside else .50 if satin else .65 if role=='Sight' else ROUGH)
 metal=parameter(mat,'Metallic',.65 if satin else METAL)
 if role in ['Surface','Receiver']:
  texroot='/Game/Weapons/LMG201/'+('Detail35/Textures/T_LMG201_D35_Receiver_' if role=='Receiver' else 'Surface32/Textures/T_LMG201_S32_')
  bc=sampled(mat,load(texroot+'BaseColor'),'color');orm=sampled(mat,load(texroot+'ORM'),'mask')
  original=sampled(mat,load('/Game/Weapons/LMG201/Install30/Textures/T_201_R29_Surface_ORM'),'mask')
  mask=custom(mat,'F37 original painted region','return smoothstep(.30,.65,Metal);',{'Metal':(original,'B')})
  base=custom(mat,'F37 coating with restrained source variation','float3 shade=clamp(Base/float3(.010960,.014444,.017642),.35,1.8); return lerp(Base,Tint*(.80+.20*shade),Region);',{'Base':(bc,'RGB'),'Tint':base,'Region':mask},True)
  rough=custom(mat,'F37 coated roughness','return lerp(Base,Center+clamp((Base-.604)*.40,-.025,.025),Region);',{'Base':(orm,'G'),'Center':rough,'Region':mask})
  metal=custom(mat,'F37 dielectric coating over metal','return lerp(Base,Coating,Region);',{'Base':(original,'B'),'Coating':metal,'Region':mask})
  normal=load('/Game/Weapons/LMG201/Repair36/Textures/T_LMG201_R36_Receiver_Normal' if role=='Receiver' else '/Game/Weapons/LMG201/Install30/Textures/T_201_R29_Surface_Normal')
  output((sampled(mat,normal,'normal'),'RGB'),u.MaterialProperty.MP_NORMAL);output((orm,'R'),u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 elif role.startswith('Cover'):
  output((sampled(mat,cover['Normal'],'normal'),'RGB'),u.MaterialProperty.MP_NORMAL);output((sampled(mat,cover['AO'],'mask'),'R'),u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 output(metal,u.MaterialProperty.MP_METALLIC);output(parameter(mat,'Specular',SPEC),u.MaterialProperty.MP_SPECULAR)
 wet_film(mat,base,fine_roughness(mat,rough));compile_save(mat);receipt['materials'][role]=mat.get_path_name();record()
receipt['family_recipe_version']=2;record()

# Private copies of legacy finishes. Work from dry graphs; the new wet table
# points at the same graph with WeaponWetness, avoiding two competing recipes.
targets=set(json.loads((S/'Material21/bindings.json').read_text())['meshes'])
targets.update(v['asset'] for v in json.loads((S/'Accessories22/install_receipt.json').read_text())['meshes'].values())
sources={}
for path in sorted(targets):
 a=load(path);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 for s in slots:
  if s.material_interface:sources[s.material_interface.get_path_name()]=s.material_interface

for path,original in sources.items():
 if path.startswith(P+'/'):continue
 if path in receipt['adapted']:continue
 base=original.get_base_material();params={str(n) for n in M.get_scalar_parameter_names(base)}
 if base.blend_mode not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:
  receipt['preserved'][path]='translucent/optical';continue
 if 'A762CoatingRoughness' in params:kind='regional_a762'
 elif 'PKM_SatinRoughness' in params:kind='regional_pkm'
 elif ('RoughnessCenter' in params and any(k in original.get_name() for k in ['Magazine','Trigger','Bipod'])):kind='legacy_metal'
 else:
  receipt['preserved'][path]='other surface identity or replaced by named F37 role';continue
 name='M_F37_'+original.get_name().removeprefix('MI_').removeprefix('M_')+'_'+hashlib.sha1(path.encode()).hexdigest()[:7]
 graph=u.load_asset(P+'/Adapted/'+name) or E.duplicate_asset(base.get_path_name(),P+'/Adapted/'+name)
 scalars={};vectors={};region=None
 if kind=='regional_a762':
  scalars={'A762CoatingRoughness':ROUGH,'A762CoatingMetallic':METAL,'A762CoatingSpecular':SPEC};vectors={'A762CoatingColor':COLOR}
  # The original coating blend's alpha excludes bright markings and optics.
  for n in M.get_material_expressions(graph):
   if isinstance(n,u.MaterialExpressionLinearInterpolate):
    ins=M.get_inputs_for_material_expression(graph,n)
    if len(ins)>2 and isinstance(ins[1],u.MaterialExpressionVectorParameter) and str(ins[1].get_editor_property('parameter_name'))=='A762CoatingColor':region=ins[2];break
  if region is None:
   color_input=upstream(graph,u.MaterialProperty.MP_BASE_COLOR)[0]
   if isinstance(color_input,u.MaterialExpressionVectorParameter) and str(color_input.get_editor_property('parameter_name'))=='A762CoatingColor':region=node(graph,u.MaterialExpressionConstant,r=1.)
   else:raise RuntimeError('No A762 regional coating mask '+path)
 elif kind=='regional_pkm':
  scalars={'PKM_SatinRoughness':ROUGH,'PKM_MicroScratchStrength':.08,'PKM_SatinColorWeight':.98};vectors={'PKM_SatinTint':COLOR}
  region=next((n for n in M.get_material_expressions(graph) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='PKM20_SurfaceRegion'),None)
  metal_node=next((n for n in M.get_material_expressions(graph) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='PKM20 fine exposed metal'),None)
  if region is None or metal_node is None:raise RuntimeError('Missing PKM regional finish inputs '+path)
  metal_node.set_editor_property('code','float coated=saturate(Region)*smoothstep(.3,.65,Metal); return lerp(Base,saturate(Detail.r*Strength*.08),coated);')
  # Existing specular branches retain their nonmetal/optical inputs.
  oldspec=upstream(graph,u.MaterialProperty.MP_SPECULAR)
  if oldspec[0]:output(custom(graph,'F37 region specular','return lerp(Base,.28,saturate(Region));',{'Base':oldspec,'Region':region}),u.MaterialProperty.MP_SPECULAR)
 else:
  satin='Trigger' in original.get_name()
  scalars={'RoughnessCenter':.50 if satin else ROUGH,'Metallic':.65 if satin else METAL,'SourceColorWeight':.035,'LMG201MicroRoughness':.016};vectors={'FinishColor':tuple(v*(1.65 if satin else 1.) for v in COLOR)}
  output(parameter(graph,'Specular',SPEC),u.MaterialProperty.MP_SPECULAR)
 for k,v in scalars.items():parameter(graph,k,v)
 for k,v in vectors.items():parameter(graph,k,v,True)
 # V26 already has a simple wet lerp. Take its dry A input before adding F37.
 dry=[]
 for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS]:
  src=upstream(graph,prop)
  if 'WeaponWetness' in params and isinstance(src[0],u.MaterialExpressionLinearInterpolate):
   ins=M.get_inputs_for_material_expression(graph,src[0])
   if ins and ins[0]:src=(ins[0],'')
  if not src[0]:raise RuntimeError('Missing dry finish output '+path)
  dry.append(src)
 wet_film(graph,*dry,region);compile_save(graph);result=graph
 if isinstance(original,u.MaterialInstanceConstant):
  dest=P+'/Adapted/MI_'+name.removeprefix('M_');result=u.load_asset(dest) or E.duplicate_asset(path,dest)
  M.set_material_instance_parent(result,graph)
  for k,v in scalars.items():M.set_material_instance_scalar_parameter_value(result,k,v)
  for k,v in vectors.items():M.set_material_instance_vector_parameter_value(result,k,u.LinearColor(*v,1))
  M.set_material_instance_scalar_parameter_value(result,'WeaponWetness',0);M.update_material_instance(result);save(result)
 receipt['adapted'][path]={'material':result.get_path_name(),'kind':kind,'scalars':scalars,'vectors':vectors};record();print('F37_FINISH_SAVED',original.get_name(),flush=True)

receipt.update(status='compiled_and_saved',recipe=COATING);record();print('F37_MATERIALS_SAVED',len(receipt['materials']),len(receipt['adapted']),flush=True)
