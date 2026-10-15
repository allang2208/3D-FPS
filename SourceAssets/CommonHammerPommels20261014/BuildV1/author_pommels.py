"""Author three solid pommels around the original warhammer mounting section."""
import bpy, bmesh, json, math, runpy
import numpy as np
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
OPTIONS = runpy.run_path(str(P/'catalog.py'))['OPTIONS']
for folder in ('Export', 'Textures', 'Icons', 'IconSources'):
    (P/folder).mkdir(exist_ok=True)
SOURCE = ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'
with bpy.data.libraries.load(str(SOURCE), link=False) as (a, b):
    b.objects = ['SM_Warhammer_pommel_factory']
factory = b.objects[0]
original = factory.data
original.calc_loop_triangles()
mount = list(factory.location)
old = original.materials[0]
with bpy.data.libraries.load(str(ROOT/'SourceAssets/CommonHammerSeats20261014/BuildV1/CommonHammerSeats_Editable.blend'), link=False) as (a, b):
    b.materials = ['M_CommonHammerHeadSteel', 'M_CommonHammerSeatDarkSteel']
steel, dark = b.materials
for obj in list(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1

# Subtle concentric machining relief, with finite slopes in tangent space.
size = 1024
yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
x = (xx+.5)/size-.5
y = (yy+.5)/size-.5
r = np.sqrt(x*x+y*y)
height = .0000018*np.sin(r*math.tau*72) + .0000006*np.sin(r*math.tau*143)
dy, dx = np.gradient(height, .064/size)
normal = np.stack((-dx, -dy, np.ones_like(dx)), axis=-1)
normal /= np.linalg.norm(normal, axis=-1)[..., None]
rough = np.clip(.38+.025*np.sin(r*math.tau*72)+.015*np.sin(xx*.07+yy*.04), .3, .46)
images = {}
for channel, rgb in [('Normal', normal*.5+.5), ('ORM', np.stack((np.ones_like(r), rough, np.ones_like(r)*.98), axis=-1))]:
    name = 'T_HammerPommelTurned_'+channel
    im = bpy.data.images.new(name, width=size, height=size, alpha=True)
    im.colorspace_settings.name = 'Non-Color'
    rgba = np.concatenate((rgb, np.ones((size,size,1), dtype=np.float32)), axis=-1)
    im.pixels.foreach_set(rgba.astype(np.float32).ravel())
    im.filepath_raw = str(P/'Textures'/(name+'.png'))
    im.file_format = 'PNG'
    im.save()
    images[channel] = im
turned = bpy.data.materials.new('M_CommonHammerPommelTurned')
turned.use_nodes = True
n = turned.node_tree.nodes
l = turned.node_tree.links
bs = n.get('Principled BSDF')
bs.inputs['Base Color'].default_value = (.32, .32, .32, 1)
bs.inputs['Metallic'].default_value = .98
uv = n.new('ShaderNodeUVMap')
uv.uv_map = 'SteelUV'
samples = {}
for channel, im in images.items():
    node = n.new('ShaderNodeTexImage'); node.image = im
    l.new(uv.outputs[0], node.inputs['Vector']); samples[channel] = node
sep = n.new('ShaderNodeSeparateColor')
l.new(samples['ORM'].outputs['Color'], sep.inputs[0]); l.new(sep.outputs['Green'], bs.inputs['Roughness'])
nm = n.new('ShaderNodeNormalMap'); nm.uv_map = 'SteelUV'
l.new(samples['Normal'].outputs['Color'], nm.inputs['Color']); l.new(nm.outputs[0], bs.inputs['Normal'])
MATS = [old, steel, dark, turned]
CUT = -.012
CX, CY = -.00088, -.00094
TILE = .12

def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj

def clip(poly):
    out = []
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db = a[0].z-CUT,b[0].z-CUT
        if da>=0: out.append(a)
        if (da>=0)!=(db>=0): out.append(tuple(x.lerp(y,da/(da-db)) for x,y in zip(a,b)))
    return out

# Interpolate and retain original UVs and corner normals at the new lower cut.
verts, faces, corner_uv, corner_n = [], [], [], []
for tri in original.loop_triangles:
    poly = [(original.vertices[original.loops[i].vertex_index].co.copy(), original.uv_layers[0].data[i].uv.copy(), original.corner_normals[i].vector.copy()) for i in tri.loops]
    p = clip(poly)
    for i in range(1,len(p)-1):
        t = [p[0],p[i],p[i+1]]
        if (t[1][0]-t[0][0]).cross(t[2][0]-t[0][0]).length<1e-12: continue
        faces.append(tuple(range(len(verts),len(verts)+3)))
        for co,uv0,no in t: verts.append(co); corner_uv.append(uv0); corner_n.append(no)
connector = bpy.data.meshes.new('Original mounting section')
connector.from_pydata(verts,[],faces); connector.update()
for mat in MATS: connector.materials.append(mat)
u0 = connector.uv_layers.new(name='UVMap'); u1 = connector.uv_layers.new(name='SteelUV')
stored = connector.attributes.new('FactoryNormal',type='FLOAT_VECTOR',domain='CORNER')
col = connector.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for poly in connector.polygons:
    poly.use_smooth = True
    for k in poly.loop_indices:
        i = connector.loops[k].vertex_index
        u0.data[k].uv = corner_uv[i]; u1.data[k].uv = corner_uv[i]
        stored.data[k].vector = corner_n[i]; col.data[k].color = (0,0,0,1)
bm = bmesh.new(); bm.from_mesh(connector)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
# Follow real connected boundary edges instead of assuming a circular vertex sort.
edges = {e for e in bm.edges if e.is_boundary and all(abs(v.co.z-CUT)<1e-6 for v in e.verts)}
rings = []
while edges:
    edge = next(iter(edges)); edges.remove(edge)
    start, current = edge.verts
    path = [start, current]
    while current != start:
        next_edge = next((e for e in current.link_edges if e in edges), None)
        if next_edge is None: raise RuntimeError('Mounting section has an open chain')
        edges.remove(next_edge); current = next_edge.other_vert(current)
        if current != start: path.append(current)
    rings.append(path)
if len(rings)!=1: raise RuntimeError('Pommel mounting transition requires one source loop')
ring = rings[0]
if sum((ring[(i+1)%len(ring)].co.x-ring[i].co.x)*(ring[(i+1)%len(ring)].co.y+ring[i].co.y) for i in range(len(ring)))>0:
    ring.reverse()
uv0 = bm.loops.layers.uv['UVMap']; uv1 = bm.loops.layers.uv['SteelUV']
nc = bm.loops.layers.float_vector['FactoryNormal']; cc = bm.loops.layers.float_color['Color']
for z, radius in [(-.014,.0148),(-.017,.0148),(-.020,.017)]:
    target = []
    for v in ring:
        angle = math.atan2(v.co.y-CY,v.co.x-CX)
        target.append(bm.verts.new((CX+radius*math.cos(angle),CY+radius*math.sin(angle),z)))
    for i in range(len(ring)):
        j = (i+1)%len(ring)
        f = bm.faces.new((ring[i],target[i],target[j],ring[j])); f.material_index = 1; f.smooth = True
        f.normal_update()
        for loop in f.loops:
            co = loop.vert.co
            # Planar per-face UVs keep transition slivers non-collapsed.
            axes = [a for a in range(3) if a!=max(range(3),key=lambda a:abs(f.normal[a]))]
            value = (co[axes[0]]/TILE,co[axes[1]]/TILE)
            loop[uv0].uv = value; loop[uv1].uv = value
            loop[nc] = Vector((co.x-CX,co.y-CY,0)).normalized(); loop[cc] = (1,0,0,1)
    ring = target
f = bm.faces.new(tuple(reversed(ring))); f.material_index = 1; f.normal_update()
for loop in f.loops:
    co = loop.vert.co
    loop[uv0].uv = (co.x/TILE,co.y/TILE); loop[uv1].uv = loop[uv0].uv
    loop[nc] = Vector((0,0,-1)); loop[cc] = (1,0,0,1)
bmesh.ops.triangulate(bm,faces=list(bm.faces)); bm.to_mesh(connector); bm.free(); connector.update()
connector.normals_split_custom_set([tuple(a.vector.normalized()) for a in connector.attributes['FactoryNormal'].data])

def finish(obj, material=steel, bevel=.0006):
    active(obj); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    obj.data.materials.clear(); obj.data.materials.append(material)
    for f in obj.data.polygons: f.material_index=0
    if bevel:
        mod = obj.modifiers.new('Rounded machined edges','BEVEL'); mod.width=bevel; mod.segments=3
        mod.limit_method='ANGLE'; mod.angle_limit=math.radians(18); mod.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in obj.data.polygons: f.use_smooth=True
    obj.data.set_sharp_from_angle(angle=math.radians(48))
    mod = obj.modifiers.new('Weighted metal normals','WEIGHTED_NORMAL'); mod.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    a = obj.data.uv_layers.get('UVMap') or obj.data.uv_layers.new(name='UVMap')
    b = obj.data.uv_layers.get('SteelUV') or obj.data.uv_layers.new(name='SteelUV')
    c = obj.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for f in obj.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
        for k in f.loop_indices:
            co = obj.data.vertices[obj.data.loops[k].vertex_index].co
            coord = (co[axes[0]]/TILE,co[axes[1]]/TILE)
            if material==turned:
                coord=((co.x-CX)/.064+.5,(co.y-CY)/.064+.5) if abs(f.normal.z)>.5 else (co[axes[0]]/.064+.5,co[axes[1]]/.064+.5)
            a.data[k].uv=coord; b.data[k].uv=coord; c.data[k].color=(1,0,0,1)
    return obj

def lathe(name, profile, count=96, material=steel, bevel=.0005, phase=0):
    vs=[(CX+r*math.cos(phase+math.tau*i/count),CY+r*math.sin(phase+math.tau*i/count),z) for z,r in profile for i in range(count)]
    fs=[]
    for j in range(len(profile)-1):
        fs.extend((j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i) for i in range(count))
    fs.extend([tuple(range(count-1,-1,-1)),tuple((len(profile)-1)*count+i for i in range(count))])
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vs,[],fs); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    obj=bpy.data.objects.new(name,mesh); bpy.context.scene.collection.objects.link(obj)
    return finish(obj,material,bevel)

