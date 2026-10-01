"""Native HK416 mounting surface and a closed, continuous grip transition.

Metres in WPN_root. Keep the accepted lower grip and its corner UVs/normals.
The donor has overlapping shells: sample its actual outer cross-section rather
than incorrectly treating all the fragmented cut edges as one boundary loop.
"""
import bpy,bmesh,math
from mathutils import Matrix,Vector
CUT={'phantom_reargrip':0.,'stable_antislip_reargrip':-.012,'balanced_reargrip':-.003}
NATIVE_CUT=.010
SAMPLES=256

def remember_normals(mesh):
    normals=[n.vector.copy() for n in mesh.corner_normals]
    attr=mesh.attributes.get('SourceCornerNormal') or mesh.attributes.new('SourceCornerNormal','FLOAT_VECTOR','CORNER')
    for d,n in zip(attr.data,normals):d.vector=n

def restore_normals(mesh):
    attr=mesh.attributes.get('SourceCornerNormal')
    if not attr:return
    normals=[tuple(d.vector.normalized()) if d.vector.length_squared>1e-12 else (0,0,0) for d in attr.data]
    for f in mesh.polygons:f.use_smooth=True
    mesh.normals_split_custom_set(normals)

def cut_surface(ob,z,upper,weld=False):
    remember_normals(ob.data)
    bm=bmesh.new();bm.from_mesh(ob.data)
    if weld:bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper)
    bm.to_mesh(ob.data);bm.free();restore_normals(ob.data)

def section(mesh,z,count=SAMPLES):
    segments=[]
    for f in mesh.polygons:
        hits=[];ids=list(f.vertices)
        for j,i in enumerate(ids):
            a=mesh.vertices[i].co;b=mesh.vertices[ids[(j+1)%len(ids)]].co
            if (a.z-z)*(b.z-z)<0:hits.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
        if len(hits)==2:segments.append(hits)
    pts=[p for pair in segments for p in pair]
    center=Vector([(min(p[i] for p in pts)+max(p[i] for p in pts))*.5 for i in (0,1)])
    cross=lambda a,b:a.x*b.y-a.y*b.x
    outline=[]
    for j in range(count):
        angle=math.tau*j/count;d=Vector((math.cos(angle),math.sin(angle)));distances=[]
        for pa,pb in segments:
            a=pa.xy-center;b=pb.xy-center;e=b-a;denom=cross(d,e)
            if abs(denom)<1e-12:continue
            t=cross(a,e)/denom;u=cross(a,d)/denom
            if 0<=u<=1 and t>0:distances.append(t)
        if not distances:raise RuntimeError('Missing grip surface at ray '+str(j))
        p=center+d*max(distances);outline.append(Vector((p.x,p.y,z)))
    return outline

def native_loop(mesh,z):
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    edges=set(e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-6 for v in e.verts));loops=[]
    while edges:
        e=edges.pop();start=e.verts[0];v=e.verts[1];loop=[start.index,v.index]
        while v!=start:
            candidates=[e for e in v.link_edges if e in edges]
            if len(candidates)!=1:raise RuntimeError('Invalid native HK416 cut boundary')
            e=candidates[0];edges.remove(e);v=e.other_vert(v)
            if v!=start:loop.append(v.index)
        loops.append(loop)
    bm.free()
    if len(loops)!=1:raise RuntimeError('Expected one native HK416 neck boundary')
    ids=loops[0];points=[mesh.vertices[i].co for i in ids]
    area=sum(a.x*b.y-b.x*a.y for a,b in zip(points,points[1:]+points[:1]))
    if area<0:ids.reverse()
    return ids

