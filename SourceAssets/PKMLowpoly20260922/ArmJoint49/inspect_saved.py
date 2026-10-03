"""Inspect the saved cuffs and arm motion, without running or rendering the game."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
bare=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/PKM.json').read_text())
native=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())
before=json.loads((HERE/'Inputs/poses.json').read_text());after=json.loads((HERE/'SavedReadback/poses.json').read_text())
def mat(t):
    m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m
rest={n:mat(v) for n,v in native['bones'].items()};inverse={n:np.linalg.inv(m) for n,m in rest.items()}
def angle(a,b):return float(np.degrees(np.arccos(np.clip(a@b/np.linalg.norm(a)/np.linalg.norm(b),-1,1))))
def match(data,points,weights):
    tree=cKDTree(data['positions']);selected=[]
    for p,w in zip(points,weights):
        distance,nearest=tree.query(p);candidates=tree.query_ball_point(p,max(1.e-4,distance+1.e-8))
        def difference(i):return sum(abs(data['weights'][i].get(n,0)-w.get(n,0)) for n in set(w)|set(data['weights'][i]))
        selected.append(min(candidates,key=difference))
    return np.array(data['positions'])[selected], [data['weights'][i] for i in selected]
def prepare(points,weights):
    bones=sorted({n for w in weights for n in w});return np.c_[points,np.ones(len(points))],{n:np.array([w.get(n,0) for w in weights]) for n in bones}
def deform(surface,skin):
    points,weights=surface;result=np.zeros((len(points),3))
    for name,w in weights.items():result+=(points@skin[name].T)[:,:3]*w[:,None]
    return result
report={'scope':'Saved LOD0 wrist boundaries and 15 native animation pose sequences; no gameplay or rendering',
    'cuffs':{},'joints':{}}
surfaces={}
for family in ['HuntFieldGlovesV1','FittedFieldGlovesV1']:
    source=json.loads((HERE/'Authored'/f'{family}.json').read_text())
    saved=json.loads((HERE/'SavedReadback'/f'{family}.json').read_text())
    uses=Counter(tuple(sorted(e)) for f in source['triangles'] for e in [(f[0],f[1]),(f[1],f[2]),(f[2],f[0])])
    rim=sorted({v for e,c in uses.items() if c==1 for v in e})
    for side in ['l','r']:
        ids=[v for v in rim if sum(w for n,w in source['weights'][v].items() if n.endswith('_'+side))>.99]
        base_ids=[source['bare_vertex_ids'][i] for i in ids]
        gp,gw=match(saved,np.array(source['positions'])[ids],[source['weights'][i] for i in ids])
        bp,bw=match(native,np.array(bare['positions'])[base_ids],[bare['weights'][i] for i in base_ids])
        mismatch=[sum(abs(a.get(n,0)-b.get(n,0)) for n in set(a)|set(b)) for a,b in zip(gw,bw)]
        key=family+'_'+side
        report['cuffs'][key]={'rim_vertices':len(ids),'max_rest_gap_cm':float(np.linalg.norm(gp-bp,axis=1).max()),
            'max_weight_l1_difference':max(mismatch),'max_posed_gap_cm':0.0,'worst_clip':None,'worst_frame':None}
        if side=='l':surfaces[key]=(prepare(gp,gw),prepare(bp,bw))
f0=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3];f0/=np.linalg.norm(f0)
for name,clip in after.items():
    old=before[name]['frames'];wrist=[];elbow=[];contact_error=[];hand_angle=[];length_error=[];shoulder_error=[];pole_step=[];last_direction=None
    for i,row in enumerate(clip['frames']):
        world={n:mat(t) for n,t in row.items()};skin={n:m@inverse[n] for n,m in world.items()}
        s,e,w=[np.array(row[n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
        s0,e0,w0=[np.array(old[i][n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
        wrist.append(angle(skin['hand_l'][:3,:3]@f0,w-e));elbow.append(angle(e-s,w-e))
        contact_error.append(float(np.linalg.norm(w-w0)));shoulder_error.append(float(np.linalg.norm(s-s0)))
        delta=R.from_quat(row['hand_l']['q'])*R.from_quat(old[i]['hand_l']['q']).inv();hand_angle.append(float(np.degrees(delta.magnitude())))
        length_error.append(max(abs(np.linalg.norm(e-s)-np.linalg.norm(e0-s0)),abs(np.linalg.norm(w-e)-np.linalg.norm(w0-e0))))
        direction=(e-s)/np.linalg.norm(e-s)
        if last_direction is not None:pole_step.append(angle(direction,last_direction))
        last_direction=direction
        for key,(glove,skin_surface) in surfaces.items():
            gap=float(np.linalg.norm(deform(glove,skin)-deform(skin_surface,skin),axis=1).max())
            if gap>report['cuffs'][key]['max_posed_gap_cm']:
                report['cuffs'][key].update(max_posed_gap_cm=gap,worst_clip=name,worst_frame=i)
    report['joints'][name]={'wrist_axis_degrees':[min(wrist),max(wrist)],'elbow_flexion_degrees':[min(elbow),max(elbow)],
        'max_hand_position_error_cm':max(contact_error),'max_hand_orientation_error_degrees':max(hand_angle),
        'max_shoulder_position_error_cm':max(shoulder_error),'max_bone_length_error_cm':float(max(length_error)),
        'max_upperarm_direction_step_degrees':max(pole_step,default=0.)}
(HERE/'saved_joint_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'cuffs':report['cuffs'],'joints':{n:v for n,v in report['joints'].items() if n in ['A_PKM_reload','A_PKM_reload_empty','A_PKM_idle']}},indent=2))
