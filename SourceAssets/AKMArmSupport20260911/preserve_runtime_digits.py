"""Preserve the actual installed digit tracks, including corrections newer than authored blends."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=u.load_asset(P+'/Attachments/SK_AKM_MannyNative');report={}
for variant in ['prism','angled']:
 for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty']:
  name=f'A_AKM_{variant}_{clip}';dest=P+'/ArmSupportFinalV2/'+variant+'/'+name
  if not u.EditorAssetLibrary.does_asset_exist(dest):assert u.EditorAssetLibrary.duplicate_asset(P+'/ArmSupport/'+variant+'/'+name,dest)
  a=u.load_asset(dest);old=u.load_asset(P+('/GripReturn/' if 'reload' in clip else '/Attachments/')+variant+'/'+name);u.AKMAnimationAuditLibrary.finish_animation_compression(old)
  poses=[u.AnimPoseExtensions.get_anim_pose_at_time(old,f/120,opt) for f in range(round(a.get_play_length()*120)+1)]
  names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(poses[0]) if str(n).endswith('_l') and str(n).startswith(('index','middle','ring','pinky','thumb'))]
  controller=a.get_editor_property('controller');controller.open_bracket('Preserve installed AKM grip digit contact',False)
  for n in names:
   keys=[u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL) for p in poses]
   assert controller.set_bone_track_keys(n,[k.translation for k in keys],[k.rotation for k in keys],[k.scale3d for k in keys],False)
  controller.close_bracket(False);u.AKMAnimationAuditLibrary.finish_animation_compression(a);assert u.EditorAssetLibrary.save_loaded_asset(a,False);report[name]=names
  task=u.AssetExportTask();task.object=a;task.filename=str(O/variant/(name+'_Runtime.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.AnimSequenceExporterFBX();assert u.Exporter.run_asset_export_task(task)
(O/'preserved_runtime_digits.json').write_text(json.dumps(report,indent=2));u.log('AKM_RUNTIME_DIGITS_PASS')
