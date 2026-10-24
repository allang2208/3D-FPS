"""Save apartment-only material, mesh and sound assets, with resumable receipts."""
from pathlib import Path
import unreal as u,json,runpy,re,hashlib,traceback,gc
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT'];BASE=C['BASE']
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',materials={},meshes={},audio={},textures=[],game_run=False,rendered=False)
previous=json.loads((ROOT/'assets_saved.json').read_text()) if (ROOT/'assets_saved.json').exists() else {}
def record():(ROOT/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing AP7 dependency '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('AP7 save '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('AP7 material pin '+pin)
def scalar(m,v):return node(m,'Constant',r=v)
def param(m,name,v):return node(m,'ScalarParameter',parameter_name=name,default_value=v)
def rgb(m,v):return node(m,'Constant3Vector',constant=u.LinearColor(*v,1))
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
 pins=[]
 for k in inputs:p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
 n.set_editor_property('inputs',pins)
 for k,v in inputs.items():wire(v,n,k)
 return n
def texture(m,path,uv,normal=False):
 tex=load(path);st=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'MASKS' in str(tex.get_editor_property('compression_settings')) else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
 n=node(m,'TextureSample',texture=tex,sampler_type=st);wire(uv,n,'UVs');return n
def compile_save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 save(m)
def material(key):
 name='M_AP7_'+key;path=BASE+'/Materials/'+name
 m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
 report['materials'][key]=m.get_path_name();return m
def slab(m,color,normal,rough,metal,emission=None):
 s=node(m,'SubstrateShadingModels')
 for a,pin,prop in [(color,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(metal,'Metallic','METALLIC')]:
  wire(a,s,pin);L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+prop))
 if emission:wire(emission,s,'Emissive Color');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
 L.connect_material_property(s,'',u.MaterialProperty.MP_FRONT_MATERIAL)
def finish(key,m):compile_save(m);report['materials'][key]=m.get_path_name();record()

def import_textures():
 for file in sorted((ROOT/'Textures').glob('*.png')):
  name=file.stem;path=BASE+'/Textures/'+name
  task=u.AssetImportTask();task.filename=str(file);task.destination_path=BASE+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
  A.import_asset_tasks([task]);t=load(path);suffix=name.rsplit('_',1)[-1]
  t.set_editor_property('srgb',suffix in ['BC','E']);t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='N' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_BC7)
  t.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE);t.set_editor_property('never_stream',False)
  if suffix=='N':t.set_editor_property('flip_green_channel',False)
  save(t);report['textures'].append(path)
 record()

def build_surfaces():
 for key,period,strength in [('Terry',.24,1.),('Soil',.22,.7),('Machined',.40,.35)]:
  m=material(key);uv=node(m,'TextureCoordinate',u_tiling=1/period,v_tiling=1/period)
  bc=texture(m,BASE+'/Textures/T_AP7_'+key+'_BC',uv);n=texture(m,BASE+'/Textures/T_AP7_'+key+'_N',uv,True);orm=texture(m,BASE+'/Textures/T_AP7_'+key+'_ORM',uv)
  n=custom(m,'return normalize(float3(N.xy*S,N.z));',{'N':n,'S':scalar(m,strength)})
  slab(m,bc,n,custom(m,'return P.g;',{'P':orm},1),custom(m,'return P.b;',{'P':orm},1));finish(key,m)
 key='Leather';m=material(key);uv=node(m,'TextureCoordinate',u_tiling=2.,v_tiling=2.)
 base='/Game/SubstrateMaterials/Textures/02_Upholstery/T_Leather_02_'
 c=texture(m,base+'BC',uv);c=custom(m,'return float3(.032,.038,.046)*lerp(.75,1.25,dot(C,float3(.2126,.7152,.0722)));',{'C':c})
 n=texture(m,base+'N',uv,True);r=texture(m,base+'R',uv);slab(m,c,n,custom(m,'return lerp(.34,.61,R.r);',{'R':r},1),scalar(m,0));finish(key,m)
 for key,color,metal in [('FanBlade',(.022,.027,.033),.4),('Copper',(.28,.12,.052),.93),('Plastic',(.028,.035,.044),0.)]:
  m=material(key);uv=node(m,'TextureCoordinate',u_tiling=3.,v_tiling=3.);n=texture(m,'/Game/SubstrateMaterials/Textures/01_Paints/T_Noise_N',uv,True)
  n=custom(m,'return normalize(float3(N.xy*.06,1));',{'N':n});slab(m,rgb(m,color),n,scalar(m,.44),scalar(m,metal));finish(key,m)
 for key in ['OfficeUI','WorkoutUI']:
  m=material(key);uv=node(m,'TextureCoordinate');c=texture(m,BASE+'/Textures/T_AP7_'+key+'_BC',uv)
  active=param(m,'DeviceActive',0.);time=node(m,'Time')
  emission=custom(m,'float scan=exp(-pow((UV.y-frac(T*.065))/.025,2));return C*(lerp(.12,.85,A)+scan*.06*A);',{'C':c,'A':active,'T':time,'UV':uv})
  n=texture(m,'/Game/SubstrateMaterials/Textures/01_Paints/T_Noise_N',uv,True);n=custom(m,'return normalize(float3(N.xy*.006,1));',{'N':n})
  slab(m,custom(m,'return C*.12;',{'C':c}),n,scalar(m,.22),scalar(m,.05),emission);finish(key,m)
 build_belt()