def fit_reargrip(key,body,root_matrix,native_blend,material):
    cut=CUT[key];bottom_z=cut-.0006
    low=section(body.data,bottom_z)
    with bpy.data.libraries.load(str(native_blend),link=False) as (_,data):data.objects=['Hand_grip_low']
    native=data.objects[0];bpy.context.collection.objects.link(native)
    native.data.transform(root_matrix.inverted()@native.matrix_world)
    native.parent=None;native.matrix_world=Matrix.Identity(4);native.modifiers.clear();native.data.update()
    high=section(native.data,NATIVE_CUT);high_next=section(native.data,NATIVE_CUT+.001)
    cut_surface(native,NATIVE_CUT,True,True);boundary=native_loop(native.data,NATIVE_CUT)
    old=native.data;vertices=[v.co.copy() for v in old.vertices];faces=[tuple(f.vertices) for f in old.polygons]
    old_uv=[[tuple(d.uv) for d in layer.data] for layer in old.uv_layers]
    old_normals=[tuple(n.vector) for n in old.corner_normals];old_face_count=len(faces)
    n=SAMPLES;levels=10;length=NATIVE_CUT-bottom_z;rings=[]
    for k in range(levels):
        t=k/levels;ring=[]
        for j,(p,q) in enumerate(zip(low,high)):
            a=(q-p)/length;b=(high_next[j]-q)/.001
            # The donor contains nested shells: their nearest cross-section
            # derivatives jump between shells and create corrugations. Use the
            # two actual endpoints for the lower tangent and the clean native
            # surface for the upper tangent; leave both endpoints in place.
            for tangent in (a,b):
                tangent.z=1.;lateral=tangent.xy.length
                if lateral>1.2:tangent.x*=1.2/lateral;tangent.y*=1.2/lateral
            point=p*(2*t**3-3*t*t+1)+a*(length*(t**3-2*t*t+t))+q*(-2*t**3+3*t*t)+b*(length*(t**3-t*t))
            ring.append(len(vertices));vertices.append(point)
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for j in range(n):k=(j+1)%n;faces.append((a[j],a[k],b[k],b[j]))
    # Join to every vertex of the native rim, keeping its actual contour.
    center=sum((old.vertices[i].co.xy for i in boundary),Vector((0,0)))/len(boundary)
    angle=lambda p:math.atan2(p.y-center.y,p.x-center.x)%math.tau
    top=sorted(boundary,key=lambda i:angle(vertices[i]));a=sorted(rings[-1],key=lambda i:angle(vertices[i]))
    ap=[angle(vertices[i]) for i in a];bp=[angle(vertices[i]) for i in top];i=j=0
    while i<len(a) or j<len(top):
        an=ap[(i+1)%len(a)]+(math.tau if i+1>=len(a) else 0) if i<len(a) else float('inf')
        bn=bp[(j+1)%len(top)]+(math.tau if j+1>=len(top) else 0) if j<len(top) else float('inf')
        if an<bn:faces.append((a[i%len(a)],a[(i+1)%len(a)],top[j%len(top)]));i+=1
        else:faces.append((a[i%len(a)],top[(j+1)%len(top)],top[j%len(top)]));j+=1
    # The closed lower face is embedded 0.6 mm into the unchanged donor head,
    # blocking light through its overlapping source shell cuts.
    c=len(vertices);vertices.append(sum(low,Vector())/n)
    for j in range(n):faces.append((rings[0][(j+1)%n],rings[0][j],c))
    mesh=bpy.data.meshes.new('HK416 continuous grip neck '+key);mesh.from_pydata(vertices,[],faces);mesh.materials.append(material);mesh.update()
    for f in mesh.polygons:f.use_smooth=True
    for channel in range(4):
        uv=mesh.uv_layers.new(name='HK416_UV'+str(channel))
        for f in mesh.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
            for li in f.loop_indices:
                p=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=old_uv[channel][li] if f.index<old_face_count and channel<len(old_uv) else (p[axes[0]]/.04,p[axes[1]]/.04)
    normals=[tuple(n.vector) for n in mesh.corner_normals];normals[:len(old_normals)]=old_normals
    rim_normals={i:Vector() for i in boundary}
    for f in old.polygons:
        for li in f.loop_indices:
            i=old.loops[li].vertex_index
            if i in rim_normals:rim_normals[i]+=Vector(old_normals[li])
    for f in mesh.polygons:
        if f.index<old_face_count:continue
        for li in f.loop_indices:
            i=mesh.loops[li].vertex_index
            if i in rim_normals:normals[li]=tuple(rim_normals[i].normalized())
            if c in f.vertices:normals[li]=(0,0,-1)
    mesh.normals_split_custom_set(normals)
    native.data=mesh;native.name='HK416 fitted rear-grip neck';native.hide_set(False)
    cut_surface(body,cut,False)
    body.data.transform(root_matrix);native.data.transform(root_matrix)
    return native,{'body_cut_z_m':cut,'neck_lower_z_m':bottom_z,'native_cut_z_m':NATIVE_CUT,'native_boundary_vertices':len(boundary),'surface_samples':n,'levels':levels,'lower_body_transform':'identity','native_contact':'Hand_grip_low unchanged above 10 mm','separate_M4_head_and_box_removed':True}
