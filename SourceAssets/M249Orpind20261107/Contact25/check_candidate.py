from pathlib import Path
import sys,pickle,json,numpy as np,importlib.util
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('m249_contact_motion',r/'motion.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sp=importlib.util.spec_from_file_location('contact_settle',r/'settle_motion.py');settle=importlib.util.module_from_spec(sp);sp.loader.exec_module(settle)
before=pickle.load(open(r/'corrected.pkl','rb'));candidate=pickle.load(open(r/'candidate_world.pkl','rb'));report={}
for (path,family),row in candidate.items():
 w=row['world'];source=before[(family,path)];old=source['old'];local=m.encode(w);original=settle.interpolate(source['times'],m.encode(old),row['times']);finger=m.fingers
 ts=row['times'];side='/SideMagazine' in path;window=(ts[:-1]>=2.76) if side else np.ones(len(ts)-1,bool)
 stats=dict(finger_local_translation_cm=float(np.max(abs(local[:,finger,:3]-original[:,finger,:3])))*100,finger_scale_change=float(np.max(abs(local[:,finger,7:]-original[:,finger,7:]))))
 stats['max_left_bone_rotation_step_deg']=max(float(np.degrees((R.from_matrix(m.rot(w[k,i])).inv()*R.from_matrix(m.rot(w[k+1,i]))).magnitude())) for k in np.flatnonzero(window) for i in m.arm_ids)
 if side:
  end=3.14 if path.split('.')[0].endswith('_empty') else 3.5;mask=ts>=end+.02
  hands=np.array([np.linalg.inv(m.rigid(fr[m.ix['WPN_root']]))@fr[m.ix['hand_l']] for fr in w[mask]])
  stats['settled_hand_drift_cm']=float(np.linalg.norm(hands[:,:3,3]-hands[-1,:3,3],axis=1).max())
 report[family+'/'+path.split('/')[-1]]=stats
(r/'candidate_checks.json').write_text(json.dumps(report,indent=2));print('CANDIDATE_CHECKS',len(report),'clips','finger offset cm',max(v['finger_local_translation_cm'] for v in report.values()),'scale',max(v['finger_scale_change'] for v in report.values()),'arm rotation step',max(v['max_left_bone_rotation_step_deg'] for v in report.values()))
