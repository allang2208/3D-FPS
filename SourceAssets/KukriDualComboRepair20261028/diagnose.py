"""Scoped native-bind and joint-path diagnosis for the two reported cuts."""
import importlib.util,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('dual_combat_v1',ROOT/'SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
inputs=json.loads((a.OUT/'inputs.json').read_text());report={};version=sys.argv[1] if len(sys.argv)>1 else 'before'
for label,source in inputs.items():
    body=a.c.Body(a.base.rig.DATA[label]);old=a.c.Body(source['native']) if version=='before' else body
    d=json.loads(((a.OUT if version=='before' else OUT)/(label+'-actions.json')).read_text());row={};report[label]=row
    indices=[body.ix[n+'_'+s] for s in 'lr' for n in ('clavicle','upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02')]
    row['reference_mismatch']={body.names[i]:dict(position_cm=float(np.linalg.norm(body.tp[i]-old.tp[i])),rotation_deg=float(np.degrees((R.from_quat(body.tq[i]).inv()*R.from_quat(old.tq[i])).magnitude()))) for i in indices}
    for role in ('Dual.Slash1','Dual.Slash2'):
        f=np.array(d['clips'][role]['frames']);p,q=body.world(f);delta=np.degrees((R.from_quat(f[:-1,:,3:7].reshape(-1,4)).inv()*R.from_quat(f[1:,:,3:7].reshape(-1,4))).magnitude()).reshape(len(f)-1,-1)
        row[role]={body.names[i]:dict(max_frame_delta_deg=float(delta[:,i].max()),at_seconds=float(delta[:,i].argmax()/120),reference_deviation_deg=float(np.degrees((R.from_quat(body.ref[i,3:7]).inv()*R.from_quat(f[:,i,3:7])).magnitude()).max())) for i in indices}
        for side in 'lr':
            ui,ei=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm')];ref=R.from_quat(body.ref[ui,3:7]);cur=R.from_quat(f[:,ui,3:7]);axis=a.c.unit(body.ref[ei,:3])
            swing=a.c.align(np.tile(ref.apply(axis),(len(f),1)),cur.apply(np.tile(axis,(len(f),1))))
            row[role]['upperarm_'+side]['max_axial_twist_deg']=float(np.degrees((ref.inv()*swing.inv()*cur).magnitude()).max())
        print(label,role,'largest arm steps',sorted([(body.names[i],round(delta[:,i].max(),1),round(delta[:,i].argmax()/120,3)) for i in indices],key=lambda x:-x[1])[:5],flush=True)
    print(label,'reference mismatch',[(n,round(v['position_cm'],1),round(v['rotation_deg'],1)) for n,v in row['reference_mismatch'].items()],flush=True)
(OUT/(version+'-diagnostics.json')).write_text(json.dumps(report,indent=2))
