"""Compose the accepted bay city with the hub's existing HDR night sky."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV3/Sky'
SOURCE_SKY='/Game/PWL_Light_Manager/Shader/MI_HDR_Night_Sky'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing sky dependency '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Sky save failed '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Sky pin '+pin)
def custom(m,code,inputs):
 n=node(m,'Custom',code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,a in inputs.items():wire(a,n,name)
 return n
def sample(m,tex,name):
 return node(m,'TextureSampleParameterCube',parameter_name=name,texture=tex,
  sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
def material(name):
 path=BASE+'/'+name
 m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 return m
def import_sky():
 cubes={}
 for key,size in [('Far',4096),('Reflection',1024)]:
  t=u.AssetImportTask();t.filename=str(ROOT/'Sky'/('T_City'+key+'.dds'));t.destination_path=BASE;t.destination_name='T_City'+key
  t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t])
  tex=load(BASE+'/T_City'+key)
  for prop,value in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,
   lod_group=u.TextureGroup.TEXTUREGROUP_SKYBOX,max_texture_size=size,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():tex.set_editor_property(prop,value)
  save(tex);cubes[key]=tex
 sky=L.get_material_instance_texture_parameter_value(load(SOURCE_SKY),'Sky Cubemap')
 if not isinstance(sky,u.TextureCube):raise RuntimeError('Hub night preset has no cube')
 m=material('M_ApartmentHubSky')
 m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 m.set_editor_property('two_sided',True);m.set_editor_property('is_sky',True)
 cam=node(m,'CameraPositionWS');p=node(m,'WorldPosition')
 direction=custom(m,'return normalize(P-Cam);',{'P':p,'Cam':cam})
 citydir=custom(m,'return float3(-D.x,D.z,D.y);',{'D':direction})
 city=sample(m,cubes['Far'],'CityCube');wire(citydir,city,'UVs')
 night=sample(m,sky,'HubSky');wire(direction,night,'UVs')
 blend=node(m,'LinearInterpolate');wire(night,blend,'A','RGB');wire(city,blend,'B','RGB');wire(city,blend,'Alpha','A')
 slab=node(m,'SubstrateUnlitBSDF');wire(blend,slab,'EmissiveColor')
 black=node(m,'Constant3Vector',constant=u.LinearColor(0,0,0,1));wire(black,slab,'TransmittanceColor')
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 L.connect_material_property(blend,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 save(m)
 # Keep all accepted water optics; replace only the radiance input with city+hub sky.
 original=load('/Game/Props/CyberpunkBayLayered20261022/Materials/M_Bay_ClearwaterNight')
 path=BASE+'/M_WaterHubSky'
 water=load(path) if E.does_asset_exist(path) else A.duplicate_asset('M_WaterHubSky',BASE,original)
 expressions=list(L.get_material_expressions(water))
 city=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection')
 city.set_editor_property('texture',cubes['Reflection'])
 emission=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom) and 'Radiance * fresnel' in n.get_editor_property('code'))
 normal=L.get_material_property_input_node(water,u.MaterialProperty.MP_NORMAL)
 p=node(water,'WorldPosition');cam=node(water,'CameraPositionWS')
 direction=custom(water,'return reflect(normalize(P-Cam),normalize(N));',{'P':p,'Cam':cam,'N':normal})
 night=sample(water,sky,'HubSky');wire(direction,night,'UVs')
 blend=node(water,'LinearInterpolate');wire(night,blend,'A','RGB');wire(city,blend,'B','RGB');wire(city,blend,'Alpha','A')
 wire(blend,emission,'Radiance')
 errors=L.recompile_material(water)
 if errors:raise RuntimeError(str(errors))
 save(water)
 path=BASE+'/MI_WaterHubSky'
 mi=load(path) if E.does_asset_exist(path) else A.duplicate_asset('MI_WaterHubSky',BASE,load('/Game/Props/CyberpunkBayLayered20261022/Materials/MI_BayWater'))
 L.set_material_instance_parent(mi,water)
 L.set_material_instance_texture_parameter_value(mi,'BayReflection',cubes['Reflection'])
 L.update_material_instance(mi);save(mi)
 report=dict(stage='assets_saved',source=SOURCE_SKY,sky_cube=sky.get_path_name(),city_source_unchanged=True,tests_run=False)
 (ROOT/'sky-assets.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 return report

def apply_saved_sky(world):
 detailed=ROOT.parents[1]/'CyberpunkBayBuildings20261022'
 if (detailed/'installed.json').exists():
  import runpy
  result=runpy.run_path(str(detailed/'install_level.py'))['apply_saved_buildings'](world)
  return dict(source=SOURCE_SKY,detailed_city=result)
 sky=load(BASE+'/M_ApartmentHubSky');water=load(BASE+'/MI_WaterHubSky')
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
  if actor.get_actor_label()=='BAY_FarEnvironment':actor.static_mesh_component.set_material(0,sky)
  elif actor.get_actor_label()=='BAY_Water':actor.static_mesh_component.set_material(0,water)
 return dict(source=SOURCE_SKY,sky_material=sky.get_path_name(),water_material=water.get_path_name())
