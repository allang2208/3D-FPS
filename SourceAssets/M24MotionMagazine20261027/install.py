"""Import native M24 motion, magazine geometry, and sparse reload contact layer."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/MotionMagazine20261027'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();src=json.loads((O/'authoring.json').read_text())
R={'complete':False,'saved':[],'clips':{},'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing asset '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
 if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
 record();return a
def imported(file,folder,name,opt):
 t=u.AssetImportTask();t.filename=file;t.destination_path=folder;t.destination_name=name
 t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory();t.options=opt
 A.import_asset_tasks([t]);return load(folder+'/'+name)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('Unsaved M24 authoring destination; retained without overwrite')
source=load('/Game/Weapons/M24/Surface20261027/SK_M24_SurfaceV9');skeleton=source.skeleton
if skeleton.get_path_name().split('.')[0] in dirty:raise RuntimeError('Shared source skeleton has unsaved edits')
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
 opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
 imp=opt.skeletal_mesh_import_data;imp.set_editor_property('import_morph_targets',True);imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 mesh=imported(src['mesh'],D,'SK_M24_MotionV9',opt)
 material={str(s.material_slot_name):s.material_interface for s in source.materials}
 material['M24_Magazine5']=material['M24_Body'];slots=list(mesh.materials)
 for i,slot in enumerate(slots):slot.material_interface=material[str(slot.material_slot_name)];slots[i]=slot
 mesh.set_editor_property('materials',slots)
 sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);bs=sub.get_lod_build_settings(mesh,0)
 bs.recompute_normals=False;bs.recompute_tangents=False;bs.compute_weighted_normals=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
 sub.set_lod_build_settings(mesh,0,bs);save(mesh)
 # Reuse the accepted skeleton; no authored bone, socket, or retarget mode changes.
 save(skeleton)
 R['mesh']=mesh.get_path_name();R['skeleton']=mesh.skeleton.get_path_name();R['arm_materials']=[i for i,v in enumerate(slots) if str(v.material_slot_name).startswith('MI_Manny')]
 compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel');clips={}
 for role,row in src['clips'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
  # Comparison clips are production intermediates, not runtime variants.
  folder=D+'/Authoring' if role.endswith('_mag10') else D+'/Animations'
  clip=imported(row['file'],folder,'A_M24_'+role,opt);clip.set_editor_property('bone_compression_settings',compression)
  if not role.endswith('_mag10'):save(clip)
  clips[role]=clip;R['clips'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length(),'saved':not role.endswith('_mag10')}
 profile_path=D+'/DA_M24_Mag10'
 if E.does_asset_exist(profile_path):profile=load(profile_path)
 else:
  factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
  profile=A.create_asset('DA_M24_Mag10',D,u.WeaponGripProfile,factory)
 profile.set_editor_property('family','base')
 for role in ('reload','reload_empty'):
  if not profile.bake_clip(clips[role],clips[role+'_mag10']):raise RuntimeError('Sparse contact bake failed '+role)
 save(profile);R['magazine_profile']=profile.get_path_name()
 R['profile_clips']=[{'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'bones':[str(t.get_editor_property('bone')) for t in c.get_editor_property('tracks')]} for c in profile.get_editor_property('clips')]
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
 imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 mag=imported(src['magazine_mesh'],D,'SM_M24_m24_extended_mag_10',opt)
 for i,slot in enumerate(mag.static_materials):
  name='MI_M24_IronSatin' if str(slot.material_slot_name)=='M24_ExtensionSteel' else 'MI_M24_Body_Static'
  mag.set_material(i,load('/Game/Weapons/M24/Surface20261027/Materials/'+name))
 sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
 bs=sub.get_lod_build_settings(mag,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
 sub.set_lod_build_settings(mag,0,bs);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mag);save(mag)
 R['magazine_mesh']=mag.get_path_name();R['complete']=True;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
print('M24_MOTION_MAGAZINE_SAVED',len(R['saved']),flush=True)
