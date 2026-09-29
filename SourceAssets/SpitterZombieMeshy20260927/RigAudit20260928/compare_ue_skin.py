"""Compare an exported UE LOD0 with the original Meshy skin, in memory only."""
import bpy,json,itertools
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,kdtree
ROOT=Path(__file__).resolve().parent

def load(file):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(file),use_image_search=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    p=[];weights=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        names={g.index:g.name for g in o.vertex_groups}
        for v in o.data.vertices:
            p.append(list(o.matrix_world@v.co))
            weights.append({names[g.group]:g.weight for g in v.groups if g.weight>1e-6})
    return np.array(p),weights,{b.name:np.array(rig.matrix_world@b.head_local) for b in rig.data.bones}

a,wa,ba=load(ROOT.parent/'Meshy/rig/downloads/result_rigged_character_fbx_url.fbx')
b,wb,bb=load(ROOT/'UE_CurrentSkin.fbx')
names=sorted(set(ba)&set(bb));aa=np.array([ba[n] for n in names]);ab=np.array([bb[n] for n in names])
# Only FBX axis/unit conversion is allowed; no per-vertex fitting.
best=None
for perm in itertools.permutations(range(3)):
    for sign in itertools.product([-1,1],repeat=3):
        rotation=np.eye(3)[list(perm)]*np.array(sign)[:,None]
        for scale in [1.,.01,100.]:
            transformed=ab@rotation.T*scale
            translation=aa.mean(0)-transformed.mean(0)
            error=float(np.sqrt(np.mean(np.sum((transformed+translation-aa)**2,axis=1))))
            if best is None or error<best[0]:best=(error,rotation,scale,translation)
error,rotation,scale,translation=best;b=b@rotation.T*scale+translation
kd=kdtree.KDTree(len(a))
for i,p in enumerate(a):kd.insert(Vector(p),i)
kd.balance();distances=[];diffs=[];missing=[];extra=[]
for p,w in zip(b,wb):
    co,idx,dist=kd.find(Vector(p));distances.append(dist)
    candidates=kd.find_range(Vector(p),max(1e-5,dist+1e-7))
    def difference(i):return sum(abs(wa[i].get(n,0)-w.get(n,0)) for n in set(wa[i])|set(w))
    idx=min([i for co,i,d in candidates],key=difference)
    diffs.append(difference(idx))
    missing.append(sum(v for n,v in wa[idx].items() if n not in w))
    extra.append(sum(v for n,v in w.items() if n not in wa[idx]))
def stats(xs):return dict(zip(['min','median','p95','max'],map(float,np.percentile(xs,[0,50,95,100]))))
report=dict(original_vertices=len(a),ue_export_vertices=len(b),common_bones=names,
    coordinate_axis_matrix=rotation.tolist(),coordinate_scale=scale,coordinate_translation_m=translation.tolist(),
    bone_head_rms_error_m=error,vertex_nearest_distance_m=stats(distances),
    vertex_weight_L1_difference=stats(diffs),missing_influence_mass=stats(missing),extra_influence_mass=stats(extra),
    ue_influence_histogram={str(n):sum(len(w)==n for w in wb) for n in sorted(set(map(len,wb)))},
    ue_weight_sum=stats([sum(w.values()) for w in wb]),
    caveat='LOD0 export; FBX vertex order/UV splits matched spatially; not a GPU skin-capture')
(ROOT/'ue_skin_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SPITTER_UE_SKIN_COMPARISON',json.dumps(report),flush=True)
