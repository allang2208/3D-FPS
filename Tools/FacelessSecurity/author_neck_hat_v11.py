"""V11: sewn fitted neck opening and separate rigid security cap.

Production only: no pose playback, preview render, or runtime acceptance.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
ROOT=BASE/'V11'
for d in ['Authoring','Delivery','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V10/Authoring/FacelessSecurity_V10.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Security_CompleteBody']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
report={'source':'V10','rendered':False,'runtime_tested':False}

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)

def weights(o):
    names={g.index:g.name for g in o.vertex_groups}
    return [{names[g.group]:g.weight for g in v.groups} for v in o.data.vertices]

def norm(ws):
    ws={n:w for n,w in ws.items() if w>1e-6};s=sum(ws.values())
    return {n:w/s for n,w in ws.items()}

def mix(a,b,t):
    return norm({n:a.get(n,0)*(1-t)+b.get(n,0)*t for n in a.keys()|b.keys()})

def put(o,rows):
    o.vertex_groups.clear()
    for n in sorted({n for row in rows for n in row}):o.vertex_groups.new(name=n)
    for v,row in zip(o.data.vertices,rows):
        for n,w in row.items():o.vertex_groups[n].add([v.index],w,'REPLACE')

def surface(o):
    o.data.calc_loop_triangles();p=[v.co.copy() for v in o.data.vertices];t=[tuple(f.vertices) for f in o.data.loop_triangles]
    return BVHTree.FromPolygons(p,t,all_triangles=True),p,t

def sample(p,surf,rows):
    tree,points,tri=surf;hit=tree.find_nearest(p);ids=tri[hit[2]]
    abc=barycentric_transform(hit[0],*(points[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    abc=[max(0.,float(x)) for x in abc];total=sum(abc);out={}
    for i,c in zip(ids,abc):
        for n,w in rows[i].items():out[n]=out.get(n,0)+w*c/total
    return norm(out)

def normals(o):
    if o.data.has_custom_normals:o.data.normals_split_custom_set([(0.,0.,0.)]*len(o.data.loops))
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    o.data.update()
    for f in o.data.polygons:f.use_smooth=True

def make(name,vertices,faces,family):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(bpy.data.materials['Security_'+family])
    normals(o);uv=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        for li in f.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p.x/.2,p.z/.2)
    return o

body_rows=weights(body);skin=surface(body)
shirt=bpy.data.objects['Security_Uniform_Native_V09'];old_rows=weights(shirt)
# V09 built paired thickness last: first half is its native outer surface.
# Retain that exact surface, vertex weights and UV data; discard only its
# old generated inner wall before extending the shared neck boundary.
nouter=len(shirt.data.vertices)//2
shirt.modifiers.clear()
bm=bmesh.new();bm.from_mesh(shirt.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index>=nouter],context='VERTS')
bm.to_mesh(shirt.data);bm.free();shirt.data.update()
shirt.name='Security_Uniform_SewnNeck_V11'
rows=old_rows[:nouter]
bm=bmesh.new();bm.from_mesh(shirt.data);bm.verts.ensure_lookup_table()
neck=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-1.535)<.0001 for v in e.verts)]
adj={}
for e in neck:
    a,b=e.verts;adj.setdefault(a.index,[]).append(b.index);adj.setdefault(b.index,[]).append(a.index)
if not adj or any(len(v)!=2 for v in adj.values()):raise RuntimeError('Cannot sew the source neck boundary')
start=min(adj);loop=[start];prev=None;current=start
while True:
    next_id=next(v for v in adj[current] if v!=prev)
    if next_id==start:break
    loop.append(next_id);prev,current=current,next_id
bm.free()
points=[v.co.copy() for v in shirt.data.vertices]
faces=[tuple(f.vertices) for f in shirt.data.polygons]
original_uv=[[tuple(shirt.data.uv_layers.active.data[li].uv) for li in f.loop_indices] for f in shirt.data.polygons]
old_materials=list(shirt.data.materials);old_polymats=[f.material_index for f in shirt.data.polygons]
old_surface=surface(shirt);old_outer_rows=rows.copy()
# Correct near-neck exterior fit where the source shell sat inside the skin.
# The complete source body is retained; no shoulder/neck skin is deleted.
fit_shifts={}
for i,p in enumerate(points):
    if p.z<1.44 or abs(p.x)>.29:continue
    hit,normal,_,_=skin[0].find_nearest(p)
    signed=(p-hit).dot(normal)
    if signed<.0052:
        delta=normal*(.0052-signed);p+=delta;fit_shifts[i]=delta

body_points=np.array([v.co[:] for v in body.data.vertices])
def neck_center(z):
    q=body_points[(abs(body_points[:,2]-z)<.005)&(abs(body_points[:,0])<.035)]
    if not len(q):raise RuntimeError('No source neck at '+str(z))
    return Vector((0,float((q[:,1].min()+q[:,1].max())*.5),z))

ring_base=[points[i].copy() for i in loop];start_z=sum(p.z for p in ring_base)/len(ring_base)
base_center=neck_center(start_z)
theta=[math.atan2(p.x-base_center.x,-(p.y-base_center.y)) for p in ring_base]
first_r=[(Vector((p.x,p.y,0))-Vector((base_center.x,base_center.y,0))).length for p in ring_base]
previous=loop
for j in range(1,13):
    t=j/12;s=t*t*(3-2*t);new=[]
    for k,index in enumerate(loop):
        # A lower front than rear follows the throat without hitting the jaw.
        z=ring_base[k].z+(1.574-.009*max(0,math.cos(theta[k]))-ring_base[k].z)*t
        c=neck_center(z);d=Vector((math.sin(theta[k]),-math.cos(theta[k]),0))
        hit=skin[0].ray_cast(c,d,.20)[0]
        if hit is None:raise RuntimeError('Cannot fit collar to source neck')
        fitted=(hit-c).length+.0050
        radius=max(fitted,first_r[k]*(1-s)+fitted*s)
        p=c+d*radius
        # Start/end have real shared vertices and paired wall weights.
        new.append(len(points));points.append(p);rows.append(mix(rows[index],sample(hit,skin,body_rows),s))
    for k in range(len(loop)):
        faces.append((previous[k],previous[(k+1)%len(loop)],new[(k+1)%len(loop)],new[k]))
    previous=new

me=bpy.data.meshes.new('Security_SewnNeck_Surface_V11');me.from_pydata(points,[],faces);me.update()
shirt.data=me
for mat in old_materials:me.materials.append(mat)
trim=bpy.data.materials['Security_Trim'];trim_index=len(me.materials);me.materials.append(trim)
uv=me.uv_layers.new(name='UVMap')
for f in me.polygons:
    if f.index<len(original_uv):
        f.material_index=old_polymats[f.index]
        for li,coord in zip(f.loop_indices,original_uv[f.index]):uv.data[li].uv=coord
    else:
        f.material_index=trim_index
        coords=[]
        for li in f.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;c=neck_center(p.z)
            coords.append((math.atan2(p.x,-(p.y-c.y))/(2*math.pi),p.z/.2))
        if max(x for x,y in coords)-min(x for x,y in coords)>.5:coords=[(x+(1 if x<0 else 0),y) for x,y in coords]
        for li,coord in zip(f.loop_indices,coords):uv.data[li].uv=coord
put(shirt,rows);normals(shirt)
new_surface=surface(shirt)

# Existing floating collar rings and leaves are replaced by the sewn stand.
# Shoulder straps remain; they inherit the revised parent shell surface field.
removed=[]
for o in list(bpy.context.scene.objects):
    if o.name.startswith(('Security_CollarStand','Security_CollarLeaf')):
        removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
    elif o.name.startswith('Security_Epaulette'):
        for v in o.data.vertices:
            old_hit=old_surface[0].find_nearest(v.co)[0]
            new_hit=new_surface[0].find_nearest(old_hit)[0]
            v.co+=new_hit-old_hit
        put(o,[sample(v.co,new_surface,rows) for v in o.data.vertices]);normals(o)
solid=shirt.modifiers.new('PairedSewnCollarInnerWall','SOLIDIFY');solid.thickness=.0026;solid.offset=-1;apply(shirt,solid)
normals(shirt);shirt.parent=rig;shirt.matrix_parent_inverse=rig.matrix_world.inverted()
mod=shirt.modifiers.new('NativeBodySkin','ARMATURE');mod.object=rig
report['neck']={'shared_rim_vertices':len(loop),'new_rings':12,'inner_wall_mm':2.6,'removed_independent_parts':removed,
    'near_neck_clearance_vertices':len(fit_shifts),'body_preserved':True,'method':'shared sewn neckline with source neck fit and matching paired skin weights'}
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V11.blend'))
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V11')
exec(compile(export,'export_security_v11','exec'),{})

# The cap is a separate rigid prop; it is never merged into skeletal clothing.
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V11.blend'))
materials={m.name:m for m in bpy.data.materials}
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
parts=[];N=80;cx=0.;cy=-.042

def ringmesh(name,rings,family,close_top=False,thickness=0):
    v=[]
    for rx,ry,z in rings:
        for i in range(N):
            a=2*math.pi*i/N;v.append((cx+rx*math.sin(a),cy-ry*math.cos(a),z))
    f=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(rings)-1) for i in range(N)]
    if close_top:f.append(tuple((len(rings)-1)*N+i for i in range(N)))
    o=make(name,v,f,family)
    if thickness:
        m=o.modifiers.new('ActualCapShell','SOLIDIFY');m.thickness=thickness;m.offset=-1;apply(o,m);normals(o)
    parts.append(o);return o

# Stiff service cap: low navy crown, leather headband, short curved visor.
crown=ringmesh('Security_CapCrown',[(.090,.107,1.748),(.093,.111,1.766),(.100,.118,1.793),(.098,.118,1.816),(.088,.104,1.836),(.065,.078,1.849),(.032,.039,1.854),(.004,.005,1.855)],'Uniform',True,.003)
band=ringmesh('Security_CapBand',[(.091,.108,1.745),(.092,.109,1.750),(.094,.112,1.768),(.094,.112,1.772)],'Leather',False,.003)
for z,rx,ry in [(1.771,.0945,.1125),(1.748,.092,.109)]:
    ringmesh('Security_CapPiping_'+str(z),[(rx,ry,z-.0010),(rx+.0008,ry+.0008,z),(rx,ry,z+.0010)],'Trim',False,.001)
v=[];NX=64;NY=10
for j in range(NY+1):
    t=j/NY
    for i in range(NX+1):
        a=-1.43+2.86*i/NX
        x=math.sin(a)*(.087+.008*t)
        y=cy-math.cos(a)*(.105+.066*t)
        z=1.748-.013*t-.010*math.sin(a)**2
        v.append((x,y,z))
f=[(j*(NX+1)+i,j*(NX+1)+i+1,(j+1)*(NX+1)+i+1,(j+1)*(NX+1)+i) for j in range(NY) for i in range(NX)]
visor=make('Security_CapVisor',v,f,'Leather')
m=visor.modifiers.new('VisorThickness','SOLIDIFY');m.thickness=.0035;m.offset=-1;apply(visor,m);normals(visor);parts.append(visor)

# Applied hatband strap, with rivets on its two ends.
v=[];segments=48
for dz in [-.004,.004]:
    for i in range(segments+1):
        a=-1.28+2.56*i/segments;v.append((.095*math.sin(a),cy-.114*math.cos(a),1.763+dz-.002*math.cos(a)))
strap=make('Security_CapStrap',v,[(i,i+1,segments+2+i,segments+1+i) for i in range(segments)],'Trim')
m=strap.modifiers.new('StrapLeatherThickness','SOLIDIFY');m.thickness=.0015;apply(strap,m);normals(strap);parts.append(strap)
for sign in [-1,1]:
    a=sign*1.28;bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.0035,location=(.096*math.sin(a),cy-.115*math.cos(a),1.763))
    o=bpy.context.object;o.name='Security_CapRivet';o.data.materials.append(materials['Security_Hardware']);parts.append(o)

# Cast silver shield badge, with a small raised SEC wordmark.
outline=[(-.013,1.800),(-.013,1.821),(0,1.826),(.013,1.821),(.013,1.800),(0,1.788)]
v=[(x,y,z) for y in [cy-.120,cy-.123] for x,z in outline];n=len(outline)
f=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
badge=make('Security_CapBadge',v,f,'Hardware');parts.append(badge)
curve=bpy.data.curves.new('Security_CapBadgeText','FONT');curve.body='SEC';curve.align_x='CENTER';curve.size=.006;curve.extrude=.00035;curve.resolution_u=3
text=bpy.data.objects.new('Security_CapBadgeText',curve);bpy.context.collection.objects.link(text);active(text);bpy.ops.object.convert(target='MESH');text=bpy.context.object
for p in text.data.vertices:p.co=Vector((p.co.x,cy-.124-p.co.z,1.804+p.co.y))
text.data.materials.append(materials['Security_Trim']);parts.append(text)

# Apply all per-part transforms, then join only visible cap geometry.
for o in parts:
    active(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=crown;bpy.ops.object.join();cap=bpy.context.object;cap.name='SM_SecurityServiceCap_V11'
normals(cap)
# Unwrap each small rigid prop part without changing existing clothing UVs.
active(cap);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')

# Two authored convex bodies for Chaos: crown and visor. They are not rendered.
colliders=[]
for num,points in enumerate([
    [(rx*math.sin(2*math.pi*i/24),cy-ry*math.cos(2*math.pi*i/24),z) for rx,ry,z in [(.091,.108,1.745),(.100,.118,1.800),(.089,.104,1.836),(.033,.040,1.855)] for i in range(24)],
    [(v[0],v[1],v[2]+dz) for v in [tuple(x.co) for x in visor.data.vertices] for dz in [0]] if bpy.data.objects.get('Security_CapVisor') else
    [(math.sin(a)*(.087+.008*t),cy-math.cos(a)*(.105+.066*t),1.748-.013*t-.010*math.sin(a)**2+dz) for t in [0,1] for a in np.linspace(-1.43,1.43,20) for dz in [0,-.0035]]
]):
    me=bpy.data.meshes.new('CapConvex');me.from_pydata(points,[],[]);bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new('UCX_'+cap.name+'_%02d'%num,me);bpy.context.collection.objects.link(o);o.hide_render=True;colliders.append(o)

ref=json.loads((ROOT/'neck_source.json').read_text(encoding='utf-8'))['ue_head_reference']
q=ref['rotation_xyzw'];rotation=Quaternion((q[3],q[0],q[1],q[2]));origin=Vector(ref['translation_cm'])
pivot_author=Vector((0,cy,1.791));pivot_ue=Vector((pivot_author.x*100,-pivot_author.y*100,pivot_author.z*100))
local_pivot=rotation.inverted()@(pivot_ue-origin)
# Store editable cap in anatomical author space as well as engine-local delivery.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/SecurityServiceCap_Anatomical_V11.blend'))
for o in [cap]+colliders:
    for v in o.data.vertices:
        p=v.co;ue=Vector((p.x*100,-p.y*100,p.z*100));local=rotation.inverted()@(ue-origin)-local_pivot
        v.co=Vector((local.x,-local.y,local.z))/100
    normals(o)
active(cap)
for o in colliders:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/SecurityServiceCap_EngineLocal_V11.blend'))
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery/SM_SecurityServiceCap_V11.fbx'),use_selection=True,object_types={'MESH'},
    add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',use_mesh_modifiers=True)
report['hat']={'mesh_name':cap.name,'attachment_bone':'head','relative_location_cm':list(local_pivot),'relative_rotation_degrees':[0,0,0],
    'triangles':sum(len(f.vertices)-2 for f in cap.data.polygons),'convex_collision_bodies':len(colliders),
    'materials':[m.name for m in cap.data.materials],'mass_kg':.32,'dropped_lifetime_seconds':35,
    'design':'low navy service crown, black leather visor and band, silver shield, SEC wordmark'}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_V11_NECK_AND_CAP_AUTHORED '+json.dumps(report),flush=True)
