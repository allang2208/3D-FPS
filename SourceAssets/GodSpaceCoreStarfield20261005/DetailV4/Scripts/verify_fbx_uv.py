"""Read two exported FBXs, compare geometry, count UV-degenerate textured triangles.
Blender background only. Never writes either input or accesses Unreal.
"""
import bpy,json,hashlib,math,gc
import numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];W=R.parent
old=W/'BaselineV2/Authored/SM_GodSpaceCore_Starfield_V2.fbx'
new=R/'Authored/SM_GodSpaceCore_Starfield_V4.fbx'
def measure(path,version):
    bpy.ops.wm.read_factory_settings(use_empty=True);gc.collect()
    bpy.ops.import_scene.fbx(filepath=str(path))
    result={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'materials':{}}
    geometry={};mapped={};points=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        m=o.data;m.calc_loop_triangles();uv=m.uv_layers.active
        for tr in m.loop_triangles:
            name=m.materials[tr.material_index].name.split('.')[0]
            p=np.array([tuple(o.matrix_world@m.vertices[i].co) for i in tr.vertices],dtype=float)
            points.extend(p.tolist())
            geometry.setdefault(name,[]).append(tuple(sorted(tuple(round(float(c),6) for c in v) for v in p)))
            q=np.array([tuple(uv.data[i].uv) for i in tr.loops],dtype=float)
            mapped.setdefault(name,[]).append(tuple(sorted(tuple(round(float(c),7) for c in [*v,*t]) for v,t in zip(p,q))))
            r=result['materials'].setdefault(name,{'triangles':0,'uv_degenerate':0,'geometry_degenerate':0,'uv_min':[1e9,1e9],'uv_max':[-1e9,-1e9],'density_ratios':[],'min_px_per_meter':[]})
            r['triangles']+=1
            r['uv_min']=np.minimum(r['uv_min'],q.min(axis=0)).tolist();r['uv_max']=np.maximum(r['uv_max'],q.max(axis=0)).tolist()
            a=p[1]-p[0];b=p[2]-p[0];uv1=q[1]-q[0];uv2=q[2]-q[0]
            area=abs(uv1[0]*uv2[1]-uv1[1]*uv2[0])*.5
            al=np.linalg.norm(a);cross=np.linalg.norm(np.cross(a,b))
            if cross<1e-14:r['geometry_degenerate']+=1;continue
            if area<1e-12:r['uv_degenerate']+=1;continue
            if name=='Core_EngravedGold':
                dims=np.array([1024,256] if version=='V2' else [2048,512])
                mat=np.array([[al,np.dot(a/al,b)],[0,cross/al]])
                jac=np.stack([uv1*dims,uv2*dims],axis=1)@np.linalg.inv(mat)
                sv=np.linalg.svd(jac,compute_uv=False)
                r['density_ratios'].append(float(sv.max()/sv.min()));r['min_px_per_meter'].append(float(sv.min()))
    for name,r in result['materials'].items():
        for field in ['density_ratios','min_px_per_meter']:
            a=r.pop(field);r[field+'_p05_p50_p95']=np.percentile(a,[5,50,95]).tolist() if a else []
        r['geometry_triangle_hash_1um']=hashlib.sha256(repr(sorted(geometry[name])).encode()).hexdigest()
        r['geometry_and_uv_hash']=hashlib.sha256(repr(sorted(mapped[name])).encode()).hexdigest()
    p=np.array(points);result['bounds_cm']={'min':(p.min(axis=0)*100).tolist(),'max':(p.max(axis=0)*100).tolist()}
    return result
a=measure(old,'V2');b=measure(new,'V4')
same=all(a['materials'][k]['geometry_triangle_hash_1um']==v['geometry_triangle_hash_1um'] for k,v in b['materials'].items())
result={'old':a,'new':b,'same_material_triangle_geometry_at_1um':same,'new_gold_all_triangles_have_uv_area':b['materials']['Core_EngravedGold']['uv_degenerate']==0,'sphere_uv_unchanged':a['materials']['Core_Starfield']['geometry_and_uv_hash']==b['materials']['Core_Starfield']['geometry_and_uv_hash'],'actual_ue_readback':False}
(R/'Receipts/source_uv_validation.json').write_text(json.dumps(result,indent=2))
assert same,result
assert result['new_gold_all_triangles_have_uv_area'],result
assert result['sphere_uv_unchanged']
print(json.dumps({'same_geometry':same,'sphere_uv_unchanged':result['sphere_uv_unchanged'],'gold_uv_degenerate_before':a['materials']['Core_EngravedGold']['uv_degenerate'],'gold_uv_degenerate_after':b['materials']['Core_EngravedGold']['uv_degenerate']},indent=2))
