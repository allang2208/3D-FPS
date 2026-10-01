"""Receiver-matched HK416 attachment finishes, preserving structural UV0/maps."""
import unreal as u,re
from pathlib import Path
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
D='/Game/Weapons/HK416/CommonAttachments20260930'
F='/Game/Weapons/HK416/AttachmentSurface20261001'
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing finish input '+path)
 return obj
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,n,pin):
 obj,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(obj,out,n,pin):raise RuntimeError('Finish input '+pin)
def output(src,prop):
 obj,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(obj,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Finish output '+prop)
def current(m,prop,fallback):
 p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
 return (n,L.get_material_property_input_node_output_name(m,p)) if n else node(m,u.MaterialExpressionConstant,r=fallback)
def custom(m,code,inputs,size):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n
def sample(m,key,uv):
 sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
 n=node(m,u.MaterialExpressionTextureSample,texture=load(D+'/Textures/T_HK416_Coat_'+key),sampler_type=sampler)
 wire(uv,n,'UVs');return (n,'RGB' if key in ('BaseColor','Normal') else 'R')
def compile_save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('HK416 finish compilation '+m.get_name()+': '+str(errors))
 save(m)

class SurfaceLibrary:
 def __init__(self):self.wet={};self.records={}
 def material(self,key,slot,path):
  label=(slot+' '+(path or '')).lower()
  # Optical surfaces, engravings/index markings, recesses and soft butt pads
  # retain their functional source materials. Native HK atlases stay on UV0.
  if (path and '/HK416/' in path) or key=='ext_mag' or any(s in label for s in ('glass','reticle','lens','rubber','recess','interior','titanium')) or slot=='DrumIndex':return load(path)
  name='M_HK416_'+key+'_'+re.sub('[^A-Za-z0-9_]','_',slot)+'_Matched'
  m=u.load_asset(F+'/'+name);w=u.load_asset(F+'/'+name+'_Wet')
  if m and w:
   self.wet[m.get_path_name()]=w;self.records[name]={'source':path,'dry':m.get_path_name(),'wet':w.get_path_name()};return m
  if m:raise RuntimeError('Incomplete finish asset '+m.get_path_name())
  if path:
   source=load(path);m=A.duplicate_asset(name,F,source.get_base_material())
   if isinstance(source,u.MaterialInstanceConstant):
    for n in L.get_material_expressions(m):
     parameter=n.get_editor_property('parameter_name') if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter,u.MaterialExpressionStaticSwitchParameter)) else None
     if isinstance(n,u.MaterialExpressionScalarParameter):n.set_editor_property('default_value',L.get_material_instance_scalar_parameter_value(source,parameter))
     elif isinstance(n,u.MaterialExpressionVectorParameter):n.set_editor_property('default_value',L.get_material_instance_vector_parameter_value(source,parameter))
     elif isinstance(n,u.MaterialExpressionTextureSampleParameter):n.set_editor_property('texture',L.get_material_instance_texture_parameter_value(source,parameter))
     elif isinstance(n,u.MaterialExpressionStaticSwitchParameter):n.set_editor_property('default_value',L.get_material_instance_static_switch_parameter_value(source,parameter))
  else:m=A.create_asset(name,F,u.Material,u.MaterialFactoryNew())
  base=current(m,'BASE_COLOR',.04);rough=current(m,'ROUGHNESS',.58);metal=current(m,'METALLIC',0.)
  n=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
  normal=(n,L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)) if n else node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1))
  full=not path or any(s in slot.lower() for s in ('metal','collar','adapter','saddle','fastener')) or key in ('panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','tactical_suppressor','phantom_reargrip')
  polymer='polymer' in slot.lower() or (key=='stable_antislip_reargrip' and 'collar' not in slot.lower() and path is not None)
  mask=node(m,u.MaterialExpressionConstant,r=0. if polymer else 1.) if polymer or full else custom(m,'return smoothstep(.18,.55,Metal);',{'Metal':metal},1)
  uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=3)
  coat=sample(m,'BaseColor',uv)
  # Keep texture variation on polymer but constrain its value to the host's
  # dark finish. Metal masking must not reject pale donor albedo pixels.
  poly=custom(m,'return Coat*.42*clamp(dot(Base,float3(.2126,.7152,.0722))/.12,.7,1.4);',{'Base':base,'Coat':coat},3)
  for prop,a,b in [('BASE_COLOR',poly,coat),('METALLIC',node(m,u.MaterialExpressionConstant,r=0.),sample(m,'Metallic',uv)),('ROUGHNESS',custom(m,'return max(Base,.60);',{'Base':rough},1),sample(m,'Roughness',uv))]:
   blend=node(m,u.MaterialExpressionLinearInterpolate);wire(a,blend,'A');wire(b,blend,'B');wire(mask,blend,'Alpha');output(blend,prop)
  output(custom(m,'return normalize(float3(Base.xy+Fine.xy*.15*Mask,Base.z));',{'Base':normal,'Fine':sample(m,'Normal',uv),'Mask':mask},3),'NORMAL')
  m.set_editor_property('automatically_set_usage_in_editor',False);m.set_editor_property('used_with_skeletal_mesh',False)
  E.set_metadata_tag(m,'HK416Finish','Reworked Upper_Body receiver patch (1022,417,48,48); UV3 4cm; source UV0 normal/AO retained; separate polymer and metal response')
  compile_save(m)
  w=A.duplicate_asset(name+'_Wet',F,m)
  base=current(w,'BASE_COLOR',.03);rough=current(w,'ROUGHNESS',.5);normal=L.get_material_property_input_node(w,u.MaterialProperty.MP_NORMAL)
  beads=custom(w,(Path(__file__).parent.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text(),{'UV':node(w,u.MaterialExpressionTextureCoordinate),'Wet':node(w,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)},4)
  output(custom(w,'return Base*(1-Data.a*.055);',{'Base':base,'Data':beads},3),'BASE_COLOR')
  output(custom(w,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1),'ROUGHNESS')
  output(custom(w,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':normal,'Data':beads},3),'NORMAL')
  compile_save(w);self.wet[m.get_path_name()]=w
  self.records[name]={'source':path,'dry':m.get_path_name(),'wet':w.get_path_name()};return m
