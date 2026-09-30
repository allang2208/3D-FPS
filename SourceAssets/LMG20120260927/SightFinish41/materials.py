"""Private 201 finishes referenced to the currently bound QBZ191 body shader."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/SightFinish41';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
COLOR=(.02810,.03179,.03532);ROUGH=.357;METAL=.73
targets=json.loads((O/'finish_targets.json').read_text());sources={s['material'] for row in targets.values() for s in row['slots'] if s['material']}
out={'reference':'/Game/Weapons/QBZ191/Attachments20260913/Materials/M_QBZ191_Unified_M_QBZ191_Wear_Body_metal','reference_region':{'linear_base_median':COLOR,'roughness_p10_p50_p90':[.35411,.35654,.35897],'metallic_median':.72941},'mapping':{},'recipes':{},'preserved':{}}
if (O/'materials.json').exists():out=json.loads((O/'materials.json').read_text())

def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(a,out,prop):
 if not L.connect_material_property(a,out,prop):raise RuntimeError('Cannot connect '+str(prop))
def parameter(m,key,value):
 vector=isinstance(value,tuple);cls=u.MaterialExpressionVectorParameter if vector else u.MaterialExpressionScalarParameter
 ns=[n for n in L.get_material_expressions(m) if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==key]
 if not ns:ns=[node(m,cls,parameter_name=key)]
 for n in ns:n.set_editor_property('default_value',u.LinearColor(*value,1) if vector else value)
 return ns[0]
def custom(m,label,code,inputs,vector=False):
 n=node(m,u.MaterialExpressionCustom,description=label,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3 if vector else u.CustomMaterialOutputType.CMOT_FLOAT1);pins=[]
 for key in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
 n.set_editor_property('inputs',pins)
 for key,(src,ch) in inputs.items():wire(src,ch,n,key)
 return n

for path in sorted(sources):
 if path in out['mapping']:continue
 if '/LMG201/' not in path or any(k in path for k in ['Cloth','Belt','_Case','_Copper','_Link','Manny']):continue
 original=u.load_asset(path);base=original.get_base_material();params={str(n) for n in L.get_scalar_parameter_names(base)};name=original.get_name()
 if base.get_editor_property('blend_mode') not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:out['preserved'][path]='optical/translucent';continue
 interior=any(s in name for s in ['Interior','Inside','Sight']) and 'RearSight' not in name and 'FrontSight' not in name
 satin=any(s in name for s in ['Satin','Trigger','ChargingHandle'])
 poly=any(s in name for s in ['Polymer','RearGrip']) or name=='M_LMG201_Handguard'
 if poly or interior:
  out['preserved'][path]='polymer identity' if poly else 'matte interior / sight';continue
 if 'A762CoatingRoughness' in params:kind='regional_a762'
 elif 'PKM_SatinRoughness' in params:kind='regional_pkm'
 elif ('FinishColor' in {str(n) for n in L.get_vector_parameter_names(base)} and ('DryRoughness' in params or 'RoughnessCenter' in params)):kind='body'
 else:out['preserved'][path]='independent surface identity';continue
 tag=hashlib.sha1(path.encode()).hexdigest()[:8];dest=P+'/Materials/M_S41_'+name.removeprefix('MI_').removeprefix('M_')+'_'+tag
 graph=u.load_asset(dest) or E.duplicate_asset(base.get_path_name(),dest)
 color=(.035,.039,.043) if satin else COLOR;rough=.32 if satin else ROUGH;metal=.82 if satin else METAL
 scalars={};vectors={};instance=isinstance(original,u.MaterialInstanceConstant)
 if instance:
  # Preserve every inherited parameter before applying this finish's changes.
  for typ in ['scalar','vector','texture','static_switch']:
   for n in getattr(L,'get_'+typ+'_parameter_names')(base):
    val=getattr(L,'get_material_instance_'+typ+'_parameter_value')(original,n)
    if typ=='scalar':parameter(graph,str(n),val)
    elif typ=='vector':parameter(graph,str(n),(val.r,val.g,val.b))
    elif typ=='texture':
     for ex in L.get_material_expressions(graph):
      if isinstance(ex,u.MaterialExpressionTextureSampleParameter) and str(ex.get_editor_property('parameter_name'))==str(n):ex.set_editor_property('texture',val)
 if kind=='body':
  scalars={k:v for k,v in {'DryRoughness':rough,'RoughnessCenter':rough,'Metallic':metal,'Specular':.5,'SourceColorWeight':.045,'LMG201MicroRoughness':.012}.items() if k in params or k=='Specular'};vectors={'FinishColor':color}
 elif kind=='regional_a762':scalars={'A762CoatingRoughness':ROUGH,'A762CoatingMetallic':METAL,'A762CoatingSpecular':.5};vectors={'A762CoatingColor':COLOR}
 else:scalars={'PKM_SatinRoughness':ROUGH,'PKM_MicroScratchStrength':.045,'PKM_SatinColorWeight':.98};vectors={'PKM_SatinTint':COLOR}
 for k,v in scalars.items():parameter(graph,k,v)
 for k,v in vectors.items():parameter(graph,k,v)
 has_f37_wet=False
 for n in L.get_material_expressions(graph):
  if not isinstance(n,u.MaterialExpressionCustom):continue
  desc=n.get_editor_property('description');code=n.get_editor_property('code')
  if desc=='F37 unified wet film' and 'max(.48' in code:
   n.set_editor_property('code','return lerp(Base,max(.25,Base*.78),Wet);');has_f37_wet=True
  if desc=='F37 region specular':n.set_editor_property('code','return lerp(Base,.5,saturate(Region));')
  if desc=='PKM20 fine exposed metal':n.set_editor_property('code','float coated=saturate(Region)*smoothstep(.3,.65,Metal); return lerp(Base,min(.86,.73+Detail.r*Strength*.08),coated);')
  if desc=='F37 coated roughness':n.set_editor_property('code','return lerp(Base,Center+clamp((Base-.604)*.24,-.016,.016),Region);')
  if desc=='F37 coating with restrained source variation':
   n.set_editor_property('code','float3 shade=clamp(Base/float3(.010960,.014444,.017642),.5,1.6); return lerp(Base,Tint*(.92+.08*shade),Region);')
 # Only generated panel relief is moderated. Its per-panel mask and original
 # UV0 normal/AO remain attached; no atlas from the 191 is used on this weapon.
 if name in ['M_LMG201_H39_Receiver','M_LMG201_H39_Handguard']:
  old=L.get_material_property_input_node(graph,u.MaterialProperty.MP_NORMAL);ch=L.get_material_property_input_node_output_name(graph,u.MaterialProperty.MP_NORMAL)
  if old:
   detail=custom(graph,'S41 restrained generated relief','return normalize(float3(N.xy*.78,N.z));',{'N':(old,ch)},True);output(detail,'',u.MaterialProperty.MP_NORMAL)
 if kind=='body':output(parameter(graph,'Specular',.5),'',u.MaterialProperty.MP_SPECULAR)
 if 'WeaponWetness' not in params:
  wet=parameter(graph,'WeaponWetness',0)
  for prop,code in [(u.MaterialProperty.MP_BASE_COLOR,'return Base*(1-saturate(Wet)*.10);'),(u.MaterialProperty.MP_ROUGHNESS,'return lerp(Base,max(.25,Base*.78),saturate(Wet));')]:
   old=L.get_material_property_input_node(graph,prop);ch=L.get_material_property_input_node_output_name(graph,prop)
   if old:output(custom(graph,'S41 single wet film',code,{'Base':(old,ch),'Wet':(wet,'')},prop==u.MaterialProperty.MP_BASE_COLOR),'',prop)
 graph.set_editor_property('used_with_skeletal_mesh',base.get_editor_property('used_with_skeletal_mesh'))
 errors=L.recompile_material(graph)
 if errors:raise RuntimeError('Material compile '+dest+' '+str(errors))
 E.set_metadata_tag(graph,'201FinishRevision','SightFinish41: QBZ191 current body reference; original UV0 and surface identities retained');save(graph);result=graph
 if instance:
  instpath=dest.replace('/M_S41_','/MI_S41_');result=u.load_asset(instpath) or E.duplicate_asset(path,instpath);L.set_material_instance_parent(result,graph)
  for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(result,k,v)
  for k,v in vectors.items():L.set_material_instance_vector_parameter_value(result,k,u.LinearColor(*v,1))
  L.set_material_instance_scalar_parameter_value(result,'WeaponWetness',0);L.update_material_instance(result);save(result)
 out['mapping'][path]=result.get_path_name();out['recipes'][path]={'kind':kind,'scalars':scalars,'vectors':vectors};(O/'materials.json').write_text(json.dumps(out,indent=2));print('S41_FINISH_SAVED',name,flush=True)
out['status']='compiled_and_saved';(O/'materials.json').write_text(json.dumps(out,indent=2));print('S41_MATERIALS_COMPLETE',len(out['mapping']),flush=True)