def build_belt():
 m=material('Belt');uv=node(m,'TextureCoordinate');phase=param(m,'DevicePhase',0.);active=param(m,'DeviceActive',0.)
 uv=custom(m,'return float2(UV.x*2,UV.y*6+Phase*.5);',{'UV':uv,'Phase':phase},2)
 n=texture(m,'/Game/SubstrateMaterials/Textures/07_Rubbers/T_Rubber_N',uv,True);r=texture(m,'/Game/SubstrateMaterials/Textures/07_Rubbers/T_Rubber_R_02',uv)
 slab(m,rgb(m,(.018,.022,.027)),n,custom(m,'return lerp(.65,.85,R.r)-Active*.02;',{'R':r,'Active':active},1),scalar(m,0));finish('Belt',m)

def glass():
 for key in ['WindowGlass','ShowerGlass']:
  source=load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV5/Materials/M_AP5_'+key);name='M_AP7_'+key;path=BASE+'/Materials/'+name
  m=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',source)
  front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
  zero=scalar(m,0.);wire(zero,front,'Opacity');L.connect_material_property(zero,'',u.MaterialProperty.MP_OPACITY)
  if key=='WindowGlass' and E.get_metadata_tag(m,'AP7.Rain')!='2':
   uv=node(m,'TextureCoordinate',coordinate_index=1);physical=node(m,'TextureCoordinate');rain=param(m,'WindowRain',0.);time=node(m,'Time')
   edge=custom(m,'float e=min(min(UV.x,1-UV.x),min(UV.y,1-UV.y));return 1-smoothstep(.008,.045,e);',{'UV':uv},1)
   streak=custom(m,'float2 p=UV*float2(37,6);float h=frac(sin(floor(p.x)*127.1)*43758.5453);float x=frac(p.x)-.5;float y=frac(p.y+T*(.12+h*.13))-.5;float d=exp(-x*x/.0049-y*y/.0289);return float3(clamp(-2*x*d/.0049,-8,8),clamp(-2*y*d/.0289,-8,8),d)*Rain;',{'UV':physical,'T':time,'Rain':rain})
   oldn=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
   if isinstance(oldn,u.MaterialExpressionCustom) and 'ddx(S)' in oldn.get_editor_property('code'):oldn=L.get_inputs_for_material_expression(m,oldn)[0]
   n=custom(m,'return normalize(N+float3(S.xy*.0012,0));',{'N':oldn,'S':streak})
   r=custom(m,'return .028+Edge*.07+Rain*.018;',{'Edge':edge,'Rain':rain},1)
   for value,pin,prop in [(n,'Normal',u.MaterialProperty.MP_NORMAL),(r,'Roughness',u.MaterialProperty.MP_ROUGHNESS)]:wire(value,front,pin);L.connect_material_property(value,'',prop)
   E.set_metadata_tag(m,'AP7.Rain','2')
  finish(key,m)

def city():
 for name in ['Corporate','Financial','Housing','Terraces','Data','Harbor']:
  key='City'+name;m=material(key);uv=node(m,'TextureCoordinate');root=BASE+'/Textures/T_AP7_'+name+'_'
  c=texture(m,root+'BC',uv);n=texture(m,root+'N',uv,True);packed=texture(m,root+'ORM',uv);e=texture(m,root+'E',uv)
  sun=node(m,'SkyAtmosphereLightDirection',light_index=0);night=custom(m,'return 1-smoothstep(-.08,.12,Sun.z);',{'Sun':sun},1)
  world=node(m,'WorldPosition');time=node(m,'Time')
  e=custom(m,'float zone=floor(P.z/1520.0)+floor(P.x/2800.0);float variation=.92+.08*sin(zone*1.73+T*.018);return E*lerp(.025,1.15,Night)*variation;',{'E':e,'P':world,'T':time,'Night':night})
  slab(m,c,n,custom(m,'return R.g;',{'R':packed},1),custom(m,'return R.b;',{'R':packed},1),e);finish(key,m)

