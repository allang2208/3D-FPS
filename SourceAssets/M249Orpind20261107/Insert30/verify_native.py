"""Compare identical offline animation-graph captures before/after installation."""
from pathlib import Path
import sys
import json,pickle,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;label=sys.argv[1]if len(sys.argv)>1 else 'after';d=pickle.load(open(r/'current.pkl','rb'));names=d['names'];ix={n:i for i,n in enumerate(names)}
arm=['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l']
protected=[i for i,n in enumerate(names) if n not in arm]
def mat(v):
 m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*np.array(v[7:10]);m[:3,3]=v[:3];return m
def capture(folder):
 j=json.loads((folder/'review.json').read_text());a=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7);return j,a[:,:4],a[:,4:].reshape(-1,j['bone_count'],7)
def distance(folder,row):
 stem=folder/Path(row['file']).stem;v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);dom=np.fromfile(folder/'dominant.bin',np.uint32)
 left=np.array([n.endswith('_l')and n.startswith(('upperarm','lowerarm'))for n in names])[dom]
 xf=np.linalg.inv(mat(row['camera']))@mat(row['component']);v=v[left]@xf[:3,:3].T+xf[:3,3]
 depth=v[:,0];x=v[:,1]/np.maximum(depth,1.e-6);y=v[:,2]/np.maximum(depth,1.e-6);half=np.tan(np.radians(107.5/2));visible=(depth>=1)&(abs(x)<=half)&(abs(y)<=half*540/960)
 return dict(eye_distance_cm=float(np.linalg.norm(v,axis=1).min()),visible_depth_cm=float(depth[visible].min())if visible.any()else None,visible_vertex_count=int(visible.sum()),near_visible_vertices=int(((depth<10)&visible).sum()))
report={}
for folder in sorted((r/'before').iterdir()):
 if not(folder/'review.json').exists():continue
 other=r/label/folder.name;ja,ta,a=capture(folder);jb,tb,b=capture(other);assert np.array_equal(ta,tb)
 win=(ta[:-1,1]>=2.3)&(ta[:-1,1]<=2.90);metrics={}
 for n in arm:
  vals=[]
  for pose in [a,b]:
   q=R.from_quat(pose[:,ix[n],3:7]);step=np.degrees((q[:-1].inv()*q[1:]).magnitude());vals.append(float(step[win].max()))
  metrics[n]=vals
 position=np.linalg.norm(b[:,protected,:3]-a[:,protected,:3],axis=2);qa=R.from_quat(a[:,protected,3:].reshape(-1,4));qb=R.from_quat(b[:,protected,3:].reshape(-1,4));angle=np.degrees((qa.inv()*qb).magnitude())
 hand=np.linalg.norm(b[:,ix['hand_l'],:3]-a[:,ix['hand_l'],:3],axis=1)
 surfaces=[]
 for ra,rb in zip(ja['frames'],jb['frames']):surfaces.append(dict(source=ra['source'],before=distance(folder,ra),after=distance(other,rb)))
 entry=dict(protected_max_cm=float(position.max()),protected_max_deg=float(angle.max()),hand_max_cm=float(hand.max()),insertion_release_rotation_step_deg=metrics,surfaces=surfaces)
 report[folder.name]=entry
 print(folder.name,'protected_cm',round(entry['protected_max_cm'],5),'hand_cm',round(entry['hand_max_cm'],5),'upper_deg',np.round(metrics['upperarm_l'],2),'lower_deg',np.round(metrics['lowerarm_l'],2),'near_depth',[round(x['visible_depth_cm'],2)if x['visible_depth_cm']else None for x in [surfaces[2]['before'],surfaces[2]['after']]],flush=True)
(r/(label+'_comparison.json')).write_text(json.dumps(report,indent=2))
assert len(report)==12 and max(v['protected_max_cm']for v in report.values())<.06
