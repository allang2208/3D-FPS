"""Rebuild coherent robe panels and cuffs around the unchanged V12 anatomy.

This is garment authoring, not animation playback or a simulation acceptance run.
The robe follows torso support; independent donor legs pass through eased openings.
"""
from pathlib import Path
import bpy, bmesh, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT = ROOT/'GarmentContinuityV14'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SurfaceFitV12/BoundCongregate_SurfaceFitV12.blend'))
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['BC_Flesh']
body.data.calc_loop_triangles()
positions = np.array([v.co[:] for v in body.data.vertices])
triangles = [tuple(t.vertices) for t in body.data.loop_triangles]
names = [b.name for b in rig.data.bones]
indices = {n:i for i,n in enumerate(names)}
weights = np.zeros((len(positions), len(names)))
for v in body.data.vertices:
    for group in v.groups:
        name = body.vertex_groups[group.group].name
        if name in indices:
            weights[v.index, indices[name]] = group.weight
all_tree = BVHTree.FromPolygons(positions.tolist(), triangles, all_triangles=True)
torso_names = ['body', 'body_front', 'body_rear']
root_names = [f'attack_tentacle_{i:02d}' for i in range(4)]

def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)

def tree_for(allowed):
    influence = weights[:, [indices[n] for n in allowed]].sum(axis=1)
    faces = [t for t in triangles if influence[list(t)].mean() > .55]
    return BVHTree.FromPolygons(positions.tolist(), faces, all_triangles=True), faces

def support_at(p, tree, faces, allowed):
    q, normal, face, distance = tree.find_nearest(Vector(p))
    ids = faces[face]
    bary = np.clip(np.array(barycentric_transform(q, *[Vector(positions[i]) for i in ids],
                   Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1)))), 0, 1)
    bary /= max(1e-8, bary.sum())
    field = bary @ weights[list(ids)]
    field[[i for i,n in enumerate(names) if n not in allowed]] = 0
    field /= field.sum()
    return field

def ray_radius(tree, origin, direction, fallback):
    # Use the outer exit of the selected anatomy, never a nearest-point jump
    # from the torso to a neighbouring hand or leg.
    start = Vector(origin)
    direction = Vector(direction)
    result = None
    walked = 0.
    for _ in range(24):
        q, normal, face, distance = tree.ray_cast(start, direction, 2.5-walked)
        if q is None:
            break
        walked = (q-Vector(origin)).dot(direction)
        if normal.dot(direction) > .05:
            result = walked
        start = q + direction*.0005
        walked += .0005
        if walked > 2.49:
            break
    return result if result is not None and result > .035 else fallback

def blur_grid(values, passes, wrap=False):
    values = values.copy()
    for _ in range(passes):
        padded = np.pad(values, ((1,1),(0,0)), mode='edge')
        vertical = (padded[:-2]+padded[2:])*.5
        if wrap:
            horizontal = (np.roll(values,1,axis=1)+np.roll(values,-1,axis=1))*.5
        else:
            padded = np.pad(values, ((0,0),(1,1)), mode='edge')
            horizontal = (padded[:,:-2]+padded[:,2:])*.5
        values = .4*values + .3*(vertical+horizontal)
    return values

def assign(ob, fields):
    ob.vertex_groups.clear()
    for n in names:
        ob.vertex_groups.new(name=n)
    for i, field in enumerate(fields):
        ids = np.argsort(field)[-8:]
        total = field[ids].sum()
        for j in ids:
            if field[j] > 1e-7:
                ob.vertex_groups[int(j)].add([i], float(field[j]/total), 'REPLACE')

report = {'revision':'GarmentContinuityV14', 'gameplay_tested':False,
          'source':'SurfaceFitV12', 'garments':{},
          'preserved':'flesh, UVs, skeleton, tentacle fork and actions',
          'construction':'continuous radial panels; torso-only skin; separate fitted cuffs'}

