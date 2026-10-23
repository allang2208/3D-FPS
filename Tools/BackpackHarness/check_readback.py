"""Compare the actual saved LODs with the authored mesh, including harness weights."""
from collections import Counter
import hashlib
import numpy as np
from scipy.spatial import cKDTree
from author import R,read,write
from winding import to_unreal


def signatures(data,mask):
    # Skeletal source vertices are stored as float32. Compare that exact
    # representation; decimal rounding creates false mismatches at cell borders.
    v=np.asarray(data['positions'],np.float32);t=np.asarray(data['triangles'],int)[mask]
    mats=np.asarray(data['triangle_materials'])[mask]
    def oriented(face):
        corners=tuple(tuple(p) for p in v[face])
        return min(corners[i:]+corners[:i] for i in range(3))
    return Counter((int(m),oriented(f)) for m,f in zip(mats,t))


manifest=read(R/'manifest.json');report=[]
for row in manifest['variants']:
    source=to_unreal(read(R/'Authored'/(row['profile']+'.json')))
    source_hash=hashlib.sha256((R/'Authored'/(row['profile']+'.json')).read_bytes()).hexdigest()
    source_mats=np.asarray(source['triangle_materials'])
    source_names={b['index']:b['name'] for b in source['bones']}
    source_vertices=np.asarray(source['positions'])
    for lod in (0,1):
        data=read(R/'SavedReadback'/(row['profile']+('' if lod==0 else '_lod1')+'.json'))
        mats=np.asarray(data['triangle_materials']);mask=mats>0
        hv=np.unique(np.asarray(data['triangles'])[mask]);v=np.asarray(data['positions'])
        distance,nearest=cKDTree(source_vertices).query(v[hv])
        names={b['index']:b['name'] for b in data['bones']}
        weight_error=0.
        for vi,si in zip(hv,nearest):
            a={names[b]:w for b,w in data['weights'][vi]}
            b={source_names[b]:w for b,w in source['weights'][si]}
            weight_error=max(weight_error,sum(abs(a.get(k,0)-b.get(k,0)) for k in a.keys()|b.keys()))
        uv=np.asarray(data['uv'])[mask];a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
        degenerate=int(np.sum(abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])<1e-10))
        normals=np.asarray(data['normals'])[mask];t=np.asarray(data['triangles'])[mask]
        fn=np.cross(v[t[:,2]]-v[t[:,0]],v[t[:,1]]-v[t[:,0]])
        opposed=int(np.sum(np.einsum('ij,ij->i',normals.mean(1),fn)<-1e-7))
        harness_equal=signatures(data,mask)==signatures(source,source_mats>0)
        all_equal=signatures(data,np.ones(len(mats),bool))==signatures(source,np.ones(len(source_mats),bool)) if lod==0 else None
        materials_equal=data['materials']==source['materials']
        ok=(data['revision']==manifest['revision'] and data['source_sha256']==source_hash and data['lod_count']==2
            and harness_equal and (all_equal if lod==0 else True) and materials_equal
            and distance.max()<.001 and weight_error<.001 and degenerate==0 and opposed==0)
        result=dict(profile=row['profile'],lod=lod,passed=bool(ok),triangles=len(mats),
                    harness_triangles=int(mask.sum()),harness_geometry_equal=harness_equal,lod0_geometry_equal=all_equal,
                    materials_equal=materials_equal,max_harness_vertex_delta_cm=float(distance.max()),
                    max_harness_weight_l1_delta=float(weight_error),uv_degenerate=degenerate,normal_opposed=opposed,
                    material_triangle_counts=dict(Counter(int(m) for m in mats)))
        report.append(result);print('HARNESS_SAVED_READBACK',result,flush=True)
passed=all(r['passed'] for r in report)
write(R/'saved_readback_checks.json',dict(passed=passed,lods=report,
      scope='saved source LOD0/LOD1 geometry, materials, UV validity, normals and harness skin weights; not live rendering'))
if not passed:raise SystemExit(1)
