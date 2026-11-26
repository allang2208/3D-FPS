import json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]/'SourceAssets/ModernTacticalSet20261113'
R=ROOT/'HelmetContourR2'
cell=.14
audit={}
for rig in ['Jason','Kaitlin']:
    pr=np.load(R/(rig+'-profile.npz'));origin=pr['origin'];rad=pr['rad'];ends=pr['ends'];step=float(pr['step'])
    q=np.load(ROOT/'HelmetHairFitR1'/(rig+'-hair-envelope.npz'))['positions']
    delta=q-origin
    angle=np.arctan2(delta[:,0],delta[:,1])%(2*np.pi)
    ph=np.arccos((delta[:,2]/np.maximum(1e-6,np.linalg.norm(delta,axis=1))).clip(-1,1))
    ec=angle/(2*np.pi)*len(ends);i=ec.astype(int)%len(ends);j=(i+1)%len(ends);u=ec%1
    edge=(1-u)*ends[i]+u*ends[j]
    protected=q[ph<edge-.022]
    centers=np.unique(np.round(protected/cell).astype(np.int32),axis=0)*cell
    lods=[]
    for i in range(3):
        d=json.loads((R/'SavedLods'/f'{rig}_LOD{i}.json').read_bytes())
        frame=d['attachment_frame'];v=np.array(d['positions'])@np.array(frame['axes'])+frame['position']
        tree=BVHTree.FromPolygons(v.tolist(),d['triangles'],all_triangles=True)
        lower=100.;outside=0;seen=0;minimum_radius=100.;misses=0
        for p in centers:
            distance=tree.find_nearest(Vector(p))[3];lower=min(lower,distance)
            axis=Vector(p-origin).normalized()
            hit=tree.ray_cast(Vector(origin)+axis*55,-axis,75)[0]
            if hit is None:misses+=1;continue
            radial=(hit-Vector(p)).dot(axis);minimum_radius=min(minimum_radius,radial);seen+=1
            outside+=radial<0
        lods.append(dict(lod=i,nearest_shell_lower_bound_cm=round(lower-math.sqrt(3)*cell/2,4),minimum_outer_radial_cm=round(minimum_radius,4),radially_outside=int(outside),total_voxels=len(centers),rays_missed_open_rim=misses))
        print('HELMET_3LOD',rig,lods[-1],flush=True)
    audit[rig]=dict(raw_protected_points=len(protected),lods=lods)
(R/'clearance.json').write_text(json.dumps(dict(scope='static captured native head and groom directions inside revised open rim, three saved UE render LODs',rigs=audit),indent=2),encoding='utf8')
