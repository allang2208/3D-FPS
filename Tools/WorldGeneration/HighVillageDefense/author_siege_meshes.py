"""Adapt the two Fab source models to the village kit's centimetre meshes."""
import array
import collections
import json
import pathlib
import sys

import bpy
from mathutils import Vector

run = pathlib.Path(sys.argv[sys.argv.index('--') + 1])
downloads = run / 'Downloads'
out = run / 'Authored'
out.mkdir(exist_ok=True)
roles = collections.defaultdict(dict)


def connected_islands(mesh):
    parent = list(range(len(mesh.vertices)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for edge in mesh.edges:
        a, b = edge.vertices
        parent[root(a)] = root(b)
    groups = {}
    return [groups.setdefault(root(v.index), len(groups)) for v in mesh.vertices]


def geometry(obj, convert, classify, preview, atlas=False):
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active
    groups = connected_islands(mesh)
    points = [convert(obj.matrix_world @ v.co) * 100 for v in mesh.vertices]
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    bounds = {}
    for p, g in zip(points, groups):
        if g not in bounds:
            bounds[g] = [p.copy(),p.copy()]
        else:
            lo, hi = bounds[g]
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
    for tri in mesh.loop_triangles:
        a,b,c=(points[i] for i in tri.vertices)
        if min((a-b).length,(b-c).length,(c-a).length)<.035 or (b-a).cross(c-a).length<.025:
            continue
        g = groups[tri.vertices[0]]
        center = sum((points[i] for i in tri.vertices), Vector()) / 3
        role, material, origin, basis = classify(g, center, bounds[g])
        for name, pivot, axes in [(role,origin,basis)] + ([(preview,Vector(),None)] if preview else []):
            buf = roles[name].setdefault(material, {k:array.array('i' if k=='indices' else 'f') for k in ('vertices','normals','uv','indices')})
            first = len(buf['vertices']) // 3
            for idx in tri.loops:
                loop = mesh.loops[idx]
                p = points[loop.vertex_index]
                n = convert(normal_matrix @ mesh.corner_normals[idx].vector).normalized()
                xyz = p-pivot
                if atlas:
                    tu,tv = uv.data[idx].uv
                    tex = (tu,1-tv)
                else:
                    axis=max(range(3),key=lambda i:abs(n[i]))
                    a,b=((1,2),(0,2),(0,1))[axis]
                    tex=(p[a]/115,-p[b]/115)
                buf['vertices'].extend(tuple(xyz.dot(a) for a in axes) if axes else xyz)
                buf['normals'].extend(tuple(n.dot(a) for a in axes) if axes else n)
                buf['uv'].extend(tex)
            # Both coordinate mappings reflect one axis, giving UE's clockwise winding.
            buf['indices'].extend((first,first+1,first+2))


def axes_for(direction):
    x = direction.normalized()
    y = Vector((0,0,1)).cross(x).normalized()
    return (x, y, x.cross(y))


nock=Vector((-140,0,97))
bolt=Vector((81,0,153))
bolt_axes=axes_for(Vector((1,0,.32)))
def ballista(group, center, bounds):
    side = 1 if center.y>=0 else -1
    origin=Vector()
    axes=None
    if 45<=group<=50:
        role='Bolt'
        origin,axes=bolt,bolt_axes
    elif group==39:
        role='String'+('R' if side>0 else 'L')
        origin=nock
        axes=axes_for(Vector((21,side*96,139))-origin)
    elif group in (5,6,7,8,9,10,11,12,13,40,41,42,43):
        role='Limb'+('R' if side>0 else 'L')
        origin=Vector((67,0,147))
    elif group in range(21,39):role='Base'
    elif group in (15,16,17):
        role='Windlass'
        origin=Vector((-149,0,84))
    else:role='Stock'
    return 'SM_Ballista'+role,'Ballista',origin,axes


bpy.ops.wm.open_mainfile(filepath=str(next((downloads/'Ballista').glob('*.blend'))))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
geometry(body,lambda v:Vector((-v.y,-v.x,v.z)),ballista,'SM_BallistaPreview',True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((downloads/'Trebuchet').rglob('Trebuchet*.fbx'))))
for obj in list(bpy.context.scene.objects):
    if not obj.name.endswith('LOD1'):
        continue
    part=obj.name.split('_')[1]
    pivot=Vector((obj.matrix_world.translation.x,-obj.matrix_world.translation.y,obj.matrix_world.translation.z))*100
    def mechanism(group,center,bounds):
        lo,hi=bounds
        dim=hi-lo
        material='Oak'
        if part=='Weight':
            material='Iron' if min(dim)<5 else 'Stone'
        elif max(dim)<26 or (part=='Arm' and dim.y>50):
            material='Iron'
        return 'SM_Trebuchet'+part,material,pivot,None
    geometry(obj,lambda v:Vector((v.x,-v.y,v.z)),mechanism,'SM_TrebuchetPreview')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((downloads/'Trebuchet').rglob('CatapultStone*.fbx'))))
