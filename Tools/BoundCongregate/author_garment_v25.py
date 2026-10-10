"""Build a skinned garment, covered-body cut, and short simulated hems.

The fitted opaque core follows the original body skin. Only its outer hem is
cloth. Body faces safely inside that core are omitted in this derived outfit,
with overlap margins and compatible skin support; the complete source is kept.
"""
from pathlib import Path
import json
import math
import heapq
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT = ROOT / 'GarmentDrapeV25'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GarmentRebuildV19/BoundCongregate_GarmentRebuildV19.blend'))
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
if rig.animation_data:
    rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
rig.data.pose_position = 'REST'
body = bpy.data.objects['BC_Flesh']
body.data.calc_loop_triangles()
P = np.asarray([v.co[:] for v in body.data.vertices], dtype=np.float64)
T = np.asarray([tuple(t.vertices) for t in body.data.loop_triangles], dtype=np.int32)
names = [b.name for b in rig.data.bones]
index = {n:i for i,n in enumerate(names)}
W = np.zeros((len(P), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        name = body.vertex_groups[group.group].name
        if name in index:
            W[vertex.index, index[name]] = group.weight
flesh_faces = [tuple(t.vertices) for t in body.data.loop_triangles
               if body.data.materials[body.data.polygons[t.polygon_index].material_index].name == 'BC_Flesh']
flesh_tree = BVHTree.FromPolygons(P.tolist(), flesh_faces, all_triangles=True)
materials = {m.name:m for m in bpy.data.materials}
for obj in list(scene.objects):
    if obj.type == 'MESH' and obj.name not in ('BC_Flesh', 'BC_M_Tag', 'BC_M_Stamp'):
        bpy.data.objects.remove(obj, do_unlink=True)

report = dict(revision='GarmentDrapeV25', rendered=False, gameplay_tested=False,
              source='GarmentRebuildV19 anatomy only', garments={}, materials={},
              construction='skinned fitted core, covered-body cut with overlap, short independent simulated hem',
              vertex_channels='R travel/45cm, G interior-to-wear, B hem dirt, A attachment drive; UV1.x body contact')
collision_recipe = dict(revision='GarmentDrapeV25', coordinates='UE mesh centimetres', garments={})
outfit_cores=[]


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0., 1.)
    return t*t*(3.-2.*t)


def anatomy_weights(point, tree=flesh_tree, faces=flesh_faces, allowed=None):
    q, normal, face, _ = tree.find_nearest(Vector(point))
    ids = faces[face]
    bary = np.clip(np.asarray(barycentric_transform(q, *[Vector(P[j]) for j in ids],
                      Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1)))), 0., 1.)
    weights = (bary/max(bary.sum(), 1.e-8)) @ W[list(ids)]
    if allowed is not None:
        weights[[i for i,n in enumerate(names) if n not in allowed]] = 0.
    if weights.sum() < 1.e-8:
        raise RuntimeError('No anatomical garment support at '+str(point))
    return weights/weights.sum()


def skin(obj, weights):
    obj.vertex_groups.clear()
    for name in names:
        obj.vertex_groups.new(name=name)
    for i, values in enumerate(weights):
        ids = np.argsort(values)[-8:]
        total = values[ids].sum()
        for j in ids:
            if values[j] > 1.e-7:
                obj.vertex_groups[int(j)].add([i], float(values[j]/total), 'REPLACE')
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    modifier = obj.modifiers.new('Original anatomy rig', 'ARMATURE')
    modifier.object = rig


def quads(nx, ny, wrap=False):
    width = nx if wrap else nx+1
    return [(r*width+c, r*width+(c+1)%width,
             (r+1)*width+(c+1)%width, (r+1)*width+c)
            for r in range(ny) for c in range(nx)]


