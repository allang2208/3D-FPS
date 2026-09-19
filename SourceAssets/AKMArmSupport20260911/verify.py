import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset(P+'/Attachments/SK_AKM_MannyNative');opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;report={}
def pose(a,f):return u.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
def bone(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
def dist(a,b):return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2)
for variant in ['prism','angled']:
 for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty']:
  name=f'A_AKM_{variant}_{clip}';a=u.load_asset(P+'/ArmSupportFinalV2/'+variant+'/'+name);old=u.load_asset(P+('/GripReturn/' if 'reload' in clip else '/Attachments/')+variant+'/'+name);assert a and old
  assert abs(a.get_play_length()-old.get_play_length())<.0001 and a.get_editor_property('skeleton')==old.get_editor_property('skeleton')
  u.AKMAnimationAuditLibrary.finish_animation_compression(a);u.AKMAnimationAuditLibrary.finish_animation_compression(old)
  maximum=0;rotation=0;errors={}
  for f in range(round(a.get_play_length()*120)+1):
   p,q=pose(a,f),pose(old,f)
   for n in ['hand_l','hand_r','WPN_root','WPN_SOCKET_Magazine','index_03_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']:
    bp,bq=bone(p,n),bone(q,n);error=dist(bp.translation,bq.translation);maximum=max(maximum,error);errors[n]=max(errors.get(n,0),error)
  assert maximum<.03,(name,maximum)
  report[name]={'duration':a.get_play_length(),'preserved_contact_max_position_error_cm':maximum,'errors':errors}
optic=u.load_asset(P+'/ArmSupport/SM_AKM_optic');oldoptic=u.load_asset(P+'/Attachments/SM_AKM_optic');slots={str(s.material_slot_name):s.material_interface.get_path_name() for s in optic.static_materials}
assert '/ArmSupport/M_AKM_Soviet_MountSteel' in slots['AKM_Soviet_MountSteel']
assert optic.get_num_sections(0)==oldoptic.get_num_sections(0)
report['optic_materials']=slots
(O/'ue_validation.json').write_text(json.dumps(report,indent=2));u.log('AKM_SUPPORT_VERIFY_PASS')
