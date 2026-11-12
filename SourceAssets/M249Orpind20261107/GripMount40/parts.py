"""Author the three replacement grip shells and the paired factory assembly parts."""
import bpy
import bmesh
import json
import numpy as np
from pathlib import Path
from mathutils import Matrix

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent
PLAN=json.loads((HERE/'fit.json').read_text())
OUT=HERE/'Exports'
OUT.mkdir(exist_ok=True)
root=np.array(PLAN['root_rotation'])
origin=np.array(PLAN['root_position'])
mirror=np.array([1.,-1.,1.])
ring=np.asarray(PLAN['rear_ring_cm'])*mirror


def area(p):
    return np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))*.5


def ordered(points):
    if area(points)<0:points=points[::-1]
    return np.roll(points,-np.argmax(points[:,0]),axis=0)


def component(raw):
    return (raw[:,[1,0,2]]*100+[5.45,-28.6,-5.3])*mirror


def section_center(points,faces,z):
    sub=points[faces]
    cut=sub[(sub[:,:,2].min(1)<z)&(sub[:,:,2].max(1)>=z)]
    result=[]
    for k in range(3):
        a,b=cut[:,k],cut[:,(k+1)%3]
        ok=(a[:,2]<z)!=(b[:,2]<z)
        a,b=a[ok],b[ok]
        result.extend(a+(b-a)*((z-a[:,2])/(b[:,2]-a[:,2]))[:,None])
    q=np.asarray(result)
    return (q.min(0)+q.max(0))*.5


def export(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
                             axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')


def table_parts():
    remove=np.asarray(PLAN['moved_body_faces'])
    rec=np.load(SOURCE/'Geometry/Receiver.npz')
    grip=np.load(SOURCE/'Geometry/RearGrip.npz')
    for key,inputs,original,slot in [
        ('body',[(rec,np.delete(np.arange(len(rec['faces'])),remove))],rec,'Receiver'),
        ('reargrip',[(grip,np.arange(len(grip['faces']))),(rec,remove)],grip,'RearGrip')]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        pivot=component(original['positions'])[:,[2,1,0]]
        pivot=(pivot.min(0)+pivot.max(0))*.5
        coords=[];indices=[];normals=[];uvs=[]
        for src,facelist in inputs:
            keep,ind=np.unique(src['faces'][facelist],return_inverse=True)
            p=component(src['positions'][keep])[:,[2,1,0]]
            indices.extend(ind.reshape(-1,3)[:,::-1]+len(coords))
            coords.extend((p-pivot)/100)
            normals.extend(src['normals'][keep][:,[2,0,1]]*[1,-1,1])
            uv=src['uv'][keep].copy();uv[:,1]=1-uv[:,1];uvs.extend(uv)
        mesh=bpy.data.meshes.new(key);mesh.from_pydata(coords,[],indices);mesh.update()
        o=bpy.data.objects.new('M249_'+slot,mesh);bpy.context.collection.objects.link(o)
        mesh.materials.append(bpy.data.materials.new('M249_Factory_'+slot))
        mesh.polygons.foreach_set('use_smooth',np.ones(len(mesh.polygons),bool))
        loops=np.array([l.vertex_index for l in mesh.loops])
        mesh.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uvs,dtype=np.float32)[loops].ravel())
        mesh.normals_split_custom_set_from_vertices(np.asarray(normals).tolist())
        export([o],'SM_M249_'+key)


def loops_on_plane(bm,z):
    on=[v for v in bm.verts if abs(v.co.z-z)<.0002]
    bmesh.ops.remove_doubles(bm,verts=on,dist=.002)
    edges={e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<.001 for v in e.verts)}
    # Legacy grip scans can have split UV seams and isolated cut fragments.
    # Trace silhouette chains first, then join their nearest corresponding ends.
    paths=[]
    loops=[]
    while edges:
        start=next((v for e in edges for v in e.verts if sum(x in edges for x in v.link_edges)==1),None)
        if start is None:edge=edges.pop();start,at=edge.verts
        else:
            edge=next(e for e in start.link_edges if e in edges);edges.remove(edge);at=edge.other_vert(start)
        loop=[start]
        while at!=start:
            loop.append(at)
            next_edge=next((e for e in at.link_edges if e in edges),None)
            if next_edge is None:break
            edges.remove(next_edge);at=next_edge.other_vert(at)
        if at==start and len(loop)>2:loops.append(loop)
        elif len(loop)>1:paths.append(loop)
    while paths:
        chain=max(paths,key=len);paths.remove(chain)
        while paths:
            close=(chain[-1].co-chain[0].co).length
            candidates=[((chain[-1].co-frag[end].co).length,i,end) for i,frag in enumerate(paths) for end in (0,-1)]
            distance,i,end=min(candidates)
            if close<=distance:break
            frag=paths.pop(i);chain.extend(frag if end==0 else frag[::-1])
        if len(chain)>2:loops.append(chain)
    loops=[list(dict.fromkeys(chain)) for chain in loops]
    return sorted([chain for chain in loops if len(chain)>2],key=lambda l:abs(area(np.array([v.co[:] for v in l]))),reverse=True)


