"""Make a clean cloth envelope; temporary volume caps never enter the garment."""
import numpy as np
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import norm_weights

def weight_at(p,tri,weights,hit):
    a,b,c=p[tri];v0=b-a;v1=c-a;v2=np.asarray(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
    if abs(den)<1e-12:return weights[int(tri[0])]
    v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;w=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den;bary=np.maximum([1-v-w,v,w],0);bary/=bary.sum();out={}
    for i,k in enumerate(tri):
        for name,value in weights[int(k)].items():out[name]=out.get(name,0)+float(bary[i]*value)
    return norm_weights(out)

def tailor(p,f,weights,bones,waist,top):
    source=BVHTree.FromPolygons([Vector(v) for v in p],f.tolist(),all_triangles=True)
    bm=bmesh.new();vs=[bm.verts.new(v) for v in p]
    for ids in f:bm.faces.new([vs[int(i)] for i in ids])
    edges={e for e in bm.edges if e.is_boundary};rings=[]
    while edges:
        edge=edges.pop();start,current=edge.verts;ring=[start,current]
        while current!=start:
            candidates=[e for e in current.link_edges if e in edges]
            if not candidates:raise RuntimeError('Tailoring boundary is branched')
            edge=candidates[0];edges.remove(edge);current=edge.other_vert(current)
            if current!=start:ring.append(current)
        rings.append(ring)
    planes=[(np.array([0.,0.,top]),np.array([0.,0.,1.]),'neck'),(np.array([0.,0.,waist-3.2]),np.array([0.,0.,-1.]),'waist')]
    for side in ('l','r'):
        e=np.array(bones['lowerarm_'+side]['position']);w=np.array(bones['hand_'+side]['position']);axis=(w-e)/np.linalg.norm(w-e);planes.append((w-axis,axis,side))
    for ring in rings:
        points=np.array([v.co[:] for v in ring]);score=[np.abs((points-center)@axis).mean() for center,axis,label in planes];choice=int(np.argmin(score));center,axis,label=planes[choice]
        tolerance=2. if label=='neck' and np.max(np.abs(points[:,0]))<12 else .12
        if score[choice]>tolerance:raise RuntimeError('Unidentified native opening '+str((label,score[choice],points.mean(0).tolist())))
        ring_set=set(ring);boundary_edges=[e for e in bm.edges if e.is_boundary and all(v in ring_set for v in e.verts)]
        extension={v:bm.verts.new(np.array(v.co)+axis*2.) for v in ring};cap_center=bm.verts.new(points.mean(0)+axis*2.)
        for edge in boundary_edges:
            loop=edge.link_loops[0];a,b=loop.vert,loop.link_loop_next.vert
            bm.faces.new([b,a,extension[a]]);bm.faces.new([b,extension[a],extension[b]]);bm.faces.new([extension[b],extension[a],cap_center])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    # Inflate the temporary solid before remeshing: the union forms a tailored
    # armpit instead of offsetting two concave native sheets into each other.
    for v in bm.verts:
        point=np.array(v.co);ease=.82
        if point[2]>top-6 and abs(point[0])<10:ease=.55
        for center,axis,label in planes[2:]:
            q=point-center;prox=-float(q@axis);radial=np.linalg.norm(q-axis*(q@axis))
            if prox<7 and radial<9:ease=min(ease,.50+.20*np.clip(prox/7,0,1))
        v.co+=v.normal*ease
    mesh=bpy.data.meshes.new('Robe_TEMP_FitVolume');bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    remesh=ob.modifiers.new('Continuous tailoring volume','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.55;remesh.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=remesh.name)
    soften=ob.modifiers.new('Cloth-scale surface ease','SMOOTH');soften.factor=.5;soften.iterations=3;bpy.ops.object.modifier_apply(modifier=soften.name)
    bm=bmesh.new();bm.from_mesh(ob.data)
    for center,axis,label in planes:
        if label=='waist':
            faces=[ff for ff in bm.faces if all(abs(v.co.x)<27 for v in ff.verts)];es={e for ff in faces for e in ff.edges};verts={v for ff in faces for v in ff.verts};geom=list(verts)+list(es)+faces
        else:geom=list(bm.verts)+list(bm.edges)+list(bm.faces)
        bmesh.ops.bisect_plane(bm,geom=geom,plane_co=Vector(center),plane_no=Vector(axis),dist=.00001,clear_inner=False,clear_outer=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
    pp=np.array([v.co[:] for v in bm.verts]);ff=np.array([[v.index for v in face.verts][::-1] for face in bm.faces]);bm.free();bpy.data.objects.remove(ob,do_unlink=True)
    ww=[]
    for i,point in enumerate(pp):
        hit,no,fi,dist=source.find_nearest(Vector(point))
        if hit is None:raise RuntimeError('Missing native weight capture')
        ww.append(weight_at(p,f[fi],weights,hit))
    return pp,ff,ww
