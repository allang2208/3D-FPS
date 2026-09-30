"""Private 201 finish family. No 191/shared material or cloth reload asset writes."""
import unreal as u, json, hashlib
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/SurfaceFinish50'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
cap=json.loads((O/'Inputs/assets.json').read_text());model=json.loads((O/'model.json').read_text())
out=json.loads((O/'materials.json').read_text()) if (O/'materials.json').exists() else {'jobs':{},'bindings':{},'new_slots':{}}
def record():(O/'materials.json').write_text(json.dumps(out,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
def node(m,c,**props):
 n=L.create_material_expression(m,c)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def scalar(m,name,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=v)
def vector(m,name,v):return node(m,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*v,1))
def wire(a,ch,b,pin):
 if not L.connect_material_expressions(a,ch,b,pin):raise RuntimeError('Connect '+pin)
def output(a,ch,prop):
 if not L.connect_material_property(a,ch,prop):raise RuntimeError('Connect '+str(prop))
def custom(m,desc,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
 n=node(m,u.MaterialExpressionCustom,description=desc,code=code,output_type=kind);pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,(a,ch) in inputs.items():wire(a,ch,n,name)
 return n
def settings(role):
 if role in ['polymer','grip']:return (.012,.015,.018),.455,0.,.015
 if role=='rubber':return (.009,.011,.013),.63,0.,.018
 if role in ['satin','stock_mount']:return (.044,.049,.056),.30,.87,.024
 return (.02810,.03179,.03532),.357,.73,.023

def make(source=None,role='coat',skeletal=False):
 key=(source or 'new')+'|'+role+'|'+str(skeletal)
 if key in out['jobs']:return load(out['jobs'][key]['asset'])
 path=P+'/Materials/M_F50_'+role+'_'+hashlib.sha1(key.encode()).hexdigest()[:10]
 m=u.load_asset(path)
 if m:E.delete_asset(path)
 original=load(source) if source else None
 m=E.duplicate_asset(original.get_base_material().get_path_name(),path) if original else A.create_asset(path.rsplit('/',1)[1],P+'/Materials',u.Material,u.MaterialFactoryNew())
 tint,rough,metal,amp=settings(role)
 if original:
  if isinstance(original,u.MaterialInstance):
   for n in L.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionScalarParameter):n.set_editor_property('default_value',L.get_material_instance_scalar_parameter_value(original,n.get_editor_property('parameter_name')))
    elif isinstance(n,u.MaterialExpressionVectorParameter):n.set_editor_property('default_value',L.get_material_instance_vector_parameter_value(original,n.get_editor_property('parameter_name')))
    elif isinstance(n,u.MaterialExpressionTextureSampleParameter):
     tex=L.get_material_instance_texture_parameter_value(original,n.get_editor_property('parameter_name'))
     if tex:n.set_editor_property('texture',tex)
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionScalarParameter):
    name=str(n.get_editor_property('parameter_name'))
    if name=='G43_Roughness':n.set_editor_property('default_value',rough)
    elif name=='G43_Metallic':n.set_editor_property('default_value',metal)
    elif name=='G43_MicroNormalStrength':n.set_editor_property('default_value',0.)
   elif isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='G43_FinishTint':n.set_editor_property('default_value',u.LinearColor(*tint,1))
   elif isinstance(n,u.MaterialExpressionCustom):
    desc=n.get_editor_property('description')
    if desc=='G43 roughness hierarchy and single wet film':
     n.set_editor_property('code','float fresh=Center+(D.r-.5)*'+str(amp)+'+(D.a-.5)*.020-D.b*.006-Edge*.018;float r=lerp(Base,clamp(fresh,.24,.70),Region);return lerp(r,max(.20,r*.78),saturate(Wet)*Region);')
    elif desc=='G43 base coating and restrained wear':
     n.set_editor_property('code','float v=dot(Base,float3(.2126,.7152,.0722));float3 tone=Tint*(.985+.03*D.g)*lerp(1.,clamp(v/.032,.7,1.3),.08);float e=saturate(Edge)*(.035+.065*D.a);tone=lerp(tone,Wear,e);return lerp(Base,tone,Region)*(1-saturate(Wet)*.12);')
  n=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
  if n:
   ch=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)
   strength=.75 if role in ['grip','polymer'] else .60
   n=custom(m,'F50 retained structural relief, no added grain bump','return normalize(float3(N.xy*Strength,lerp(1.,N.z,Strength)));',{'N':(n,ch),'Strength':(scalar(m,'F50_StructuralNormalStrength',strength),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
   output(n,'',u.MaterialProperty.MP_NORMAL)
 else:
  # One physical texel density across newly authored surfaces. No old atlas
  # normal/AO is evaluated on their new UVs; geometry provides the hard relief.
  pos=node(m,u.MaterialExpressionPreSkinnedPosition);normal=node(m,u.MaterialExpressionPreSkinnedNormal)
  pi=node(m,u.MaterialExpressionVertexInterpolator);ni=node(m,u.MaterialExpressionVertexInterpolator);wire(pos,'',pi,'');wire(normal,'',ni,'')
  tex=node(m,u.MaterialExpressionTextureObject,texture=load('/Game/Weapons/LMG201/GripFinish43/Textures/T_LMG201_G43_Finish'))
  detail=custom(m,'F50 shared 6 cm coating texture','float3 w=pow(abs(normalize(N)),4);w/=max(dot(w,1),.0001);float3 q=P/6.;return Texture2DSample(T,TSampler,q.yz)*w.x+Texture2DSample(T,TSampler,q.xz)*w.y+Texture2DSample(T,TSampler,q.xy)*w.z;',{'P':(pi,''),'N':(ni,''),'T':(tex,'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
  wet=scalar(m,'WeaponWetness',0.);color=vector(m,'F50_FinishTint',tint);r=scalar(m,'F50_Roughness',rough)
  bc=custom(m,'F50 restrained coating color','return Tint*(.985+.03*D.g)*(1-saturate(Wet)*.12);',{'Tint':(color,''),'D':(detail,''),'Wet':(wet,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
  rr=custom(m,'F50 fine roughness and one wet film','float r=clamp(Center+(D.r-.5)*Amplitude+(D.a-.5)*.020-D.b*.006,.24,.70);return lerp(r,max(.20,r*.78),saturate(Wet));',{'Center':(r,''),'Amplitude':(scalar(m,'F50_GrainAmplitude',amp),''),'D':(detail,''),'Wet':(wet,'')})
  output(bc,'',u.MaterialProperty.MP_BASE_COLOR);output(rr,'',u.MaterialProperty.MP_ROUGHNESS)
  output(scalar(m,'F50_Metallic',metal),'',u.MaterialProperty.MP_METALLIC)
  output(scalar(m,'F50_Specular',.42 if metal==0 else .5),'',u.MaterialProperty.MP_SPECULAR)
  output(vector(m,'F50_GeometricNormal',(0.,0.,1.)),'',u.MaterialProperty.MP_NORMAL)
  output(scalar(m,'F50_CleanAO',1.),'',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 m.set_editor_property('used_with_skeletal_mesh',skeletal);m.set_editor_property('automatically_set_usage_in_editor',False)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compile '+path+' '+str(errors))
 E.set_metadata_tag(m,'201FinishRevision','SurfaceFinish50: fine physical coating, differentiated metal/polymer, no added grain bump');save(m)
 out['jobs'][key]={'asset':m.get_path_name(),'source':source,'role':role,'roughness':rough,'metallic':metal,'skeletal':skeletal};record();print('F50_MATERIAL_SAVED',path,flush=True)
 return m

# Restrict old graphs to the existing 201 private finish family. Reticles,
# glass, interiors, cloth, cartridge links and all cloth props stay untouched.
for path,row in cap['meshes'].items():
 if '/Cloth' in path:continue
 binds={};out['bindings'][path]=binds
 for slot in row['slots']:
  name=slot['name'];source=slot['material']
  if not source or not any(p in source for p in ['/GripFinish43/','/GripJunction44/']):continue
  if any(k in name for k in ['Cloth','Feed__','Inside','Interior','Lens','Glass','Manny']):continue
  meta=cap['materials'].get(source,{})
  if '/GripJunction44/' in source:role='grip'
  elif 'M_G43_polymer_' in source:role='polymer'
  elif 'M_G43_satin_' in source:role='satin'
  elif 'M_G43_mixed_' in source:role='mixed'
  else:role='coat'
  binds[name]=make(source,role,row['skeletal']).get_path_name()

body_slots={s['name']:s['material'] for s in cap['meshes'][model['body']]['slots']}
for name,role in model['roles'].items():
 if name in body_slots:
  if role=='stock_mount':source=body_slots[name];role='stock_mount'
  else:
   out['new_slots'][name]=out['bindings'][model['body']].get(name,body_slots[name]);continue
 else:source=None
 out['new_slots'][name]=make(source,role,True).get_path_name()
out['status']='compiled_and_saved';record();print('F50_FINISH_FAMILY_SAVED',len(out['jobs']),flush=True)