def resolve(role):
 role=re.sub(r'[._][0-9]{3}$','',role).removeprefix('AP_')
 if role in report['materials']:return load(report['materials'][role])
 if 'City'+role in report['materials']:return load(report['materials']['City'+role])
 if role in ['Frame','Stone','Roof','WarmLight']:
  return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV6/Materials/M_AP6_WarmLight' if role=='WarmLight' else '/Game/Props/CyberpunkBayBuildings20261022/Materials/M_DetailedBay_'+role)
 if role.startswith('Neon') or role in ['Signs','Navigation']:return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV6/Materials/M_AP6_'+role)
 aliases=runpy.run_path(str(ROOT.parent/'RefinementV4/surface_specs.py'));role=aliases['ALIASES'].get(role,role)
 if role in aliases['SPECS']:return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV4/Materials/MI_AP4_'+role)
 return load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV3/Materials/M_AP_'+role)

def meshes():
 rows=json.loads((ROOT/'detail-assembly.json').read_text())['meshes']+json.loads((ROOT/'city-assembly.json').read_text())['meshes']
 for row in rows:
  digest=hashlib.file_digest(Path(row['fbx']).open('rb'),'sha256').hexdigest()
  if E.does_asset_exist(row['asset']) and previous.get('meshes',{}).get(row['key'],{}).get('sha256')==digest:report['meshes'][row['key']]=previous['meshes'][row['key']];continue
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=row['name'];task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.FbxFactory()
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  data=opt.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():data.set_editor_property(k,v)
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt;A.import_asset_tasks([task]);mesh=load(row['asset'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,resolve(str(s.material_slot_name)))
  settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
  settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=row['nanite'];settings.explicit_tangents=True;settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;settings.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',settings)
  if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('AP7 Nanite build '+row['key'])
  if row['key']=='ComputerChassis':SM.remove_collisions(mesh);SM.add_simple_collisions(mesh,u.ScriptingCollisionShapeType.BOX)
  save(mesh);report['meshes'][row['key']]=dict(path=row['asset'],sha256=digest,triangles=row['triangles']);record();gc.collect()

def sounds():
 for file in (ROOT/'Audio').glob('*.wav'):
  t=u.AssetImportTask();t.filename=str(file);t.destination_path=BASE+'/Audio';t.destination_name=file.stem;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);s=load(BASE+'/Audio/'+file.stem)
  s.set_editor_property('looping',True);s.set_editor_property('virtualization_mode',u.VirtualizationMode.PLAY_WHEN_SILENT);save(s);report['audio'][file.stem.removeprefix('S_AP7_')]=s.get_path_name();record()
def water():
 old='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV6/Materials/'
 name='T_AP7_CityReflection';path=BASE+'/Textures/'+name
 task=u.AssetImportTask();task.filename=str(ROOT/(name+'.dds'));task.destination_path=BASE+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory()
 A.import_asset_tasks([task]);cube=load(path)
 for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,max_texture_size=2048,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,lod_group=u.TextureGroup.TEXTUREGROUP_SKYBOX).items():cube.set_editor_property(k,v)
 save(cube);report['textures'].append(path)
 name='M_AP7_BayWater';path=BASE+'/Materials/'+name
 m=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',load(old+'M_AP6_BayWater'))
 samples=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection']
 if len(samples)!=1:raise RuntimeError('Retained V6 water reflection sampler changed')
 samples[0].set_editor_property('texture',cube);compile_save(m)
 name='MI_AP7_BayWater';path=BASE+'/Materials/'+name
 mi=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',load(old+'MI_AP6_BayWater'))
 L.set_material_instance_parent(mi,m)
 L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube)
 L.update_material_instance(mi);save(mi)
 report['water']=dict(path=mi.get_path_name(),v6_wave_filter_preserved=True,city_reflection=cube.get_path_name(),city_reflection_gain=.12,reflection_mip_bias=2,dynamic_sky_preserved=True);record()
def main():
 try:
  import_textures();build_surfaces();glass();city();meshes();sounds();water();report['stage']='assets_saved';record();print('AP7_ASSETS_SAVED')
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