def replacement(key):
    name='SM_M249_'+key
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'Repair13/Exports'/(name+'.blend')),use_scripts=False)
    bpy.context.preferences.filepaths.save_version=0
    collar=next(o for o in bpy.context.scene.objects if o.name.startswith('M249_GripCollar'))
    bpy.data.objects.remove(collar,do_unlink=True)
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    obj.data.calc_loop_triangles()
    faces=np.asarray([t.vertices[:] for t in obj.data.loop_triangles])
    # Design in Blender component centimetres, returning to the exact native
    # weapon-root import convention when the part is finished.
    basis=np.diag(mirror)@root@np.diag(mirror)*100.
    xf=np.eye(4);xf[:3,:3]=basis;xf[:3,3]=mirror*origin
    obj.data.transform(Matrix(xf))
    points=np.array([v.co[:] for v in obj.data.vertices])
    factory=np.load(SOURCE/'Geometry/RearGrip.npz')
    z=-15.5
    align=section_center(component(factory['positions']),factory['faces'],z)-section_center(points,faces,z)
    align[2]=0
    obj.data.transform(Matrix.Translation(align))
    # Replace the upper shell down to the first continuous palm section.
    zcut=-12.55
    bm=bmesh.new();bm.from_mesh(obj.data)
    primary=max(bm.faces,key=lambda f:f.calc_area()).material_index
    bmesh.ops.bisect_plane(bm,geom=[*bm.faces,*bm.edges,*bm.verts],plane_co=(0,0,zcut),
                           plane_no=(0,0,1),dist=.00001,clear_outer=True)
    loops=loops_on_plane(bm,zcut)
    if not loops:raise RuntimeError('No grip perimeter '+key)
    border=loops[0]
    for interior in loops[1:]:
        if bm.faces.get(interior) is None:bm.faces.new(interior).material_index=primary
    base=np.array([v.co[:] for v in border])
    if area(base)<0:border=border[::-1];base=base[::-1]
    start=int(np.argmax(base[:,0]));border=border[start:]+border[:start];base=np.roll(base,-start,axis=0)
    rim=ordered(ring.copy());rim[:,2]+=.21
    def perimeter(points):
        d=np.linalg.norm(np.diff(np.vstack([points,points[0]]),axis=0)[:,:2],axis=1)
        return np.r_[0.,np.cumsum(d)]/d.sum()
    ts=perimeter(base);rs=perimeter(rim)
    target=np.column_stack([np.interp(ts[:-1],rs,np.r_[rim[:,k],rim[0,k]]) for k in range(3)])
    uv=bm.loops.layers.uv.verify()
    prev=border
    for weight in (.25,.56,.84,1.):
        blend=weight*weight*(3-2*weight)
        pos=base+(target-base)*blend;pos[:,2]=zcut+weight*(target[:,2]-zcut)
        upper=[bm.verts.new(p) for p in pos]
        for i,j in enumerate(list(range(1,len(prev)))+[0]):
            f=bm.faces.new([prev[i],prev[j],upper[j],upper[i]])
            f.smooth=True;f.material_index=primary
            for l in f.loops:
                x,y,h=l.vert.co;l[uv].uv=(y*.05,h*.05)
        prev=upper
    cap=bm.faces.new(prev);cap.material_index=primary
    bmesh.ops.triangulate(bm,faces=[cap])
    bm.normal_update();bm.to_mesh(obj.data);bm.free()
    obj.data.transform(Matrix(np.linalg.inv(xf)));obj.data.update()
    export([obj],name)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
    print('Authored',key,'complete upper grip, palm alignment',align,flush=True)


table_parts()
for key in ('phantom_reargrip','balanced_reargrip','stable_antislip_reargrip'):replacement(key)
