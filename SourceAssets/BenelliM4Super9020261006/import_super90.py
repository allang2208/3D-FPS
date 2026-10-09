"""Import and save this batch only; no editor launch, game, or acceptance run."""
import unreal as u,json,re,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/Super90/Cransh20261006';OUTFIT='/Game/Characters/ModularOutfit20260924/Super90Source20261006'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([ROOT,OUTFIT],True)
report={'saved':[],'runtime_tested':False};auth=json.loads((O/'authoring.json').read_text())
def record():(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
def load(p):
 v=u.load_asset(p)
 if not v:raise RuntimeError('Missing asset '+p)
 return v
def save(v):
 if not u.EditorLoadingAndSavingUtils.save_packages([v.get_outermost()],False):raise RuntimeError('Save failed '+v.get_path_name())
 if v.get_path_name() not in report['saved']:report['saved'].append(v.get_path_name())
 record();return v
def imported(file,folder,name,opt=None):
 file=Path(file);sha=hashlib.sha256(file.read_bytes()).hexdigest();p=folder+'/'+name
 if E.does_asset_exist(p):
  v=load(p)
  if E.get_metadata_tag(v,'Super90SourceSHA256')==sha:return v
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 if opt:task.options=opt;task.factory=u.FbxFactory()
 A.import_asset_tasks([task]);v=load(p);E.set_metadata_tag(v,'Super90SourceSHA256',sha);return save(v)
def node(m,cls):return L.create_material_expression(m,cls)
textures={}
for file in sorted((O/'Original/Source/textures').glob('*.png')):
 tex=imported(file,ROOT+'/Textures','T_S90_'+file.stem);normal='Normal' in file.stem;color='Base' in file.stem
 tex.srgb=color;tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS
 tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON
 if normal:tex.flip_green_channel=file.stem!='TTI_Benelli_M4_Normal_brand_friendly'
 save(tex);textures[file.stem]=tex
# Current audio is the user's gamedev selection; full restoration must keep it.
audio_script=P/'SourceAssets/Super90GameDevAudio20261007/import_audio.py'
exec(compile(audio_script.read_text(encoding='utf-8'),str(audio_script),'exec'),{'__file__':str(audio_script),'__name__':'__main__'})
materials={}
for name,stems in auth['material_groups'].items():
 path=ROOT+'/Materials/M_S90_'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset('M_S90_'+name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
 if not m:raise RuntimeError('Could not create material '+path)
 for ex in list(L.get_material_expressions(m)):L.delete_material_expression(m,ex)
 m.set_editor_property('used_with_skeletal_mesh',True);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 for key,stem in zip(('BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AMBIENT_OCCLUSION'),stems):
  if stem:
   tx=node(m,u.MaterialExpressionTextureSample);tx.texture=textures[stem];tx.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='NORMAL' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BASE_COLOR' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
   L.connect_material_property(tx,'RGB' if key in ('BASE_COLOR','NORMAL') else 'R',getattr(u.MaterialProperty,'MP_'+key))
  elif key=='ROUGHNESS':
   c=node(m,u.MaterialExpressionScalarParameter);c.set_editor_property('parameter_name','Roughness');c.set_editor_property('default_value',.72);L.connect_material_property(c,'',u.MaterialProperty.MP_ROUGHNESS)
 E.set_metadata_tag(m,'Attribution','Cransh / haoliu95 / teenjust500; Sketchfab 225a62190f6043ca975eaa2798ab7e2c; CC BY 4.0; adapted for FPSGAME')
 if name=='TTI_Benelli_M4':
  import sys
  sys.path.insert(0,str(P/'SourceAssets/Super90SurfaceRepair20261007'))
  from material_surface import apply_receiver_surface
  apply_receiver_surface(m)
 L.recompile_material(m);save(m);materials[name]=m
materials['FactorySights']=materials['TTI_Benelli_M4']
materials['12gauge_mounted']=materials['12gauge']
# Saved WS1 instances own the current gun surfaces; original outfit/shell
# materials above remain the source for their separate equipment and ammo.
surface_receipt=P/'SourceAssets/Super90WS1Surface20261007/import_receipt.json'
if surface_receipt.exists():
 for slot,entry in json.loads(surface_receipt.read_text())['materials'].items():
  if slot!='MountSteel':materials[slot]=load(entry['asset'])
base=load('/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7')
skin=[x.material_interface for x in base.materials]
def bind(mesh):
 slots=list(mesh.materials);arm=[]
 for i,v in enumerate(slots):
  n=re.sub(r'[._]\d{3}$','',str(v.material_slot_name))
  if n in materials:v.material_interface=materials[n]
  else:
   index=0 if 'upper' in n.lower() else 1 if ('fore' in n.lower() or 'lower' in n.lower()) else 2
   v.material_interface=skin[min(index,len(skin)-1)];v.material_slot_name='Manny_S90_'+n.removeprefix('Manny_S90_');arm.append(i)
  slots[i]=v
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None);save(mesh);return arm
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 def mesh_opt(skeleton=None,import_tangents=False):
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
  if skeleton:o.skeleton=skeleton
  o.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS if import_tangents else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;return o
 mesh=imported(auth['mesh'],ROOT,'SK_Super90_V7',mesh_opt(import_tangents=True))
 editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
 settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.recompute_normals=False;settings.recompute_tangents=False
 editor.set_lod_build_settings(mesh,0,settings)
 report['arm_materials']=bind(mesh);save(mesh.skeleton);report['mesh']=mesh.get_path_name();report['skeleton']=mesh.skeleton.get_path_name();report['material_slots']=[str(x.material_slot_name) for x in mesh.materials]
 report['outfit']={};report['outfit_material_slots']={}
 for role,file in auth['outfit'].items():
  v=imported(file,OUTFIT+'/Super90',Path(file).stem,mesh_opt(mesh.skeleton));bind(v);report['outfit'][role]=v.get_path_name();report['outfit_material_slots'][role]=[str(x.material_slot_name) for x in v.materials];record()
 report['static']={}
 for kind,name in [('gloves','SM_ue_hardknuckle_gloves'),('shirt','SM_ue_st6_sleeves'),('casing','SM_Super90_Casing')]:
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_as_skeletal=False;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.static_mesh_import_data.combine_meshes=True
  folder=ROOT+'/Parts' if kind=='casing' else OUTFIT+'/Pickups'
  v=imported(O/'Exports'/(name+'.fbx'),folder,name,o);slots=list(v.static_materials)
  for i,slot in enumerate(slots):
   n=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));slot.material_interface=materials.get(n,skin[-1]);slots[i]=slot
  v.set_editor_property('static_materials',slots);save(v);report['static'][kind]=v.get_path_name();record()
 report['animations']={}
 for kind,entry in auth['clips'].items():
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;o.import_mesh=False;o.import_animations=True;o.skeleton=mesh.skeleton
  o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
  a=imported(entry['fbx'],ROOT+'/Animations','A_Super90_'+kind,o);a.set_editor_property('bone_compression_settings',load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(a);report['animations'][kind]={'asset':a.get_path_name(),'duration':a.get_play_length()};record()
 report['assets_imported']=True;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
print('SUPER90_ASSETS_SAVED',len(report['saved']))
