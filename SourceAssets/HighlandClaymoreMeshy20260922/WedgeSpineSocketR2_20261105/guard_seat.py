"""Cut fitted Highland guards at the gem setting, retaining their native corner attributes."""
import bmesh
import bpy
from mathutils import Vector
import numpy as np

# Piecewise-planar mating face. It clears the gem crown and follows the two
# quillon beds. The last ramp passes above even the tall riposte quillons.
BREAKS=np.array([0.,.009,.018,.031,.041,.048,.065,.25])
HEIGHTS=np.array([.0222,.0135,.0091,.0100,.0129,.0188,.065,.45])

def seat_z(x):
    return float(np.interp(abs(x),BREAKS,HEIGHTS))

def cut_guard(obj):
    mesh=obj.data
    shading=mesh.attributes.get('SocketSourceNormal') or mesh.attributes.new('SocketSourceNormal','FLOAT_VECTOR','CORNER')
    normals=np.asarray([n.vector[:] for n in mesh.corner_normals],dtype=np.float32)
    shading.data.foreach_set('vector',normals.ravel())
    bm=bmesh.new()
    bm.from_mesh(mesh)
    # Each triangle intersecting two cutter facets must be split at their hinge.
    for x in sorted({v*s for v in BREAKS[:-1] for s in (1,-1)}):
        h=seat_z(x)
        crossing=[f for f in bm.faces if min(v.co.x for v in f.verts)<x<max(v.co.x for v in f.verts)
                  and min(v.co.z for v in f.verts)<h+.018 and max(v.co.z for v in f.verts)>h-.018]
        if crossing:
            geom={element for f in crossing for element in [f,*f.edges,*f.verts]}
            bmesh.ops.bisect_plane(bm,geom=list(geom),plane_co=(x,0,0),plane_no=(1,0,0),dist=1e-8)
    for v in bm.verts:
        v.co.z-=seat_z(v.co.x)
    cut=bmesh.ops.bisect_plane(bm,geom=[*bm.verts,*bm.edges,*bm.faces],plane_co=(0,0,0),
                               plane_no=(0,0,1),dist=1e-7,clear_outer=True)
    rim=[v for v in bm.verts if abs(v.co.z)<.0000008]
    bmesh.ops.remove_doubles(bm,verts=rim,dist=.0000005)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z)<.0000008 for v in e.verts)]
    adjacent={}
    for e in edges:
        a,b=e.verts
        adjacent.setdefault(a,[]).append(b)
        adjacent.setdefault(b,[]).append(a)
    start=max(adjacent,key=lambda v:v.co.x)
    ring=[start]
    prev,at=None,start
    while True:
        ns=adjacent[at]
        if len(ns)!=2:
            raise ValueError(f'{obj.name}: disconnected socket rim at {at.co}')
        nxt=ns[0] if ns[1]==prev else ns[1]
        if nxt==start:
            break
        if nxt in ring:
            raise ValueError(f'{obj.name}: self-intersecting socket rim')
        ring.append(nxt)
        prev,at=at,nxt
    if len(ring)!=len(adjacent):
        raise ValueError(f'{obj.name}: socket has multiple contours ({len(ring)}/{len(adjacent)})')
    area=sum(a.co.x*b.co.y-a.co.y*b.co.x for a,b in zip(ring,ring[1:]+ring[:1]))
    if area<0:
        ring=ring[:1]+ring[:0:-1]
    layer=bm.loops.layers.float_vector['SocketSourceNormal']
    seam=[(v.co.x,v.co.y,seat_z(v.co.x)) for v in ring]
    normals=[tuple(sum((l[layer] for l in v.link_loops),Vector()).normalized()) for v in ring]
    caps=bmesh.ops.triangle_fill(bm,edges=edges,use_beauty=True,normal=Vector((0,0,1)))['geom']
    for v in bm.verts:
        v.co.z+=seat_z(v.co.x)
    bm.normal_update()
    layer=bm.loops.layers.float_vector['SocketSourceNormal']
    for f in caps:
        if isinstance(f,bmesh.types.BMFace):
            if f.normal.z<0:
                f.normal_flip()
            f.smooth=False
            for l in f.loops:
                l[layer]=f.normal
                for uv in bm.loops.layers.uv.values():
                    l[uv].uv=(.03+3*l.vert.co.x,.20+10*l.vert.co.y)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    field=mesh.attributes['SocketSourceNormal']
    mesh.normals_split_custom_set([v.vector.normalized()[:] for v in field.data])
    mesh.attributes.remove(field)
    return {'points':seam,'normals':normals}
