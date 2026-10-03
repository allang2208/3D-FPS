"""Import/save RSH-12 meshes, source PBR and sparse shared-animation profiles."""
import unreal as u,json,re,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];DEST='/Game/Weapons/RSH12'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=dict(saved=[],meshes={},profiles={},source_acquired=True,complete=False,runtime_tested=False)
attribution='Rsh-12 by Medji; https://sketchfab.com/3d-models/rsh-12-177cd570002d4e89bd378ec328a47f9c; CC BY 4.0; modifications: normalized units, closed assembly, five original cartridges, 715 native binding, sparse mechanical/contact profiles, source PBR, icon.'
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing production dependency '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
 if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
 record();return a
def create(name,folder,cls,factory):
 a=u.load_asset(folder+'/'+name)
 return a or A.create_asset(name,folder,cls,factory)
def imported(file,folder,name,options=None):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
 task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 if options:task.options=options;task.factory=u.FbxFactory()
 A.import_asset_tasks([task]);a=load(folder+'/'+name);E.set_metadata_tag(a,'SourceAttribution',attribution);return a
textures={}
for key,file,normal in [('albedo','DefaultMaterial_albedo.jpg',False),('roughness','DefaultMaterial_roughness.jpg',False),('metallic','DefaultMaterial_metallic.jpg',False),('ao','DefaultMaterial_AO.jpg',False),('normal','DefaultMaterial_normal.png',True)]:
 tex=imported(O/'Original/Extracted/textures'/file,DEST+'/Textures','T_RSH12_'+key)
 tex.srgb=key=='albedo';tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
 tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if key=='albedo' else u.TextureCompressionSettings.TC_MASKS
 if normal:tex.set_editor_property('flip_green_channel',True)
 textures[key]=save(tex)
# Private source adapter retains the existing shared WS surface/water graph.
masterpath=DEST+'/Materials/M_RSH12_SourceSurface'
master=load(masterpath) if E.does_asset_exist(masterpath) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',masterpath)
for n in L.get_material_expressions(master):
 if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceRoughness':
  n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS);n.set_editor_property('texture',textures['roughness'])
for key,prop in [('metallic',u.MaterialProperty.MP_METALLIC),('ao',u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
 for oldnode in L.get_material_expressions(master):
  if isinstance(oldnode,u.MaterialExpressionTextureSampleParameter2D) and str(oldnode.get_editor_property('parameter_name'))=='RSH12_'+key:L.delete_material_expression(master,oldnode)
 n=L.create_material_expression(master,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name','RSH12_'+key);n.set_editor_property('texture',textures[key]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 L.connect_material_property(n,'R',prop)
L.set_material_usage(master,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(master);save(master)
mi=create('MI_RSH12_SourcePBR',DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
L.clear_all_material_instance_parameters(mi);L.set_material_instance_parent(mi,master)
for name,key in [('SourceBaseColor','albedo'),('SourceRoughness','roughness'),('SurfaceNormal','normal'),('RSH12_metallic','metallic'),('RSH12_ao','ao')]:L.set_material_instance_texture_parameter_value(mi,name,textures[key])
for name,value in dict(SourceColorWeight=1.,SourceRoughnessWeight=1.,SourceRoughnessPivot=.5,Roughness=.5,GrainRoughness=0.,MottleRoughness=0.,MottleColor=0.,Stipple=0.,EdgeWear=0.,EdgeHighlight=0.,CavityDarken=0.,CavityRoughness=0.,HandlingPolish=0.,ScratchAmount=0.,MaskUVChannel=0.,WeaponWetness=0.,BeadScale=78.).items():L.set_material_instance_scalar_parameter_value(mi,name,value)
L.update_material_instance(mi);E.set_metadata_tag(mi,'SourceAttribution',attribution);save(mi)
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
wet=create('DA_RSH12_WetMaterials',DEST+'/Materials',u.WeatherPresentationAssets,factory);wet.set_editor_property('wet_materials',{mi.get_path_name():mi});save(wet)
outfits=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['profiles'];newoutfits={}
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for side,relative,folder in [('single','Single',DEST),('r','Dual/r',DEST+'/Dual/r'),('l','Dual/l',DEST+'/Dual/l')]:
  source=O/relative;author=json.loads((source/'authoring.json').read_text());donor=json.loads((O/'Donor'/side/'motion.json').read_text())
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
  opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=load(author['skeleton'])
  opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False);opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
  opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  mesh=imported(source/author['mesh'],folder,Path(author['mesh']).stem,opt)
  bare=load('/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default');slots=list(mesh.materials);arms=[]
  for i,s in enumerate(slots):
   if 'Manny' in str(s.material_slot_name):s.material_interface=bare;arms.append(i)
   else:s.material_interface=mi
   slots[i]=s
  mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
  subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
  for lod in range(subsystem.get_lod_count(mesh)):
   settings=subsystem.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;subsystem.set_lod_build_settings(mesh,lod,settings)
  save(mesh);receipt['meshes'][side]=dict(asset=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),arm_slots=arms)
  entry=copy.deepcopy(outfits[donor['mesh']]);entry.update(native_bare_arms=True,hide_source_materials=arms);entry.pop('original_gloved_source',None);newoutfits[mesh.get_path_name()]=entry
  profilefolder='/Game/Weapons/AnimationProfiles20261001/ue_rsh12'+('' if side=='single' else '/Dual_'+side)
  f=u.DataAssetFactory();f.set_editor_property('data_asset_class',u.WeaponGripProfile);profile=create('DA_base',profilefolder,u.WeaponGripProfile,f)
  data=json.loads((source/'profile.json').read_text())
  if not profile.set_shared_clips_from_json(json.dumps(data)):raise RuntimeError('Cannot publish shared pose profile '+side)
  E.set_metadata_tag(profile,'SourceAttribution',attribution);save(profile)
  receipt['profiles'][side]=dict(asset=profile.get_path_name(),shared_sequences=len(data['clips']),duplicated_sequences=0);record()
  print('RSH12_FAMILY_IMPORTED_AND_SAVED',side,flush=True)
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
 opt.static_mesh_import_data.combine_meshes=True
 cartridge=imported(O/'SM_RSH12_Cartridge.fbx',DEST,'SM_RSH12_Cartridge',opt)
 slots=list(cartridge.static_materials)
 for s in slots:s.material_interface=mi
 cartridge.set_editor_property('static_materials',slots);save(cartridge)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
icon=imported(P/'Content/ColdSteelData/Icons/ue_rsh12.png','/Game/ColdSteelData/Icons','ue_rsh12');icon.srgb=True;icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI;icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(icon)
config=P/'Content/ColdSteelData/modular_outfits.json';text=config.read_text(encoding='utf-8-sig');at=text.index('{',text.index('"profiles"'));data,n=json.JSONDecoder().raw_decode(text[at:]);data.update(newoutfits)
if config.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Outfit catalog changed during publication')
backup=O/'BeforeCatalog/modular_outfits.json';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_text(text,encoding='utf8')
config.write_text(text[:at]+json.dumps(data,ensure_ascii=False,indent=2)+text[at+n:],encoding='utf8')
receipt.update(complete=True,status='assets_imported_and_saved',materials=mi.get_path_name(),cartridge=cartridge.get_path_name());record()
print('RSH12_ASSET_IMPORT_COMPLETE',flush=True)
