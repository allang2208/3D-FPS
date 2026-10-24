"""Produce first-row display materials and wave-coupled water reflection assets."""
from pathlib import Path
import unreal as u,json,runpy,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',materials={},meshes={},reused_textures=[],game_run=False)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing AP10 source '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('AP10 asset save failed '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind));n.set_editor_property('desc','AP10/'+kind)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin):
 names=list(L.get_material_expression_input_names(b));norm=lambda s:str(s).replace(' ','').replace('_','').lower()
 actual=next((str(n) for n in names if norm(n)==norm(pin)),pin)
 if not L.connect_material_expressions(a,'',b,actual):raise RuntimeError('AP10 pin '+pin+' available '+str(names))
def custom(m,code,inputs,width=3,description='AP10 shader'):
 n=node(m,'Custom',code=code,description=description,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
 pins=[]
 for name in inputs:p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,value in inputs.items():wire(value,n,name)
 return n
def param(m,name,v):return node(m,'ScalarParameter',parameter_name=name,default_value=v)
def texture(m,name,path):return node(m,'TextureObjectParameter',parameter_name=name,texture=load(path),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
def night(m):return custom(m,'return 1-smoothstep(-.08,.12,Sun.z);',{'Sun':node(m,'SkyAtmosphereLightDirection',light_index=0)},1)
def compile_save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('AP10 material build '+str(errors))
 save(m);report['materials'][m.get_name()]=m.get_path_name();record()
def new_material(name):
 path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(m);return m
def texture_inputs(m):
 return dict(Atlas=texture(m,'CampaignAtlas',C['OLD8']+'/Textures/T_AP8_CampaignAtlas_BC'),Ticker=texture(m,'TickerAtlas',C['OLD8']+'/Textures/T_AP8_Ticker_BC'))

def displays():
 for kind in ['portrait','ribbon']:
  m=new_material('M_AP10_'+kind.title());uv=node(m,'TextureCoordinate');clock=node(m,'Time')
  t=custom(m,'return (Clock+Phase)*Rate;',{'Clock':clock,'Phase':param(m,'Phase',0),'Rate':param(m,'PlaybackRate',1)},1)
  inputs=dict(UV=uv,T=t,Slot=param(m,'Campaign',0),Aspect=param(m,'Aspect',2/3),Night=night(m),**texture_inputs(m))
  emission=custom(m,(R/(kind.title()+'.hlsl')).read_text(),inputs)
  slab=node(m,'SubstrateShadingModels');zero=node(m,'Constant',r=0);rough=node(m,'Constant',r=.43);normal=node(m,'Constant3Vector',constant=u.LinearColor(0,0,1,1))
  for n,pin,prop in [(zero,'BaseColor','BASE_COLOR'),(zero,'Metallic','METALLIC'),(rough,'Roughness','ROUGHNESS'),(normal,'Normal','NORMAL'),(emission,'EmissiveColor','EMISSIVE_COLOR')]:wire(n,slab,pin);L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop))
  L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);compile_save(m)
 for b in C['BOARDS']:
  name='MI_AP10_'+b['key'];path=BASE+'/Materials/'+name
  mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.set_material_instance_parent(mi,load(BASE+'/Materials/M_AP10_'+b['kind'].title()))
  for k,v in dict(Phase=b['phase'],Campaign=b['slot'],Aspect=b['w']/b['h'],PlaybackRate=.92 if b['key']=='Port' else 1).items():L.set_material_instance_scalar_parameter_value(mi,k,v)
  L.update_material_instance(mi);save(mi);report['materials'][name]=mi.get_path_name()
 record()

def water():
 old=C['OLD7']+'/Materials/';name='M_AP10_BayWater';path=BASE+'/Materials/'+name
 m=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',load(old+'M_AP7_BayWater'))
 # Keep V6/V7 spectrum, filtering, sky, water absorption and static city supplement.
 for n in list(L.get_material_expressions(m)):
  if str(n.get_editor_property('desc')).startswith('AP10/'):L.delete_material_expression(m,n)
 retained=next(n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='Soft city-only reflection, native dynamic sky retained')
 normal=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
 inputs=dict(Position=node(m,'WorldPosition'),Camera=node(m,'CameraPositionWS'),WaterNormal=normal,Clock=node(m,'Time'),Night=night(m),**texture_inputs(m))
 mapping=dict(AdGain='AdReflectionGain',BeamGain='BeamReflectionGain',NormalWeight='ReflectionNormalWeight',Blur='ReflectionBlur',MaxRadiance='ReflectionMaxRadiance')
 for pin,name in mapping.items():inputs[pin]=param(m,name,C['WATER_PARAMETERS'][name])
 dynamic=custom(m,(R/'WaterReflection.hlsl').read_text(),inputs,description='AP10 coherent billboard and sweeping beam water reflections')
 result=node(m,'Add');wire(retained,result,'A');wire(dynamic,result,'B');L.connect_material_property(result,'',u.MaterialProperty.MP_EMISSIVE_COLOR);compile_save(m)
 name='MI_AP10_BayWater';path=BASE+'/Materials/'+name
 mi=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',load(old+'MI_AP7_BayWater'))
 L.set_material_instance_parent(mi,m)
 for k,v in C['WATER_PARAMETERS'].items():L.set_material_instance_scalar_parameter_value(mi,k,v)
 L.update_material_instance(mi);save(mi);report['materials'][name]=mi.get_path_name()
 report['water']=dict(path=mi.get_path_name(),base_source=old+'MI_AP7_BayWater',native_water_preserved=True,reflection_type='analytic world-space emitter supplement inside existing filtered water',billboards=6,sweeping_beams=6,additional_scene_captures=0,additional_passes=0,added_tick_actors=0,maximum_extra_texture_samples=10,ray_occlusion='curated distant light proxies, not full-scene ray tracing')
 record()

def frames():
 row=json.loads((R/'assembly.json').read_text())['meshes'][0]
 t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 data=opt.static_mesh_import_data
 for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():data.set_editor_property(k,v)
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
 old='/Game/Props/CyberpunkApartmentRebuild20261022/'
 roles=dict(MountMetal=old+'RefinementV7/Materials/M_AP7_Machined',CyanTrim=old+'RefinementV6/Materials/M_AP6_Neon0',AmberTrim=old+'RefinementV6/Materials/M_AP6_Neon2')
 for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(roles[str(s.material_slot_name)]))
 settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
 settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True;settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;settings.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',settings)
 if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('AP10 frame Nanite production failed')
 save(mesh);report['meshes']['frames']=mesh.get_path_name();record()

def main():
 try:
  displays();water();frames()
  report['reused_textures']=[C['OLD8']+'/Textures/T_AP8_CampaignAtlas_BC',C['OLD8']+'/Textures/T_AP8_Ticker_BC'];report['stage']='assets_saved';record()
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