def cap(parts,z,radius,count=96):
    parts.append(lathe('Recessed dark lock seat',[(z+.0007,radius),(z-.0001,radius)],count,dark,.0002))
    parts.append(lathe('Flush lock cap',[(z+.0001,radius*.91),(z-.0004,radius*.91)],count,turned,.00025))
    # A closed recessed fastener with six visible socket faces.
    parts.append(lathe('Fastener socket',[(z-.00045,.0022),(z-.00052,.0022)],6,dark,.00005))

def cage_rib(index):
    # A solid bowed rectangular rib with explicit inner face and capped ends.
    count=40; vs=[]; theta=math.tau*index/6+math.pi/6
    normal=Vector((math.cos(theta),math.sin(theta),0)); side=Vector((-math.sin(theta),math.cos(theta),0))
    for i in range(count+1):
        t=i/count; z=-.022-.060*t; radius=.015+.0105*math.sin(math.pi*t)**.82
        center=Vector((CX,CY,z))+normal*radius
        for a,b in [(-1,-1),(-1,1),(1,1),(1,-1)]:
            vs.append(center+normal*(a*.0020)+side*(b*.0035))
    fs=[]
    for i in range(count):
        fs.extend((4*i+k,4*i+(k+1)%4,4*(i+1)+(k+1)%4,4*(i+1)+k) for k in range(4))
    fs.extend([(3,2,1,0),tuple(4*count+k for k in range(4))])
    mesh=bpy.data.meshes.new('Arc rib');mesh.from_pydata(vs,[],fs);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new('Cage rib '+str(index+1),mesh);bpy.context.scene.collection.objects.link(obj)
    return finish(obj,steel,.0007)

