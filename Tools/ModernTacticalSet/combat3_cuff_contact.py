"""Measure the reported M4 sleeve/glove junction in its own native bind."""
import sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,unit
C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
d=read(C/'Authored/shirt_fp_M4.json');glove=read(C/'Read/Glove_M4.json');old=read(C/'Read/PreviousSleeve_M4.json');p=np.array(d['positions']);f=np.array(d['triangles']);gp=np.array(glove['positions']);bones={b['name']:b for b in d['bones']};names={b['index']:b['name'] for b in d['bones']};report={}
for part in d['parts']:
    side=part['name'][-1];start=part['first_vertex'];count=part['vertices']//2;ids=np.arange(start,start+count);w=np.array(bones['hand_'+side]['position']);axis=unit(w-np.array(bones['lowerarm_'+side]['position']));dist=-(p[ids]-w)@axis;outer=f[((f>=start)&(f<start+count)).all(1)];tree=BVHTree.FromPolygons(p.tolist(),outer.tolist(),all_triangles=True);clear=[]
    samples=[]
    for vi,(q,weights) in enumerate(zip(gp,glove['weights'])):
        if sum(v for k,v in weights.items() if k.endswith('_'+side))<.5:continue
        gd=-np.dot(q-w,axis)
        if not 1.3<gd<3.7:continue
        center=w-axis*gd;radial=q-center;radius=np.linalg.norm(radial);hit=tree.ray_cast(Vector(center),Vector(radial/radius),10.)
        if hit[0] is not None:
            clearance=float(np.linalg.norm(np.array(hit[0])-center)-radius-.12);clear.append(clearance);samples.append(dict(vertex=vi,clearance=clearance,along=gd,radius=radius,weights=weights,position=q.tolist()))
    rim=ids[dist<3.9];finger=max(sum(v for bi,v in d['weights'][i] if names[bi].startswith(('thumb','index','middle','ring','pinky'))) for i in rim)
    gd=[-np.dot(q-w,axis) for q,ws in zip(gp,glove['weights']) if sum(v for k,v in ws.items() if k.endswith('_'+side))>.5]
    report[side]=dict(outer_rim_from_wrist_cm=float(dist.min()),glove_overlap_cm=float(max(gd)-dist.min()),contact_samples=len(clear),inner_clearance_min_cm=min(clear),inner_clearance_median_cm=float(np.median(clear)),cuff_finger_weight=finger,paired_weights=all(d['weights'][int(i)]==d['weights'][int(i+count)] for i in ids),tightest_samples=sorted(samples,key=lambda s:s['clearance'])[:12])
write(C/'Review/M4-native-glove-contact.json',dict(measurement='Native bind geometry only',sides=report,gameplay_tested=False));print(report,flush=True)
