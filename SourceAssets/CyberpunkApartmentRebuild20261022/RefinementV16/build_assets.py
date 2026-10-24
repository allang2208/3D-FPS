"""Build shared display, street and GPU traffic assets, then save shader programs."""
from pathlib import Path
import unreal as u,json,runpy,gc
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
helper=runpy.run_path(str(R.parent/'RefinementV10/build_assets.py'))
node=helper['node'];wire=helper['wire'];custom=helper['custom'];param=helper['param']
report=dict(stage='building',materials={},meshes={},textures={})
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing AP16 dependency '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def duplicate(name,old,folder='Materials'):
 p=BASE+'/'+folder+'/'+name
 return load(p) if E.does_asset_exist(p) else A.duplicate_asset(name,BASE+'/'+folder,load(old))
def compile_save(m):
 errors=list(L.recompile_material(m))
 if errors:raise RuntimeError(str(errors))
 stats=L.get_statistics(m)
 if stats.get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('No compiled pixel program '+m.get_name())
 save(m);report['materials'][m.get_name()]=m.get_path_name();record()
def instance(name,parent,scalars={},color=None):
 p=BASE+'/Materials/'+name;m=load(p) if E.does_asset_exist(p) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 L.set_material_instance_parent(m,parent)
 for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(m,k,float(v))
 if color:L.set_material_instance_vector_parameter_value(m,'Tint',u.LinearColor(*color,1))
 L.update_material_instance(m);save(m);report['materials'][name]=m.get_path_name();return m
def texture_copy(name,source):
 t=duplicate(name,source,'Textures');t.set_editor_property('never_stream',True);t.set_editor_property('lod_bias',0);t.set_editor_property('max_texture_size',2048);save(t);report['textures'][name]=t.get_path_name();return t
def displays():
 atlas=texture_copy('T_AP16_Campaign','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV8/Textures/T_AP8_CampaignAtlas_BC')
 ticker=texture_copy('T_AP16_Ticker','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV8/Textures/T_AP8_Ticker_BC')
 for kind in ['Portrait','Ribbon']:
  m=duplicate('M_AP16_'+kind,'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV10/Materials/M_AP10_'+kind)
  count=0
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionCustom) and 'float2 Foot=max(abs(ddx(UV))' in str(n.get_editor_property('code')):
    n.set_editor_property('code',(R/(kind+'.hlsl')).read_text());count+=1
   if isinstance(n,u.MaterialExpressionTextureObjectParameter):
    key=str(n.get_editor_property('parameter_name'))
    if key in ['CampaignAtlas','TickerAtlas']:n.set_editor_property('texture',atlas if key=='CampaignAtlas' else ticker)
  if count!=1:raise RuntimeError('Display source changed '+kind)
  compile_save(m)
 for b in C['BOARDS']:
  m=duplicate('MI_AP16_'+b['key'],'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV10/Materials/MI_AP10_'+b['key'])
  L.set_material_instance_parent(m,load(report['materials']['M_AP16_'+b['kind'].title()]));L.set_material_instance_texture_parameter_value(m,'CampaignAtlas',atlas);L.set_material_instance_texture_parameter_value(m,'TickerAtlas',ticker);L.update_material_instance(m);save(m);report['materials'][m.get_name()]=m.get_path_name()
 # Same artwork timeline and searchlight trajectory in the existing water.
 m=duplicate('M_AP16_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV15/Materials/M_AP15_BayWater');count=0
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='AP10 coherent billboard and sweeping beam water reflections':n.set_editor_property('code',(R/'WaterReflection.hlsl').read_text());count+=1
 if count!=1:raise RuntimeError('Water emitter branch changed')
 compile_save(m);mi=duplicate('MI_AP16_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV15/Materials/MI_AP15_BayWater');L.set_material_instance_parent(mi,m);L.update_material_instance(mi);save(mi);report['materials'][mi.get_name()]=mi.get_path_name();record()
