"""PKM-only dry finish, wet partners, slot rebinding and rain coverage report."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;R=O.parent
P='/Game/Weapons/PKMLowpoly20260922/Finish20'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
source=json.loads((O/'materials_before.json').read_text())
report={'dry':{},'wet':{},'meshes':[],'excluded':{},'coverage_before':[],'coverage_after':[],'compiled':[]}

def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def constant(m,value):
 if isinstance(value,tuple):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))
 return node(m,u.MaterialExpressionConstant,r=value)
def wire(src,dest,pin):
 n,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(n,out,dest,pin):raise RuntimeError('Cannot connect '+pin)
def output(src,name):
 n,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError(name)
def custom(m,code,inputs,size,label):
 n=node(m,u.MaterialExpressionCustom,code=code,description=label,
  output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 ci=[]
 for name in inputs:
  item=u.CustomInput();item.set_editor_property('input_name',name);ci.append(item)
 n.set_editor_property('inputs',ci)
 for name,src in inputs.items():wire(src,n,name)
 return n
def original(m,name,default):
 prop=getattr(u.MaterialProperty,'MP_'+name);n=L.get_material_property_input_node(m,prop)
 return (n,L.get_material_property_input_node_output_name(m,prop)) if n else constant(m,default)
def vertex_value(m,cls):
 n=node(m,u.MaterialExpressionVertexInterpolator)
 wire(node(m,cls),n,'VS')
 return n
def fix_vertex_inputs(m):
 # UE 5.8's material generator requires explicit vertex-to-pixel transport.
 for expr in L.get_material_expressions(m):
  if isinstance(expr,u.MaterialExpressionCustom) and expr.get_editor_property('description')=='PKM20 physical micro finish':
   expr.set_editor_property('code',micro_code)
   for pin,src in zip(['P','N'],L.get_inputs_for_material_expression(m,expr)):
    if isinstance(src,(u.MaterialExpressionPreSkinnedPosition,u.MaterialExpressionPreSkinnedNormal)):
     bridge=node(m,u.MaterialExpressionVertexInterpolator);wire(src,bridge,'VS');wire(bridge,expr,pin)
   L.recompile_material(m);save(m)
def fix_dry_weather(m):
 for expr in L.get_material_expressions(m):
  if isinstance(expr,u.MaterialExpressionCustom) and expr.get_editor_property('description')=='WeatherBeads':
   if expr.get_editor_property('code')!=bead_code:
    expr.set_editor_property('code',bead_code);L.recompile_material(m);save(m)
def clone(obj,path):
 if E.does_asset_exist(path):return u.load_asset(path),False
 result=E.duplicate_asset(obj.get_path_name(),path)
 if not result:raise RuntimeError('Duplicate failed '+path)
 return result,True
def category(path):
 s=path.lower()
 if any(x in s for x in ['manny','reticle','glass']):return 'excluded'
 if any(x in s for x in ['wood','laminated']):return 'wood'
 if 'rubber' in s:return 'rubber'
 if any(x in s for x in ['polymer','stableantislipreargrip']):return 'polymer'
 if any(x in s for x in ['recess','interior']):return 'recess'
 if any(x in s for x in ['copperjacket','caselacquer']):return 'ammunition'
 return 'metal'
def mask_for(m,path):
 # These mixed optical/device shells retain the existing coating-region mask.
 # Separate glass/reticle slots are excluded entirely. Inputs preserve order in
 # UMaterialEditingLibrary::GetInputsForMaterialExpression (including nulls).
 if any(s in path.lower() for s in ['holographic_0','panoramic_red_dot_','prism_scope_2x_',
    'lpvo_1_6x_','lpvo_ring_','laser_0','flashlight_0']):
  root=L.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
  if not isinstance(root,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Missing shell-region mask: '+path)
  inputs=L.get_inputs_for_material_expression(m,root)
  mask=inputs[2]
  if not mask:raise RuntimeError('Missing coating alpha: '+path)
  if isinstance(mask,u.MaterialExpressionTextureSample):raise RuntimeError('Channel-specific shell alpha needs explicit wiring: '+path)
  if isinstance(mask,u.MaterialExpressionVertexColor):return (mask,'R')
  return mask
 return constant(m,1.)

# Read the same aggregate libraries consumed by WeatherViewEffectsComponent.
weather_before={}
for table in ['/Game/Weather/RainVisibility/DA_WeatherPresentation',
 '/Game/Weapons/DanWesson715/AccessoryPolymer20260914/DA_DW715_WetMaterials',
 '/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials',
 '/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials']:
 a=u.load_asset(table)
 if a:
  weather_before.update({str(k):v.get_path_name() for k,v in a.get_editor_property('wet_materials').items() if v})
for row in source['coverage']:
 report['coverage_before'].append(dict(row,wet=weather_before.get(row['material'])))

bead_code=(Path(u.Paths.project_dir())/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text()
bead_code=bead_code.replace('return float4(slope,beads,saturate(Wet));',
 'float coverage=saturate(Wet*20.0);\nreturn float4(slope*coverage,beads*coverage,saturate(Wet));')
micro_code=(O/'MicroFinish.hlsl').read_text()
mapping={};dry_by_source={}
for path,info in source['materials'].items():
 kind=category(path)
 if kind=='excluded':report['excluded'][path]='Hands or optical glass/reticle';continue
 original_asset=u.load_asset(path);base=original_asset.get_base_material()
 if base.blend_mode not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:
  report['excluded'][path]='Non-opaque effect';continue
 if L.get_material_property_input_node(base,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES) or L.get_material_property_input_node(base,u.MaterialProperty.MP_FRONT_MATERIAL):
  raise RuntimeError('Unsupported material-attributes surface '+path)
 key=hashlib.sha1(path.encode()).hexdigest()[:8];name=original_asset.get_name()
 dry,fresh=clone(base,P+'/Materials/M_Dry_'+name+'_'+key)
 if fresh:
  values={k:original(dry,k,d) for k,d in [('BASE_COLOR',(.03,.03,.03)),('ROUGHNESS',.5),('METALLIC',0.),('NORMAL',(0,0,1))]}
  mask=mask_for(dry,path)
  # Label the exact optical protection for its wet copy. The laser's polymer
  # shell must also receive rain; only the existing emissive aperture is spared.
  weather_mask=mask
  if 'laser_0' in path.lower():
   emissive=original(dry,'EMISSIVE_COLOR',(0,0,0))
   weather_mask=custom(dry,'return 1-saturate(max(Emission.r,max(Emission.g,Emission.b)));',
    {'Emission':emissive},1,'PKM20 laser aperture protection')
  region=custom(dry,'return Value;',{'Value':weather_mask},1,'PKM20_SurfaceRegion')
  detail=custom(dry,micro_code,{'P':vertex_value(dry,u.MaterialExpressionPreSkinnedPosition),
    'N':vertex_value(dry,u.MaterialExpressionPreSkinnedNormal)},4,'PKM20 physical micro finish')
  strength=scalar(dry,'PKM_MicroScratchStrength',{'metal':.34,'wood':.12,'polymer':.10,'rubber':.025,'recess':0.,'ammunition':.08}[kind])
  common={'Detail':detail,'Strength':strength,'Region':mask,'Metal':values['METALLIC']}
  # White markings and mixed non-metal/optical surfaces retain their identities.
  base_code='float marks=1-smoothstep(.42,.72,dot(Base,float3(.2126,.7152,.0722))); float wear=Detail.r*Strength*Region*marks; '
  if kind=='metal':
   base_code+='float metal=smoothstep(.3,.65,Metal); return lerp(Base,Base*(.965+.05*Detail.g)*(1-.018*Detail.b)+wear*lerp(float3(.024,.026,.028),float3(.075,.08,.085),metal),Region);'
  else:base_code+='return Base*(1+Region*(Detail.g-.5)*.025)+wear*.018;'
  output(custom(dry,base_code,dict(common,Base=values['BASE_COLOR']),3,'PKM20 restrained scuffs'),'BASE_COLOR')
  rough='float grain=(Detail.g-.5)*.045-Detail.b*.018; return saturate(Base+Region*grain-Detail.r*Strength*Region*.12);'
  if kind in ['recess','ammunition']:rough='return Base;'
  output(custom(dry,rough,dict(common,Base=values['ROUGHNESS']),1,'PKM20 varied roughness'),'ROUGHNESS')
  if kind=='metal':
   output(custom(dry,'return lerp(Base,.94,Detail.r*Strength*Region*.50*smoothstep(.3,.65,Base));',
    dict(common,Base=values['METALLIC']),1,'PKM20 fine exposed metal'),'METALLIC')
  # Keep every original structural normal, AO, emissive and opacity connection.
  L.set_material_usage(dry,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
  E.set_metadata_tag(dry,'PKM20_Source',path);E.set_metadata_tag(dry,'PKM20_Category',kind)
  L.recompile_material(dry);save(dry)
 else:fix_vertex_inputs(dry)
 dry_result=dry
 if isinstance(original_asset,u.MaterialInstanceConstant):
  dry_result,new=clone(original_asset,P+'/Materials/MI_Dry_'+name+'_'+key)
  if new:L.set_material_instance_parent(dry_result,dry);L.update_material_instance(dry_result);save(dry_result)
 dry_by_source[path]=dry_result
 wet,new=clone(dry,P+'/Materials/M_Wet_'+name+'_'+key)
 if new:
  values={k:original(wet,k,d) for k,d in [('BASE_COLOR',(.03,.03,.03)),('ROUGHNESS',.5),('NORMAL',(0,0,1))]}
  region=next(n for n in L.get_material_expressions(wet) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='PKM20_SurfaceRegion')
  wetness=custom(wet,'return saturate(Wet)*Region;',{'Wet':scalar(wet,'WeaponWetness',0),'Region':region},1,'PKM20 weather region')
  data=custom(wet,bead_code,{'UV':node(wet,u.MaterialExpressionTextureCoordinate),'Wet':wetness},4,'WeatherBeads')
  film={'metal':.065,'wood':.095,'polymer':.06,'rubber':.035,'ammunition':.045,'recess':.015}[kind]
  output(custom(wet,f'return Base*(1-Data.a*{film});',dict(Base=values['BASE_COLOR'],Data=data),3,'PKM20 rain film'),'BASE_COLOR')
  output(custom(wet,'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',dict(Base=values['ROUGHNESS'],Data=data),1,'PKM20 wet roughness'),'ROUGHNESS')
  output(custom(wet,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',dict(Base=values['NORMAL'],Data=data),3,'PKM20 subtle water beads'),'NORMAL')
  E.set_metadata_tag(wet,'PKM20_WetSource',dry_result.get_path_name());L.recompile_material(wet);save(wet)
 else:fix_vertex_inputs(wet);fix_dry_weather(wet)
 wet_result=wet
 if isinstance(original_asset,u.MaterialInstanceConstant):
  wet_result,new=clone(dry_result,P+'/Materials/MI_Wet_'+name+'_'+key)
  if new:L.set_material_instance_parent(wet_result,wet);L.update_material_instance(wet_result);save(wet_result)
 mapping[dry_result.get_path_name()]=wet_result
 report['dry'][path]=dry_result.get_path_name();report['wet'][dry_result.get_path_name()]=wet_result.get_path_name()
 report['compiled'] += [dry.get_path_name(),wet.get_path_name()]
 print('PKM20_FINISH',name,kind,flush=True)

# Save a dedicated library before rebinding the live meshes. Other guns retain
# their original materials; no shared weather or material graph is overwritten.
table_path=P+'/DA_PKM_WetMaterials'
table=u.load_asset(table_path) if E.does_asset_exist(table_path) else None
if not table:
 factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
 table=A.create_asset('DA_PKM_WetMaterials',P,u.WeatherPresentationAssets,factory)
table.set_editor_property('wet_materials',mapping);save(table)
for item in source['meshes']:
 mesh=u.load_asset(item['asset']);is_sk=isinstance(mesh,u.SkeletalMesh)
 slots=mesh.materials if is_sk else mesh.static_materials
 changed=[]
 for slot in item['slots']:
  i=slot['index'];old=slot['material'];replacement=dry_by_source.get(old)
  if replacement:
   entry=slots[i];entry.material_interface=replacement;slots[i]=entry
   changed.append({'index':i,'slot':slot['slot'],'original':old,'dry':replacement.get_path_name()})
 if changed:
  mesh.set_editor_property('materials' if is_sk else 'static_materials',slots)
  E.set_metadata_tag(mesh,'PKM20_Finish','PKM-only subtle microfinish and dedicated rain partners');save(mesh)
 actual=mesh.materials if is_sk else mesh.static_materials
 for i,slot in enumerate(actual):
  mat=slot.material_interface
  if not mat:continue
  p=mat.get_path_name();wet=mapping.get(p)
  expected=p in report['wet']
  report['coverage_after'].append({'mesh':mesh.get_path_name(),'slot':str(slot.material_slot_name),'material':p,
   'wet':wet.get_path_name() if wet else None,'requires_wet':expected})
 report['meshes'].append({'asset':mesh.get_path_name(),'changes':changed})
report['wet_library']=table.get_path_name();report['saved']=True
(O/'finish_import.json').write_text(json.dumps(report,indent=2))
print('PKM20_FINISH_AND_WET_LIBRARY_SAVED',len(dry_by_source),len(report['meshes']),flush=True)
