"""Compare only the two requested saved Ji Lei takes, in native data-model time."""
import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent
mesh=json.loads((P/'native-mesh.json').read_text())
def matrix(t):return Matrix.LocRotScale(Vector(t[:3]),Quaternion((t[6],*t[3:6])).normalized(),Vector(t[7:]))
def deg(q):
 a=math.degrees(q.angle);return min(a,360-a)
rest={n:matrix(b['transform']) for n,b in mesh['bones'].items()}
report={'scope':'two saved native Ji Lei takes; 240 Hz data model; offline skin, no gameplay','before':{},'after':{}}
for label,file in [('before','native-poses-before.json'),('after','native-poses.json')]:
 data=json.loads((P/file).read_text())
 for kind,clip in data.items():
  names=clip['names'];ix={n:i for i,n in enumerate(names)};frames=clip['frames'];summary={s:{} for s in ['l','r']};previous={}
  rows=[]
  for frame_index,row in enumerate(frames):
   pose={n:matrix(t) for n,t in zip(names,row)};metrics={}
   for s in ['l','r']:
    U,F,H=[n+'_'+s for n in ['upperarm','lowerarm','hand']]
    upper=(pose[F].translation-pose[U].translation).normalized();fore=(pose[H].translation-pose[F].translation).normalized()
    b=(rest[H].translation-rest[F].translation).normalized()
    neutral=pose[H].to_quaternion()@rest[H].to_quaternion().inverted()@b
    values={'wrist_bend_deg':math.degrees(fore.angle(neutral)),
       'upperarm_length_cm':(pose[F].translation-pose[U].translation).length,
       'forearm_length_cm':(pose[H].translation-pose[F].translation).length}
    for n in [U,F,H,'lowerarm_twist_01_'+s]:
     par=mesh['bones'][n]['parent'];local=pose[par].inverted()@pose[n]
     values[n+'_local_step_deg']=deg(local.to_quaternion().rotation_difference(previous[n])) if n in previous else 0.
     previous[n]=local.to_quaternion()
    values['wrist_step_cm']=math.dist(row[ix[H]][:3],frames[max(0,frame_index-1)][ix[H]][:3])
    for key,value in values.items():
     item=summary[s].setdefault(key,{'max':value,'min':value,'max_time':frame_index/clip['fps']})
     item['min']=min(item['min'],value)
     if value>item['max']:item['max']=value;item['max_time']=frame_index/clip['fps']
    metrics[s]=values
   rows.append(metrics)
  summary['last_frame']=rows[-1]
  w=matrix(frames[-1][ix['WPN_root']]);head=w@Vector((0,0,.916));head=Vector((head.x,-head.y,head.z))
  summary['last_head_camera_cm']=list(head)
  summary['last_head_center_vertical_angle_deg']=math.degrees(math.atan2(head.z,head.y))
  report[label][kind]=summary
 # Grip rigidity is measured separately from skin appearance.
 grip=[]
 for clip in data.values():
  ix={n:i for i,n in enumerate(clip['names'])}
  for row in clip['frames']:
   grip.append(matrix(row[ix['WPN_root']]).inverted()@matrix(row[ix['hand_r']]))
 report[label]['right_grip_position_drift_cm']=max((g.translation-grip[0].translation).length*100 for g in grip)
 report[label]['right_grip_rotation_drift_deg']=max(deg(g.to_quaternion().rotation_difference(grip[0].to_quaternion())) for g in grip)
report['visual_limit']='Saved data-model pose checks; companion renders include the actual equipped sleeves and gloves with simplified materials. Runtime corrective morphs and camera feedback are not evaluated.'
(P/'review-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({label:{kind:{'right_bend_max':report[label][kind]['r']['wrist_bend_deg']['max'],
 'right_bend_last':report[label][kind]['last_frame']['r']['wrist_bend_deg'],
 'right_max_local_step':max(v['max'] for k,v in report[label][kind]['r'].items() if 'local_step' in k),
 'left_max_local_step':max(v['max'] for k,v in report[label][kind]['l'].items() if 'local_step' in k)} for kind in ['Charge','Release']} for label in ['before','after']}),flush=True)
