"""Read the failing reload's coordinates and native contact before editing."""
import json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent
author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
f=json.loads((O.parent/'Super90SprintArmR3_20261007/current.json').read_text())['framing']
def frame(key,up):
    d=f[key];r=s['uemat'](d['WPN_root']);x=(Vector(d['WPN_FrontSight'][:3])-Vector(d['WPN_RearSight'][:3])).normalized()
    z=r.to_quaternion()@Vector(up);y=z.cross(x).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()
base=Quaternion(Vector((0,0,1)),math.pi/2)
rotation=base@frame('M4',(0,0,1))@frame('Super90',(0,-1,0)).inverted()
location=Vector((6,7,-7))+base@Vector(f['M4']['hand_r'][:3])-rotation@Vector(f['Super90']['hand_r'][:3])
def cam(v):return list(location+rotation@Vector((v.x*100,-v.y*100,v.z*100)))
out={'camera':{'rotation':list(rotation),'location':list(location)},'rows':[]}
for n in ('WPN_root','WPN_Load','WPN_Shell','hand_l','upperarm_l'):
    out.setdefault('native',{})[n]={'rest':[list(r) for r in s['rest'][n]],'idle':[list(r) for r in s['idle'][n]]}
for f in (0,7,14,23,42,60,69,74,80,87,90,100,114,120,127,134,140,146):
    p,handle,tube=s['pose'](f,7,False)
    shoulder,elbow,wrist=[p[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
    neutral=p['lowerarm_l'].to_quaternion()@s['rest']['lowerarm_l'].to_quaternion().inverted()@s['rest']['hand_l'].to_quaternion()
    wrist_delta=p['hand_l'].to_quaternion()@neutral.inverted();axis=(wrist-elbow).normalized()
    twist=2*math.atan2(Vector((wrist_delta.x,wrist_delta.y,wrist_delta.z)).dot(axis),wrist_delta.w)
    twist=(twist+math.pi)%(2*math.pi)-math.pi
    swing=wrist_delta@Quaternion(axis,twist).inverted()
    row={'frame':f,'camera_cm':{n:cam(p[n].translation) for n in ('upperarm_l','lowerarm_l','hand_l','hand_r','WPN_root','WPN_Load','WPN_Shell')},
      'tube_rear_camera_cm':cam(tube@Vector((0,-.35,0))),'handle_camera_cm':cam(handle.translation),
      'wrist_swing':math.degrees(swing.angle),'forearm_twist':math.degrees(twist),
      'shoulder_move_cm':100*(shoulder-s['idle']['upperarm_l'].translation).length,
      'elbow_bend':math.degrees((elbow-shoulder).angle(wrist-elbow)),
      'scales':{n:list(p[n].to_scale()) for n in ('hand_l','lowerarm_l','WPN_Shell')}}
    out['rows'].append(row)
(O/'author_geometry_working.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
for r in out['rows']:print(json.dumps(r),flush=True)
