from pathlib import Path
import unreal as u,json,runpy,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',materials={},masters=[],meshes={},reused_textures=[],textures=[],game_run=False)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing fixture dependency '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Fixture asset save failed '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin):
 names=list(L.get_material_expression_input_names(b));norm=lambda s:str(s).replace(' ','').replace('_','').lower();actual=next((str(n) for n in names if norm(n)==norm(pin)),pin)
 if not L.connect_material_expressions(a,'',b,actual):raise RuntimeError('Fixture material pin '+pin+' available '+str(names))
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));pins=[]
 for name in inputs:p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,value in inputs.items():wire(value,n,name)
 return n
def scalar(m,value):return node(m,'Constant',r=value)
def rgb(m,v):return node(m,'Constant3Vector',constant=u.LinearColor(*v,1))
def texture(m,path,uv,normal=False):
 tex=load(path)
 sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'MASKS' in str(tex.get_editor_property('compression_settings')) else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
 n=node(m,'TextureSample',texture=tex,sampler_type=sampler);wire(uv,n,'UVs')
 if not path.startswith(BASE+'/Textures/') and path not in report['reused_textures']:report['reused_textures'].append(path)
 return n
def begin(key):
 name='M_AP13_'+key;path=BASE+'/Materials/'+name
 m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
 m.set_editor_property('used_with_nanite',True);return m
def slab(m,color,normal,rough,metal,emission=None):
 s=node(m,'SubstrateShadingModels')
 for n,pin,prop in [(color,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(metal,'Metallic','METALLIC')]:wire(n,s,pin);L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop))
 if emission:wire(emission,s,'Emissive Color');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
 L.connect_material_property(s,'',u.MaterialProperty.MP_FRONT_MATERIAL)
def finish(key,m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 save(m);report['materials'][key]=m.get_path_name();report['masters'].append(m.get_path_name());record()

def param(m,name,value):return node(m,'ScalarParameter',parameter_name=name,default_value=value)

def import_textures():
 for f in sorted((R/'Textures').glob('*.png')):
  task=u.AssetImportTask();task.filename=str(f);task.destination_path=BASE+'/Textures';task.destination_name=f.stem
  task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);t=load(BASE+'/Textures/'+f.stem)
  t.set_editor_property('srgb',True);t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
  t.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE);t.set_editor_property('never_stream',False)
  t.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);t.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
  save(t);report['textures'].append(t.get_path_name())

def clone_dimmer(key,path):
 name='M_AP13_'+key;dest=BASE+'/Materials/'+name
 m=load(dest) if E.does_asset_exist(dest) else A.duplicate_asset(name,BASE+'/Materials',load(path))
 if E.get_metadata_tag(m,'AP13.Dimmer')!='1':
  front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
  old=L.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
  if not old:raise RuntimeError('Missing emitter source '+path)
  e=node(m,'Multiply');wire(old,e,'A');wire(param(m,'FixtureLevel',.86),e,'B');wire(e,front,'Emissive Color');L.connect_material_property(e,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
  E.set_metadata_tag(m,'AP13.Dimmer','1')
 finish(key,m)

def materials():
 for key,path in C['REUSE'].items():report['materials'][key]=load(path).get_path_name()
 m=begin('Pearl');uv=node(m,'TextureCoordinate',u_tiling=1.5,v_tiling=1.5)
 n=texture(m,C['SUB']+'01_Paints/T_OrangePeel_N',uv,True);n=custom(m,'return normalize(float3(N.xy*.12,1));',{'N':n})
 r=texture(m,C['SUB']+'03_Metals/T_Metal_Painted_R',uv)
 slab(m,rgb(m,(.23,.26,.29)),n,custom(m,'return lerp(.42,.60,R.r);',{'R':r},1),scalar(m,.22));finish('Pearl',m)
 for key,source in [('FixtureWarm','DiffuserWarm'),('FixtureNeutral','DiffuserNeutral'),('FixtureCool','DiffuserCool'),('EdgeLight','GuideCyan')]:clone_dimmer(key,C['OLD12']+'/Materials/M_AP12_'+source)
 clone_dimmer('PendantWarm','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV5/Materials/M_AP5_Surface_M_AP_Warm')
 for key,tex,uv_channel,workout in [('Display','BaynetAtlas',1,False),('OfficeUI','Office',0,False),('TreadmillUI','Treadmill',0,True),('RowerUI','Rower',0,True),('Control','Control',1,False)]:
  m=begin(key);uv=node(m,'TextureCoordinate',coordinate_index=uv_channel)
  # This prototype emits toward local -Y; its visible left-to-right axis is -X.
  if key=='Control':
   uv=custom(m,'return float2(1-UV.x,UV.y);',{'UV':uv},2);E.set_metadata_tag(m,'AP13.FrontUV','1')
  power=param(m,'DevicePower',0.);active=param(m,'DeviceActive',0.);phase=param(m,'DevicePhase',0.)
  sampling=uv
  if key=='Display':sampling=custom(m,'float frame=fmod(floor(Phase/16.0),3.0);return float2(UV.x,(frame*1310.0+2.0+UV.y*1306.0)/4096.0);',{'UV':uv,'Phase':phase},2)
  color=texture(m,BASE+'/Textures/T_AP13_'+tex,sampling)
  if key=='Display':color=custom(m,'float bar=step(.965,UV.y)*step(UV.y,.969)*step(.037,UV.x)*step(UV.x,.963)*step(UV.x,.037+.926*frac(Phase/16.0));return lerp(C,float3(.12,.38,.43),bar*.8);',{'UV':uv,'C':color,'Phase':phase})
  if key in ('OfficeUI','TreadmillUI','RowerUI'):
   stateuv=custom(m,'float state=Power<.5?0:Active>.8?1:Workout>.5?3:2;float2 q=saturate((UV-float2(.06,.84))/float2(.38,.12));return float2(q.x,(state+.06+q.y*.88)/4.0);',{'UV':uv,'Power':power,'Active':active,'Workout':scalar(m,1. if workout else 0.)},2)
   states=texture(m,BASE+'/Textures/T_AP13_States',stateuv)
   color=custom(m,'float show=step(.06,UV.x)*step(UV.x,.44)*step(.84,UV.y)*step(UV.y,.96);return lerp(Base,State,show);',{'UV':uv,'Base':color,'State':states})
  if workout:color=custom(m,(R/'workout_digits.hlsl').read_text(),{'UV':uv,'Elapsed':param(m,'DeviceElapsed',0.),'Base':color})
  n=texture(m,C['SUB']+'01_Paints/T_Noise_N',uv,True);n=custom(m,'return normalize(float3(N.xy*.004,1));',{'N':n})
  if key=='Control':emission=custom(m,'return C*(.10+.35*Power+.30*Active);',{'C':color,'Power':power,'Active':active})
  else:emission=custom(m,'float luminance=lerp(.20,.92,Active)*Power;return C*luminance;',{'C':color,'Power':power,'Active':active})
  base=custom(m,'return lerp(float3(.008,.012,.018),C*.09,Power);',{'C':color,'Power':power})
  slab(m,base,n,scalar(m,.19 if key=='Display' else .26),scalar(m,.06),emission);finish(key,m)
 record()

def meshes():
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=row['name'];task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.FbxFactory()
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  d=opt.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt;A.import_asset_tasks([task]);mesh=load(row['asset'])
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(report['materials'][str(slot.material_slot_name)]))
  settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
  nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True;nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',nanite)
  if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('AP13 Nanite build failed '+row['key'])
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),source_triangles=row['triangles']);record()

def main():
 try:import_textures();materials();meshes();report['stage']='assets_saved';record()
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
