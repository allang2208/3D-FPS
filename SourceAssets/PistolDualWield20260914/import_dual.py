"""Import dual assets; -DualSprintSmoothUpdate imports only SprintSmoothV5 actions."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
root='/Game/Weapons/PistolDualWield20260914'
revolver_flick='DualRevolverReloadFlickUpdate' in u.SystemLibrary.get_command_line()
reload_update=revolver_flick
natural_update='DualNaturalAimUpdate' in u.SystemLibrary.get_command_line()
smooth_sprint='DualSprintSmoothUpdate' in u.SystemLibrary.get_command_line()
if any(flag in u.SystemLibrary.get_command_line() for flag in ('DualSprintUpdate','DualPoseUpdate','DualReloadUpdate')):
 raise RuntimeError('Legacy outputs are archived; use -DualNaturalAimUpdate, -DualSprintSmoothUpdate or -DualRevolverReloadFlickUpdate')
sprint_update=smooth_sprint
pose_update=revolver_flick or sprint_update or natural_update
revision='RevolverReloadFlickV6' if revolver_flick else 'SprintSmoothV5' if smooth_sprint else 'NaturalAimV3'
output=O/revision if pose_update else O
sources={'M1911':'/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny','DW715':'/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny'}
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel');receipt={}
def import_file(file,dest,opt):
 t=u.AssetImportTask();t.filename=file;t.destination_path=dest;t.destination_name=Path(file).stem;t.options=opt;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);obj=u.load_asset(dest+'/'+t.destination_name)
 if not obj:raise RuntimeError('Import failed: '+file)
 return obj
for family,source_path in sources.items():
 if reload_update and family!='DW715':continue
 source=u.load_asset(source_path);bindings={str(m.material_slot_name):m.material_interface for m in source.materials}
 data=json.loads((output/f'{family}-authoring.json').read_text(encoding='utf-8'));receipt[family]={}
 for side,entry in data['sides'].items():
  dest=f'{root}/{family}/{side}'
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
  opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=source.skeleton
  opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
  opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
  opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  mesh=u.load_asset(dest+'/'+Path(entry['mesh']).stem) if reload_update or pose_update else import_file(entry['mesh'],dest,opt);slots=mesh.materials
  for i,slot in enumerate(slots):
   key=str(slot.material_slot_name)
   if key in bindings:slot.material_interface=bindings[key];slots[i]=slot
  if not reload_update and not pose_update:mesh.set_editor_property('materials',slots);E.save_loaded_asset(mesh,False)
  receipt[family][side]={'mesh':mesh.get_path_name(),'animations':{}}
  # The default invocation restores the original left/right mesh only. Current
  # actions are imported explicitly from V3/V5/V6; initial actions are retired.
  if not pose_update and not reload_update:continue
  for kind,info in entry['clips'].items():
   if reload_update and not kind.startswith(('single_','speed_')):continue
   if natural_update and (kind.startswith('sprint') or (family=='DW715' and kind.startswith(('single_','speed_')))):continue
   opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
   opt.import_mesh=False;opt.import_animations=True;opt.skeleton=source.skeleton
   opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
   clip=import_file(info['fbx'],dest+('/'+revision+'/Animations' if pose_update else '/Animations'),opt)
   if compression:clip.set_editor_property('bone_compression_settings',compression)
   if not E.save_loaded_asset(clip,False):raise RuntimeError('Save failed: '+clip.get_path_name())
   receipt[family][side]['animations'][kind]=clip.get_path_name()
(output/('reload-import.json' if reload_update else 'import.json')).write_text(json.dumps({'assets':receipt,'state':'Imported; no runtime tests'},indent=2),encoding='utf-8')
u.log('DUAL_IMPORT_COMPLETE')