def create_pair(name, points, faces, uv_values, fields, travel):
    visible = bpy.data.objects[name]
    proxy = bpy.data.objects[name+'_SimulationProxy']
    material = visible.data.materials[0]
    proxy_material = proxy.data.materials[0]
    # Retain a connected piece of cloth. Sampling anatomical openings must
    # not leave isolated scraps or two surfaces joined at a single point.
    edge_faces = {}
    for fi,face in enumerate(faces):
        for a,b in zip(face, face[1:]+face[:1]):
            edge_faces.setdefault(tuple(sorted((a,b))), []).append(fi)
    links = [set() for _ in faces]
    for attached in edge_faces.values():
        for fi in attached:links[fi].update(set(attached)-{fi})
    remaining=set(range(len(faces)));components=[]
    while remaining:
        seed=remaining.pop();component={seed};queue=[seed]
        while queue:
            neighbours=links[queue.pop()] & remaining
            remaining.difference_update(neighbours);component.update(neighbours);queue.extend(neighbours)
        components.append(component)
    keep=max(components,key=len)
    faces=[face for fi,face in enumerate(faces) if fi in keep]
    # Compact unused samples from designed arm/leg openings; do not delete
    # collapsed triangles from an already distorted garment to hide problems.
    used = sorted({i for face in faces for i in face})
    remap = {old:new for new,old in enumerate(used)}
    points = points[used]
    fields = fields[used]
    travel = np.array(travel)[used]
    uv_values = np.array(uv_values)[used]
    faces = [tuple(remap[i] for i in face) for face in faces]
    # Ease the sampled aperture edges into continuous rounded borders.
    edges={}
    for face in faces:
        for a,b in zip(face, face[1:]+face[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
    border_links=[[] for _ in points]
    for (a,b),count in edges.items():
        if count==1:border_links[a].append(b);border_links[b].append(a)
    for _ in range(5):
        updated=points.copy()
        for i,near in enumerate(border_links):
            if len(near)==2:updated[i]=points[i]*.7+points[near].mean(axis=0)*.3
        points=updated
    mesh = bpy.data.meshes.new(name+'_ContinuousV14')
    mesh.from_pydata(points.tolist(), [], faces)
    mesh.update()
    proxy.data = mesh
    mesh.materials.append(proxy_material)
    uv = mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for li in polygon.loop_indices:
            uv.data[li].uv = uv_values[mesh.loops[li].vertex_index]
    # Weight interpolation is performed on connected fabric, after anatomy
    # selection. It cannot introduce weights from a different donor limb.
    links = [[] for _ in points]
    for edge in mesh.edges:
        a,b = edge.vertices
        links[a].append(b); links[b].append(a)
    for _ in range(14):
        fields = np.array([.7*w + .3*np.mean(fields[links[i]], axis=0) if links[i] else w
                           for i,w in enumerate(fields)])
    assign(proxy, fields)
    color = mesh.color_attributes.new(name='ClothTravel', type='FLOAT_COLOR', domain='POINT')
    uses = {}
    for face in faces:
        for a,b in zip(face, face[1:]+face[:1]):
            edge = tuple(sorted((a,b))); uses[edge] = uses.get(edge,0)+1
    boundary = set(i for edge,count in uses.items() if count == 1 for i in edge)
    # Colour channels retain the V8 woven/worn material contract.
    for i,p in enumerate(points):
        edge = 0. if i in boundary else .65
        color.data[i].color = (float(travel[i]/.45), edge, float(1-smooth(.55,1.1,p[2])), 1)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    facing = 0.
    for face in bm.faces:
        q,n,_,_ = all_tree.find_nearest(face.calc_center_median())
        facing += face.normal.dot(n)*face.calc_area()
    if facing < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    # Triangulate a well-spaced surface once, shared by render and simulation.
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free(); mesh.update()
    visible.data = mesh.copy()
    visible.data.materials.clear(); visible.data.materials.append(material)
    assign(visible, fields)
    bpy.ops.object.select_all(action='DESELECT')
    visible.select_set(True); bpy.context.view_layer.objects.active = visible
    shell = visible.modifiers.new('Continuous outward 3mm fabric V14', 'SOLIDIFY')
    shell.thickness = .003; shell.offset = 1; shell.use_even_offset = False
    shell.thickness_clamp = .5
    bpy.ops.object.modifier_apply(modifier=shell.name)
    for polygon in visible.data.polygons:
        polygon.use_smooth = True
    report['garments'][name] = {'proxy_vertices':len(points), 'triangles':len(mesh.polygons),
                               'connected_pieces':1,
                               'max_travel_cm':float(travel.max()*100),
                               'influence_bones':[n for i,n in enumerate(names) if fields[:,i].max()>.001]}
    print(name, json.dumps(report['garments'][name]), flush=True)

def make_panel(name, side, y0, y1, theta0, theta1, nx, ny):
    allowed = torso_names + (root_names if side > 0 else [])
    tree, surface_faces = tree_for(allowed)
    v,u = np.mgrid[0:ny+1,0:nx+1].astype(float)
    u /= nx; v /= ny
    y = y0+(y1-y0)*u
    # Low-frequency irregularity preserves a worn edge without needle teeth.
    hem = .035*np.sin(u*math.tau*2+.7)+.018*np.sin(u*math.tau*5)
    theta = theta0+(theta1-theta0)*v+hem*smooth(.78,1,v)
    direction = np.stack((side*np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
    origin = np.stack((np.zeros_like(y),y,np.full_like(y,.8373)),axis=-1)
    radii = np.empty_like(y)
    for r in range(ny+1):
        for c in range(nx+1):
            radii[r,c] = ray_radius(tree, origin[r,c], direction[r,c], .77)
    # Bridge small pustules with a fabric envelope, keeping all points on a
    # regular radial parameterization instead of collapsing onto creases.
    padded = np.pad(radii,1,mode='edge')
    envelope = np.maximum.reduce([padded[a:a+ny+1,b:b+nx+1] for a in range(3) for b in range(3)])
    envelope = blur_grid(envelope,10)
    envelope = np.maximum(envelope,radii+.006)
    envelope = blur_grid(envelope,3)+.030
    fold = .009*np.sin(u*math.tau*4.5+v*.8)*np.sin(v*math.pi)**2
    points = origin+direction*(envelope+fold)[...,None]
    # The garment ends beside the upper legs, rather than forming taut webs
    # that connect their independently animated knees.
    points[:,:,2] = np.maximum(points[:,:,2], .66+.025*np.sin(u*math.tau*3))
    flat = points.reshape(-1,3)
    fields = np.array([support_at(p,tree,surface_faces,allowed) for p in flat])
    # Use the donor's actual skin to lay out openings. A capsule enclosing an
    # irregular fused limb would remove whole rows of otherwise valid fabric.
    opening = np.full(len(flat), .20)
    donor_indices = [i for i,n in enumerate(names) if n.startswith('leg_')]
    for i,p in enumerate(flat):
        q,n,f,d = all_tree.find_nearest(Vector(p))
        donor_weight = weights[list(triangles[f])][:,donor_indices].sum(axis=1).mean()
        if donor_weight > .42:
            opening[i] = min(.20, (Vector(p)-q).dot(n)-.045)
    opening = blur_grid(opening.reshape(ny+1,nx+1),3).ravel()
    face_list = []
    for r in range(ny):
        for c in range(nx):
            i=r*(nx+1)+c
            face=(i,i+1,i+nx+2,i+nx+1)
            if min(opening[list(face)]) < 0:
                continue
            face_list.append(face)
    release = smooth(.14,.64,v.ravel())
    travel = .032*release*(.5+.5*smooth(.015,.10,np.maximum(0,opening)))
    travel[travel < .0075] = 0
    create_pair(name, flat, face_list, np.column_stack((u.ravel()*1.8,v.ravel()*1.6)), fields, travel)

make_panel('BC_LeftTornRobe',-1,-.47,.78,.55,1.82,48,40)
make_panel('BC_RightLining',1,.11,.96,.80,1.81,36,36)

def make_cuff(name, stem):
    allowed = [stem+s for s in ('upper','lower','foot')]
    tree, surface_faces = tree_for(allowed)
    bone = rig.data.bones[stem+'lower']
    a,b = np.array(bone.head_local),np.array(bone.tail_local)
    axis = (b-a)/np.linalg.norm(b-a)
    x = np.cross(axis,(0,0,1)); x /= np.linalg.norm(x)
    z = np.cross(axis,x); z /= np.linalg.norm(z)
    nu,nv = 40,18
    v,u = np.mgrid[0:nv+1,0:nu].astype(float)
    u /= nu; v /= nv
    along = .18+.47*v + .009*np.sin(u*math.tau*4)*smooth(.85,1,v)
    origin = a+(b-a)*along[...,None]
    directions = np.cos(u*math.tau)[...,None]*x+np.sin(u*math.tau)[...,None]*z
    radii = np.empty_like(u)
    for r in range(nv+1):
        for c in range(nu):
            radii[r,c] = ray_radius(tree,origin[r,c],directions[r,c],.11)
    radii = np.maximum(blur_grid(radii,8,True),radii+.003)
    radii = blur_grid(radii,2,True)+.022
    points = (origin+directions*radii[...,None]).reshape(-1,3)
    fields = np.array([support_at(p,tree,surface_faces,allowed) for p in points])
    faces=[]
    for r in range(nv):
        for c in range(nu):
            j=(c+1)%nu
            faces.append((r*nu+c,r*nu+j,(r+1)*nu+j,(r+1)*nu+c))
    travel=.012*smooth(.72,1,v.ravel());travel[travel<.0075]=0
    create_pair(name,points,faces,np.column_stack((u.ravel(),v.ravel()*.6)),fields,travel)
    # Cylinder seam is a UV seam only; the geometry stays welded.
    for ob in (bpy.data.objects[name],bpy.data.objects[name+'_SimulationProxy']):
        uv=ob.data.uv_layers.active
        for polygon in ob.data.polygons:
            values=[uv.data[li].uv.x for li in polygon.loop_indices]
            if max(values)-min(values)>.5:
                for li in polygon.loop_indices:
                    if uv.data[li].uv.x<.5:uv.data[li].uv.x+=1

make_cuff('BC_DonorSleeve1','leg_L2_')
make_cuff('BC_DonorSleeve8','leg_R4_')

# The leather restraint and its plate use the same supported cloth surface.
robe=bpy.data.objects['BC_LeftTornRobe_SimulationProxy'];robe.data.calc_loop_triangles()
rp=[v.co.copy() for v in robe.data.vertices];rt=[tuple(t.vertices) for t in robe.data.loop_triangles]
robe_tree=BVHTree.FromPolygons(rp,rt,all_triangles=True)
torso_tree,torso_faces=tree_for(torso_names)
strap=bpy.data.objects['BC_ShoulderRestraint'];half=len(strap.data.vertices)//2
old=np.array([v.co[:] for v in strap.data.vertices]);strap_fields=np.zeros((len(old),len(names)))
for i in range(half):
    p=Vector((old[i]+old[i+half])*.5)
    q,n,face,d=robe_tree.find_nearest(p)
    if d>.18:
        q,n,face,d=torso_tree.find_nearest(p)
        q+=n*.03
    center=q+n*.01
    field=support_at(center,torso_tree,torso_faces,torso_names)
    width=min(.008,float(np.linalg.norm(old[i]-old[i+half])))
    strap.data.vertices[i].co=center+n*width*.5
    strap.data.vertices[i+half].co=center-n*width*.5
    strap_fields[i]=strap_fields[i+half]=field
assign(strap,strap_fields);strap.data.update()
plate=bpy.data.objects['BC_M_Tag'];stamp=bpy.data.objects['BC_M_Stamp']
center=sum((v.co for v in plate.data.vertices),Vector())/len(plate.data.vertices)
strap.data.calc_loop_triangles()
strap_tree=BVHTree.FromPolygons([v.co[:] for v in strap.data.vertices],
                             [tuple(t.vertices) for t in strap.data.loop_triangles],all_triangles=True)
q,n,_,_=strap_tree.find_nearest(center)
_,outward,_,_=all_tree.find_nearest(q)
if n.dot(outward)<0:n=-n
shift=q+n*.012-center
field=support_at(q,torso_tree,torso_faces,torso_names)
for ob in (plate,stamp):
    for v in ob.data.vertices:v.co+=shift
    assign(ob,np.tile(field,(len(ob.data.vertices),1)));ob.data.update()

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_GarmentContinuityV14.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_SurfaceFitV12_GarmentV14.fbx'),
    use_selection=True, object_types={'MESH','ARMATURE'}, axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BOUND_CONGREGATE_GARMENT_V14_EXPORTED',flush=True)
