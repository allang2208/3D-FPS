"""Own traffic shaders: synchronized motion, PBR, dusk-to-night vehicle lamps."""
from pathlib import Path
import unreal as u,json,runpy
R=Path(__file__).resolve().parent
PROJECT=R.parents[1]
OLD=PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV16'
BASE='/Game/Props/CyberpunkTrafficUpgrade20261026'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
H=runpy.run_path(str(OLD.parent/'RefinementV10/build_assets.py'))
node=H['node'];wire=H['wire'];custom=H['custom'];param=H['param']

def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing dependency '+p)
 return a

def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())

def record(report):(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')

def fresh(name):
 m=u.load_asset(BASE+'/Materials/'+name) or A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(m);return m

def motion(m):
 collection=load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV21/MPC_ApartmentClock')
 shifted=node(m,'Add');wire(node(m,'Time'),shifted,'A')
 offset=node(m,'CollectionParameter',collection=collection,parameter_name='ServerTimeOffset');wire(offset,shifted,'B')
 inputs=dict(Path=node(m,'TextureObjectParameter',parameter_name='Path',texture=load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV16/Textures/T_AP16_TrafficPath'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),UV=node(m,'TextureCoordinate',coordinate_index=1),Clock=shifted,Speed=param(m,'Speed',16.),RouteLength=param(m,'RouteLength',json.loads((OLD/'assembly.json').read_text(encoding='utf8'))['route_length_m']))
 wpo=custom(m,(OLD/'Traffic.hlsl').read_text(encoding='utf8'),dict(inputs,Position=node(m,'WorldPosition')),description='Original route, UV1 phase, synchronized clock')
 L.connect_material_property(wpo,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 E.set_metadata_tag(m,'AP21.Clock','1')
 return inputs

def night(m):
 # Atmosphere light index 0 is the existing moving sun. Start at low dusk sun.
 return custom(m,'return 1-smoothstep(-.035,.16,Sun.z);',dict(Sun=node(m,'SkyAtmosphereLightDirection',light_index=0)),1,description='Dusk automatic lamps, no independent timer')

def compile_save(m):
 errors=list(L.recompile_material(m))
 if errors:raise RuntimeError('Material production failed '+str(errors))
 save(m)

def main():
 report=json.loads((R/'assets_saved.json').read_text(encoding='utf8')) if (R/'assets_saved.json').exists() else dict(stage='building',materials={},meshes={})
 m=fresh('M_CT_Vehicle');m.set_editor_property('tangent_space_normal',False)
 inputs=motion(m);phase=inputs['UV'];uv=node(m,'TextureCoordinate')
 tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.16,.22,.28,1))
 # Stable per-vehicle palette derived from the same immutable phase as motion.
 base=custom(m,'''float k=fmod(floor(Phase.x*36+.1),6);
float3 p=k<1?float3(.12,.18,.23):k<2?float3(.46,.48,.44):k<3?float3(.18,.045,.035):k<4?float3(.055,.075,.085):k<5?float3(.15,.22,.18):float3(.34,.21,.09);
return lerp(Tint,p,Paint);''',dict(Tint=tint,Phase=phase,Paint=param(m,'PaintVariation',0)))
 rough=param(m,'Roughness',.32);metal=param(m,'Metallic',.55)
 sampled=node(m,'TextureSample',texture=load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Textures/T_AP7_Machined_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 wire(uv,sampled,'UVs')
 ts=custom(m,'return normalize(lerp(float3(0,0,1),N,Strength));',dict(N=sampled,Strength=param(m,'NormalStrength',.04)))
 world=node(m,'Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
 wire(ts,world,'')
 normal=custom(m,(OLD/'TrafficNormal.hlsl').read_text(encoding='utf8'),dict(inputs,N=world),description='PBR tangent normal follows vehicle rotation')
 emission=custom(m,'return Tint*lerp(DayGlow,NightGlow,Night);',dict(Tint=tint,DayGlow=param(m,'DayGlow',0),NightGlow=param(m,'NightGlow',0),Night=night(m)),description='Independent daytime running lights and nighttime low beams')
 slab=node(m,'SubstrateShadingModels')
 for a,pin,prop in [(base,'BaseColor','BASE_COLOR'),(rough,'Roughness','ROUGHNESS'),(metal,'Metallic','METALLIC'),(normal,'Normal','NORMAL'),(emission,'EmissiveColor','EMISSIVE_COLOR')]:
  wire(a,slab,pin);L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+prop))
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);compile_save(m);report['materials']['Master']=m.get_path_name();record(report)
 specs={
  'Body':((.16,.22,.28),.25,.72,0,0,.035,1),
  'Glass':((.008,.021,.031),.13,.28,0,0,0,0),
  'Rubber':((.009,.011,.014),.87,0,0,0,.06,0),
  'Alloy':((.34,.39,.43),.27,.92,0,0,.12,0),
  'Trim':((.018,.024,.03),.49,.15,0,0,.025,0),
  'Headlamp':((.78,.88,1),.18,.15,0,34,0,0),
  'DRL':((.75,.87,1),.20,.10,1.2,12,0,0),
  'Tail':((1,.012,.004),.24,.10,0,16,0,0),
  'Amber':((1,.18,.008),.24,.10,0,3,0,0)}
 for role,(rgb,roughness,metallic,day,ng,norm,var) in specs.items():
  name='MI_CT_'+role;mi=u.load_asset(BASE+'/Materials/'+name) or A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.set_material_instance_parent(mi,m);L.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*rgb,1))
  for key,v in dict(Roughness=roughness,Metallic=metallic,DayGlow=day,NightGlow=ng,NormalStrength=norm,PaintVariation=var).items():L.set_material_instance_scalar_parameter_value(mi,key,float(v))
  L.update_material_instance(mi);save(mi);report['materials'][role]=mi.get_path_name()
 record(report)
 pool=fresh('M_CT_HeadlightPool');motion(pool);pool.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);pool.set_editor_property('two_sided',True)
 mask=custom(pool,'''float x=saturate(UV.x);float y=abs(UV.y*2-1);
return smoothstep(0,.09,x)*(1-smoothstep(.20,1,x))*pow(saturate(1-y*y),3)*Night;''',dict(UV=node(pool,'TextureCoordinate'),Night=night(pool)),1,description='Soft low-beam footprint fades completely in daylight')
 color=custom(pool,'return float3(.58,.72,1)*Mask*Gain;',dict(Mask=mask,Gain=param(pool,'PoolGain',.85)))
 slab=node(pool,'SubstrateUnlitBSDF');wire(color,slab,'EmissiveColor');wire(node(pool,'Constant3Vector',constant=u.LinearColor(1,1,1,1)),slab,'TransmittanceColor')
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);L.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.connect_material_property(node(pool,'Constant',r=1),'',u.MaterialProperty.MP_OPACITY)
 compile_save(pool);report['materials']['Pool']=pool.get_path_name();report['stage']='materials_saved';record(report)
 print('TRAFFIC_MATERIALS_SAVED',len(report['materials']))
if __name__=='__main__':main()
