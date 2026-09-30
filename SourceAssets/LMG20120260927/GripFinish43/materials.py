"""201 private finish revision: current UV/regions + clean-panel detail."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/GripFinish43';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();cap=json.loads((O/'capture.json').read_text());out={'status':'authoring','bindings':{},'jobs':{},'new_slots':{}}
if (O/'materials.json').exists():out=json.loads((O/'materials.json').read_text())
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,ch,b,pin):
 if not L.connect_material_expressions(a,ch,b,pin):raise RuntimeError('Link '+pin)
def output(n,ch,p):
 if not L.connect_material_property(n,ch,p):raise RuntimeError('Output '+str(p))
def custom(m,desc,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
 n=node(m,u.MaterialExpressionCustom,description=desc,code=code,output_type=kind);pins=[]
 for k in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
 n.set_editor_property('inputs',pins)
 for k,(s,ch) in inputs.items():wire(s,ch,n,k)
 return n
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def vector(m,name,v):return node(m,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*v,1))
def prop(m,p,fallback):
 n=L.get_material_property_input_node(m,p);return (n,L.get_material_property_input_node_output_name(m,p)) if n else (fallback,'')

textures={}
for key in ['Finish','MicroNormal']:
 name='T_LMG201_G43_'+key;path=P+'/Textures/'+name;t=u.load_asset(path)
 if not t:
  task=u.AssetImportTask();task.filename=str(O/'Textures'/(name+'.png'));task.destination_path=P+'/Textures';task.destination_name=name;task.automated=True;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(path)
 t.set_editor_property('srgb',False);t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='MicroNormal' else u.TextureCompressionSettings.TC_MASKS);save(t);textures[key]=t

def make(original,role,edge=False,skeletal=False):
 job=(original or 'new')+'|'+role+'|'+str(edge)+'|'+str(skeletal);tag=hashlib.sha1(job.encode()).hexdigest()[:10]
 if job in out['jobs']:return u.load_asset(out['jobs'][job]['asset'])
 path=P+'/Materials/M_G43_'+role+'_'+tag;a=u.load_asset(original) if original else None;base=a.get_base_material() if a else None
 partial=u.load_asset(path)
 if partial:E.delete_asset(path)
 m=E.duplicate_asset(base.get_path_name(),path) if base else A.create_asset(path.rsplit('/',1)[1],P+'/Materials',u.Material,u.MaterialFactoryNew())
 # Resolve instance texture/parameter overrides in the private graph before
 # replacing its finish layer. Old wet parameters become constant dry inputs.
 if isinstance(a,u.MaterialInstance):
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionScalarParameter):n.set_editor_property('default_value',L.get_material_instance_scalar_parameter_value(a,n.get_editor_property('parameter_name')))
   elif isinstance(n,u.MaterialExpressionVectorParameter):n.set_editor_property('default_value',L.get_material_instance_vector_parameter_value(a,n.get_editor_property('parameter_name')))
   elif isinstance(n,u.MaterialExpressionTextureSampleParameter):
    t=L.get_material_instance_texture_parameter_value(a,n.get_editor_property('parameter_name'))
    if t:n.set_editor_property('texture',t)
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='WeaponWetness':n.set_editor_property('parameter_name','G43_LegacyWetDisabled');n.set_editor_property('default_value',0.)
 zero=scalar(m,'G43_Zero',0.);flat=vector(m,'G43_FlatNormal',(0.,0.,1.));one=scalar(m,'G43_One',1.)
 oldbase=prop(m,u.MaterialProperty.MP_BASE_COLOR,vector(m,'G43_SourceDefault',(.025,.028,.033)));oldrough=prop(m,u.MaterialProperty.MP_ROUGHNESS,scalar(m,'G43_SourceRoughness',.40));oldmetal=prop(m,u.MaterialProperty.MP_METALLIC,scalar(m,'G43_SourceMetal',.73));oldnormal=prop(m,u.MaterialProperty.MP_NORMAL,flat)
 pos=node(m,u.MaterialExpressionPreSkinnedPosition);normal=node(m,u.MaterialExpressionPreSkinnedNormal);pi=node(m,u.MaterialExpressionVertexInterpolator);ni=node(m,u.MaterialExpressionVertexInterpolator);wire(pos,'',pi,'');wire(normal,'',ni,'');tex=node(m,u.MaterialExpressionTextureObject,texture=textures['Finish'])
 detail=custom(m,'G43 attached physical coating detail','float3 w=pow(abs(normalize(N)),4);w/=max(dot(w,1),.0001);float3 q=P/6.;return Texture2DSample(T,T'+ 'Sampler,q.yz)*w.x+Texture2DSample(T,TSampler,q.xz)*w.y+Texture2DSample(T,TSampler,q.xy)*w.z;',{'P':(pi,''),'N':(ni,''),'T':(tex,'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
 polymer=role=='polymer';satin=role=='satin';mixed=role=='mixed'
 color=(.010,.013,.016) if polymer else (.045,.050,.057) if satin else (.0175,.021,.0255)
 rough=.53 if polymer else .30 if satin else .385;metal=0. if polymer else .87 if satin else .68
 tint=vector(m,'G43_FinishTint',color);wear=vector(m,'G43_ExposedSteel',(.10,.115,.13));region=custom(m,'G43 material region','return smoothstep(.15,.55,M);' if mixed else 'return 1.;',{'M':oldmetal})
 vertex=node(m,u.MaterialExpressionVertexColor) if edge else zero
 wet=scalar(m,'WeaponWetness',0.);rpar=scalar(m,'G43_Roughness',rough);mpar=scalar(m,'G43_Metallic',metal)
 bc=custom(m,'G43 base coating and restrained wear','float v=dot(Base,float3(.2126,.7152,.0722));float3 tone=Tint*(.92+.16*D.g)*lerp(1.,clamp(v/.032,.6,1.6),.13);float e=saturate(Edge)*(.06+.18*D.a);tone=lerp(tone,Wear,e)+D.b*.0018;float3 result=lerp(Base,tone,Region);return result*(1-saturate(Wet)*.12);',{'Base':oldbase,'Tint':(tint,''),'Wear':(wear,''),'D':(detail,''),'Edge':(vertex,'R' if edge else ''),'Region':(region,''),'Wet':(wet,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
 rr=custom(m,'G43 roughness hierarchy and single wet film','float fresh=Center+(D.r-.5)*.045+(D.a-.5)*.075-D.b*.018-Edge*.04;float r=lerp(Base,clamp(fresh,.22,.68),Region);return lerp(r,max(.20,r*.73),saturate(Wet)*Region);',{'Base':oldrough,'Center':(rpar,''),'D':(detail,''),'Edge':(vertex,'R' if edge else ''),'Region':(region,''),'Wet':(wet,'')})
 mm=custom(m,'G43 material identity','return lerp(Base,Value,Region);',{'Base':oldmetal,'Value':(mpar,''),'Region':(region,'')})
 output(bc,'',u.MaterialProperty.MP_BASE_COLOR);output(rr,'',u.MaterialProperty.MP_ROUGHNESS);output(mm,'',u.MaterialProperty.MP_METALLIC)
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0,u_tiling=18.,v_tiling=18.);micro=node(m,u.MaterialExpressionTextureSample,texture=textures['MicroNormal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv,'',micro,'UVs')
 strength=.45 if polymer else .30;nn=custom(m,'G43 shallow micro normal','return normalize(float3(N.xy+Detail.xy*Strength,N.z));',{'N':oldnormal,'Detail':(micro,'RGB'),'Strength':(scalar(m,'G43_MicroNormalStrength',strength),'')},u.CustomMaterialOutputType.CMOT_FLOAT3);output(nn,'',u.MaterialProperty.MP_NORMAL)
 output(scalar(m,'G43_Specular',.42 if polymer else .5),'',u.MaterialProperty.MP_SPECULAR)
 m.set_editor_property('used_with_skeletal_mesh',skeletal);m.set_editor_property('used_with_morph_targets',False);m.set_editor_property('used_with_clothing',False);m.set_editor_property('automatically_set_usage_in_editor',False)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Compile '+path+': '+str(errors))
 E.set_metadata_tag(m,'201FinishRevision','GripFinish43: region-aware finish, physical roughness grain, restrained wear, preserved original UV relief');save(m);out['jobs'][job]={'asset':m.get_path_name(),'role':role,'source':original,'edge_mask':edge,'skeletal':skeletal};(O/'materials.json').write_text(json.dumps(out,indent=2));return m

usage={}
for path,row in cap['meshes'].items():
 for s in row['slots']:
  if s['material']:usage[s['material']]=usage.get(s['material'],False) or '/SK_' in path
for path,row in cap['meshes'].items():
 binds={};out['bindings'][path]=binds
 for slot in row['slots']:
  name=slot['slot'];source=slot['material']
  if not source or '/LMG201/' not in source or any(k in name for k in ['Manny','Cloth','Feed__','Inside','Interior','Lens','Glass']):continue
  original=u.load_asset(source);base=original.get_base_material()
  if base.get_editor_property('blend_mode') not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:continue
  if any(k in name for k in ['FactoryRearGrip','Polymer','FactoryStock']) or 'reargrip' in source.lower():role='polymer'
  elif any(k in name for k in ['Satin','Trigger','ChargingHandle']):role='satin'
  else:
   pars={str(n) for n in L.get_scalar_parameter_names(base)};role='mixed' if 'A762CoatingRoughness' in pars or 'PKM_SatinRoughness' in pars else 'coat'
  binds[name]=make(source,role,False,usage[source]).get_path_name()
for name,role,source,edge in [
 ('M_LMG201_G43_EdgeCoat','coat',None,True),
 ('M_LMG201_G43_GripPolymer','polymer',None,False),
 ('M_LMG201_G43_FactoryGrip','polymer','/Game/Weapons/LMG201/SightFinish41/Materials/M_S41_LMG201_F37_Surface_6b7dafeb',False),
 ('M_LMG201_G43_LidCoat','coat','/Game/Weapons/LMG201/SightFinish41/Materials/M_S41_LMG201_R38_Cover_d5d810cb',True)]:out['new_slots'][name]=make(source,role,edge,True).get_path_name()
out['status']='compiled_and_saved';(O/'materials.json').write_text(json.dumps(out,indent=2));print('G43_MATERIALS_SAVED',len(out['jobs']),flush=True)
