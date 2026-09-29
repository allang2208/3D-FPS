"""Ward-local glass, persistent dry blood, and synchronized fixture/light fault materials."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/IsolationWard20260929/Materials'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
saved=[]
def make(name,domain=u.MaterialDomain.MD_SURFACE,blend=u.BlendMode.BLEND_OPAQUE):
 path=BASE+'/'+name
 if path in dirty:raise RuntimeError('Preserve unsaved ward material '+path)
 m=u.load_asset(path) or A.create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
 m.modify();L.delete_all_material_expressions(m);m.set_editor_property('material_domain',domain);m.set_editor_property('blend_mode',blend)
 m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 if domain==u.MaterialDomain.MD_SURFACE:
  m.set_editor_property('used_with_instanced_static_meshes',True)
  if blend==u.BlendMode.BLEND_OPAQUE:m.set_editor_property('used_with_nanite',True)
 return m
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,dst,pin):
 n,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Cannot wire '+pin)
def prop(m,n,key):
 if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Cannot author '+key)
def scalar(m,key,value):return node(m,'ScalarParameter',parameter_name=key,default_value=value)
def color(m,key,rgb):return node(m,'VectorParameter',parameter_name=key,default_value=u.LinearColor(*rgb,1))
def custom(m,code,inputs,w=1):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(w)))
 pins=[]
 for key in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
 n.set_editor_property('inputs',pins)
 for key,value in inputs.items():wire(value,n,key)
 return n
def surface(m,inputs,decal=False):
 slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
 for key,value in inputs.items():
  prop(m,value,key);wire(value,slab,{'BASE_COLOR':'BaseColor','ROUGHNESS':'Roughness','SPECULAR':'Specular',
                                  'OPACITY':'Opacity','NORMAL':'Normal','EMISSIVE_COLOR':'Emissive Color','METALLIC':'Metallic'}[key])
 if decal:
  dec=node(m,'SubstrateConvertToDecal');wire(slab,dec,str(L.get_material_expression_input_names(dec)[0]));wire(inputs['OPACITY'],dec,'Coverage');slab=dec
 prop(m,slab,'FRONT_MATERIAL')
def save(m):
 if isinstance(m,u.Material):
  errors=L.recompile_material(m)
  if errors:raise RuntimeError('Ward material build failed '+str(errors))
  L.layout_material_expressions(m)
 if not E.save_loaded_asset(m,False):raise RuntimeError('Cannot save '+m.get_path_name())
 saved.append(m.get_path_name())
def instance(name,parent,params,colors=None):
 path=BASE+'/'+name
 if path in dirty:raise RuntimeError('Preserve unsaved '+path)
 mi=u.load_asset(path) or A.create_asset(name,BASE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 mi.modify();L.set_material_instance_parent(mi,parent)
 for k,v in params.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
 for k,v in (colors or {}).items():L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v,1))
 L.update_material_instance(mi);save(mi);return mi

glass=make('M_WardGlassV2',blend=u.BlendMode.BLEND_TRANSLUCENT)
glass.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
glass.set_editor_property('two_sided',False);glass.set_editor_property('screen_space_reflections',True)
glass.set_editor_property('disable_depth_test',False)
uv=node(glass,'TextureCoordinate');fresnel=node(glass,'Fresnel')
dust=custom(glass,'''
float2 q=UV*float2(17,23);float2 i=floor(q),f=frac(q);f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
float n=lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
float border=pow(saturate(1-min(min(UV.x,1-UV.x),min(UV.y,1-UV.y))/.11),2);
float wipe=pow(saturate(.5+.5*sin(UV.x*9+UV.y*3+sin(UV.y*11)*.38)),8);
return saturate(border*(.50+.50*n)+wipe*n*.14);
''',{'UV':uv})
surface(glass,{'BASE_COLOR':color(glass,'GlassTint',(.72,.79,.76)),
 'METALLIC':scalar(glass,'Metallic',0),'SPECULAR':scalar(glass,'Specular',.5),
 'ROUGHNESS':custom(glass,'return .075+D*.24;',{'D':dust}),
 'OPACITY':custom(glass,'return clamp(.027+F*.23+D*.16,.027,.35);',{'F':fresnel,'D':dust}),
 'NORMAL':custom(glass,'return normalize(float3(sin(UV.y*137)*.0018,sin(UV.x*83+UV.y*3)*.001,1));',{'UV':uv},3)})
save(glass)

# Time is evaluated by both shaders; no Actor Tick, per-frame actor lookup or timer allocation.
fault_code='''
float c=fmod(T+Phase,13.7);float a=1;
if(c<.10)a=.08;else if(c<.22)a=.76;else if(c<.37)a=.04;else if(c<.56)a=.44;
else if(c>6.1&&c<6.23)a=.14;else if(c>6.28&&c<6.40)a=.42;
else if(c>10.7&&c<11.65)a=.12;
return lerp(1,a,Fault)*(1-Dead);
'''
function=make('M_WardLampFunctionV2',u.MaterialDomain.MD_LIGHT_FUNCTION)
factor=custom(function,fault_code,{'T':node(function,'Time'),'Phase':scalar(function,'Phase',0),
                                 'Fault':scalar(function,'Fault',1),'Dead':scalar(function,'Dead',0)})
prop(function,factor,'EMISSIVE_COLOR');save(function)
fixture=make('M_WardLampDiffuserV2')
factor=custom(fixture,fault_code,{'T':node(fixture,'Time'),'Phase':scalar(fixture,'Phase',0),
                                'Fault':scalar(fixture,'Fault',0),'Dead':scalar(fixture,'Dead',0)})
emission=custom(fixture,'return Tint*Factor*2.1;',{'Tint':color(fixture,'LampTint',(.63,.78,1)),'Factor':factor},3)
surface(fixture,{'BASE_COLOR':color(fixture,'DiffuserColor',(.22,.25,.26)),
                 'ROUGHNESS':scalar(fixture,'Roughness',.46),'SPECULAR':scalar(fixture,'Specular',.28),'EMISSIVE_COLOR':emission})
save(fixture)
cfg=json.loads((ROOT/'Config/room.json').read_text(encoding='utf-8'))
for s in cfg['lights']:
 pars=dict(Phase=s['phase'],Fault=float(s['fault']=='flicker'),Dead=float(s['fault']=='dead'))
 # Stable fixtures share two instances; faults retain their independent phases.
 key=s['id'] if s['fault']!='steady' else 'Warm' if s['warm'] else 'Cool'
 if BASE+'/MI_Diffuser_'+key+'.MI_Diffuser_'+key not in saved:
  instance('MI_Diffuser_'+key,fixture,pars,dict(LampTint=(1,.65,.34) if s['warm'] else (.63,.78,1)))
 if s['fault']=='flicker':instance('MI_LampFunction_'+s['id'],function,pars)

blood=make('M_WardDryBloodV2',u.MaterialDomain.MD_DEFERRED_DECAL,u.BlendMode.BLEND_TRANSLUCENT)
decal=node(blood,'DecalColor');drops=node(blood,'TextureObject',texture=u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Droplets_A'))
shape=custom(blood,(PROJECT/'SourceAssets/FluidPolish20260924/BloodStain.hlsl').read_text(encoding='utf-8'),
 {'UV':node(blood,'TextureCoordinate'),'Seed':(decal,'R'),'Wall':(decal,'B'),
  'Born':scalar(blood,'FixedBorn',0),'Clock':scalar(blood,'FixedAge',100),'Drops':drops})
surface(blood,{'BASE_COLOR':color(blood,'DriedBloodTint',(.060,.009,.006)),
 'OPACITY':custom(blood,'return Shape*.79;',{'Shape':shape}),
 'ROUGHNESS':scalar(blood,'DryRoughness',.79),'SPECULAR':scalar(blood,'DrySpecular',.25)},True)
save(blood)
(ROOT/'Receipts/materials-v2.json').write_text(json.dumps(dict(stage='materials_saved',assets=saved,tests_run=False),indent=2),encoding='utf-8')
print('WARD_ATMOSPHERE_MATERIALS_SAVED',len(saved),flush=True)
