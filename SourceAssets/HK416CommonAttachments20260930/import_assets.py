"""Author/save private HK416 assets in the full editor through the batch mutex."""
import unreal as u,json,re,time
from pathlib import Path
from runpy import run_path
O=Path(__file__).parent;D='/Game/Weapons/HK416/CommonAttachments20260930';H='/Game/Weapons/HK416/Reworked20260930';P=O.parents[1]
apply_current_bindings=run_path(str(P/'SourceAssets/WeaponSurface20260930/HK416/current_bindings.py'))['apply_current_bindings']
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
host=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if host not in (P.resolve(),(P/'Saved/AssetAuthoring/HK416CommonHost').resolve()) or Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong project/content mount for HK416 asset authoring')
models=json.loads((O/'models.json').read_text());animations=json.loads((O/'animations.json').read_text())
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf-8')) if (O/'import_receipt.json').exists() else {'meshes':{},'materials':{},'animations':{},'testing':'Not run; production import/save only'}
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing asset '+path)
 return obj
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outer()],False):raise RuntimeError('Save failed '+obj.get_path_name())
def record(): (O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,n,pin):
 x,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(x,out,n,pin):raise RuntimeError('Material input '+pin)
def output(src,prop):
 x,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(x,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def current(m,prop,default):
 p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
 return (n,L.get_material_property_input_node_output_name(m,p)) if n else node(m,u.MaterialExpressionConstant,r=default)
def custom(m,code,inputs,size):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n
def imported(file,name,folder,options=None):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.options=options
 A.import_asset_tasks([task]);return load(folder+'/'+name)
textures={}
for key in ('BaseColor','Metallic','Roughness','Normal'):
 name='T_HK416_Coat_'+key;t=imported(O/'Textures'/(name+'.png'),name,D+'/Textures');t.srgb=key=='BaseColor'
 t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
 if key=='Normal':t.flip_green_channel=True
 t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;save(t);textures[key]=t
def sample(m,key,uv):
 n=node(m,u.MaterialExpressionTextureSample,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);wire(uv,n,'UVs');return (n,'RGB' if key in ('BaseColor','Normal') else 'R')
import importlib.util
spec=importlib.util.spec_from_file_location('hk416_surfaces',O/'surface_materials.py');surface_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(surface_module)
surface_library=surface_module.SurfaceLibrary()
wet={row['dry']:load(row['wet']) for row in receipt['materials'].values()}
def material(key,slot,path):
 m=surface_library.material(key,slot,path)
 wet.update(surface_library.wet);receipt['materials'].update(surface_library.records);record()
 return m

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,part in models['parts'].items():
  if globals().get('RESUME_SAVED',False) and key in receipt['meshes']:continue
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  mesh=imported(part['file'],part['name'],D+'/Meshes',opt);slots=list(mesh.static_materials)
  for i,slot in enumerate(slots):
   name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));binding=next((k for k in part['bindings'] if re.sub(r'[._]\d{3}$','',k)==name),None)
   if binding is None:raise RuntimeError('Missing source slot '+key+' '+name)
   slot.material_interface=material(key,binding,part['bindings'][binding]);slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
  if editor:
   settings=editor.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;editor.set_lod_build_settings(mesh,0,settings)
  for name,p in part['sockets'].items():
   socket=mesh.find_socket(name)
   if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
   socket.set_editor_property('relative_location',u.Vector(p[0]*100,-p[1]*100,p[2]*100))
   if name=='ZoomRing':
    m=models['ring_rotation_blender'];x=u.Vector(m[0][0],-m[1][0],m[2][0]);z=u.Vector(m[0][2],-m[1][2],m[2][2])
    socket.set_editor_property('relative_rotation',u.MathLibrary.make_rot_from_xz(x,z))
  E.set_metadata_tag(mesh,'HK416CommonParts','Source UV0 preserved, measured interfaces, metal coating UV3, September 30 2026')
  apply_current_bindings(mesh)
  save(mesh);receipt['meshes'][key]=mesh.get_path_name();record()
 oldmesh=load(H+'/SK_HK416_Manny');oldslots={str(x.material_slot_name):x.material_interface for x in oldmesh.materials}
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.create_physics_asset=False;opt.skeleton=oldmesh.skeleton
 opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
 mesh=imported(models['mesh'],'SK_HK416_Manny',H,opt);slots=list(mesh.materials);arms=[]
 for i,slot in enumerate(slots):
  name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));old=models['sections'].get(name,name)
  source=next((v for k,v in oldslots.items() if re.sub(r'[._]\d{3}$','',k)==old),None)
  if source is None:source=load(H+'/Materials/'+old)
  slot.material_interface=source;slots[i]=slot
  # FBX reimport can preserve the previous display slot name although the
  # imported section was renamed. Runtime visibility uses the display name.
  if name=='M_HK416_Stock':
   slot.material_slot_name='M_HK416_FactoryStock';slots[i]=slot
  if 'Manny' in name:arms.append(i)
 mesh.set_editor_property('materials',slots);apply_current_bindings(mesh);save(mesh)
 receipt['skeletal_mesh']=mesh.get_path_name();receipt['arm_materials']=arms;record()
 for key,clip in animations['clips'].items():
  if globals().get('RESUME_SAVED',False) and key in receipt['animations']:continue
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  anim=imported(clip['file'],clip['name'],H+'/Animations/'+clip['family'],opt);anim.set_editor_property('bone_compression_settings',load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(anim)
  receipt['animations'][key]=anim.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
spec=importlib.util.spec_from_file_location('hk416_refresh_profiles',O/'import_grip_profiles.py');profile_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile_module)
receipt['runtime_empty_drum_profiles']=profile_module.refresh_empty_drum_profiles(O);record()
receipt['runtime_empty_standard_profiles']=profile_module.refresh_empty_profiles(O);record()
receipt['runtime_inspect_profiles']=profile_module.refresh_inspect_profiles(O);record()
library=load(H+'/DA_HK416_WetMaterials');entries=dict(library.get_editor_property('wet_materials'));entries.update(wet);library.set_editor_property('wet_materials',entries);save(library)
file=P/'Content/ColdSteelData/modular_outfits.json';text=file.read_text(encoding='utf-8-sig');start=text.index('{',text.index('"profiles"'));profiles,n=json.JSONDecoder().raw_decode(text[start:]);profiles[mesh.get_path_name()]['hide_source_materials']=arms
if file.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Outfit catalog changed during asset publication')
file.write_text(text[:start]+json.dumps(profiles,ensure_ascii=False,indent=2)+text[start+n:],encoding='utf-8')
receipt['status']='HK416 common attachment meshes, materials, skeletal sections and animations imported and saved';record();print('HK416_COMMON_ASSETS_SAVED',len(receipt['meshes']),len(receipt['animations']))

script=O/"import_icons.py"
exec(compile(script.read_text(encoding="utf-8"),str(script),"exec"),{"__file__":str(script),"__name__":"__main__"})
