from pathlib import Path
import gzip,json,bpy,bmesh,numpy as np
O=Path(__file__).resolve().parent
src=O.parent/'M24ReceiverGripRebuild20261031'
d=json.load(gzip.open(src/'Inputs/geometry.json.gz','rt'))['M24']
print('NATIVE_KEYS',[(k,len(v) if hasattr(v,'__len__') else type(v).__name__) for k,v in d.items()])
p=np.asarray(d['positions'])*[.01,-.01,.01];f=np.asarray(d['triangles']);m=np.asarray(d['material_ids'])
centers=np.asarray(json.loads((src/'Inputs/native_rear_seat_faces.json').read_text()))*[.01,-.01,.01]
keys={tuple(np.round(v,7)) for v in centers}
selected=[i for i,t in enumerate(f) if tuple(np.round(p[t].mean(0),7)) in keys]
print('SELECTED',len(selected),'bounds',p[np.unique(f[selected])].min(0),p[np.unique(f[selected])].max(0))
with bpy.data.libraries.load(str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),link=False) as (av,ld):
    ld.objects=['M24_base']
ob=ld.objects[0];bpy.context.collection.objects.link(ob)
print('SOURCE_OBJECT',ob.matrix_world,ob.matrix_local,'uv',[v.name for v in ob.data.uv_layers])
ob.data.calc_loop_triangles()
for world in (False,True):
    vp=np.array([(ob.matrix_world@v.co if world else v.co)[:] for v in ob.data.vertices]);hits=[t for t in ob.data.loop_triangles if tuple(np.round(vp[t.vertices].mean(0),7)) in keys]
    print('SOURCE_MATCHES',world,len(hits),'bounds',vp.min(0),vp.max(0))
for y in (.1,.09,.08,.07,.06):
    me=bpy.data.meshes.new('Removed native faces');me.from_pydata(p.tolist(),[],f[selected].tolist());me.update();bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,y,0),plane_no=(0,1,0),clear_inner=True,dist=1e-8)
    es={e for e in bm.edges if e.is_boundary and all(abs(v.co.y-y)<2e-7 for v in e.verts)}
    ps=np.array([v.co[:] for v in {v for e in es for v in e.verts}]);bad=[v.co[:] for v in {v for e in es for v in e.verts} if sum(e in es for e in v.link_edges)!=2]
    print('CUT',y,'edges',len(es),'bounds',ps.min(0).tolist(),ps.max(0).tolist(),'open',bad)
    bm.free();bpy.data.meshes.remove(me)