stone=next(o for o in bpy.context.scene.objects if o.type=='MESH' and 'LOD1' in o.name)
pts=[stone.matrix_world@v.co for v in stone.data.vertices]
lo,hi=[Vector([func(p[i] for p in pts) for i in range(3)]) for func in (min,max)]
factor=.38/max(hi-lo)
stone.matrix_world.translation-=(lo+hi)*.5
geometry(stone,lambda v:Vector((v.x,-v.y,v.z)),lambda g,c,b:('SM_TrebuchetStone','Stone',Vector(),None),None)
for buf in roles['SM_TrebuchetStone'].values():
    buf['vertices']=array.array('f',(s*factor for s in buf['vertices']))

# A leather sling makes the stone's seat and its delayed follow-through visible in first person.
def sling_art():
    import math
    points=[];faces=[]
    def ring(x,y,z,rx,ry):
        ids=[]
        for k in range(16):
            a=math.tau*k/16
            ids.append(len(points));points.append((x+rx*math.cos(a),y+ry*math.sin(a),z))
        return ids
    def connect(a,b):
        for j in range(len(a)):
            n=(j+1)%len(a);faces.append((a[j],a[n],b[n],b[j]))
    a=ring(-58,0,-43,9,7)
    b=ring(-58,0,-35,21,15)
    c=ring(-58,0,-27,22,17)
    d=ring(-58,0,-29,20,15)
    connect(a,b);connect(b,c);connect(c,d)
    faces.append(tuple(reversed(a)));faces.append(tuple(d))
    for side in (-1,1):
        path=((0,side*2,0),(-14,side*5,-10),(-34,side*10,-22),(-58,side*15,-29))
        sections=[]
        for x,y,z in path:
            ids=[]
            for j in range(8):
                t=math.tau*j/8;ids.append(len(points));points.append((x,y+2*math.cos(t),z+1.25*math.sin(t)))
            sections.append(ids)
        for a,b in zip(sections,sections[1:]):connect(a,b)
    mesh=bpy.data.meshes.new('Sling')
    mesh.from_pydata([(x,-y,z) for x,y,z in points],[],[tuple(reversed(f)) for f in faces])
    obj=bpy.data.objects.new('Sling',mesh);bpy.context.collection.objects.link(obj)
    geometry(obj,lambda v:Vector((v.x,-v.y,v.z)),lambda g,c,b:('SM_TrebuchetSling','Leather',Vector(),None),None)
    # geometry() takes metres from the two source files. These additions were sculpted in cm.
    for buf in roles['SM_TrebuchetSling'].values():
        buf['vertices']=array.array('f',(s*.01 for s in buf['vertices']))
        buf['uv']=array.array('f',(s*.015 for s in buf['uv']))
sling_art()


def add_to_preview(name,translation):
    for material,part in roles[name].items():
        dest=roles['SM_TrebuchetPreview'].setdefault(material,{k:array.array(v.typecode) for k,v in part.items()})
        base=len(dest['vertices'])//3
        dest['vertices'].extend(x+translation[i%3] for i,x in enumerate(part['vertices']))
        dest['indices'].extend(i+base for i in part['indices'])
        for key in ('normals','uv'):dest[key].extend(part[key])

add_to_preview('SM_TrebuchetSling',(-273,0,72))
add_to_preview('SM_TrebuchetStone',(-331,0,52))


def export_fbx(name,materials):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=.01
    verts, normals, faces, uv, slots=[],[],[],[],[]
    cache={}
    for slot,(material,buf) in enumerate(materials.items()):
        pos,ns,atlas=buf['vertices'],buf['normals'],buf['uv']
        for n in range(0,len(buf['indices']),3):
            ids=[]
            for i in buf['indices'][n:n+3]:
                x,y,z=pos[3*i:3*i+3];nx,ny,nz=ns[3*i:3*i+3]
                u,v=atlas[2*i:2*i+2]
                key=(x,-y,z,nx,-ny,nz,u,1-v)
                if key not in cache:
                    cache[key]=len(verts);verts.append(key[:3]);normals.append(key[3:6])
                ids.append(cache[key]);uv.append(key[6:])
            faces.append(ids);slots.append(slot)
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    for material in materials:mesh.materials.append(bpy.data.materials.new(material))
    layer=mesh.uv_layers.new(name='UVMap')
    for i,coord in enumerate(uv):layer.data[i].uv=coord
    for i,poly in enumerate(mesh.polygons):poly.material_index=slots[i];poly.use_smooth=True
    mesh.normals_split_custom_set_from_vertices(normals)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,axis_forward='-Y',axis_up='Z',
        use_space_transform=False,apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')


for name,materials in roles.items():
    export_fbx(name,materials)
    boxes=[]
    if name in ('SM_BallistaBase','SM_BallistaPreview'):
        boxes=[dict(center=[0,0,13],size=[145,105,26]),dict(center=[-5,0,64],size=[28,28,80])]
    if name in ('SM_TrebuchetBase','SM_TrebuchetPreview'):
        boxes=[dict(center=[-10,y,37],size=[438,38,70]) for y in (-128,128)]
        boxes.extend(dict(center=[0,y,160],size=[55,32,276]) for y in (-69,69))
    spec=dict(materials=list(materials),boxes=boxes,faces=sum(len(b['indices'])//3 for b in materials.values()))
    (out/(name+'.json')).write_text(json.dumps(spec),encoding='utf8')
