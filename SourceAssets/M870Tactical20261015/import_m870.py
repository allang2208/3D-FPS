"""Import and save M870's private assets; never open a map or run gameplay."""
import unreal as u,json,re,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/M870/Tactical20261015';D=json.loads((O/'Donor/animation_inputs.json').read_text());auth=json.loads((O/'authoring.json').read_text())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;report=dict(saved=[],runtime_tested=False)
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([ROOT],True)
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing production asset: '+path)
 return a
def save(a):
 if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Cannot save '+a.get_path_name())
 if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
 (O/'import_receipt.json').write_text(json.dumps(report,indent=2));return a
def imported(file,folder,name,options=None):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 if options:task.options=options;task.factory=u.FbxFactory()
 A.import_asset_tasks([task]);asset=load(folder+'/'+name);E.set_metadata_tag(asset,'M870SourceSHA256',hashlib.sha256(Path(file).read_bytes()).hexdigest());return asset
textures={}
for role,stem in [('BaseColor','Albedo'),('Metallic','Metalic'),('Roughness','Roughness'),('Normal','Normal')]:
 t=imported(O/'Original/Source/textures'/('M870_Tactical_'+stem+'.png'),ROOT+'/Textures','T_M870_'+role);t.srgb=role=='BaseColor';t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if role=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if role=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
 if role=='Normal':t.flip_green_channel=True
 textures[role]=save(t)
mp=ROOT+'/Materials/M_M870_OriginalSurface';m=u.load_asset(mp)
if not m:m=A.create_asset('M_M870_OriginalSurface',ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
if not m:raise RuntimeError('Could not load/create the saved M870 material: '+mp)
for ex in list(L.get_material_expressions(m)):L.delete_material_expression(m,ex)
m.set_editor_property('used_with_skeletal_mesh',True);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
m.set_editor_property('two_sided',True)
for role,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Normal',u.MaterialProperty.MP_NORMAL)]:
 t=L.create_material_expression(m,u.MaterialExpressionTextureSample);t.texture=textures[role];t.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS;L.connect_material_property(t,'RGB' if role in ('BaseColor','Normal') else 'R',prop)
E.set_metadata_tag(m,'Attribution','M870 Tactical by WillisChiejina, Sketchfab fad4289d1083447d9c8cc833362b04c6, CC BY 4.0; adapted for FPSGAME');L.recompile_material(m);save(m)
materials={}
for entry in D['materials']:
 if entry['asset']:
  materials[entry['slot']]=entry['asset'];materials[entry['asset'].rsplit('.',1)[-1]]=entry['asset']
def bind(mesh):
 slots=[s.copy() for s in mesh.materials];skin=[]
 for i,slot in enumerate(slots):
  name=str(slot.get_editor_property('imported_material_slot_name'));name=re.sub(r'[._]\d{3}$','',name)
  if name.startswith('M870_OriginalSurface'):slot.material_interface=m;slot.material_slot_name='M870_OriginalSurface'
  else:
   path=materials.get(name)
   if not path and re.search(r'_\d+$',name):path=materials.get(re.sub(r'_\d+$','',name))
   if not path:
    path=next((v for k,v in materials.items() if re.sub(r'[._]\d{3}$','',k)==name),None)
   if not path:raise RuntimeError('Unmapped M870 retained material '+name)
   slot.material_interface=load(path)
   if any(k in name.lower() for k in ('skin','manny','barearm')):slot.material_slot_name='Manny_M870_'+str(i);skin.append(i)
   elif '12gauge' in name.lower():slot.material_slot_name='12gauge'
  slots[i]=slot
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None);return skin
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 mesh=imported(auth['mesh'],ROOT,'SK_M870_V7',options);report['arm_materials']=bind(mesh)
 editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.recompute_normals=False;editor.set_lod_build_settings(mesh,0,settings)
 save(mesh);save(mesh.skeleton);report['mesh']=mesh.get_path_name();report['skeleton']=mesh.skeleton.get_path_name();report['clips']={}
 compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
 for role,entry in auth['clips'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
  a=imported(entry['file'],ROOT+'/Animations','A_M870_'+role,opt);a.set_editor_property('bone_compression_settings',compression)
  if role=='quick_melee':
   curve='Super90MeleeArmAuthored'
   if u.AnimationLibrary.does_curve_exist(a,curve,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(a,curve)
   u.AnimationLibrary.add_curve(a,curve);u.AnimationLibrary.add_float_curve_keys(a,curve,[0.,entry['duration']],[1.,1.])
   if not u.WeaponAnimationAuthoring.finalize_authored_animation(a):raise RuntimeError('Cannot finalize M870 melee ownership curve')
  save(a);report['clips'][role]=a.get_path_name()
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 world=imported(auth['world_mesh'],ROOT+'/Parts','SM_M870',opt)
 for i in range(len(world.static_materials)):world.set_material(i,m)
 save(world);report['world_mesh']=world.get_path_name()
 for entry in json.loads((O/'Assembly/manifest.json').read_text()):
  part=imported(entry['file'],ROOT+'/Assembly',entry['name'],opt)
  for i in range(len(part.static_materials)):part.set_material(i,m)
  save(part)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
for file in (O/'Audio').glob('*.wav'):
 sound=imported(file,ROOT+'/Audio',file.stem);sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM);sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE);sound.set_editor_property('looping',False);save(sound)
# The arms share the exact retained bind. Existing native outfits follow the
# same final pose and retain their own independent material/skin provenance.
f=P/'Content/ColdSteelData/modular_outfits.json';before=f.read_bytes();data=json.loads(before.decode('utf-8-sig'));profile=dict(data['profiles'][D['mesh']]);profile['hide_source_materials']=report['arm_materials'];data['profiles'][report['mesh']]=profile
if f.read_bytes()!=before:raise RuntimeError('Outfit catalog changed during import; keep saved assets and merge again')
backup=O/'Before/Content/ColdSteelData/modular_outfits.json';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_bytes(before)
f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report['completed']=True;(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('M870_SAVED',len(report['saved']),'assets')
