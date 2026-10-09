"""Read the reported neckline defect and the actual head fitting frame."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Matrix
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');ROOT=BASE/'V11'
for d in ['Authoring','Delivery','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V10/Authoring/FacelessSecurity_V10.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Security_CompleteBody']
report={'objects':{},'head_sections':[]}
for name in ['Security_Uniform_Native_V09','Security_Uniform_Native_DenseSource_V09','Security_CollarStand_Native']:
    o=bpy.data.objects.get(name)
    if not o:continue
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();edges=[e for e in bm.edges if e.is_boundary];remaining=set(edges);loops=[]
    while remaining:
        seed=remaining.pop();part={seed};todo=list(seed.verts);vv=set(todo)
        while todo:
            v=todo.pop()
            for e in v.link_edges:
                if e not in remaining:continue
                remaining.remove(e);part.add(e)
                for other in e.verts:
                    if other not in vv:vv.add(other);todo.append(other)
        p=np.array([v.co for v in vv]);loops.append({'vertices':len(vv),'bounds':[p.min(0).tolist(),p.max(0).tolist()], 'center':p.mean(0).tolist()})
    report['objects'][name]={'vertices':len(bm.verts),'boundary_loops':loops};bm.free()
points=np.array([v.co for v in body.data.vertices]);head=points[points[:,2]>1.59]
for z in np.arange(1.66,1.87,.02):
    q=head[abs(head[:,2]-z)<.006]
    if len(q):report['head_sections'].append({'z':float(z),'min':q.min(0).tolist(),'max':q.max(0).tolist()})
cache=json.loads((BASE/'V03/Native/native_idle.json').read_text(encoding='utf-8'))
ref=cache['reference'];common=[b for b in rig.data.bones if b.name in ref]
a=np.array([rig.matrix_world@b.head_local for b in common]);b=np.array([ref[x.name]['translation_cm'] for x in common]);am=a.mean(0);bm=b.mean(0)
u,s,vt=np.linalg.svd((a-am).T@(b-bm));rot=u@vt;scale=s.sum()/((a-am)**2).sum();offset=bm-am@rot*scale
report['author_to_ue']={'rotation_row':rot.tolist(),'scale':float(scale),'translation_cm':offset.tolist(),'reference_fit_error_cm':float(np.linalg.norm((a@rot*scale+offset)-b,axis=1).max())}
report['ue_head_reference']=ref['head'];report['native_head_matrix']=[list(row) for row in rig.matrix_world@rig.data.bones['head'].matrix_local]
(ROOT/'neck_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
