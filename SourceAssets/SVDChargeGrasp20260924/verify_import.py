"""Requested scoped readback of saved SVD reload data, without PIE or gameplay tests."""
import unreal as u,json,math,hashlib
from pathlib import Path
O=Path(__file__).parent;jobs=json.loads((O/'authoring.json').read_text());receipts=json.loads((O/'import_receipt.json').read_text())
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
options={}
for label,kind in [('source',u.AnimDataEvalType.SOURCE),('compressed',u.AnimDataEvalType.COMPRESSED)]:
 opt=u.AnimPoseEvaluationOptions();opt.set_editor_property('evaluation_type',kind);opt.set_editor_property('optional_skeletal_mesh',mesh);options[label]=opt
def vec(v):return list(v.to_tuple())
def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(vec(a),vec(b))))
def qvalues(q):return [q.x,q.y,q.z,q.w]
def angle(a,b):
 x=qvalues(a);y=qvalues(b);dot=abs(sum(v*w for v,w in zip(x,y)))/math.sqrt(sum(v*v for v in x)*sum(v*v for v in y))
 return math.degrees(2*math.acos(min(1.,dot)))
def rotate(v,q):
 x,y,z,w=q;vx,vy,vz=v
 tx=2*(y*vz-z*vy);ty=2*(z*vx-x*vz);tz=2*(x*vy-y*vx)
 return [vx+w*tx+y*tz-z*ty,vy+w*ty+z*tx-x*tz,vz+w*tz+x*ty-y*tx]
def local_position(child,parent):
 q=qvalues(parent.rotation);q=[-q[0],-q[1],-q[2],q[3]]
 v=rotate([a-b for a,b in zip(vec(child.translation),vec(parent.translation))],q)
 return [a/b for a,b in zip(v,vec(parent.scale3d))]
def bone(p,n,world=False):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD if world else u.AnimPoseSpaces.LOCAL)
report={'game_tested':False,'inspection':'Saved animation data: SOURCE versus COMPRESSED, scoped to changed interval and hold contact. No renderer or PIE.','clips':{}}
for key,info in jobs.items():
 anim=u.load_asset(info['path']);actual=anim.get_editor_property('asset_import_data').get_first_filename()
 if Path(actual).resolve()!=Path(info['source']).resolve():raise RuntimeError('Wrong saved source: '+key)
 disk=O.parents[1]/'Content'/Path(info['path'].removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(disk.read_bytes()).hexdigest()!=receipts[key]['saved_sha256']:raise RuntimeError('Saved package changed: '+key)
 if abs(anim.get_play_length()-515/120)>1e-5:raise RuntimeError('Changed timing: '+key)
 names=info['modified_bones']+['WPN_root','WPN_bolt'];frames=sorted(set(range(220,516,2))|{0,268,294,310,330,344,350,364,408,432,515})
 maxima={'local_position_api_units':0.,'world_position_api_units':0.,'rotation_degrees':0.,'scale_delta':0.};held=[];poses={}
 for f in frames:
  poses={label:u.AnimPoseExtensions.get_anim_pose_at_time(anim,f/120,opt) for label,opt in options.items()}
  for n in names:
   s=bone(poses['source'],n);c=bone(poses['compressed'],n)
   maxima['local_position_api_units']=max(maxima['local_position_api_units'],distance(s.translation,c.translation))
   maxima['rotation_degrees']=max(maxima['rotation_degrees'],angle(s.rotation,c.rotation))
   maxima['scale_delta']=max(maxima['scale_delta'],distance(s.scale3d,c.scale3d))
   ws=bone(poses['source'],n,True);wc=bone(poses['compressed'],n,True)
   maxima['world_position_api_units']=max(maxima['world_position_api_units'],distance(ws.translation,wc.translation))
  if 310<=f<=344:held.append(local_position(bone(poses['compressed'],'hand_r',True),bone(poses['compressed'],'WPN_bolt',True)))
 drift=max(math.dist(p,held[0]) for p in held)
 sample_pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,330/120,options['compressed'])
 scale_probe={'upperarm_to_elbow_world_api_units':distance(bone(sample_pose,'upperarm_r',True).translation,bone(sample_pose,'lowerarm_r',True).translation),
 'root_world_scale':vec(bone(sample_pose,'root',True).scale3d),'bolt_world_scale':vec(bone(sample_pose,'WPN_bolt',True).scale3d)}
 row={'source':actual,'duration':anim.get_play_length(),'sample_count':len(frames),'bone_count':len(names),'max_source_compressed_delta':maxima,'held_hand_bolt_local_drift_api_units':drift,'coordinate_probe':scale_probe}
 report['clips'][key]=row;(O/'import_inspection.json').write_text(json.dumps(report,indent=2));print('SVD_GRASP_READBACK',key,json.dumps(row),flush=True)
print('SVD_GRASP_READBACK_COMPLETE',len(report['clips']),flush=True)
