"""Measure actual sleeve/glove overlap in the requested native profiles."""
import sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,read,write,unit
rigs=sys.argv[sys.argv.index('--')+1].split(',')
for rig in rigs:
    d=read(C/'Authored'/f'shirt_fp_{rig}.json');g=read(C/'Authored'/f'gloves_{rig}.json');p=np.array(d['positions']);f=np.array(d['triangles']);gp=np.array(g['positions']);names={b['index']:b['name'] for b in g['bones']};bones={b['name']:b for b in d['bones']};report={}
    for part in d['parts']:
        side=part['name'][-1];start=part['first_vertex'];count=part['vertices']//2;ids=np.arange(start,start+count);w=np.array(bones['hand_'+side]['position']);axis=unit(w-np.array(bones['lowerarm_'+side]['position']));dist=-(p[ids]-w)@axis;outer=f[((f>=start)&(f<start+count)).all(1)];tree=BVHTree.FromPolygons(p.tolist(),outer.tolist(),all_triangles=True);clear=[]
        for q,ws in zip(gp,g['weights']):
            if sum(v for bi,v in ws if names[bi].endswith('_'+side))<.5:continue
            gd=-np.dot(q-w,axis)
            if gd<dist.min()+.25:continue
            center=w-axis*gd;radial=q-center;radius=np.linalg.norm(radial);hit=tree.ray_cast(Vector(center),Vector(radial/radius),12.)
            if hit[0] is not None:clear.append(float(np.linalg.norm(np.array(hit[0])-center)-radius-.12))
        report[side]=dict(samples=len(clear),min_inner_clearance_cm=min(clear),median_inner_clearance_cm=float(np.median(clear)),below_zero_samples=sum(v<0 for v in clear),outer_cuff_from_wrist_cm=float(dist.min()))
    write(C/'Review'/(rig+'-fitted-glove-contact.json'),dict(rig=rig,contact=report,gameplay_tested=False));print('FITTED_GLOVE_CONTACT',rig,report,flush=True)
