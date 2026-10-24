"""Apartment-local water filtering, daylight-aware city materials and far meshes."""
from pathlib import Path
import json,runpy,re,hashlib,traceback
import unreal as u
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT'];BASE=C['BASE']
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
CITY='/Game/Props/CyberpunkBayBuildings20261022';OLD='/Game/Props/CyberpunkBayLayered20261022'
report=dict(stage='preparing',materials={},meshes={},game_run=False,rendered=False)
old=json.loads((ROOT/'assets_saved.json').read_text()) if (ROOT/'assets_saved.json').exists() else {}
def record():(ROOT/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing environment dependency '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Environment asset save '+a.get_path_name())
def duplicate(name,source):
 path=BASE+'/Materials/'+name
 return load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',source)
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Environment material pin '+pin)
def custom(m,code,inputs,width=3,description=''):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)),description=description)
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,source in inputs.items():wire(source,n,name)
 return n
def compile_save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Environment material compile '+str(errors))
 save(m)
def night(m):
 sun=node(m,'SkyAtmosphereLightDirection',light_index=0)
 return custom(m,'return 1-smoothstep(-.08,.12,Sun.z);',{'Sun':sun},1,'Existing sky sun elevation; no independent clock')
def daylight_materials():
 sources={k:CITY+'/Materials/M_DetailedBay_'+k for k in ['Office','Residential','Tech','Frame','Stone','Roof','WarmLight']}
 sources.update({k:OLD+'/Materials/M_Bay_'+k for k in ['Signs','Neon0','Neon1','Neon2','Neon3','Navigation']})
 mats={}
 for key,path in sources.items():
  source=load(path)
  if key in ['Frame','Stone','Roof']:
   mats[key]=source;report['materials'][key]=source.get_path_name();continue
  mat=duplicate('M_AP6_'+key,source)
  if E.get_metadata_tag(mat,'Apartment.V6.Material')!='daylight-1':
   emission=L.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
   if not emission:raise RuntimeError('Expected city emission '+key)
   gain=custom(mat,'return lerp(.055,1.0,Night);',{'Night':night(mat)},1)
   out=node(mat,'Multiply');wire(emission,out,'A');wire(gain,out,'B')
   front=L.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
   if front:wire(out,front,'Emissive Color')
   L.connect_material_property(out,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
   E.set_metadata_tag(mat,'Apartment.V6.Material','daylight-1');compile_save(mat)
  mats[key]=mat;report['materials'][key]=mat.get_path_name();record()
 mats['Metal']=mats['Roof'];mats['Concrete']=mats['Stone']
 return mats
def water():
 accepted=load('/Game/Clearwater/MI_ClearwaterWater');parent=accepted.get_editor_property('parent')
 m=duplicate('M_AP6_BayWater',parent)
 if E.get_metadata_tag(m,'Apartment.V6.Material')!='filtered-water-1':
  p=node(m,'WorldPosition');cam=node(m,'CameraPositionWS');clock=node(m,'Time')
  height=node(m,'ScalarParameter',parameter_name='WaveHeightScale',default_value=.72)
  filtered=custom(m,(ROOT/'BayPixelWave.hlsl').read_text('utf8'),{'Position':p,'Clock':clock,'WaveHeightScale':height},3,'Bay pixel-footprint filtered Clearwater spectrum')
  n=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
  if not n:raise RuntimeError('Accepted water has no normal')
  wire(filtered,n,'Wave')
  rough=L.get_material_property_input_node(m,u.MaterialProperty.MP_ROUGHNESS)
  if not isinstance(rough,u.MaterialExpressionCustom):raise RuntimeError('Accepted native roughness contract changed')
  rough.set_editor_property('code','return lerp(.105+.07*smoothstep(10000,120000,length(P-Cam)),.34,Field.z);')
  # Geometry at this altitude does not resolve metre-scale crests on 40 m quads.
  # Fade their vertex contribution at distance; the filtered normal retains motion.
  old_wpo=L.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
  wpo=custom(m,'return Offset*(1-smoothstep(8000,60000,distance(P,Cam)));',{'Offset':old_wpo,'P':p,'Cam':cam},3,'Bay distance-filtered displacement')
  L.connect_material_property(wpo,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
  # Only the prefiltered city supplement remains. Native SLW owns sky/cloud/light
  # reflection; the former hard box-projection and fixed HDR night sky are absent.
  direction=custom(m,'float3 r=reflect(normalize(P-Cam),normalize(N));return float3(-r.x,r.z,r.y);',{'P':p,'Cam':cam,'N':n})
  cube=node(m,'TextureSampleParameterCube',parameter_name='BayReflection',texture=load(CITY+'/Textures/T_CityReflection'),
   sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR,mip_value_mode=u.TextureMipValueMode.TMVM_MIP_BIAS,const_mip_value=2)
  wire(direction,cube,'UVs')
  city=node(m,'Multiply');wire(cube,city,'A','RGB');wire(cube,city,'B','A')
  radiance=custom(m,'float nv=saturate(dot(normalize(N),normalize(Cam-P)));float f=.02037+.97963*pow(1-nv,5);return min(City,float3(2,2,2))*f*.12*Night;',
   {'P':p,'Cam':cam,'N':n,'City':city,'Night':night(m)},3,'Soft city-only reflection, native dynamic sky retained')
  L.connect_material_property(radiance,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
  E.set_metadata_tag(m,'Apartment.V6.Material','filtered-water-1');compile_save(m)
 source=load(CITY+'/Materials/MI_WaterHubSky')
 mi=duplicate('MI_AP6_BayWater',source);L.set_material_instance_parent(mi,m)
 L.set_material_instance_scalar_parameter_value(mi,'WaveHeightScale',.72)
 L.set_material_instance_scalar_parameter_value(mi,'WaterImpactEnabled',0.)
 L.update_material_instance(mi);save(mi)
 report['water']=dict(path=mi.get_path_name(),native_parent=parent.get_path_name(),spectrum_source='Clearwater 48 existing waves',
  screen_footprint_filter=True,distance_displacement_filter=True,reflection_mip_bias=2,city_reflection_gain=.12,
  fixed_sky_removed=True,box_projection_removed=True)
 record()
def import_far(mats):
 manifest=json.loads((ROOT/'far-assembly.json').read_text())
 u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 for row in manifest['meshes']:
  sha=hashlib.file_digest(Path(row['fbx']).open('rb'),'sha256').hexdigest()
  mesh=load(row['asset']) if E.does_asset_exist(row['asset']) else None
  if not mesh or old.get('meshes',{}).get(row['key'],{}).get('sha256')!=sha:
   t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
   opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
   opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
   d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
   d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt
   A.import_asset_tasks([t]);mesh=load(row['asset'])
   for i,s in enumerate(mesh.get_editor_property('static_materials')):
    key=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));mesh.set_material(i,mats[key])
   SM.remove_collisions(mesh);b=SM.get_lod_build_settings(mesh,0)
   for k,v in dict(use_full_precision_u_vs=True,recompute_normals=False,recompute_tangents=True,use_mikk_t_space=True,distance_field_resolution_scale=0.).items():b.set_editor_property(k,v)
   SM.set_lod_build_settings(mesh,0,b)
   settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=row['nanite'];settings.explicit_tangents=True
   settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;settings.fallback_percent_triangles=1.
   mesh.set_editor_property('nanite_settings',settings)
   if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Far city Nanite build '+row['key'])
   save(mesh)
  report['meshes'][row['key']]=dict(path=row['asset'],sha256=sha,triangles=row['triangles']);record()
def main():
 try:
  mats=daylight_materials();water();import_far(mats)
  report['stage']='assets_saved';record();print('APARTMENT_V6_ASSETS_SAVED')
 except Exception:report['error']=traceback.format_exc();report['stage']='failed';record();raise
if __name__=='__main__':main()
