import sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,read,write,unit
result={}
for rig in ['Jason','Kaitlin']:
    d=read(C/'Authored'/f'shirt_cloth_{rig}.json');g=read(C/'Authored'/f'gloves_{rig}.json') if (C/'Authored'/f'gloves_{rig}.json').exists() else read(C/'Read'/f'Glove_{rig}.json')
    if isinstance(g['bones'],list):
        names={b['index']:b['name'] for b in g['bones']};g['bones']={b['name']:b for b in g['bones']};g['weights']=[{names[bi]:v for bi,v in ws} for ws in g['weights']]
    p=np.array(d['positions']);count=len(p)//2;f=np.array(d['triangles']);tree=BVHTree.FromPolygons(p.tolist(),f[(f<count).all(1)].tolist(),all_triangles=True);record={}
    for side in ['l','r']:
        w=np.array(g['bones']['hand_'+side]['position']);axis=unit(w-np.array(g['bones']['lowerarm_'+side]['position']));clear=[];distances=[]
        for q,ws in zip(np.array(g['positions']),g['weights']):
            if sum(v for k,v in ws.items() if k.endswith('_'+side))<.5:continue
            dist=-np.dot(q-w,axis);distances.append(dist)
            if not .8<dist<4:continue
            center=w-axis*dist;radial=q-center;radius=np.linalg.norm(radial);hit=tree.ray_cast(Vector(center),Vector(radial/radius),10.)
            if hit[0] is not None:clear.append(float(np.linalg.norm(np.array(hit[0])-center)-radius-.125))
        record[side]=dict(samples=len(clear),min_clearance_cm=min(clear),median_clearance_cm=float(np.median(clear)),glove_end_cm=max(distances))
    result[rig]=record
write(C/'Review/World-native-glove-contact.json',result);print(result,flush=True)
