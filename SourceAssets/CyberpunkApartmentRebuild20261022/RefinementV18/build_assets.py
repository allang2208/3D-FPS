"""Produce and save V18 meshes, PBR paving and static-reflection supplement."""
from pathlib import Path
import unreal as u,json,runpy,gc,hashlib
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
H=runpy.run_path(str(R.parent/'RefinementV10/build_assets.py'));node=H['node'];wire=H['wire'];custom=H['custom'];param=H['param']
report=dict(stage='building',materials={},meshes={},textures={})
previous=json.loads((R/'assets_saved.json').read_text()) if (R/'assets_saved.json').exists() else {}
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing V18 dependency '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
def duplicate(name,source):
 path=BASE+'/Materials/'+name
 return load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',load(source))
def finish(key,m):
 errors=list(L.recompile_material(m))
 if errors:raise RuntimeError(str(errors))
 if L.get_statistics(m).get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('No shader program '+key)
 save(m);report['materials'][key]=m.get_path_name();record()
def texture(file,name,kind='color'):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=BASE+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t]);a=load(BASE+'/Textures/'+name)
 values=dict(srgb=kind in ['color','cube'],compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else (u.TextureCompressionSettings.TC_MASKS if kind=='mask' else u.TextureCompressionSettings.TC_BC7),max_texture_size=2048 if kind=='cube' else 1024,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
 if kind=='cube':values['lod_group']=u.TextureGroup.TEXTUREGROUP_SKYBOX
 for k,v in values.items():a.set_editor_property(k,v)
 save(a);report['textures'][name]=a.get_path_name();return a
def surfaces():
 master=duplicate('M_AP18_Surface','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV16/Materials/M_AP16_Street');finish('SurfaceMaster',master)
 for role,(rgb,rough,metal,glow) in C['SURFACES'].items():
  if role=='Paving':continue
  name='MI_AP18_'+role;path=BASE+'/Materials/'+name
  m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(m,master)
  for k,v in dict(Roughness=rough,Metallic=metal,Glow=glow,NormalStrength=.025 if role=='Glass' else .22).items():L.set_material_instance_scalar_parameter_value(m,k,v)
  L.set_material_instance_vector_parameter_value(m,'Tint',u.LinearColor(*rgb,1));L.update_material_instance(m);save(m);report['materials'][role]=m.get_path_name()
 maps={}
 for suffix,kind in [('BC','color'),('N','normal'),('ORM','mask')]:maps[suffix]=texture(R/'Textures'/f'T_AP18_Paving_{suffix}.png',f'T_AP18_Paving_{suffix}',kind)
 name='M_AP18_Paving';path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
 base=node(m,'TextureSample',texture=maps['BC'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 normal=node(m,'TextureSample',texture=maps['N'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 orm=node(m,'TextureSample',texture=maps['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 rough=custom(m,'return ORM.g;',{'ORM':orm},1);ao=custom(m,'return ORM.r;',{'ORM':orm},1);zero=node(m,'Constant',r=0);slab=node(m,'SubstrateShadingModels')
 for value,pin,prop in [(base,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(zero,'Metallic','METALLIC'),(zero,'EmissiveColor','EMISSIVE_COLOR')]:wire(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
 L.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION);L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);finish('Paving',m)
 record()
def meshes():
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();old=previous.get('meshes',{}).get(row['key'],{})
  if old.get('sha256')==digest and E.does_asset_exist(old['path']):report['meshes'][row['key']]=old;continue
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False;d=o.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):
   role=str(s.material_slot_name).removeprefix('AP18_');mesh.set_material(i,load(report['materials'][role]))
  settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,settings)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',ns)
  if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite production failed '+row['key'])
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),triangles=row['triangles'],sha256=digest);record();gc.collect();u.SystemLibrary.collect_garbage();print('AP18_MESH_SAVED',row['key'])
 # Nanite may set material-use flags during mesh production. Save owned dependencies.
 for path in report['materials'].values():save(load(path))
def water():
 cube=texture(R/'T_AP18_CityReflection.dds','T_AP18_CityReflection','cube')
 m=duplicate('M_AP18_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV17/Materials/M_AP17_Water');count=0
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection':n.set_editor_property('texture',cube);count+=1
 if count!=1:raise RuntimeError('Retained reflection slot changed')
 finish('WaterMaster',m);mi=duplicate('MI_AP18_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV17/Materials/MI_AP17_Water');L.set_material_instance_parent(mi,m);L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube);L.update_material_instance(mi);save(mi);report['materials']['Water']=mi.get_path_name();record()
def main():
 surfaces();meshes();water();report.update(stage='assets_saved',shader_compiled=True,new_dynamic_lights=0,new_tick_actors=0,new_capture_actors=0);record();print('AP18_ASSETS_SAVED')
if __name__=='__main__':main()
