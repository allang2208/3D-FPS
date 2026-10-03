"""Read source muzzle planes and longitudinal sections for the replacement mesh."""
import json
from pathlib import Path
import numpy as np

O=Path(__file__).parent
SI=O.parent/'PitViper2011SICompensator20261002'
raw=json.loads((O.parent/'PitViper2011Integration20261002/canonical_parts.json').read_text())
T=np.array(json.loads((SI/'authoring_receipt.json').read_text(encoding='utf8'))['source_to_part'])
for identity in ('2011pv slide_1','2011pv barrel compensator_2','2011pv frame_12'):
    part=next(p for p in raw if p['identity']==identity and p['material']=='h-190')
    v=(np.c_[part['verts'],np.ones(len(part['verts']))]@T.T)[:,:3]*1000
    groups={}
    for face in part['faces']:
        p=v[face]
        n=np.cross(p[1]-p[0],p[2]-p[0]);area=np.linalg.norm(n)/2
        if area<1e-7:continue
        n/=2*area
        if max(p[:,0])<-.1 or min(p[:,0])>20:continue
        if identity=='2011pv barrel compensator_2' and (n[0]<.01 or max(p[:,0])<6):continue
        key=tuple(np.round(n,3))+tuple(np.round([n@p.mean(axis=0)],3))
        a,points=groups.get(key,(0,[]));groups[key]=(a+area,points+list(p))
    print(identity)
    for key,(area,points) in sorted(groups.items(),key=lambda kv:-kv[1][0])[:50]:
        p=np.array(points)
        print('plane',key,'area_mm2',round(area,3),'bounds_mm',np.round(p.min(axis=0),4).tolist(),np.round(p.max(axis=0),4).tolist())
    sections={}
    for y in (0,5,9,10.5,11,11.5):
        line=[]
        for z in (11,10,8,6,4,2,0,-2,-4,-6,-8,-10,-12,-13.5,-15,-17,-19):
            hits=[]
            for face in part['faces']:
                p=v[face];uv=p[:,1:]
                A=np.column_stack((uv[1]-uv[0],uv[2]-uv[0]))
                if abs(np.linalg.det(A))<1e-9:continue
                s,t=np.linalg.solve(A,np.array((y,z))-uv[0])
                if s>=-1e-7 and t>=-1e-7 and s+t<=1+1e-7:
                    x=p[0,0]+s*(p[1,0]-p[0,0])+t*(p[2,0]-p[0,0])
                    if x>=-.1:hits.append(float(x))
            if hits:line.append([z,round(max(hits),5)])
        sections[str(y)]=line
    print('forward_envelope_x_by_z_mm',json.dumps(sections))
