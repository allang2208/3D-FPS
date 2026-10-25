"""Sample rear surfaces by triangle rays, including sparsely tessellated panels."""
import json,os
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactFitR3'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');records=read(R/'captured.json');frames=read(R/'Surfaces/frames.json');out=R/'Shells';out.mkdir(exist_ok=True)
rot=lambda q:np.asarray(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
static_override=read(out/'static_overrides.json') if (out/'static_overrides.json').exists() else {}
for row in plan['rows']:
    if 'hanging_pack' in row:continue
    path=row.get('rigid_mesh',row['mesh']);folder=Path(records[path]['folder']);v=np.fromfile(folder/'positions.bin',dtype='<f4').reshape(-1,3).astype(float);f=np.fromfile(folder/'triangles.bin',dtype='<i4').reshape(-1,3)
    if path in static_override:v=np.load(static_override[path]['source'])['positions'].astype(float)
    if row.get('rigid_mesh'):v=v@rot(row['rigid_rotation_quat']).T+row['rigid_location']
    else:
        if records[path].get('cargo_vertices'):
            cargo=np.fromfile(records[path]['cargo_vertices'],dtype='u1');f=f[np.all(cargo[f]>0,axis=1)]
        else:raise RuntimeError('Classify cargo islands before sampling '+path)
    frame=frames[row['rig']];v=(v-np.asarray(frame['translation']))@np.asarray(frame['matrix']).T
    bvh=BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True);points=[]
    lo,hi=v[f.ravel()].min(0),v[f.ravel()].max(0)
    xs=np.arange(np.floor(lo[0]*2)/2-.5,hi[0]+1.,.5);zs=np.arange(np.floor(lo[2]*2)/2-.5,hi[2]+1.,.5)
    rear=np.full((len(xs),len(zs)),np.nan);front=rear.copy()
    for xi,x in enumerate(xs):
        for zi,z in enumerate(zs):
            hit=bvh.ray_cast(Vector((x,100,z)),Vector((0,-1,0)),200)[0]
            if hit is not None:points.append(list(hit));rear[xi,zi]=hit.y
            hit=bvh.ray_cast(Vector((x,-100,z)),Vector((0,1,0)),200)[0]
            if hit is not None:front[xi,zi]=hit.y
    key=row['rig']+'_'+row['item']+'_'+(row['shirt'] or 'bare')
    np.savez_compressed(out/(key+'.npz'),rear_points=np.asarray(points),positions=v,triangles=f,xs=xs,zs=zs,rear=rear,front=front)
    print('BACKPACK_SHELL_SAMPLED',key,len(points),flush=True)
(out/'static_overrides.json').write_text(json.dumps(static_override,indent=2))
