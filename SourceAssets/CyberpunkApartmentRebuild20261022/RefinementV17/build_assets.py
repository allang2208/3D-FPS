"""New architectural lighting families, retained PBR, city meshes and reflection cube."""
from pathlib import Path
import unreal as u,json,runpy,gc,hashlib
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
helper=runpy.run_path(str(R.parent/'RefinementV10/build_assets.py'));node=helper['node'];wire=helper['wire'];custom=helper['custom'];param=helper['param']
report=dict(stage='building',materials={},meshes={},textures={})
previous=json.loads((R/'assets_saved.json').read_text()) if (R/'assets_saved.json').exists() else {}
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing AP17 dependency '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def duplicate(name,source):
 p=BASE+'/Materials/'+name
 return load(p) if E.does_asset_exist(p) else A.duplicate_asset(name,BASE+'/Materials',load(source))
def finish(key,m):
 errors=list(L.recompile_material(m))
 if errors:raise RuntimeError(str(errors))
 stats=L.get_statistics(m)
 if stats.get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('Shader program not produced: '+key)
 save(m);report['materials'][key]=m.get_path_name();record()
def texture(file,name,cube=False):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=BASE+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task]);t=load(BASE+'/Textures/'+name)
 for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,max_texture_size=2048,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():t.set_editor_property(k,v)
 if cube:t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_SKYBOX)
 save(t);report['textures'][name]=t.get_path_name();return t
def instance(name,parent,values):
 path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 L.set_material_instance_parent(m,parent)
 for k,v in values.items():L.set_material_instance_scalar_parameter_value(m,k,float(v))
 L.update_material_instance(m);save(m);report['materials'][name]=m.get_path_name();return m
def facades():
 for family in C['FAMILIES']:
  tex=texture(R/'Textures'/f'T_AP17_{family}_E.png',f'T_AP17_{family}_E')
  m=duplicate('M_AP17_'+family,'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Materials/M_AP7_City'+C['SOURCE_FAMILY'][family])
  emissive=0
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionTextureSample):
    t=n.get_editor_property('texture')
    if t and t.get_name().endswith('_E'):n.set_editor_property('texture',tex)
   if isinstance(n,u.MaterialExpressionCustom) and ('float zone=floor' in str(n.get_editor_property('code')) or 'AP17 stable occupancy' in str(n.get_editor_property('code'))):
    n.set_editor_property('code','// AP17 stable occupancy, ordinary glazing remains below structural lighting.\nreturn E*lerp(.015,WindowGain,Night);')
    pins=list(n.get_editor_property('inputs'))
    if not any(str(p.get_editor_property('input_name'))=='WindowGain' for p in pins):
     p=u.CustomInput();p.set_editor_property('input_name','WindowGain');pins.append(p);n.set_editor_property('inputs',pins);wire(param(m,'WindowGain',.7),n,'WindowGain')
    emissive+=1
  if emissive!=1:raise RuntimeError('Facade emission contract changed: '+family)
  finish(family,m)
 instance('MI_AP17_FarQuietGlass',load(report['materials']['QuietGlass']),{'WindowGain':.22})
 # Shared solid structural luminaires. Existing surface normal is retained.
 name='M_AP17_StructureLight';p=BASE+'/Materials/'+name;m=load(p) if E.does_asset_exist(p) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
 tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(1,.63,.28,1));gain=param(m,'Gain',1.25);night=helper['night'](m)
 emission=custom(m,'return Tint*Gain*Night;',{'Tint':tint,'Gain':gain,'Night':night});base=custom(m,'return Tint*.19;',{'Tint':tint});normal=node(m,'TextureSample',texture=load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Textures/T_AP7_Machined_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 slab=node(m,'SubstrateShadingModels')
 for value,pin,prop in [(base,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(node(m,'Constant',r=.44),'Roughness','ROUGHNESS'),(node(m,'Constant',r=.22),'Metallic','METALLIC'),(emission,'EmissiveColor','EMISSIVE_COLOR')]:wire(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);finish('StructureLight',m)
 for name,color in C['LIGHTS'].items():
  mi=instance('MI_AP17_Light'+name,m,{'Gain':1.25 if name=='Gold' else .95});L.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*color,1));L.update_material_instance(mi);save(mi)
  far=instance('MI_AP17_FarLight'+name,mi,{'Gain':.30});save(far)
 # Original small signs and navigation lamps are background accents, not window fields.
 for name in ['Signs','Navigation','WarmLight','Neon0','Neon1','Neon2','Neon3']:
  m=duplicate('M_AP17_Accent_'+name,'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV6/Materials/M_AP6_'+name)
  if E.get_metadata_tag(m,'AP17.Accent')!='1':
   old=L.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR);out=custom(m,'return E*.28;',{'E':old});front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
   if front:wire(out,front,'EmissiveColor')
   L.connect_material_property(out,'',u.MaterialProperty.MP_EMISSIVE_COLOR);E.set_metadata_tag(m,'AP17.Accent','1')
  finish(name,m)
def resolve(role,far=False):
 if role in C['FAMILIES']:return load(report['materials']['MI_AP17_FarQuietGlass' if far else role])
 if role.startswith('Light'):return load(report['materials']['MI_AP17_'+('Far' if far else '')+role])
 if role in report['materials']:return load(report['materials'][role])
 if role in ['Frame','Roof','Stone']:return load('/Game/Props/CyberpunkBayBuildings20261022/Materials/M_DetailedBay_'+role)
 raise RuntimeError('Unmapped architectural material '+role)
def meshes():
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();old=previous.get('meshes',{}).get(row['key'],{})
  if old.get('sha256')==digest and E.does_asset_exist(old['path']):report['meshes'][row['key']]=old;continue
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False;d=o.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,resolve(str(s.material_slot_name),row['key'].startswith('Far')))
  settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,settings)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',ns)
  if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed: '+row['key'])
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),triangles=row['triangles'],sha256=digest);record();gc.collect();u.SystemLibrary.collect_garbage();print('AP17_MESH_SAVED',row['key'])
def water():
 cube=texture(R/'T_AP17_CityReflection.dds','T_AP17_CityReflection',True)
 m=duplicate('M_AP17_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV16/Materials/M_AP16_Water');count=0
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection':n.set_editor_property('texture',cube);count+=1
 if count!=1:raise RuntimeError('Water reflection sampler changed')
 finish('WaterMaster',m);mi=duplicate('MI_AP17_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV16/Materials/MI_AP16_Water');L.set_material_instance_parent(mi,m);L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube);L.update_material_instance(mi);save(mi);report['materials']['Water']=mi.get_path_name();record()
def main():
 facades();meshes();water();report.update(stage='assets_saved',shader_compiled=True,new_dynamic_lights=0,new_tick_actors=0,new_capture_actors=0);record();print('AP17_ASSETS_SAVED')
if __name__=='__main__':main()
