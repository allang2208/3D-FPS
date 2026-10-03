"""Map the unchanged authored surfaces onto the captured UE vertices."""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def disk(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
out={'meshes':{},'animations':{}}
for family in ['HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1']:
    actual=json.loads((HERE/'Inputs'/f'{family}.json').read_text())
    old=json.loads((HERE/'Before'/f'{family}.json').read_text())
    new=json.loads((HERE/'Authored'/f'{family}.json').read_text())
    tree=cKDTree(old['positions']);dist,ids=tree.query(actual['positions'])
    if dist.max()>1.e-4:raise RuntimeError(f'{family}: unexpected geometry {dist.max()}')
    # Resolve coincident authored vertices by their existing weight vector.
    for i,p in enumerate(actual['positions']):
        choices=tree.query_ball_point(p,1.e-4)
        if len(choices)>1:
            weights=actual['weights'][i]
            def difference(j):
                candidate=old['weights'][j]
                return sum(abs(candidate.get(n,0)-weights.get(n,0)) for n in set(candidate)|set(weights))
            ids[i]=min(choices,key=difference)
    out['meshes'][family]={'asset':actual['asset'],'source_sha256':actual['sha256'],
        'weights':[new['weights'][i] for i in ids],'max_mapping_distance_cm':float(dist.max())}
    print('PREPARED_MESH',family,len(ids),float(dist.max()))
for p in sorted((HERE/'Tracks').glob('*.json')):
    data=json.loads(p.read_text());out['animations'][data['asset']]={'source_sha256':sha(disk(data['asset'])),'tracks_file':str(p)}
(HERE/'install_manifest.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')

# Inspect the remaining wrist angle with hand contact held fixed.
poses=json.loads((HERE/'Inputs/poses.json').read_text());native=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())
def matrix(t):
    m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m
indices={v['index']:n for n,v in native['bones'].items()}
parents={n:indices.get(v['parent']) for n,v in native['bones'].items()}
ref=native['bones'];f0=np.array(ref['hand_l']['p'])-ref['lowerarm_l']['p'];f0/=np.linalg.norm(f0)
report={}
for name in ['A_PKM_reload','A_PKM_reload_empty']:
    tracks=json.loads((HERE/'Tracks'/f'{name}.json').read_text())['tracks'];rows=poses[name]['frames'];values=[]
    for i,row in enumerate(rows):
        world={n:matrix(v) for n,v in row.items()}
        for n in ['upperarm_l','lowerarm_l','hand_l']:
            world[n]=world[parents[n]]@matrix(tracks[n][i])
        s,e,w=[world[n][:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']]
        hand=R.from_quat(row['hand_l']['q']).as_matrix()@R.from_quat(ref['hand_l']['q']).as_matrix().T@f0
        direction=(w-e)/np.linalg.norm(w-e)
        values.append(float(np.degrees(np.arccos(np.clip(hand@direction,-1,1)))))
    i=int(np.argmax(values));row=rows[i];s,e,w=[np.array(row[n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
    hand=R.from_quat(row['hand_l']['q']).as_matrix()@R.from_quat(ref['hand_l']['q']).as_matrix().T@f0
    axis=(w-s)/np.linalg.norm(w-s);l1=np.linalg.norm(e-s);l2=np.linalg.norm(w-e);distance=np.linalg.norm(w-s)
    center=s+axis*(l1*l1-l2*l2+distance*distance)/(2*distance);radius=np.linalg.norm(e-center)
    proj=w-hand*l2-center;proj-=axis*(proj@axis);best=center+proj/np.linalg.norm(proj)*radius
    best_angle=float(np.degrees(np.arccos(np.clip(hand@((w-best)/l2),-1,1))))
    report[name]={'worst_frame':i,'time':i*poses[name]['duration']/(len(rows)-1),
        'wrist_angle':values[i],'minimum_with_fixed_shoulder_and_hand':best_angle}
(HERE/'remaining_wrist_range.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
