"""HK416 receiver-to-stock seats; dimensions in the registered weapon frame (m)."""
import bpy, math
from mathutils import Matrix, Vector

STOCK_FRONT = {'skeleton': 0.0, 'qr_performance': .007,
               'core_stock': .007, 'tactical_telescopic': .007}

def section_radius(mesh, axis, plane, center, radial_axes, count=96):
    # Intersect the actual neck surface. Radial rays select the outside of the
    # closed tube section and exclude sling loops and the shoulder pad.
    segments = []
    for face in mesh.polygons:
        hits = []
        ids = list(face.vertices)
        for i, index in enumerate(ids):
            a = mesh.vertices[index].co; b = mesh.vertices[ids[(i+1)%len(ids)]].co
            if (a[axis]-plane)*(b[axis]-plane) >= 0: continue
            p = a.lerp(b, (plane-a[axis])/(b[axis]-a[axis]))
            q = Vector((p[radial_axes[0]]-center[0], p[radial_axes[1]]-center[1]))
            hits.append(q)
        if len(hits) == 2: segments.append(hits)
    radii=[]
    for i in range(count):
        d=Vector((math.cos(i*math.tau/count), math.sin(i*math.tau/count)))
        cross=lambda a,b:a.x*b.y-a.y*b.x
        values=[]
        for a,b in segments:
            e=b-a; denom=cross(d,e)
            if abs(denom)<1e-10: continue
            t=cross(a,e)/denom; u=cross(a,d)/denom
            if -.00001<=u<=1.00001 and .008<t<.045: values.append(t)
        if not values: raise RuntimeError('Missing stock neck contour at ray '+str(i))
        radii.append(max(values))
    return radii

def fit_stock(key, body, root_matrix, source_to_root, native_blend, material):
    axis=source_to_root@Vector((0,-.0385,.01945))
    with bpy.data.libraries.load(str(native_blend),link=False) as (_, data):
        data.objects=['Stock_Stick_low']
    native=data.objects[0]
    native.data.transform(root_matrix.inverted()@native.matrix_world)
    native.data.update()
    first=section_radius(native.data,1,.0420,(axis.x,axis.z),(0,2))
    bpy.data.objects.remove(native,do_unlink=True)
    lead=STOCK_FRONT[key]
    # The donor's +X points to the shoulder. After the Z turn, its radial
    # coordinate is (-Y,Z), so sample the transformed mesh for matching rays.
    transform=Matrix.Rotation(math.pi/2,4,'Z')
    transform.translation=Vector((axis.x,.0468-lead,axis.z))
    body.data.transform(transform); body.data.update()
    # Meshy QR has a nonplanar leading rim. Seat into the first complete neck
    # cross section, rather than bridging only its single foremost vertex.
    for depth in (.0008,.0015,.0025,.004,.006,.008,.012):
        neck_y=.0468+depth
        try:
            last=section_radius(body.data,1,neck_y,(axis.x,axis.z),(0,2))
            break
        except RuntimeError:
            if depth==.012: raise
    rings=[(.0409,0.,.999),(.0415,0.,1.),(.0421,.08,1.),
           (neck_y-.0012,.82,1.),(neck_y-.0002,1.,1.),(neck_y+.0002,1.,.999)]
    vertices=[]; count=len(first)
    for y,alpha,scale in rings:
        for i,(a,b) in enumerate(zip(first,last)):
            r=(a+(b-a)*alpha)*scale; angle=i*math.tau/count
            vertices.append((axis.x+r*math.cos(angle),y,axis.z+r*math.sin(angle)))
    faces=[tuple(range(count-1,-1,-1)),tuple((len(rings)-1)*count+i for i in range(count))]
    for j in range(len(rings)-1):
        for i in range(count):
            k=(i+1)%count; faces.append((j*count+i,j*count+k,(j+1)*count+k,(j+1)*count+i))
    mesh=bpy.data.meshes.new('HK416 closed receiver seat '+key)
    mesh.from_pydata(vertices,[],faces); mesh.materials.append(material);mesh.update()
    # Ring winding in X/Z is opposite the +Y axial direction.
    import bmesh
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for p in mesh.polygons:p.use_smooth=len(p.vertices)==4
    seat=bpy.data.objects.new('HK416 closed receiver seat '+key,mesh)
    bpy.context.collection.objects.link(seat)
    body.data.transform(root_matrix);seat.data.transform(root_matrix)
    return seat, {'donor_front_m':lead,'receiver_front_y_m':.0409,'stock_front_y_m':.0468,
                  'stock_translation_m':list(transform.translation),'neck_section_y_m':neck_y,'closed_seat':True}