def mesh(name, points, faces, uv_values, weights, material, travel, drive, wear):
    data = bpy.data.meshes.new(name)
    data.from_pydata(points.tolist(), [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    data.materials.append(material)
    layer = data.uv_layers.new(name='UVMap')
    for polygon in data.polygons:
        polygon.use_smooth = True
        for li in polygon.loop_indices:
            layer.data[li].uv = uv_values[data.loops[li].vertex_index]
    colors = data.color_attributes.new(name='ClothTravel', type='FLOAT_COLOR', domain='POINT')
    for i,p in enumerate(points):
        colors.data[i].color = (float(travel[i]/.45), float(wear[i]),
                               float(1.-smooth(.60,1.25,p[2])), float(drive[i]))
    data.color_attributes.active_color = colors
    data.color_attributes.render_color_index = 0
    skin(obj,weights)
    return obj


def pair(name, slot, points, faces, uv_values, weights, travel, drive, wear, contact, wrap=False):
    proxy_material = bpy.data.materials.get(slot+'_Proxy') or bpy.data.materials.new(slot+'_Proxy')
    proxy = mesh(name+'_SimulationProxy',points,faces,uv_values,weights,proxy_material,travel,drive,wear)
    bm = bmesh.new()
    bm.from_mesh(proxy.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.normal_update()
    facing = 0.
    for face in bm.faces:
        q,n,_,_ = flesh_tree.find_nearest(face.calc_center_median())
        facing += face.normal.dot(n)*face.calc_area()
    if facing < 0.:
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    # Triangulate once, before copying. FBX cannot independently choose two
    # diagonals for the render and simulation descriptions of the same surface.
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY')
    bm.to_mesh(proxy.data)
    bm.free()
    if wrap:
        layer = proxy.data.uv_layers.active
        for polygon in proxy.data.polygons:
            values = [layer.data[i].uv.x for i in polygon.loop_indices]
            width = float(max(uv_values[:,0]))
            if max(values)-min(values) > width*.5:
                period = width*len(np.unique(uv_values[:,0]))/(len(np.unique(uv_values[:,0]))-1)
                for li in polygon.loop_indices:
                    if layer.data[li].uv.x < width*.5:
                        layer.data[li].uv.x += period
    contact_layer=proxy.data.uv_layers.new(name='BodyContact')
    for polygon in proxy.data.polygons:
        for li in polygon.loop_indices:
            contact_layer.data[li].uv=(float(contact[proxy.data.loops[li].vertex_index]),0.)
    proxy.data.uv_layers.active_index=0
    proxy.data.uv_layers[0].active_render=True
    visible = proxy.copy()
    visible.data = proxy.data.copy()
    visible.name = name
    scene.collection.objects.link(visible)
    visible.data.materials.clear()
    visible.data.materials.append(materials[slot])
    # No independent subdivision shrink or thin, extrapolated render-only rim.
    # The two-sided fabric keeps the cut edge on the simulated surface itself.
    for polygon in visible.data.polygons:
        polygon.use_smooth = True
    # One metric UV chart: one unit is one metre for every newly cut garment.
    # Witch's two tiling values will be identical, so Alpha remains Anim Drive.
    visible.data.calc_loop_triangles()
    layer = visible.data.uv_layers.active
    area = sum(t.area for t in visible.data.loop_triangles)
    uv_area = 0.
    for t in visible.data.loop_triangles:
        a,b,c = [layer.data[i].uv for i in t.loops]
        uv_area += abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
    tiling = math.sqrt(area/max(uv_area,1.e-10))/.04
    report['materials'][slot] = dict(weave_tiling=tiling, repair_weave_tiling=tiling,
                                   physical_tile_metres=.04, tint={'BC_RagFabric':[.092,.101,.071],
                                   'BC_SleeveLeft':[.075,.080,.063],
                                   'BC_SleeveRight':[.108,.092,.065]}[slot])
    report['garments'][name] = dict(proxy_vertices=len(points), render_vertices=len(visible.data.vertices),
                                 max_travel_cm=float(max(travel)*100),
                                 skinned_core_vertices=int(np.count_nonzero(travel==0.)),
                                 simulated_hem_vertices=int(np.count_nonzero(travel>0.)),
                                 support_bones=[n for i,n in enumerate(names) if weights[:,i].max()>.001])
    outfit_cores.append((proxy,weights.copy(),travel.copy()))
    proxy.hide_render = True
    return proxy,visible


def envelope(radius, wrap=False):
    """Smooth the cloth's radial obstacle from outside, spanning skin grooves."""
    obstacle=radius.copy()
    result=radius.copy()
    for _ in range(36):
        padded=np.pad(result,((1,1),(0,0)),mode='edge')
        horizontal=np.pad(result,((0,0),(1,1)),mode='wrap' if wrap else 'edge')
        average=(padded[:-2]+padded[2:]+horizontal[:,:-2]+horizontal[:,2:])*.25
        result=np.maximum(obstacle,result*.35+average*.65)
    return result


def surface_fields(points, tree=flesh_tree, faces=flesh_faces, allowed=None):
    """Contact and deformation refer to the same local piece of anatomy."""
    weights=np.array([anatomy_weights(p,tree,faces) for p in points])
    # Fold distal influences into their own anatomical parent. A feeler or a
    # foot must not tug a tiny isolated point of the back panel/sleeve.
    if allowed is not None:
        for i,name in enumerate(names):
            bone=rig.data.bones[name]
            while bone and bone.name not in allowed:
                bone=bone.parent
            if bone and bone.name!=name:
                weights[:,index[bone.name]]+=weights[:,i]
                weights[:,i]=0.
    gap=np.array([tree.find_nearest(Vector(p))[3] for p in points])
    contact=1.-smooth(.024,.065,gap)
    return weights,contact


def contact_balls(slot, proxy, columns, rows, width, radius):
    """Small inner supports follow local skin; no raw multi-shell inside test."""
    proxy.data.calc_loop_triangles()
    verts=[v.co for v in proxy.data.vertices]
    triangles=[tuple(t.vertices) for t in proxy.data.loop_triangles]
    cloth_tree=BVHTree.FromPolygons(verts,triangles,all_triangles=True)
    shapes=[]
    for row in rows:
        for column in columns:
            vertex=proxy.data.vertices[row*width+column]
            center=vertex.co-vertex.normal*(radius+.018)
            # Clip to this actual garment, not the nearest internal donor shell.
            fitted=min(radius,float(cloth_tree.find_nearest(center)[3])-.009)
            if fitted<=.008:
                continue
            support=max(vertex.groups,key=lambda group:group.weight)
            bone=proxy.vertex_groups[support.group].name
            convert=lambda p:(np.asarray(p)*np.array([100.,-100.,100.])).tolist()
            shapes.append(dict(bone=bone,a=convert(center),b=convert(center),radius_cm=fitted*100))
    collision_recipe['garments'][slot]=shapes


# Cut on a smooth outer envelope of the actual anatomical cross-sections.
nx,ny = 68,36
u = np.linspace(0.,1.,nx+1)
phi = np.deg2rad(-112.+160.*u)
seam = []
seam_normals = []
supports = []
for j,t in enumerate(u):
    z = 1.48+.075*math.sin(t*math.pi)-.035*smooth(.70,1.,t)+.04*smooth(.30,.65,t)
    origin = Vector((0.,.16,z))
    radial = Vector((math.sin(phi[j]),math.cos(phi[j]),0.))
    q,n,_,_ = flesh_tree.ray_cast(origin+radial*1.6,-radial,1.6)
    if q is None:
        raise RuntimeError('Shoulder seam misses anatomy at column '+str(j))
    # Transfer the real local shoulder skin. Ignore distal extremities; shoulder
    # donor roots may participate in their own attachment and are not global pins.
    allowed = [n for n in names if n in ('body','body_front','body_rear') or n.endswith('_upper')]
    weights = anatomy_weights(q,allowed=allowed)
    seam.append(np.asarray(q)+np.asarray(n)*.012)
    seam_normals.append(np.asarray(n))
    supports.append(weights)
seam = np.asarray(seam)
seam_normals = np.asarray(seam_normals)
supports = np.asarray(supports)
# Exact local seam skinning: smoothing donor roots moved the fixed edge away
# from its underlying skin in animated poses.
lengths = .40+.24*np.exp(-((u-.74)/.22)**2)
lengths += .10*smooth(.25,.55,u)
lengths += .018*np.sin(u*math.tau*2+.7)
# Wide scalloped damage at the existing free edge, not deleted triangles/islands.
lengths -= .055*np.exp(-((u-.31)/.085)**2)+.045*np.exp(-((u-.89)/.08)**2)
rows = np.linspace(0.,1.,ny+1)
radius=[]
heights=[]
for v in rows:
    for j,t in enumerate(u):
        radial=np.array([math.sin(phi[j]),math.cos(phi[j]),0.])
        z=seam[j,2]-lengths[j]*v
        origin=Vector((0.,.16,z))
        q,n,_,_=flesh_tree.ray_cast(origin+Vector(radial)*1.8,-Vector(radial),1.8)
        if q is None:
            r=float((seam[j]-np.asarray(origin))@radial)
        else:
            r=float((q-origin).dot(Vector(radial)))+.012
        radius.append(r)
        heights.append(z)
radius=envelope(np.asarray(radius).reshape(ny+1,nx+1))
vv,uu=np.meshgrid(rows,u,indexing='ij')
# Millimetre folds are broad and positive; they cannot dig into the skin.
radius+=.004*(.5+.5*np.sin(uu*math.tau*4.0+.3*vv))*np.sin(vv*math.pi)
# Leave real clearance for the small hem motion rather than simulating the
# entire fitted layer into the body. The core remains close to the skin.
radius+=.030*smooth(.75,1.,vv)
directions=np.column_stack((np.sin(phi),np.cos(phi),np.zeros_like(phi)))
grid=np.array([0.,.16,0.])+directions[None,:,:]*radius[...,None]
grid[:,:,2]=np.asarray(heights).reshape(ny+1,nx+1)
points=grid.reshape(-1,3)
faces=quads(nx,ny)
pinned=vv.ravel()==0.
fields,contact=surface_fields(points)
seam=grid[0].copy()
supports=fields[:nx+1].copy()
# Free hem uses a smoothly extended local carrier, avoiding discontinuous
# nearest-body choices across a gap. Contact zones keep their actual skin.
carrier=fields.reshape(ny+1,nx+1,-1).copy()
# The opaque core must retain the actual skin influences of the covered body.
# Only cloth beyond its last fixed row inherits the seam's carrier.
fixed_row=int(.78*ny)
for row in range(fixed_row+1,ny+1):
    carrier[row]=carrier[fixed_row]
fields=carrier.reshape(len(points),-1)
arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(seam,axis=0),axis=1))]
uv=np.column_stack((np.tile(arc,ny+1), (vv*lengths[None,:]).ravel()))
release=smooth(rows[fixed_row],1.,vv.ravel())
travel=.022*release
drive=1.-.8*release
wear=smooth(0.,.10,np.minimum.reduce((uu.ravel(),1.-uu.ravel(),1.-vv.ravel())))
mantle,_=pair('BC_HangingMantleV25','BC_RagFabric',points,faces,uv,fields,travel,drive,wear,contact)
seam_normals=np.array([v.normal[:] for v in mantle.data.vertices[:nx+1]])
contact_balls('BC_RagFabric',mantle,[8,25,43,60],[6,17,27],nx+1,.10)

