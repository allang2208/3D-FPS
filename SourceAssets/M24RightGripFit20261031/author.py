"""Right-arm-only M24 grip overlays, authored from the current saved profiles."""
import json,gzip,ast,math,copy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
FIX=Path(__file__).resolve().parent;CHECK=FIX.parent/'M24RightGripCheck20261031'
__file__=str(CHECK/'motion.py')
exec(compile((CHECK/'motion.py').read_text().split("\nif __name__=='__main__':")[0],'current_motion','exec'))
__file__=str(FIX/'author.py')
tree=ast.parse((FIX.parent/'M24ReceiverGripRebuild20261031/author_grasp.py').read_text())
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in ('solve','mask'):exec(compile(ast.Module(body=[node],type_ignores=[]),'right_arm','exec'))
contact_masks=json.loads((FIX.parent/'M24GripOutfit20261030/right_contact_mask.json').read_text())
fit=json.loads((FIX/'fit_parameters.json').read_text());hand0=Matrix(fit['hand0_source'])
idle0,local0=compose(entry('skeleton_base','idle'),0.)
owned=[n for n in names if under(n,'upperarm_r')]+['ik_hand_r']
patch={};report={'owned_bones':owned,'families':{},'left_and_gun_tracks_changed':False,'runtime_tested':False}
for variant,solution in fit['variants'].items():
 wrist_delta=Matrix(solution['hand_target_source'])@hand0.inverted()
 finger_delta={n:local0[n].to_quaternion().inverted()@Quaternion(q) for n,q in solution['finger_local_quaternions'].items()}
 for magazine in ('base','mag10'):
  source_family='skeleton_'+magazine;family=source_family+('' if variant=='Default' else '_'+variant)
  idle,_=compose(entry(source_family,'idle'),0.);old_contact=idle['WPN_root'].inverted()@idle['hand_r']
  clips=[];stats=[]
  for original in D['profiles'][source_family]['clips']:
   role=original['base'].split('.')[-1];duration=original['duration'];data=D['clips'][original['base']]
   rate=200 if 'Bipod' in role else 120
   originals={t['bone']:t for t in original['tracks']}
   times=sorted({0.,duration,*[i/rate for i in range(int(duration*rate)+1)],*[t for n,tr in originals.items() if n in owned for t in tr['times']]})
   tracks={n:{'bone':n,'times':times,'values':[]} for n in owned};last={};held=0;preserved=0
   max_length_delta=0.;max_finger_shift=0.
   for time in times:
    row,local=compose(original,time);weight=mask(original['base'],time,magazine,row,old_contact);fixed=row
    if weight>0:
     gun=row['WPN_root']@rest['WPN_root'].inverted();desired=gun@wrist_delta@gun.inverted()@row['hand_r']
     p,q,s=row['hand_r'].decompose();p1,q1,_=desired.decompose()
     fixed=solve(row,Matrix.LocRotScale(p.lerp(p1,weight),q.slerp(q1,weight),s))
     for n in names:
      if not under(n,'hand_r') or n=='hand_r':continue
      p,q,s=local[n].decompose()
      if n in finger_delta:q=q.slerp(q@finger_delta[n],weight)
      fixed[n]=fixed[parents[n]]@Matrix.LocRotScale(p,q,s)
     held+=1
    else:preserved+=1
    for a,b in (('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')):
     max_length_delta=max(max_length_delta,abs((row[b].translation-row[a].translation).length-(fixed[b].translation-fixed[a].translation).length))
    for n,track in tracks.items():
     if weight==0:
      value=sample(originals[n],time,10,'values') if n in originals else [0,0,0,0,0,0,1,0,0,0]
      dq=Quaternion((value[6],*value[3:6]))
     else:
      loc=fixed[parents[n]].inverted()@fixed[n] if parents[n] else fixed[n]
      p,q,sc=(K@loc@K).decompose();v=raw(data,time,n)
      dq=q@Quaternion((v[6],*v[3:6])).inverted();value=[*(p-Vector(v[:3])),dq.x,dq.y,dq.z,dq.w,*(sc-Vector(v[7:10]))]
      if under(n,'hand_r') and n!='hand_r':max_finger_shift=max(max_finger_shift,(loc.translation-local[n].translation).length)
     if n in last and dq.dot(last[n])<0:dq=-dq
     last[n]=dq.copy();value[3:7]=[dq.x,dq.y,dq.z,dq.w];track['values'].extend(value)
   clips.append({'base':original['base'],'duration':duration,'tracks':list(tracks.values())})
   stats.append({'role':role,'changed_samples':held,'preserved_contact_samples':preserved,'max_limb_length_delta_mm':max_length_delta*1000,'max_finger_local_translation_delta_mm':max_finger_shift*1000})
   print('RIGHT_GRIP_AUTHORED',family,role,flush=True)
  patch[family]={'source_family':source_family,'family':family,'clips':clips};report['families'][family]=stats
with gzip.open(FIX/'right_grip_patch.json.gz','wt') as f:json.dump(patch,f)
(FIX/'authoring_receipt.json').write_text(json.dumps(report,indent=2))
print('M24_RIGHT_GRIP_AUTHORED',len(patch),flush=True)
