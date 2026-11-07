"""Recover the factory shell patch that the old radial adapter replaced."""
from pathlib import Path
import bpy,bmesh,numpy as np,json,gzip
from mathutils.kdtree import KDTree
from joint_geometry import ATTR,cut_ring,transition

def restore_front(rec,material):
    root=Path(__file__).resolve().parent.parent
    original=root/'M24ReceiverGripRebuild20261031'
    data=json.load(gzip.open(original/'Inputs/geometry.json.gz','rt'))['M24']
    p=np.asarray(data['positions'])*[.01,-.01,.01];tri=np.asarray(data['triangles'])
    centers=np.asarray(json.loads((original/'Inputs/native_rear_seat_faces.json').read_text()))*[.01,-.01,.01]
    keys={tuple(np.round(v,7)) for v in centers}
    selected=[t for t in tri if tuple(np.round(p[t].mean(0),7)) in keys]
    with bpy.data.libraries.load(str(root/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),link=False) as (av,ld):ld.objects=['M24_base']
    donor=ld.objects[0];me=donor.data;me.calc_loop_triangles()
    dp=np.array([v.co[:] for v in me.vertices]);ns=np.array([n.vector[:] for n in me.corner_normals]);ts=list(me.loop_triangles)
    kd=KDTree(len(ts))
    for i,t in enumerate(ts):kd.insert(dp[t.vertices].mean(0),i)
    kd.balance();positions=[];faces=[];normals=[];uvs=[]
    for t in selected:
        xyz=p[t];_,i,d=kd.find(xyz.mean(0))
        if d>2e-6:raise RuntimeError('Native donor face does not match '+str(d))
        source=ts[i];corners=dp[source.vertices];mapping=np.argmin(np.sum((xyz[:,None]-corners[None])**2,axis=2),axis=1)
        if np.max(np.linalg.norm(xyz-corners[mapping],axis=1))>2e-6:raise RuntimeError('Native donor corner mismatch')
        start=len(positions);positions.extend(xyz);faces.append((start,start+1,start+2))
        for k in mapping:
            li=source.loops[k];normals.append(ns[li]);uvs.append(me.uv_layers[0].data[li].uv[:])
    mesh=bpy.data.meshes.new('Recovered native front patch');mesh.from_pydata(positions,[],faces);mesh.materials.append(material);mesh.update()
    patch=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(patch)
    mesh.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uvs,np.float32).ravel())
    mesh.attributes.new(ATTR,'FLOAT_VECTOR','CORNER').data.foreach_set('vector',np.asarray(normals,np.float32).ravel())
    for f in mesh.polygons:f.use_smooth=True
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=3e-7);bm.to_mesh(mesh);bm.free()
    bpy.data.objects.remove(donor,do_unlink=True)
    # Restore the true non-planar host border. Only the rearward piece is recut.
    front=cut_ring(patch,1,.100)
    rear=cut_ring(rec,1,.050,keep_high=False)
    neck=transition(front,rear,'Native shell continuous seat',material,rows=33)
    return [patch,neck],{'removed_legacy_nonplanar_radial_adapter':True,'original_faces_recovered':len(selected),'front_cut_y_m':.1,'rear_cut_y_m':.05,'front_rim_vertices':len(front['phase']),'rear_rim_vertices':len(rear['phase']),'nonplanar_native_host_boundary':'original selected face patch retained'}