# Leather attachment tape follows the pinned seam itself; the old badge is
# relocated as one rigid detail to that same local support.
grid=points.reshape(ny+1,nx+1,3)
strap_drop=grid[1]-grid[0]
strap_fraction=np.minimum(1.,.015/np.maximum(np.linalg.norm(strap_drop,axis=1),1.e-8))
strap_points=np.concatenate((grid[0]+seam_normals*.003,
                            grid[0]+strap_drop*strap_fraction[:,None]+seam_normals*.003))
strap_faces=[(j,j+1,nx+2+j,nx+1+j) for j in range(nx)]
strap_uv=np.array([(arc[j],r*.03) for r in range(2) for j in range(nx+1)])
strap_weights=np.concatenate((supports,supports*(1.-strap_fraction[:,None])+fields[nx+1:2*(nx+1)]*strap_fraction[:,None]))
mesh('BC_SeamTapeV25',strap_points,strap_faces,strap_uv,strap_weights,materials['BC_Binding'],
     np.zeros(len(strap_points)),np.ones(len(strap_points)),np.ones(len(strap_points))*.7)
tag=bpy.data.objects['BC_M_Tag']
stamp=bpy.data.objects['BC_M_Stamp']
oldcenter=sum((v.co for v in tag.data.vertices),Vector())/len(tag.data.vertices)
column=5
target=Vector(grid[0,column]+np.array([0.,0.,-.0075])+seam_normals[column]*.012)
# Use the existing plate normal, not a guessed orientation from a prior version.
tag.data.calc_loop_triangles()
normal=max(tag.data.polygons,key=lambda f:f.area).normal.copy()
if normal.x>0:normal=-normal
rotation=normal.rotation_difference(Vector(seam_normals[column]))
for obj in (tag,stamp):
    for vert in obj.data.vertices:
        vert.co=target+rotation@(vert.co-oldcenter)
    for mod in list(obj.modifiers):
        if mod.type=='ARMATURE':obj.modifiers.remove(mod)
    skin(obj,np.tile(supports[column],(len(obj.data.vertices),1)))


