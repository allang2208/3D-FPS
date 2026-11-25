"""Blender background authoring, in centimetres, for the repairable mill yard."""
import math
import os
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from earth_form import elevation, section

OUT = Path(os.environ['WINDMILL_ART']) / 'Exchange'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    units = bpy.context.scene.unit_settings
    units.system = 'METRIC'
    units.scale_length = .01


def surface(name, vertices, faces, material, uv_plane):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(bpy.data.materials.get(material) or bpy.data.materials.new(material))
    uv = mesh.uv_layers.new()
    for face in mesh.polygons:
        for i in face.loop_indices:
            v = mesh.vertices[mesh.loops[i].vertex_index].co
            uv.data[i].uv = uv_plane(v, face.normal)
    return obj


def metric_uv(v, n):
    if abs(n.z) > .66:
        return (v.x / 200 + .41, v.y / 200 + .29)
    along = v.y if abs(n.x) > abs(n.y) else v.x
    return (along / 200 + .47, v.z / 200 + .11)


def save(name):
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes)>1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.transform(obj.matrix_world.copy())
    obj.matrix_world = Matrix.Identity(4)
    tri = obj.modifiers.new('Export triangulation', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT / (name + '.fbx')), use_selection=True,
        axis_forward='Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE', use_tspace=True, bake_anim=False, path_mode='STRIP')


def tube(name, centers, radius, material, closed=False):
    verts, faces = [], []
    count = len(centers)
    for i, center in enumerate(centers):
        prev = centers[(i-1) % count] if i or closed else center
        after = centers[(i+1) % count] if i+1 < count or closed else center
        tangent = (after - prev).normalized()
        normal = tangent.cross(Vector((1, 0, 0))).normalized()
        if normal.length < .01:
            normal = tangent.cross(Vector((0, 1, 0))).normalized()
        side = tangent.cross(normal).normalized()
        for j in range(6):
            angle = math.tau*j/6
            verts.append(center + radius*(math.cos(angle)*normal + math.sin(angle)*side))
            if closed or i+1 < count:
                a, b = i*6, (i+1) % count*6
                faces.append((a+j, a+(j+1)%6, b+(j+1)%6, b+j))
    return surface(name, verts, faces, material, metric_uv)


def bale(variant):
    reset()
    rng = random.Random(1048 + variant)
    hx, hy, hz = (52, 30, 25) if variant == 0 else (48, 28, 23)
    half = (hx, hy, hz)
    ties = (-hx*.51, hx*.45)
    def tied_point(p):
        core = Vector([max(-v+5, min(v-5, t)) for t, v in zip(p, half)])
        normal = (Vector(p) - core).normalized()
        ripple = .8*math.sin(p[0]*.16+p[1]*.09+variant) + .42*math.cos(p[2]*.29-p[0]*.11)
        pinch = sum(2.4*math.exp(-((p[0]-x)/4.2)**2) for x in ties)
        return core + normal*(5+ripple-pinch) + Vector((0,0,hz))

    verts, faces = [], []
    for axis, b, c in ((0,1,2),(1,2,0),(2,0,1)):
        for sign in (-1,1):
            nb, nc = (math.ceil(2*half[k]/3.5) for k in (b,c))
            start = len(verts)
            for i in range(nb+1):
                for j in range(nc+1):
                    p = [0.,0.,0.]
                    p[axis] = sign*half[axis]
                    p[b], p[c] = (2*i/nb-1)*half[b], (2*j/nc-1)*half[c]
                    verts.append(tied_point(p))
                    if i<nb and j<nc:
                        q = start+i*(nc+1)+j
                        face = (q,q+nc+1,q+nc+2,q+1)
                        faces.append(face if sign>0 else tuple(reversed(face)))
    body = surface('Compressed straw', verts, faces, 'Hay', metric_uv)
    for f in body.data.polygons:
        f.use_smooth = True

    for x in ties:
        loop = []
        for i in range(112):
            a = math.tau*i/112
            co, si = math.cos(a), math.sin(a)
            t = min(hy/max(abs(co),1.e-6), hz/max(abs(si),1.e-6))
            p = tied_point((x,co*t,si*t))
            loop.append(p+Vector((0,co,si))*.32)
        tube('Hemp binding',loop,.64,'Rope',True)
        knot = loop[28]
        tube('Binding tail',[knot,knot+Vector((1.8,2,.8)),knot+Vector((3.8,5,-.4))],.46,'Rope')

    # Short, opaque stalks interrupt the skyline and emerge from both cut ends.
    verts, faces = [], []
    for i in range(340):
        sign = rng.choice((-1,1))
        if i%3:
            start = tied_point((hx*sign,rng.uniform(-hy,hy),rng.uniform(-hz,hz)))
            tangent = Vector((sign*rng.uniform(1.4,5.9),rng.uniform(-1.5,1.5),rng.uniform(-2.2,1.8)))
        else:
            start = tied_point((rng.uniform(-hx,hx),rng.choice((-hy,hy)),rng.uniform(-hz,hz)))
            tangent = Vector((sign*rng.uniform(4,10),rng.uniform(-1,1),rng.uniform(-2.1,2)))
        # Keep the stack's bearing surfaces level.
        start.z=max(.65,start.z)
        tip=start+tangent
        tip.z=max(.65,tip.z)
        side=Vector((0,.11,.085))
        j=len(verts)
        verts.extend([start-side,start+side,start.lerp(tip,.58)+side*1.4,tip])
        faces.extend([(j,j+1,j+2),(j,j+2,j+3)])
    surface('Loose straw ends',verts,faces,'Hay',metric_uv)
    save('SM_MillHay'+('A','B')[variant])