def street_materials():
 task=u.AssetImportTask();task.filename=str(R/'T_AP16_TrafficPath.exr');task.destination_path=BASE+'/Textures';task.destination_name='T_AP16_TrafficPath';task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task]);path=load(BASE+'/Textures/T_AP16_TrafficPath')
 for k,v in dict(srgb=False,compression_settings=u.TextureCompressionSettings.TC_HDR_F32,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_CLAMP,filter=u.TextureFilter.TF_BILINEAR).items():path.set_editor_property(k,v)
 save(path);report['textures']['Path']=path.get_path_name();route=json.loads((R/'assembly.json').read_text())['route_length_m']
 for moving in [False,True]:
  name='M_AP16_Traffic' if moving else 'M_AP16_Street';p=BASE+'/Materials/'+name
  m=load(p) if E.does_asset_exist(p) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
  m.set_editor_property('tangent_space_normal',not moving)
  tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.1,.15,.2,1));rough=param(m,'Roughness',.5);metal=param(m,'Metallic',0);gain=param(m,'Glow',0)
  night=helper['night'](m);emission=custom(m,'return Tint*Glow*lerp(.12,1,Night);',{'Tint':tint,'Glow':gain,'Night':night})
  if moving:
   obj=node(m,'TextureObjectParameter',parameter_name='Path',texture=path,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
   inputs=dict(Path=obj,UV=node(m,'TextureCoordinate',coordinate_index=1),Clock=node(m,'Time'),Speed=param(m,'Speed',C['TRAFFIC_SPEED']),RouteLength=param(m,'RouteLength',route))
   wpo=custom(m,(R/'Traffic.hlsl').read_text(),dict(inputs,Position=node(m,'WorldPosition')));L.connect_material_property(wpo,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
   normal=custom(m,(R/'TrafficNormal.hlsl').read_text(),dict(inputs,N=node(m,'VertexNormalWS')))
  else:
   n=node(m,'TextureSample',texture=load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Textures/T_AP7_Machined_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
   normal=custom(m,'return normalize(lerp(float3(0,0,1),N,Strength));',{'N':n,'Strength':param(m,'NormalStrength',.25)})
  slab=node(m,'SubstrateShadingModels')
  for a,pin,prop in [(tint,'BaseColor','BASE_COLOR'),(rough,'Roughness','ROUGHNESS'),(metal,'Metallic','METALLIC'),(normal,'Normal','NORMAL'),(emission,'EmissiveColor','EMISSIVE_COLOR')]:wire(a,slab,pin);L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+prop))
  L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);compile_save(m)
 specs={'Asphalt':((.035,.045,.055),.85,0,0),'Concrete':((.24,.28,.3),.8,0,0),'Paint':((.65,.63,.49),.7,0,0),'Bark':((.11,.075,.05),.95,0,0),'Leaves':((.08,.19,.12),.85,0,0),'Metal':((.12,.16,.2),.4,.65,0),'Cyan':((.05,.6,.85),.4,.1,2),'Warm':((.9,.62,.28),.45,0,2),'Glass':((.02,.08,.12),.18,.45,0),'Tire':((.018,.021,.025),.9,0,0),'Headlamp':((.65,.85,1),.3,0,2),'Tail':((1,.025,.012),.3,0,1.8),'Body':((.23,.32,.36),.32,.5,0)}
 for moving in [False,True]:
  for role,(rgb,rough,metal,glow) in specs.items():
   if moving and role not in ['Body','Glass','Tire','Metal','Headlamp','Tail']:continue
   if not moving and role in ['Body','Glass','Tire','Headlamp','Tail']:continue
   instance('MI_AP16_'+('Traffic_' if moving else '')+role,load(report['materials']['M_AP16_Traffic' if moving else 'M_AP16_Street']),dict(Roughness=rough,Metallic=metal,Glow=glow),rgb)
 record()
def meshes(selected=None):
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  if selected and row['key'] not in selected:continue
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False
  d=o.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(report['materials']['MI_AP16_'+('Traffic_' if row['traffic'] else '')+str(s.material_slot_name)]))
  bs=SM.get_lod_build_settings(mesh,0);bs.use_full_precision_u_vs=True;bs.recompute_normals=False;bs.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,bs)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=not row['traffic'];ns.explicit_tangents=True;mesh.set_editor_property('nanite_settings',ns)
  if not row['traffic'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed')
  if row['traffic']:
   mesh.set_editor_property('positive_bounds_extension',u.Vector(15000,15000,1500));mesh.set_editor_property('negative_bounds_extension',u.Vector(15000,15000,1500))
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),traffic=row['traffic'],triangles=row['triangles']);record();gc.collect()
def main():
 displays();street_materials();meshes();report.update(stage='assets_saved',new_cpu_tick_actors=0,new_dynamic_lights=0,cars=36,trees=94);record();print('AP16_ASSETS_SAVED')
if __name__=='__main__':main()
