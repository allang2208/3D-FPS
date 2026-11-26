"""Measure the designed collar anchor clearance for the final production constraint."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR4';rows={}
for rig in ['Jason','Kaitlin']:
    d=read(R/'Authored'/f'shirt_outer_{rig}.json');body=read(S/'CombatShirtR3/Inputs'/f'Body_{rig}.json');head=read(S/'HelmetHairFitR1/Inputs'/f'{rig}_Head.json');p=np.array(body['positions']+head['positions']);f=np.array(body['triangles']+[[i+len(body['positions']) for i in t] for t in head['triangles']]);tree=BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True);n=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12);values=[]
    for vi in d['r4_pattern']['neck_vertices']:
        q=np.array(d['positions'][vi]);hit,_,fi,_=tree.find_nearest(Vector(q));values.append(float(np.dot(q-np.array(hit),n[fi])))
    rows[rig]=dict(min_clearance_cm=min(values),below_cloth_thickness=sum(v<.12 for v in values),below_finishing_clearance=sum(v<.23 for v in values));print('R4_COLLAR_CONSTRAINT',rig,rows[rig],flush=True)
write(R/'Receipts/collar-constraint.json',rows)
