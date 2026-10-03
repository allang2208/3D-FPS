"""Inspect both glove seams, fingers and local-pose transitions on current assets."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];IN=HERE/'Input'
bare=json.loads((IN/'Bare.json').read_text());ref=bare['bones'];indices={v['index']:n for n,v in ref.items()}
def matrix(t):
    m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m
inverse={n:np.linalg.inv(matrix(v)) for n,v in ref.items()}
def match(data,points,weights):
    tree=cKDTree(data['positions']);selected=[]
    for p,w in zip(points,weights):
        distance,index=tree.query(p);ids=tree.query_ball_point(p,max(1.e-4,distance+1.e-8))
        selected.append(min(ids,key=lambda i:sum(abs(data['weights'][i].get(n,0)-w.get(n,0)) for n in set(w)|set(data['weights'][i]))))
    points=np.c_[np.array(data['positions'])[selected],np.ones(len(selected))]
    weights={n:np.array([data['weights'][i].get(n,0) for i in selected]) for n in {n for i in selected for n in data['weights'][i]}}
    return points,weights
def deform(surface,skin):
    points,weights=surface;result=np.zeros((len(points),3))
    for n,w in weights.items():result+=(points@skin[n].T)[:,:3]*w[:,None]
    return result
base_source=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/PKM.json').read_text())
surfaces={};report={'seams':{},'fingers':{},'transitions':{}}
for label,family in [('Brown','HuntFieldGlovesV1'),('Black','FittedFieldGlovesV1')]:
    source=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925'/family/'Authored/PKM.json').read_text())
    data=json.loads((IN/(label+'.json')).read_text())
    uses=Counter(tuple(sorted(e)) for f in source['triangles'] for e in [(f[0],f[1]),(f[1],f[2]),(f[2],f[0])])
    rim=sorted({v for e,c in uses.items() if c==1 for v in e})
    ids=[v for v in rim if sum(w for n,w in source['weights'][v].items() if n.endswith('_l'))>.99]
    baseids=[source['bare_vertex_ids'][i] for i in ids]
    surfaces[label]=(match(data,np.array(source['positions'])[ids],[source['weights'][i] for i in ids]),
        match(bare,np.array(base_source['positions'])[baseids],[base_source['weights'][i] for i in baseids]))
    report['seams'][label]={'vertices':len(ids),'raw_max_gap_cm':0.,'compressed_max_gap_cm':0.}
manifest=json.loads((IN/'manifest.json').read_text());clips={}
for entry in manifest:
    clip=json.loads((IN/(entry['name']+'.json')).read_text());clips[(entry['family'],entry['action'])]=clip
    for i,(row,compressed) in enumerate(zip(clip['frames'],clip['compressed'])):
        for mode,pose in [('raw',row),('compressed',dict(row,**compressed))]:
            skin={n:matrix(t)@inverse[n] for n,t in pose.items()}
            for label,(glove,body) in surfaces.items():
                gap=float(np.linalg.norm(deform(glove,skin)-deform(body,skin),axis=1).max())
                key=mode+'_max_gap_cm'
                if gap>report['seams'][label][key]:
                    report['seams'][label][key]=gap;report['seams'][label][mode+'_worst']=[entry['name'],i]
    if entry['action'] in ['idle','aim','fire','aim_fire']:
        first=clip['frames'][0];names=[n for n in first if n.endswith('_l') and any(n.startswith(f) for f in ['thumb','index','middle','ring','pinky'])]
        gun0=R.from_quat(first['WPN_root']['q']).inv()
        p0={n:gun0.apply(np.array(first[n]['p'])-first['WPN_root']['p']) for n in names};maxmove=0.
        for row in clip['frames']:
            gun=R.from_quat(row['WPN_root']['q']).inv()
            for n in names:maxmove=max(maxmove,float(np.linalg.norm(gun.apply(np.array(row[n]['p'])-row['WPN_root']['p'])-p0[n])))
        report['fingers'][entry['name']]={'max_finger_position_change_in_gun_cm':maxmove}
def world_blend(a,b,alpha):
    world={}
    for n in a:
        x,y=a[n],b[n];q0=np.array(x['q']);q1=np.array(y['q']);q1*=1 if q0@q1>=0 else -1
        q=q0*(1-alpha)+q1*alpha;q/=np.linalg.norm(q)
        local=matrix({'p':(np.array(x['p'])*(1-alpha)+np.array(y['p'])*alpha).tolist(),'q':q.tolist(),
            's':(np.array(x['s'])*(1-alpha)+np.array(y['s'])*alpha).tolist()})
        parent=indices.get(ref[n]['parent']);world[n]=world[parent]@local if parent else local
    return world
for family in ['base','angled','canted','vertical','prism']:
    idle=clips[(family,'idle')];aim=clips[(family,'aim')];poses=[]
    for alpha in np.linspace(0,1,21):poses.append(('ADS',float(alpha),world_blend(idle['local'][0],aim['local'][0],alpha)))
    for action in ['reload','reload_empty']:
        clip=clips[(family,action)]
        for i in range(6):
            time=clip['duration']*i/(clip['keys']-1);alpha=min(1,time/.035)
            poses.append((action,float(alpha),world_blend(idle['local'][0],clip['local'][i],alpha)))
    max_gap=0.;max_contact=0.
    reference=world_blend(idle['local'][0],idle['local'][0],0.)
    r0=np.linalg.inv(reference['WPN_root'])@reference['hand_l']
    for label,alpha,world in poses:
        skin={n:m@inverse[n] for n,m in world.items()}
        for glove,body in surfaces.values():max_gap=max(max_gap,float(np.linalg.norm(deform(glove,skin)-deform(body,skin),axis=1).max()))
        if label=='ADS':max_contact=max(max_contact,float(np.linalg.norm((np.linalg.inv(world['WPN_root'])@world['hand_l'])[:3,3]-r0[:3,3])*100))
    report['transitions'][family]={'samples':len(poses),'max_cuff_gap_cm':max_gap,'ADS_max_hand_contact_change_cm':max_contact}
(HERE/'seam_blend_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'seams':report['seams'],'transitions':report['transitions'],
    'max_finger_change_cm':max(v['max_finger_position_change_in_gun_cm'] for v in report['fingers'].values())},indent=2))