def earth(name, length, width, height, rut=False):
    reset()
    verts, faces = [], []
    nx, ny = 58, 22
    for i in range(nx+1):
        s = 2*i/nx-1
        for j in range(ny+1):
            t = 2*j/ny-1
            x = s*length/2
            half,shift=section(s,width)
            y=t*half+shift
            verts.append((x,y,elevation(x,y,length,width,height,rut)))
            if i<nx and j<ny:
                q=i*(ny+1)+j
                faces.append((q,q+ny+1,q+ny+2,q+1))
    obj=surface(name,verts,faces,'Earth',metric_uv)
    for f in obj.data.polygons:
        f.use_smooth=True
    save(name)


def scanned(role):
    reset()
    # Fab stores the wheel as a child of the chassis. Each node can also carry
    # unused vertex positions from another node in the same scan.
    bpy.context.scene.unit_settings.scale_length=1.
    bpy.ops.import_scene.fbx(filepath=str(OUT/role/'Scan.fbx'))
    items=[o for o in bpy.context.scene.objects if o.type=='MESH']
    transforms=[o.matrix_world.copy() for o in items]
    orientation=Matrix.Rotation(math.radians(90),4,'Y') if role=='Fork' else Matrix.Identity(4)
    for obj,world in zip(items,transforms):
        obj.parent=None
        obj.matrix_world=Matrix.Identity(4)
        bm=bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.transform(orientation @ world)
    coords=[v.co.copy() for obj in items for v in obj.data.vertices]
    lo=[min(v[i] for v in coords) for i in range(3)]
    hi=[max(v[i] for v in coords) for i in range(3)]
    pivot=Vector(((lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,lo[2]))
    material=bpy.data.materials.new(role)
    for obj in items:
        obj.data.transform(Matrix.Scale(100,4) @ Matrix.Translation(-pivot))
        obj.data.materials.clear()
        obj.data.materials.append(material)
    bpy.context.scene.unit_settings.scale_length=.01
    save('SM_Mill'+role)


def loose_straw():
    reset()
    rng=random.Random(9421)
    verts,faces=[],[]
    for i in range(420):
        # Handfuls dragged from a sheaf: dense near the tie, sparse towards the tail.
        x=rng.gauss(0,19)
        y=rng.gauss(0,8)+4*math.sin(x*.047)
        if abs(x)>53 or abs(y)>25:
            continue
        a=rng.gauss(.2,.47) if i%5 else rng.uniform(-math.pi,math.pi)
        along=Vector((math.cos(a),math.sin(a),0))
        side=Vector((-along.y,along.x,0))*rng.uniform(.09,.27)
        length=rng.uniform(3,17)
        root=Vector((x,y,rng.uniform(.65,1.7)))
        bend=root+along*(length*.57)+Vector((0,0,rng.uniform(.25,1.8)))
        tip=root+along*length
        j=len(verts)
        verts.extend((root-side,root+side,bend+side,bend-side,tip))
        faces.extend(((j,j+3,j+2,j+1),(j+3,j+4,j+2)))
    surface('Broken straw',verts,faces,'Hay',metric_uv)
    save('SM_MillChaff')


def main():
    if '--' in sys.argv:
        scanned(sys.argv[sys.argv.index('--')+1])
        return
    for role in ('Barrow','Stone','Fork'):
        scanned(role)
    for variant in range(2):
        bale(variant)
    loose_straw()
    earth('SM_MillEarthShoulder',252,88,21)
    earth('SM_MillWheelRut',255,72,7.5,True)
    reset()
    # Origin is the underside of the host timber. The shank enters the wood.
    tube('Bent iron hook',[Vector(p) for p in [(-1.7,0,2.4),(-1.7,0,-4.5),
        (-1.3,0,-5.6),(-.4,0,-6.2),(.7,0,-6.1),(1.55,0,-5.3),(1.7,0,-3.4)]],.4,'Iron')
    save('SM_MillHook')


main()
