"""Measure the two rebuilt visual joins in the editable geometry."""
from pathlib import Path
import bpy,numpy as np,json
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Meshy_JunctionR2.blend'),use_scripts=False)
out={}
for kind in ('Native','Advanced'):
    col=bpy.data.collections[kind+' | fitted to M24'];neck=next(o for o in col.objects if 'blended receiver' in o.name)
    rec=next(o for o in col.objects if o.name.startswith('Donor receiver'));body=next(o for o in col.objects if 'Meshy carbon stock' in o.name)
    def edge(o,level):
        m=o.data; p=np.empty((len(m.vertices),3),np.float32);m.vertices.foreach_get('co',p.ravel());idx=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',idx)
        n=np.empty((len(idx),3),np.float32);m.corner_normals.foreach_get('vector',n.ravel())
        near=np.flatnonzero(abs(p[idx,1]-level)<1e-6); ans={}
        for i in near:ans.setdefault(tuple(np.round(p[idx[i],[0,2]],7)),[]).append(n[i])
        return {k:np.mean(v,axis=0)/max(1e-8,np.linalg.norm(np.mean(v,axis=0))) for k,v in ans.items()}
    limits={}
    for peer,y in [(rec,-.0295),(body,-.0649)]:
        a=edge(neck,y);b=edge(peer,y);keys=a.keys()&b.keys()
        points=np.array(list(b));err=max(np.min(np.linalg.norm(points-np.array(k),axis=1)) for k in a)
        dif=np.degrees(np.arccos(np.clip([np.dot(a[k],b[k]) for k in keys],-1,1)))
        limits[peer.name]={'gap_mm':float(err*1000),'normal_degrees_p95':float(np.percentile(dif,95)),'matched_points':len(keys),'neck_points':len(a)}
    out[kind]=limits
(O/'geometry-readback.json').write_text(json.dumps(out,indent=2))
print(out)