def sleeve(name, stem, slot):
    bone=rig.data.bones[stem+'lower']
    a,b=np.asarray(bone.head_local),np.asarray(bone.tail_local)
    axis=(b-a)/np.linalg.norm(b-a)
    x=np.cross(axis,(0,0,1));x/=np.linalg.norm(x)
    y=np.cross(axis,x)
    family=[index[n] for n in names if n.startswith(stem)]
    family_weight=W[:,family].sum(axis=1)
    longitudinal=(P-a)@axis
    radial_distance=np.linalg.norm(P-a-longitudinal[:,None]*axis,axis=1)
    local_surface=(family_weight>.30)&(radial_distance<.40)&(longitudinal>-.10)&(longitudinal<np.linalg.norm(b-a)+.10)
    faces_skin=[tuple(t) for t in T if np.count_nonzero(local_surface[t])>=2]
    tree=BVHTree.FromPolygons(P.tolist(),faces_skin,all_triangles=True)
    nx,ny=32,16
    vv,uu=np.mgrid[0:ny+1,0:nx].astype(float)
    vv/=ny;uu/=nx
    # Clearly readable sleeve with an uneven, broad hem; wrist remains bare.
    ends=.64+.018*np.sin(uu[0]*math.tau*2+.5)
    along=.20+(ends[None,:]-.20)*vv
    centers=a+(b-a)*along[...,None]
    directions=np.cos(uu*math.tau)[...,None]*x+np.sin(uu*math.tau)[...,None]*y
    radius=np.empty_like(vv)
    for r in range(ny+1):
        for c in range(nx):
            # The original donor bone is not always centred in its flesh. Fit
            # this cut to the actual anatomical cross-section before casting.
            distance=along[r,c]*np.linalg.norm(b-a)
            sample=P[local_surface&(np.abs(longitudinal-distance)<.035)]
            if len(sample)<8:
                raise RuntimeError('Missing anatomical sleeve cross-section '+stem)
            center=np.mean(sample,axis=0)
            centers[r,c]+=center-a-axis*((center-a)@axis)
            origin,direction=Vector(centers[r,c]),Vector(directions[r,c])
            q,_,_,_=tree.ray_cast(origin+direction*.55,-direction,.55)
            if q is None:
                radial_sample=sample-centers[r,c]
                radial_sample-=((radial_sample@axis)[:,None]*axis)
                length=np.linalg.norm(radial_sample,axis=1)
                facing=(radial_sample@directions[r,c])/np.maximum(length,1.e-8)
                near=np.argsort(facing)[-max(3,len(sample)//12):]
                radius[r,c]=float(np.quantile(length[near],.85))+.012
            else:
                radius[r,c]=max(.035,float((q-origin).dot(direction)))+.012
    radius=envelope(radius,wrap=True)
    radius+=.003*(.5+.5*np.sin(uu*math.tau*4.0+.4*vv))*np.sin(vv*math.pi)
    radius+=.022*smooth(.75,1.,vv)
    pp=(centers+directions*radius[...,None]).reshape(-1,3)
    ww,contact=surface_fields(pp,tree,faces_skin)
    fixed_row=int(.78*ny)
    skin_grid=ww.reshape(ny+1,nx,-1)
    skin_grid[fixed_row+1:]=skin_grid[fixed_row]
    ff=quads(nx,ny,True)
    circumference=math.tau*float(np.mean(radius))
    uv=np.column_stack((uu.ravel()*circumference,((along-.20)*np.linalg.norm(b-a)).ravel()))
    release=smooth(fixed_row/ny,1.,vv.ravel())
    proxy,_=pair(name,slot,pp,ff,uv,ww,.015*release,1.-.70*release,
         smooth(0.,.12,1.-vv.ravel()),contact,True)
    # A centred capsule is fitted against the authored sleeve interior. This
    # stays present even when the original donor mesh has overlapping shells.
    centerline=centers.mean(axis=1)
    ca,cb=centerline[2],centerline[-3]
    proxy.data.calc_loop_triangles()
    sleeve_tree=BVHTree.FromPolygons([v.co[:] for v in proxy.data.vertices],
        [tuple(t.vertices) for t in proxy.data.loop_triangles],all_triangles=True)
    clearance=min(float(sleeve_tree.find_nearest(Vector(ca+(cb-ca)*t))[3]) for t in np.linspace(0.,1.,17))
    convert=lambda p:(np.asarray(p)*np.array([100.,-100.,100.])).tolist()
    collision_recipe['garments'][slot]=[dict(bone=stem+'lower',a=convert(ca),b=convert(cb),
                                          radius_cm=max(.008,clearance-.018)*100)]


sleeve('BC_LeftSleeveV25','leg_L2_','BC_SleeveLeft')
sleeve('BC_RightSleeveV25','leg_R4_','BC_SleeveRight')


def cut_covered_body():
    """Outfit authoring: retain exposed anatomy and a covered edge allowance.

    Coverage is measured on the fixed cloth core, not on its moving hem. The
    original body's skin must agree with the cover's local carrier before a face
    is omitted; a separate crossing limb is not cut just because it is nearby.
    """
    covered=np.zeros(len(P),dtype=bool)
    for proxy,weights,travel in outfit_cores:
        proxy.data.calc_loop_triangles()
        vertices=np.array([v.co[:] for v in proxy.data.vertices])
        triangles=[tuple(t.vertices) for t in proxy.data.loop_triangles
                   if np.all(travel[list(t.vertices)]==0.)]
        tree=BVHTree.FromPolygons(vertices.tolist(),triangles,all_triangles=True)
        edges={}
        graph=[[] for _ in vertices]
        for tri in triangles:
            for a,b in zip(tri,(tri[1],tri[2],tri[0])):
                key=tuple(sorted((a,b)))
                edges[key]=edges.get(key,0)+1
        for a,b in edges:
            length=float(np.linalg.norm(vertices[a]-vertices[b]))
            graph[a].append((b,length));graph[b].append((a,length))
        boundary={v for edge,count in edges.items() if count==1 for v in edge}
        margin=np.full(len(vertices),np.inf)
        queue=[]
        for v in boundary:
            margin[v]=0.;heapq.heappush(queue,(0.,v))
        while queue:
            distance,v=heapq.heappop(queue)
            if distance>margin[v]:continue
            for other,length in graph[v]:
                candidate=distance+length
                if candidate<margin[other]:
                    margin[other]=candidate;heapq.heappush(queue,(candidate,other))
        candidates=np.flatnonzero(np.all((P>=vertices.min(axis=0)-.12)&(P<=vertices.max(axis=0)+.12),axis=1))
        for i in candidates:
            q,n,face,distance=tree.find_nearest(Vector(P[i]),.12)
            if q is None:continue
            ids=list(triangles[face])
            bary=np.clip(np.asarray(barycentric_transform(q,*[Vector(vertices[j]) for j in ids],
                Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0.,1.)
            bary/=max(float(bary.sum()),1.e-8)
            # Three centimetres of fixed opaque cover remains beyond the body
            # cut, before the additional fixed-to-simulated transition and hem.
            if float(bary@margin[ids])<.03:continue
            carrier=bary@weights[ids]
            if float(np.abs(carrier-W[i]).sum())>.45:continue
            covered[i]=True
    remove=[p.index for p in body.data.polygons
            if body.data.materials[p.material_index].name=='BC_Flesh'
            and all(covered[i] for i in p.vertices)]
    if not remove:
        raise RuntimeError('No covered body surface was authored; do not export the previous two-layer design')
    (OUT/'covered_body_faces.json').write_text(json.dumps(dict(
        source='GarmentRebuildV19/BC_Flesh',original_polygons=remove,
        fixed_core_overlap_metres=.03,maximum_skin_weight_l1_difference=.45)),encoding='utf8')
    bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[i] for i in remove],context='FACES')
    bm.to_mesh(body.data);bm.free();body.data.update()
    report['covered_body']=dict(removed_polygons=len(remove),retained_polygons=len(body.data.polygons),
        fixed_core_overlap_cm=3.,original_complete_body_retained=True,
        mode='outfit-only geometric omission, no runtime opacity or depth trick')
    print('V25 authored covered-body cut:',len(remove),'faces',flush=True)


cut_covered_body()


# Author-source shading uses the same Witch weave and parameter values as UE.
detail_root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Refinement20260922/Textures')
normal_files=[detail_root/'T_Witch_FabricDetail_N.png']
rough_files=[detail_root/'T_Witch_FabricDetail_R.png']
report['source_weave_textures']=[str(p) for p in normal_files+rough_files]
for slot,settings in report['materials'].items():
    mat=materials[slot];mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial')
    principled=nodes.new('ShaderNodeBsdfPrincipled')
    principled.inputs['Base Color'].default_value=(*settings['tint'],1)
    principled.inputs['Roughness'].default_value=.86
    principled.inputs['Specular IOR Level'].default_value=.20
    links.new(principled.outputs['BSDF'],output.inputs['Surface'])
    def math_node(operation,a,b):
        node=nodes.new('ShaderNodeMath');node.operation=operation
        for i,value in enumerate((a,b)):
            if isinstance(value,(int,float)):node.inputs[i].default_value=value
            else:links.new(value,node.inputs[i])
        return node.outputs[0]
    if normal_files and rough_files:
        uv=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='SCALE'
        mapping.inputs[3].default_value=settings['weave_tiling'];links.new(uv.outputs['UV'],mapping.inputs[0])
        for files,target in [(normal_files,'Normal'),(rough_files,'Roughness')]:
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(files[0]),check_existing=True)
            tex.image.colorspace_settings.name='Non-Color';links.new(mapping.outputs[0],tex.inputs['Vector'])
            if target=='Normal':
                split=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],split.inputs['Color'])
                invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1.
                links.new(split.outputs['Green'],invert.inputs[1])
                combine=nodes.new('ShaderNodeCombineColor')
                links.new(split.outputs['Red'],combine.inputs['Red']);links.new(invert.outputs[0],combine.inputs['Green'])
                links.new(split.outputs['Blue'],combine.inputs['Blue'])
                normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.32
                links.new(combine.outputs[0],normal.inputs['Color']);links.new(normal.outputs[0],principled.inputs[target])
            else:
                deviation=math_node('SUBTRACT',tex.outputs['Color'],.75)
                rough=math_node('ADD',.86,math_node('MULTIPLY',deviation,.22))
                links.new(rough,principled.inputs[target])
                vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='ClothTravel'
                channels=nodes.new('ShaderNodeSeparateColor');links.new(vertex.outputs['Color'],channels.inputs[0])
                multiplier=math_node('MULTIPLY',math_node('ADD',1.,math_node('MULTIPLY',deviation,.50)),
                                     math_node('SUBTRACT',1.,math_node('MULTIPLY',channels.outputs['Blue'],.20)))
                color=nodes.new('ShaderNodeVectorMath');color.operation='SCALE';color.inputs[0].default_value=settings['tint']
                links.new(multiplier,color.inputs['Scale'])
                edge=math_node('POWER',math_node('SUBTRACT',1.,channels.outputs['Green']),2.)
                wear=nodes.new('ShaderNodeVectorMath');wear.operation='SCALE';wear.inputs[0].default_value=(.018,.016,.010)
                links.new(edge,wear.inputs['Scale'])
                final=nodes.new('ShaderNodeVectorMath');final.operation='ADD'
                links.new(color.outputs[0],final.inputs[0]);links.new(wear.outputs[0],final.inputs[1])
                links.new(final.outputs[0],principled.inputs['Base Color'])

(OUT/'collision_recipe.json').write_text(json.dumps(collision_recipe,indent=2),encoding='utf8')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
rig.data.pose_position='POSE'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_GarmentDrapeV25.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj.type in ('MESH','ARMATURE'):
        obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_GarmentDrapeV25.fbx'),
    use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP',
    colors_type='SRGB',prioritize_active_color=True)
print('GARMENT_V25_SOURCE_EXPORTED '+json.dumps(report),flush=True)
