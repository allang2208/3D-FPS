"""Import the dedicated detailed-city revision without changing shared assets."""
from pathlib import Path
import sys,json,hashlib,re,traceback
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
# Explicit module avoids a cached 'design' from another editor script.
import runpy
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'))
ROOT=C['ROOT'];PROJECT=C['PROJECT'];DEST=C['DEST'];OWNER=C['OWNER'];OLD=C['OLD'];FACADES=C['FACADES'];PALETTE=C['PALETTE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='preparing',saved=[],meshes={},textures={},materials={},tests_run=False,game_run=False)
priorfile=ROOT/'assets_saved.json';prior=json.loads(priorfile.read_text()) if priorfile.exists() else {}
manifest=json.loads((ROOT/'assembly.json').read_text());REV='detailed-bay-1'
def record():priorfile.write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing city dependency '+path)
 return a
def save(a):
 E.set_metadata_tag(a,'Bay.Owner',OWNER)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 report['saved'].append(a.get_path_name());record()
def create(name,source=None,folder='Materials'):
 path=DEST+'/'+folder+'/'+name
 if E.does_asset_exist(path):return load(path)
 return A.duplicate_asset(name,DEST+'/'+folder,load(source)) if source else A.create_asset(name,DEST+'/'+folder,u.Material,u.MaterialFactoryNew())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('City pin '+pin)
def rgb(m,c):return node(m,'Constant3Vector',constant=u.LinearColor(*c,1))
def scalar(m,v):return node(m,'Constant',r=v)
def compile_save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compilation '+str(errors))
 save(m)
def texture(file,name,kind='color',size=2048,cube=False):
 path=DEST+'/Textures/'+name;digest=hashlib.file_digest(Path(file).open('rb'),'sha256').hexdigest()
 tex=load(path) if E.does_asset_exist(path) else None
 if not tex or prior.get('textures',{}).get(name,{}).get('sha256')!=digest:
  t=u.AssetImportTask();t.filename=str(file);t.destination_path=DEST+'/Textures';t.destination_name=name
  t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t]);tex=load(path)
  props=dict(srgb=kind=='color',compression_settings={'normal':u.TextureCompressionSettings.TC_NORMALMAP,'mask':u.TextureCompressionSettings.TC_MASKS}.get(kind,u.TextureCompressionSettings.TC_BC7),
   max_texture_size=size,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,
   lod_group=u.TextureGroup.TEXTUREGROUP_SKYBOX if cube else u.TextureGroup.TEXTUREGROUP_WORLD)
  if not cube:props['never_stream']=False
  for k,v in props.items():tex.set_editor_property(k,v)
  save(tex)
 report['textures'][name]=dict(path=path,sha256=digest,size=size,kind=kind);record();return tex
def material(key,textures):
 m=create('M_DetailedBay_'+key)
 if prior.get('materials',{}).get(key)==REV:report['materials'][key]=REV;return m
 for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
 m.set_editor_property('used_with_nanite',True)
 slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
 def prop(a,pin,legacy,out=''):
  wire(a,slab,pin,out);L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+legacy))
 if key in textures:
  ts=textures[key]
  def sample(k,sampler):return node(m,'TextureSample',texture=ts[k],sampler_type=sampler)
  bc=sample('BC',u.MaterialSamplerType.SAMPLERTYPE_COLOR);em=sample('E',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  normal=sample('N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);orm=sample('ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  prop(bc,'BaseColor','BASE_COLOR','RGB');prop(normal,'Normal','NORMAL','RGB')
  prop(orm,'Roughness','ROUGHNESS','G');prop(orm,'Metallic','METALLIC','B')
  L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  gain=node(m,'Multiply',const_b=1.1);wire(em,gain,'A','RGB');prop(gain,'Emissive Color','EMISSIVE_COLOR')
 else:
  color,metal,rough,em={
   'Frame':((.055,.070,.092),.65,.36,0),'Stone':((.10,.125,.15),.15,.72,0),
   'Roof':((.027,.038,.05),.3,.65,0),'WarmLight':((.72,.38,.14),0,.5,1.2)}[key]
  prop(rgb(m,color),'BaseColor','BASE_COLOR');prop(scalar(m,metal),'Metallic','METALLIC');prop(scalar(m,rough),'Roughness','ROUGHNESS')
  if em:prop(rgb(m,[v*em for v in color]),'Emissive Color','EMISSIVE_COLOR')
 prop(scalar(m,.35),'Specular','SPECULAR');L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 compile_save(m);report['materials'][key]=REV;record();return m
def import_sky(cubes):
 source='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV3/Sky'
 for name,param,cube in [('M_ApartmentHubSky','CityCube',cubes['Far']),('M_WaterHubSky','BayReflection',cubes['Reflection'])]:
  m=create(name,source+'/'+name)
  samples=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))==param]
  if len(samples)!=1:raise RuntimeError('Expected accepted city sampler '+param)
  samples[0].set_editor_property('texture',cube);compile_save(m)
 mi=create('MI_WaterHubSky',source+'/MI_WaterHubSky');L.set_material_instance_parent(mi,load(DEST+'/Materials/M_WaterHubSky'))
 L.set_material_instance_texture_parameter_value(mi,'BayReflection',cubes['Reflection']);L.update_material_instance(mi);save(mi)
 report['sky']=dict(accepted_hub_sky_preserved=True,accepted_water_optics_preserved=True,far_size=4096,reflection_size=2048)
def main():
 try:
  if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve running game; stop PIE before importing')
  dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]
  if dirty:raise RuntimeError('Preserve unsaved detailed-city assets '+str(dirty))
  textures={}
  for key in ['Office','Residential','Tech']:
   textures[key]={suffix:texture(FACADES/f'T_{key}_{suffix}.png',f'T_{key}_{suffix}',kind) for suffix,kind in [('BC','color'),('E','color'),('N','normal'),('ORM','mask')]}
  mats={key:material(key,textures) for key in ['Office','Residential','Tech','Frame','Stone','Roof','WarmLight']}
  for key in ['Signs','Neon0','Neon1','Neon2','Neon3','Navigation']:mats[key]=load('/Game/Props/CyberpunkBayLayered20261022/Materials/M_Bay_'+key)
  u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
  for row in manifest['meshes']:
   digest=hashlib.file_digest(Path(row['fbx']).open('rb'),'sha256').hexdigest()
   mesh=load(row['asset']) if E.does_asset_exist(row['asset']) else None
   if not mesh or prior.get('meshes',{}).get(row['key'],{}).get('sha256')!=digest:
    t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=DEST+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;t.options=opt
    A.import_asset_tasks([t]);mesh=load(row['asset'])
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
     name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mesh.set_material(i,mats[name])
    SM.remove_collisions(mesh);settings=SM.get_lod_build_settings(mesh,0)
    for k,v in dict(use_full_precision_u_vs=True,recompute_normals=False,recompute_tangents=True,use_mikk_t_space=True,distance_field_resolution_scale=0.).items():settings.set_editor_property(k,v)
    SM.set_lod_build_settings(mesh,0,settings)
    nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True
    nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.
    mesh.set_editor_property('nanite_settings',nanite)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+row['key'])
    save(mesh)
   report['meshes'][row['key']]=dict(path=row['asset'],sha256=digest,triangles=row['triangles']);record()
  cubes={key:texture(ROOT/'Sky'/('T_City'+key+'.dds'),'T_City'+key,size=size,cube=True) for key,size in [('Far',4096),('Reflection',2048)]}
  import_sky(cubes);report['stage']='assets_saved';record();print('DETAILED_BAY_ASSETS_SAVED',len(report['meshes']))
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
