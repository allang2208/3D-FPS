"""Measure the reported cuff mismatch and the installed PKM wrist/elbow poses."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925'
bare=json.loads((ROOT/'BarePalmV7/Authored/PKM.json').read_text())
native=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())
poses=json.loads((HERE/'Inputs/poses.json').read_text())
def mat(t):
    m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m
rest={n:mat(b) for n,b in native['bones'].items()};inverse={n:np.linalg.inv(m) for n,m in rest.items()}
def deform(points,weights,skin):
    out=[]
    for p,ws in zip(points,weights):
        h=np.r_[p,1.];out.append(sum(w*(skin[n]@h)[:3] for n,w in ws.items()))
    return np.array(out)
def angle(a,b):return np.degrees(np.arccos(np.clip(np.sum(a*b,axis=-1)/(np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1)),-1,1)))
report={'cuffs':{},'joints':{}}
boundaries={}
for family in ['HuntFieldGlovesV1','FittedFieldGlovesV1']:
    g=json.loads((ROOT/family/'Authored/PKM.json').read_text())
    uses=Counter(tuple(sorted(e)) for f in g['triangles'] for e in [(f[0],f[1]),(f[1],f[2]),(f[2],f[0])])
    rim=sorted({v for e,c in uses.items() if c==1 for v in e})
    left=[v for v in rim if sum(w for n,w in g['weights'][v].items() if n.endswith('_l'))>.99]
    ids=[g['bare_vertex_ids'][i] for i in left]
    mismatch=[sum(abs(g['weights'][i].get(n,0)-bare['weights'][j].get(n,0)) for n in set(g['weights'][i])|set(bare['weights'][j])) for i,j in zip(left,ids)]
    rest_gap=np.linalg.norm(np.array(g['positions'])[left]-np.array(bare['positions'])[ids],axis=1)
    report['cuffs'][family]={'left_rim_vertices':len(left),'max_rest_gap_cm':float(rest_gap.max()),
       'max_weight_l1_difference':max(mismatch),'mismatched_rim_vertices':sum(v>1.e-5 for v in mismatch),'clips':{}}
    boundaries[family]=(g,left,ids)
for name,clip in poses.items():
    elbow_bends=[];wrist_bends=[];max_gaps={f:(0.,0) for f in boundaries}
    f0=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3];f0/=np.linalg.norm(f0)
    for i,row in enumerate(clip['frames']):
        skin={n:mat(t)@inverse[n] for n,t in row.items()}
        s,e,w=[np.array(row[n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
        elbow_bends.append(float(angle(e-s,w-e)))
        wrist_bends.append(float(angle(skin['hand_l'][:3,:3]@f0,w-e)))
        for family,(g,ids,base_ids) in boundaries.items():
            a=deform([g['positions'][j] for j in ids],[g['weights'][j] for j in ids],skin)
            b=deform([bare['positions'][j] for j in base_ids],[bare['weights'][j] for j in base_ids],skin)
            gap=float(np.linalg.norm(a-b,axis=1).max())
            if gap>max_gaps[family][0]:max_gaps[family]=(gap,i)
    report['joints'][name]={'elbow_flexion_degrees':list(map(float,[min(elbow_bends),max(elbow_bends)])),
       'wrist_axis_degrees':list(map(float,[min(wrist_bends),max(wrist_bends)])),
       'max_wrist_frame':int(np.argmax(wrist_bends))}
    for family,(gap,frame) in max_gaps.items():report['cuffs'][family]['clips'][name]={'max_gap_cm':gap,'frame':frame}
(HERE/'diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'cuffs':{f:{**{k:v for k,v in r.items() if k!='clips'},'worst':sorted(r['clips'].items(),key=lambda x:x[1]['max_gap_cm'],reverse=True)[:3]} for f,r in report['cuffs'].items()},
    'joints':{n:v for n,v in report['joints'].items() if n in ['A_PKM_idle','A_PKM_reload','A_PKM_reload_empty']}},indent=2))
