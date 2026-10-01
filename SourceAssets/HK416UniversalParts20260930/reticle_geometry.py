"""Readable EOTH glyph plane on the existing optical axis; metres in mesh space."""
import bpy,bmesh
from mathutils import Vector

def replace_reticle(ob,sockets):
    slot=next(i for i,m in enumerate(ob.data.materials) if m.name.split('.')[0]=='M_HK416_Eo_tech_Reticle')
    faces=[f for f in ob.data.polygons if f.material_index==slot]
    points=[ob.data.vertices[i].co for f in faces for i in f.vertices]
    old_center=Vector([(min(p[k] for p in points)+max(p[k] for p in points))*.5 for k in range(3)])
    rear=Vector(sockets['SightRear']);front=Vector(sockets['SightFront'])
    forward=(front-rear).normalized();up=Vector(sockets['SightUp'])-rear
    up=(up-forward*up.dot(forward)).normalized();right=forward.cross(up).normalized()
    center=rear+forward*(old_center-rear).dot(forward)
    # 14 mm on rifle variants / 9.1 mm on the 65% pistol variants. The shader
    # ring occupies 60% of this width, only slightly larger than the old glyph.
    # Use the authored 40 mm optical-up reference so rebuilding an already
    # converted mesh cannot repeatedly enlarge its reticle plane.
    width=.014*((Vector(sockets['SightUp'])-rear).length/.04)
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==slot],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    coords=[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]
    vertices=[bm.verts.new(center+width*(right*x+up*y)) for x,y in coords]
    face=bm.faces.new(vertices);face.material_index=slot
    for layer in bm.loops.layers.uv.values():
        for loop,(x,y) in zip(face.loops,coords):loop[layer].uv=(x+.5,y+.5)
    bmesh.ops.triangulate(bm,faces=[face]);bm.to_mesh(ob.data);bm.free();ob.data.update()
    return {'plane_width_m':width,'center_m':list(center),'previous_center_m':list(old_center),'aim_sockets_unchanged':True}
