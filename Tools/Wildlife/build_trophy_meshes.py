"""Author the seven wildlife pickups in centimetres, with unwrapped detail UVs."""
from pathlib import Path
from math import cos, sin, pi, exp
import bpy
from mathutils import Vector

out = Path(__file__).resolve().parents[2] / 'SourceAssets/HillsWildlifeLoot'
out.mkdir(parents=True, exist_ok=True)


def surface(rows, cols, point):
    base = len(verts)
    for i in range(rows + 1):
        for j in range(cols + 1):
            u, v = j / cols, i / rows
            verts.append(point(u, v))
            coords.append((u, v))
    for i in range(rows):
        for j in range(cols):
            a = base + i * (cols + 1) + j
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))


def hide(u, v):
    t = 2 * v - 1
    edge = (0.66 + .32 * sin(pi*v)**.65 - .14 * exp(-((v-.78)/.08)**2)
            + .035*sin(8*pi*v) + .018*sin(29*v+2*u))
    if kind.endswith('pelt'):
        edge *= .89 + .10*sin(pi*v) - .27*exp(-((v-.985)/.086)**2)
    # A laid-out piece of hide, with one long edge turned back over itself.
    a = min(u, .69)
    angle = max(0, (u-.69)/.31) * (1.40*pi + .36*cos(5*v))
    x = (a - .44)*width*edge + width*.085*sin(angle)*edge
    y = length*.5*t + 1.15*sin(8*u + 4*v) + 1.4*(2*u-1)*cos(7*v)
    z = .7 + width*.081*(1-cos(angle)) + .8*(1+sin(14*u+8*v))*(.35+.65*v)
    return (x, y, z)


def shaft(points, radii, grain=.035):
    pts = list(map(Vector, points))
    def ring(u, v):
        f = v*(len(pts)-1)
        k = min(int(f),len(pts)-2)
        p = pts[k].lerp(pts[k+1], f-k)
        tangent = (pts[min(k+2,len(pts)-1)] - pts[max(k-1,0)]).normalized()
        side = tangent.cross(Vector((0,0,1))).normalized()
        up = tangent.cross(side).normalized()
        r = radii[k] + (radii[k+1]-radii[k])*(f-k)
        angle = 2*pi*u
        r *= 1+grain*cos(angle*9+.65*v)+grain*.7*sin(11*angle-4*v)
        return p+r*(cos(angle)*side + sin(angle)*up)
    base=len(verts)
    sides=24
    rows=(len(pts)-1)*5
    surface(rows,sides,ring)
    for i, reverse in ((0,False),(rows,True)):
        start=base+i*(sides+1)
        rim=tuple(start+j for j in range(sides))
        faces.append(tuple(reversed(rim)) if not reverse else rim)


def feather(u,v):
    side=2*u-1
    width=(2.55 if side<0 else 1.58)*sin(pi*v)**.70*min(v/.21,1.)
    serration=.06*abs(sin(58*pi*v)) + sum(.30*exp(-((v-at)/.008)**2) for at in (.43,.62,.79))
    x=1.05*v*v + side*width*(1-serration)
    return (x,.2+21.8*v-.85*abs(side)*width,.36+.8*sin(pi*v)+.32*abs(side)*width)


for kind, width, length in [('deer_hide',33,44),('boar_hide',35,38),('fox_pelt',21,41),('wolf_pelt',32,51),
                            ('deer_antler',0,0),('boar_tusk',0,0),('crow_feather',0,0)]:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    verts, coords, faces = [], [], []
    if width:
        surface(54,42,hide)
    elif kind=='deer_antler':
        shaft([(0,0,2),(1,4,2.5),(2,10,3.2),(5,17,4.6),(9,24,5.8),(13,29,7.4),(17,32,7.8)],
              [2.8,2.2,1.9,1.65,1.27,.8,.07])
        shaft([(1,4,2.6),(-1,5,5),(-3,6,8),(-4,8,11.9)],[1.45,1.12,.75,.06])
        shaft([(4.5,16,4.5),(2,18.6,7.5),(.4,20.6,11),(-.1,23,13.4)],[1.35,1.08,.64,.07])
        shaft([(9.2,24,5.9),(8.8,26,8.2),(9,29,10.7),(10.4,31,12.1)],[1.10,.82,.48,.06])
    elif kind=='boar_tusk':
        shaft([(0,0,2.1),(.4,2.3,2.3),(1.1,5,2.7),(2.6,7.5,3.1),(4.9,9.1,3.3),(7,9.7,3.7),(8.5,9.4,4.2)],
              [1.85,1.76,1.53,1.27,.90,.46,.045],.012)
    else:
        surface(130,14,feather)
        shaft([(0,-2,.36),(.025,4,.61),(.23,10,1.16),(.55,16,.97),(1.05,22,.36)],
              [.14,.135,.10,.065,.015],.01)
    mesh=bpy.data.meshes.new(kind)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        uv.data[loop.index].uv=coords[loop.vertex_index]
    for poly in mesh.polygons:
        poly.use_smooth=True
    obj=bpy.data.objects.new('SM_'+kind,mesh)
    mesh.materials.append(bpy.data.materials.new('TrophySurface'))
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    if width or kind=='crow_feather':
        solid=obj.modifiers.new('Hide edge' if width else 'Vane edge','SOLIDIFY')
        solid.thickness=.22 if width else .033
    bpy.ops.export_scene.fbx(filepath=str(out/('SM_'+kind+'.fbx')),use_selection=True,
                              apply_unit_scale=False,global_scale=.01,add_leaf_bones=False,
                              mesh_smooth_type='FACE',axis_forward='-Y',axis_up='Z')