rows=[]
for index,option in enumerate(OPTIONS):
    root=bpy.data.objects.new('Original mounting end '+option['id'],connector.copy())
    bpy.context.scene.collection.objects.link(root); parts=[root]
    parts.append(lathe('Shoulder seat', [(-.0185,.0167),(-.0205,.018),(-.023,.018)],material=steel))
    if option['id']=='octagonal_impact':
        parts.append(lathe('Eight forged facets',[(-.021,.0175),(-.027,.020),(-.034,.0265),(-.039,.028),(-.071,.028),(-.081,.0235),(-.087,.0175)],8,steel,.0011,math.pi/8))
        cap(parts,-.087,.0155,8)
    elif option['id']=='caged_agility':
        parts.extend(cage_rib(i) for i in range(6))
        parts.append(lathe('Closed bottom disk',[(-.0795,.0165),(-.082,.018),(-.085,.018),(-.087,.0155)],96,steel,.00065))
        cap(parts,-.087,.0138)
    else:
        parts.append(lathe('Rigid central core',[(-.021,.013),(-.082,.013)],96,dark,.0007))
        parts.append(lathe('Upper turned disk',[(-.023,.018),(-.027,.0245),(-.030,.026),(-.044,.026),(-.047,.0235)],128,steel,.0008))
        parts.append(lathe('Lower turned disk',[(-.059,.0265),(-.062,.029),(-.080,.029),(-.085,.025)],128,steel,.0009))
        # Distinct solid end plate with concentric surface texture.
        parts.append(lathe('Machined bottom plate',[(-.084,.0245),(-.087,.021)],128,turned,.0006))
        cap(parts,-.087,.015)
    active(root)
    for obj in parts: obj.select_set(True)
    bpy.ops.object.join()
    root.name='SM_CommonHammerPommel_'+option['id']+'_V1'
    mod=root.modifiers.new('Export triangles','TRIANGULATE');mod.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Author valid tangent UVs only on newly generated faces; keep factory mappings.
    mesh=root.data
    for poly in mesh.polygons:
        for layer in mesh.uv_layers:
            coords=[layer.data[k].uv for k in poly.loop_indices]
            if abs((coords[1]-coords[0]).cross(coords[2]-coords[0]))<1e-11 and mesh.materials[poly.material_index]!=old:
                axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(poly.normal[i]))]
                for k in poly.loop_indices:
                    co=mesh.vertices[mesh.loops[k].vertex_index].co;layer.data[k].uv=(co[axes[0]]/TILE,co[axes[1]]/TILE)
    mesh.update()
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(root.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    mesh.calc_loop_triangles()
    points=[v.co for v in mesh.vertices]
    rows.append({'id':option['id'],'name':option['name'],'mesh':root.name,'triangles':len(mesh.loop_triangles),
                 'location_cm':[v*100 for v in mount],'materials':[m.name for m in mesh.materials],
                 'bounds_local_m':[[min(p[j] for p in points) for j in range(3)],[max(p[j] for p in points) for j in range(3)]]})
    root.location=(index*.085,0,mount[2])
    print('POMMEL_EXPORTED '+json.dumps(rows[-1],ensure_ascii=False),flush=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerPommels_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'parts':rows,'slot':'pommel','interface':'warhammer_factory_v1',
    'factory_source':str(SOURCE),'mount_m':mount,'factory_preserved_local_z_min':CUT,'stats_assigned':False,
    'concept':'../ConceptV1/three-pommels-design.png','game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('COMMON_HAMMER_POMMELS_AUTHORED',flush=True)
