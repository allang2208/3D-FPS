import copy,sys
from pathlib import Path
exec(compile((Path(__file__).parent/'preview.py').read_text().split("\nif __name__=='__main__':")[0],'preview','exec'))
before=copy.deepcopy(D['profiles']);patch=json.load(gzip.open(O/'arm_root_patch.json.gz','rt'))
for family,changes in patch.items():
 for change in changes:
  e=entry(family,change['base'].split('.')[-1].removeprefix('A_M24_'));owned={t['bone'] for t in change['tracks']};e['tracks']=[t for t in e['tracks'] if t['bone'] not in owned]+change['tracks']
use_saved=(O/'saved_profiles.json.gz').exists() and '--candidate' not in sys.argv
if use_saved:D['profiles']=json.load(gzip.open(O/'saved_profiles.json.gz','rt'))
from collections import Counter
_,weld=np.unique(np.round(P,6),axis=0,return_inverse=True)
counts=Counter(tuple(sorted((int(a),int(b)))) for f in weld[F] for a,b in zip(f,np.roll(f,-1)))
open_ids={v for e,n in counts.items() if n==1 for v in e}
root=left&(np.linalg.norm(P-np.array(rest['upperarm_l'].translation),axis=1)<.13)&np.isin(weld,list(open_ids))
report={}
for family in ('base','mag10','skeleton_base','skeleton_mag10'):
 result={'max_hand_error_mm':0.,'max_elbow_error_mm':0.,'max_gun_error_mm':0.,'max_forearm_rotation_error_deg':0.,'max_bone_length_error_mm':0.,'minimum_root_clearance_cm':999.,'root_vertices_in_frame':0,'samples':0}
 camera=C.copy()
 if not family.startswith('skeleton'):
  camera[:3,3]-=(C[:3,:3]@(np.array(base_idle['hand_r'].translation)-np.array(skeleton_idle['hand_r'].translation)))
 for role in ('idle','sprint_enter','sprint_loop','sprint_exit'):
  e=entry(family,role);old=next(c for c in before[family]['clips'] if c['base']==e['base'])
  for t in np.linspace(0,e['duration'],max(3,round(e['duration']*60)+1)):
   row,_=compose(e,float(t));original,_=compose(old,float(t))
   for bone,key in [('hand_l','max_hand_error_mm'),('lowerarm_l','max_elbow_error_mm'),('WPN_root','max_gun_error_mm')]:result[key]=max(result[key],(row[bone].translation-original[bone].translation).length*1000)
   result['max_forearm_rotation_error_deg']=max(result['max_forearm_rotation_error_deg'],math.degrees(row['lowerarm_l'].to_quaternion().rotation_difference(original['lowerarm_l'].to_quaternion()).angle))
   for a,b in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:result['max_bone_length_error_mm']=max(result['max_bone_length_error_mm'],abs((row[a].translation-row[b].translation).length-(original[a].translation-original[b].translation).length)*1000)
   # Surface evaluation at 15 Hz includes every phase of enter/loop/exit.
   if result['samples']%4==0:
    X=skin(row);cp=np.c_[X,np.ones(len(X))]@camera.T;near=root&(cp[:,0]>1)
    margin=-cp[near,2]-cp[near,0]*math.tan(math.radians(37.5));result['minimum_root_clearance_cm']=min(result['minimum_root_clearance_cm'],float(margin.min()));result['root_vertices_in_frame']=max(result['root_vertices_in_frame'],int((margin<0).sum()))
   result['samples']+=1
  if family=='skeleton_base' and role in ('idle','sprint_loop'):
   draw(skin(compose(e,e['duration']*.5)[0]),O/('after_'+role+'.png'))
 report[family]=result
# Reproduce the actual local-pose idle/enter/loop blend, including subframes.
def blend(a,b,w):
 out={}
 for n in names:
  p,q,s=a[n].decompose();pp,qq,ss=b[n].decompose();out[n]=Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),s.lerp(ss,w))
 return out
def cs(local):
 out={}
 for n in names:out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
 return out
def ease3(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
nv=int(weld.max()+1);tw=weld[F]
region=left[F].all(1)&(np.linalg.norm(P[F].mean(1)-np.array(rest['lowerarm_l'].translation),axis=1)<.12)
def folded(X):
 cross=np.cross(X[F[:,1]]-X[F[:,0]],X[F[:,2]]-X[F[:,0]]);vn=np.zeros((nv,3))
 for j in range(3):np.add.at(vn,tw[:,j],cross)
 vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
 return (np.einsum('ij,ij->i',cross,vn[tw].mean(1))<0)&region
blend_report={'max_root_vertices_in_frame':0,'minimum_opening_clearance_cm':999.,'new_elbow_fold_faces':0,'max_new_fold_area_mm2':0.,'new_fold_faces_in_view':0,'poses':0}
for family in ('skeleton_base','skeleton_mag10'):
 def local(role,t,old=False):
  e=entry(family,role)
  if old:e=next(c for c in before[family]['clips'] if c['base']==e['base'])
  return compose(e,t)[1]
 for progress in np.linspace(0,1,41):
  for phase in (0,.25,.5,.75):
   def pose_blend(old):
    a=local('sprint_enter',float(progress)*entry(family,'sprint_enter')['duration'],old);b=local('sprint_loop',phase*entry(family,'sprint_loop')['duration'],old)
    return cs(blend(local('idle',0,old),blend(a,b,ease3(.65,1,float(progress))),ease3(0,.15,float(progress))))
   X=skin(pose_blend(False));oldX=skin(pose_blend(True));cp=np.c_[X,np.ones(len(X))]@C.T;near=root&(cp[:,0]>1)
   margin=-cp[near,2]-cp[near,0]*math.tan(math.radians(37.5));blend_report['max_root_vertices_in_frame']=max(blend_report['max_root_vertices_in_frame'],int((margin<0).sum()));blend_report['minimum_opening_clearance_cm']=min(blend_report['minimum_opening_clearance_cm'],float(margin.min()))
   newfold=folded(X)&~folded(oldX);blend_report['new_elbow_fold_faces']=max(blend_report['new_elbow_fold_faces'],int(newfold.sum()))
   if newfold.any():
    ft=F[newfold];areas=np.linalg.norm(np.cross(X[ft[:,1]]-X[ft[:,0]],X[ft[:,2]]-X[ft[:,0]]),axis=1)*.5e6;blend_report['max_new_fold_area_mm2']=max(blend_report['max_new_fold_area_mm2'],float(areas.max()))
    centers=cp[ft,:3].mean(1);visible=(centers[:,0]>1)&(abs(centers[:,2])<centers[:,0]*.7673)&(abs(centers[:,1])<centers[:,0]*.7673*16/9);blend_report['new_fold_faces_in_view']=max(blend_report['new_fold_faces_in_view'],int(visible.sum()))
   blend_report['poses']+=1
report['runtime_blend_emulation']=blend_report;report['saved_profile_readback']=use_saved
(O/'review.json').write_text(json.dumps(report,indent=2));print('ARM_ROOT_REVIEW',json.dumps(report),flush=True)
