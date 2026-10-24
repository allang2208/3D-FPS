"""Save this bay revision only; reusable water and surface assets remain untouched."""
from pathlib import Path
import sys,json,hashlib,traceback,re
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='preparing',saved=[],meshes={},textures={},materials={},tests_run=False,game_run=False)
prior_path=ROOT/'assets_saved.json'
prior=json.loads(prior_path.read_text()) if prior_path.exists() else {}
manifest=json.loads((ROOT/'assembly.json').read_text())
cubes=json.loads((ROOT/'cubes.json').read_text())
REV='layered-bay-v1'

def record():prior_path.write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing dependency '+path)
 return obj
def save(obj):
 E.set_metadata_tag(obj,'Bay.Owner',OWNER)
 if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
 report['saved'].append(obj.get_path_name());record()
def create(name,cls,factory):
 path=DEST+'/Materials/'+name
 obj=u.load_asset(path) if E.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',cls,factory)
 if E.get_metadata_tag(obj,'Bay.Owner') not in ('',OWNER):raise RuntimeError('Unowned asset '+path)
 return obj
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def rgb(m,c):return node(m,'Constant3Vector',constant=u.LinearColor(*c,1))
def scalar(m,v):return node(m,'Constant',r=v)
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,v in inputs.items():wire(v,n,name)
 return n
def compile_save(m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compile failed '+m.get_name()+': '+str(errors))
 save(m)

def texture(file,name,cube=False,size=2048):
 path=DEST+'/Textures/'+name;digest=hashlib.file_digest(Path(file).open('rb'),'sha256').hexdigest()
 old=prior.get('textures',{}).get(name,{})
 tex=u.load_asset(path) if E.does_asset_exist(path) else None
 if not tex or old.get('sha256')!=digest:
  task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST+'/Textures';task.destination_name=name
  task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory()
  AT.import_asset_tasks([task]);tex=load(path)
  tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
  tex.set_editor_property('max_texture_size',size)
  tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_SKYBOX if cube else u.TextureGroup.TEXTUREGROUP_WORLD)
  if not cube:tex.set_editor_property('never_stream',False)
  save(tex)
 if cube and not isinstance(tex,u.TextureCube):raise RuntimeError('Expected TextureCube '+path)
 report['textures'][name]=dict(path=path,sha256=digest,size=size);record();return tex

