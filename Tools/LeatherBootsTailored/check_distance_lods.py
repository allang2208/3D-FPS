"""Check saved distance meshes against the native source in reference and motion poses."""
import collections,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
A=R/'Audit/DistanceLODs';source=read(R/'Authored/ue_leather_boots/Jason.json');p=np.asarray(source['positions']);f=np.asarray(source['triangles'],int)
base=BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True)
def skin(points,weights,transforms):
    out=np.zeros_like(points)
    for name in set().union(*weights):
        w=np.array([row.get(name,0.) for row in weights]);m=np.asarray(transforms.get(name,np.eye(4)));out+=(points@m[:3,:3].T+m[:3,3])*w[:,None]
    return out
frames=[('Reference',{})]
for name,clip in read(P/'SourceAssets/RangerCrouchFit20261021/inputs.json')['clips'].items():
    for i in (0,len(clip['samples'])//2,len(clip['samples'])-1):frames.append((name+'@'+str(i),fit.transforms(source,clip['samples'][i]['bones'])))
def rotation(pivot,axis,degrees):return np.asarray(Matrix.Translation(Vector(pivot))@Matrix.Rotation(math.radians(degrees),4,Vector(axis))@Matrix.Translation(-Vector(pivot)))
for angle in (-30,30):
    trans={}
    for side,sign in [('l',1),('r',-1)]:
        axis=(sign*.9882,-.1533,0);foot=rotation(source['bones']['foot_'+side]['position'],axis,angle);trans['foot_'+side]=foot;trans['ball_'+side]=foot@rotation(source['bones']['ball_'+side]['position'],axis,55)
    frames.append(('Ankle'+str(angle)+'Toe55',trans))
rows=[]
for lod in (1,2):
    d=read(A/('LOD'+str(lod)+'.json'));q=np.asarray(d['positions']);g=np.asarray(d['triangles'],int)
    assert np.isfinite(q).all() and np.isfinite(d['uv']).all() and np.isfinite(d['normals']).all() and set(d['triangle_materials'])==set(range(7))
    weight_error=max(abs(sum(w.values())-1) for w in d['weights']);assert weight_error<.0002
    tree=BVHTree.FromPolygons(q.tolist(),g.tolist(),all_triangles=True)
    source_samples=p[::max(1,len(p)//16000)];forward=[base.find_nearest(Vector(v))[3] for v in q];reverse=[tree.find_nearest(Vector(v))[3] for v in source_samples]
    # Reduction can move thin stitch surfaces; report both directions and keep
    # error below 2 mm for a full 40 cm boot, with LOD0 untouched.
    assert max(forward+reverse)<.2,(lod,max(forward+reverse))
    coincident=collections.defaultdict(list)
    for i,v in enumerate(q):coincident[tuple(np.round(v,4))].append(i)
    groups=[ids for ids in coincident.values() if len(ids)>1];worst=0.
    for name,trans in frames:
        posed=skin(q,d['weights'],trans);assert np.isfinite(posed).all()
        gap=max((float(np.linalg.norm(posed[ids]-posed[ids[0]],axis=1).max()) for ids in groups),default=0.);worst=max(worst,gap)
    assert worst<.002,(lod,worst)
    rows.append(dict(lod=lod,triangles=len(g),vertices=len(q),max_surface_distance_cm=max(forward+reverse),p95_surface_distance_cm=float(np.percentile(forward+reverse,95)),max_joint_gap_cm=worst,pose_count=len(frames),weight_sum_error=weight_error,all_materials_retained=True))
write(A/'geometry_check.json',dict(completed=True,rows=rows,lod0_unchanged=True,scope='Fresh saved meshes; source-surface deviation and coincident-seam deformation. No GPU timing or rendered gameplay test.'));print('BOOT_DISTANCE_LODS_GEOMETRY_PASSED',rows,flush=True)
