"""Authoring input: read saved V9 single-pistol data, no play or asset changes."""
import unreal as u, json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/PitViperLeftTwoHand20261020'); (O/'Source').mkdir(exist_ok=True)
mesh_path='/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny'
mesh=u.load_asset(mesh_path)
h=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017/Work/mesh_hierarchy.json').read_text())[mesh_path]
names=h['names']; ref=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
def pack(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
h['reference']=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names]
h['mesh']=mesh_path;h['skeleton']=mesh.skeleton.get_path_name()
(O/'hierarchy.json').write_text(json.dumps(h),encoding='utf-8')
roles=['idle','idle_empty','aim','aim_empty','fire','fire_last','aim_fire','aim_fire_last','equip_charge','equip_charge_empty','reload','reload_empty','sprint','sprint_empty','quickcombat']
for role in roles:
 out=O/'Source'/(role+'.json')
 if out.exists(): continue
 path='/Game/Weapons/PitViper2011/Integrated20261002/Single/Animations/A_PitViper2011_'+role
 clip=u.load_asset(path)
 if not clip: raise RuntimeError('Required author clip missing '+path)
 dmi=clip.get_editor_property('data_model_interface');rate=dmi.get_frame_rate();count=dmi.get_number_of_keys();fps=rate.numerator/rate.denominator
 frames=[]
 for k in range(count):
  poses=u.AnimationLibrary.get_bone_poses_for_time(clip,names,k/fps,False,mesh)
  frames.append([pack(t) for t in poses])
 row={'role':role,'source':path,'fps':fps,'rate':[rate.numerator,rate.denominator],'length':dmi.get_play_length(),'frames':frames}
 out.write_text(json.dumps(row,separators=(',',':')),encoding='utf-8')
 print('LEFT_TWO_HAND_SOURCE',role,count,flush=True)
print('LEFT_TWO_HAND_SOURCES_SAVED',flush=True)