def standard(key,textures):
 m=create('M_Bay_'+key,u.Material,u.MaterialFactoryNew())
 if prior.get('materials',{}).get(key)==REV and E.get_metadata_tag(m,'Bay.Owner')==OWNER:
  report['materials'][key]=REV;return m
 for old in list(L.get_material_expressions(m)):L.delete_material_expression(m,old)
 m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
 slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
 def prop(a,pin,legacy):
  wire(a,slab,pin);L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+legacy))
 def sample(t):return node(m,'TextureSample',texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 if key=='Facade':
  prop(sample(textures['T_BayFacade_BC']),'BaseColor','BASE_COLOR')
  mul=node(m,'Multiply',const_b=1.3);wire(sample(textures['T_BayFacade_E']),mul,'A','RGB');emission=mul
 elif key=='Signs':
  prop(rgb(m,(.009,.012,.018)),'BaseColor','BASE_COLOR')
  mul=node(m,'Multiply',const_b=2.);wire(sample(textures['T_BaySigns_E']),mul,'A','RGB');emission=mul
 else:
  color=PALETTE[int(key[-1])] if key.startswith('Neon') else (.8,.08,.025)
  prop(rgb(m,color),'BaseColor','BASE_COLOR');emission=rgb(m,[c*(1.4 if key!='Navigation' else 2) for c in color])
 prop(emission,'Emissive Color','EMISSIVE_COLOR');prop(scalar(m,.38),'Roughness','ROUGHNESS')
 prop(scalar(m,.15),'Metallic','METALLIC');prop(scalar(m,.35),'Specular','SPECULAR')
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 compile_save(m);report['materials'][key]=REV;record();return m

def far_background(cube):
 m=create('M_Bay_FarSky',u.Material,u.MaterialFactoryNew())
 if prior.get('materials',{}).get('Sky')==REV and E.get_metadata_tag(m,'Bay.Owner')==OWNER:
  report['materials']['Sky']=REV;return m
 for old in list(L.get_material_expressions(m)):L.delete_material_expression(m,old)
 m.set_editor_property('two_sided',True);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);m.set_editor_property('is_sky',True)
 p=node(m,'WorldPosition');cam=node(m,'CameraPositionWS')
 direction=custom(m,'float3 d=normalize(P-Cam); return float3(-d.x,d.z,d.y);',{'P':p,'Cam':cam})
 sample=node(m,'TextureSampleParameterCube',parameter_name='FarCity',texture=cube,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 wire(direction,sample,'UVs')
 slab=node(m,'SubstrateUnlitBSDF');wire(sample,slab,'EmissiveColor','RGB');wire(rgb(m,(0,0,0)),slab,'TransmittanceColor')
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 L.connect_material_property(sample,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
 compile_save(m);report['materials']['Sky']=REV;record();return m

def water(reflection):
 source=load(WATER_PARENT);parent=source.get_editor_property('parent')
 path=DEST+'/Materials/M_Bay_ClearwaterNight'
 m=u.load_asset(path) if E.does_asset_exist(path) else AT.duplicate_asset('M_Bay_ClearwaterNight',DEST+'/Materials',parent)
 if prior.get('materials',{}).get('Water')!=REV:
  # Derive from the live accepted parent, not from an obsolete experimental water master.
  expressions=list(L.get_material_expressions(m))
  normal=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
  if not normal:
   normal=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom) and
               str(n.get_editor_property('description'))=='World normal, shared impact slopes')
  pos=node(m,'WorldPosition');cam=node(m,'CameraPositionWS')
  # Night-only distant radiance. It supplements native SLW optics with an offline
  # capture of this exact city, and costs one cube sample with no SceneCapture.
  direction=custom(m,'''float3 R=reflect(normalize(P-Cam),normalize(N));
float3 origin=float3(1000,20000,-8900);
float3 safeR=lerp(-1.0,1.0,step(0.0,R))*max(abs(R),.00001);
float3 bounds=lerp(float3(-799000,-100000,-9500),float3(801000,1000000,70000),step(0.0,R));
float3 t=(bounds-P)/safeR; float travel=min(t.x,min(t.y,t.z));
float3 hit=(travel>0)?P+R*travel-origin:R;
return normalize(float3(-hit.x,hit.z,hit.y));''',{'P':pos,'Cam':cam,'N':normal})
  sample=node(m,'TextureSampleParameterCube',parameter_name='BayReflection',texture=reflection,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  wire(direction,sample,'UVs')
  emission=custom(m,'''float ndv=saturate(dot(normalize(N),normalize(Cam-P)));
float fresnel=.02037+.97963*pow(1-ndv,5);
return Radiance * fresnel * .55;''',{'P':pos,'Cam':cam,'N':normal,'Radiance':sample})
  if not L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
   raise RuntimeError('Cannot bind night radiance to native water')
  front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
  report['water_front_node']=front.get_class().get_name() if front else None
  compile_save(m)
 mi_path=DEST+'/Materials/MI_BayWater'
 mi=u.load_asset(mi_path) if E.does_asset_exist(mi_path) else AT.duplicate_asset('MI_BayWater',DEST+'/Materials',source)
 L.set_material_instance_parent(mi,m)
 L.set_material_instance_scalar_parameter_value(mi,'WaterImpactEnabled',0.)
 L.set_material_instance_scalar_parameter_value(mi,'WaveHeightScale',.72)
 L.update_material_instance(mi);save(mi)
 report['materials']['Water']=REV;report['water_parent']=parent.get_path_name();record();return mi

def main():
 try:
  if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve running game; finish play before import')
  dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]
  if dirty:raise RuntimeError('Preserve unsaved bay assets '+str(dirty))
  tex={name:texture(FACADES/(name+'.png'),name) for name in ['T_BayFacade_BC','T_BayFacade_E','T_BaySigns_E']}
  far=texture(cubes['Far']['path'],'T_BayFar',True,cubes['Far']['size'])
  reflection=texture(cubes['Reflection']['path'],'T_BayReflection',True,cubes['Reflection']['size'])
  mats={k:load(p) for k,p in SHARED.items()}
  for k in ['Facade','Signs','Neon0','Neon1','Neon2','Neon3','Navigation']:mats[k]=standard(k,tex)
  far_background(far);mats['Water']=water(reflection)
  u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
  for row in manifest['meshes']:
   digest=hashlib.file_digest(Path(row['fbx']).open('rb'),'sha256').hexdigest()
   old=prior.get('meshes',{}).get(row['key'],{})
   mesh=u.load_asset(row['asset']) if E.does_asset_exist(row['asset']) else None
   if not mesh or old.get('sha256')!=digest:
    task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=DEST+'/Meshes';task.destination_name=row['name']
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;task.options=opt
    AT.import_asset_tasks([task]);mesh=load(row['asset'])
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
     name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mesh.set_material(i,mats[name])
    SM.remove_collisions(mesh)
    settings=SM.get_lod_build_settings(mesh,0)
    for name,value in dict(use_full_precision_u_vs=True,recompute_normals=False,recompute_tangents=True,
                           use_mikk_t_space=True,distance_field_resolution_scale=0.).items():settings.set_editor_property(name,value)
    SM.set_lod_build_settings(mesh,0,settings)
    nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=row['nanite']
    nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED
    nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.
    mesh.set_editor_property('nanite_settings',nanite)
    if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+row['key'])
    save(mesh)
   report['meshes'][row['key']]=dict(path=row['asset'],sha256=digest,triangles=row['triangles'],nanite=row['nanite'])
   report['stage']='importing_meshes';record()
  report['stage']='assets_saved';record();print('LAYERED_BAY_ASSETS_SAVED',len(report['meshes']))
 except Exception:
  report['error']=traceback.format_exc();report['stage']='failed';record();raise
if __name__=='__main__':main()
