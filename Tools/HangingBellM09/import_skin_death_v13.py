"""Background production save of the repaired M09 mesh, corpse asset and release clip."""
import unreal as u,json,shutil,traceback
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/SkinDeathV13')
BASE='/Game/Monsters/HangingBellM09/V04';A=u.EditorAssetLibrary
report={'saved':[],'game_tested':False,'complete':False}
if globals().get('M09_DEATH_ONLY',False):
 report=json.loads((ROOT/'Records/import_saved.json').read_text(encoding='utf8'));report.pop('error',None)
def receipt(): (ROOT/'Records/import_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def save(a):
 if not A.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 report['saved'].append(a.get_path_name());receipt()
def task(filename,path,opts):
 t=u.AssetImportTask();t.filename=str(filename);t.destination_path=path.rsplit('/',1)[0];t.destination_name=path.rsplit('/',1)[1]
 t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
 if not t.imported_object_paths:raise RuntimeError('No imported object: '+str(filename))
 return u.load_asset(path)
try:
 dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
 if any(p.startswith(BASE) for p in dirty):raise RuntimeError('M09 has unsaved changes')
 m=u.load_asset(BASE+'/SK_M09');pa=m.physics_asset;sk=m.skeleton
 if not (ROOT/'Records/physics_asset_before.json').exists():
  (ROOT/'Records/physics_asset_before.json').write_text(u.HangingBellM09.describe_physics(m),encoding='utf8')
 backup=ROOT/'Before';backup.mkdir(exist_ok=True)
 for a in (m,pa,sk,u.load_asset(BASE+'/Animations/A_M09_Death')):
  relative=a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
  source=Path('D:/FPS3D/FPSGAME/Content')/relative;dest=backup/source.name
  if not dest.exists():shutil.copy2(source,dest)
 if not globals().get('M09_DEATH_ONLY',False):
  materials=list(m.materials)
  u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
  o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False
  o.skeleton=sk;o.create_physics_asset=False;o.physics_asset=pa
  data=o.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
  data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  m=task(ROOT/'Exports/M09_Rigged_V13.fbx',BASE+'/SK_M09',o)
  # Restore the current production slot assignments after the geometry reimport.
  old_slots={str(s.material_slot_name):s.material_interface for s in materials}
  slots=list(m.materials)
  for s in slots:
   name=str(s.material_slot_name)
   if name in old_slots:s.material_interface=old_slots[name]
  m.materials=slots
  if not u.HangingBellM09.build_physics(m,pa):raise RuntimeError('M09 physics authoring failed')
  A.set_metadata_tag(m,'M09SkinRevision','V13 owner-separated small hands and independent closures')
  A.set_metadata_tag(pa,'M09PhysicsRevision','V13 actual FBX container and rigid anchor handoff')
  for a in (m,pa,sk):save(a)
  (ROOT/'Records/physics_asset_authored.json').write_text(u.HangingBellM09.describe_physics(m),encoding='utf8')
 o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
 o.import_as_skeletal=True;o.import_mesh=False;o.import_animations=True;o.import_materials=False;o.import_textures=False;o.skeleton=sk
 data=o.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
 data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
 data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
 clip=task(ROOT/'Exports/A_M09_Death_V13.fbx',BASE+'/Animations/A_M09_Death',o)
 clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False);clip.set_editor_property('rate_scale',1.)
 clip.set_preview_skeletal_mesh(m);A.set_metadata_tag(clip,'M09DeathRevision','V13 relaxed staggered release; physics at 0.60 seconds')
 save(clip);report['complete']=True;receipt();print('M09_SKIN_DEATH_V13_SAVED')
except Exception:
 report['error']=traceback.format_exc();receipt();raise
