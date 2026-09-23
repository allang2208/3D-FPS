"""Read current rifle idle landmarks for the requested framing comparison."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent
weapons={
 'M4':('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle',0),
 'QBZ191':('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny','/Game/Weapons/QBZ191/Refined20260913/Animations/base/A_QBZ191_idle',0),
 'ASH12':('/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface','/Game/Weapons/ASH12/Integrated20260917/Animations/A_ASH12_idle',8),
 'A762':('/Game/Weapons/A762/Integrated20260920/SK_A762_Manny','/Game/Weapons/A762/Integrated20260920/Animations/A_A762_idle',6),
 'PKM':('/Game/Weapons/PKMLowpoly20260922/SK_PKM_Manny','/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_idle',6)}
c=u.get_default_object(u.load_class(None,'/Script/FPSGAME.FPSGAMECharacter'))
hip=c.get_editor_property('m4_hip_viewmodel_location');rotation=c.get_editor_property('viewmodel_rotation');fov=c.get_editor_property('base_vertical_field_of_view')
def xyz(v):return [round(v.x,5),round(v.y,5),round(v.z,5)]
report={'base_hip_cm':xyz(hip),'base_rotation':str(rotation),'vertical_fov':fov,'weapons':{}}
for name,(mp,ap,forward) in weapons.items():
 mesh=u.load_asset(mp);anim=u.load_asset(ap)
 if not mesh or not anim:raise RuntimeError('Missing comparison source '+name)
 opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,0,opt)
 tf=u.Transform(location=hip+u.Vector(forward,0,0),rotation=rotation)
 row={'mesh':mp,'idle':ap,'hip_cm':xyz(tf.translation),'bones':{}}
 for bone in ['WPN_root','WPN_RearSight','WPN_FrontSight','hand_l','hand_r']:
  p=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD)
  v=tf.transform_location(p.translation)
  row['bones'][bone]={'component_cm':xyz(p.translation),'camera_cm':xyz(v),'pose':str(p)}
  if v.x>0:row['bones'][bone]['screen_uv_16_9']=[round(.5+v.y/v.x/(math.tan(math.radians(fov/2))*16/9)*.5,4),round(.5-v.z/v.x/math.tan(math.radians(fov/2))*.5,4)]
 report['weapons'][name]=row
(O/'idle_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'base':report['base_hip_cm'],'weapons':{n:{'hip':r['hip_cm'],'rear':r['bones']['WPN_RearSight'].get('screen_uv_16_9'),'front':r['bones']['WPN_FrontSight'].get('screen_uv_16_9')} for n,r in report['weapons'].items()}}))
