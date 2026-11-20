"""Build the tavern joiner's seven assets in Blender. Dimensions use UE centimetres."""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.geometry import normal


OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(OUT))
from source_materials import bind_surfaces, relative_to_blend

FBX = OUT / 'Exports'
FBX.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
V = Vector
X, Y, Z = (V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1)))
MATS = {}
for key, rgb in {'Oak': (.24, .15, .075), 'OiledOak': (.25, .16, .09),
                 'Rot': (.16, .14, .11), 'Sawn': (.38, .25, .13),
                 'Endgrain': (.33, .21, .12), 'Iron': (.105, .09, .078)}.items():
    MATS[key] = bpy.data.materials.new(key)
    MATS[key].diffuse_color = (*rgb, 1.)


def frame(center=(0, 0, 0), angles=(0, 0, 0)):
    return Matrix.Translation(V(center)) @ Euler(tuple(map(math.radians, angles))).to_matrix().to_4x4()


def blender_point(p):
    return p.x * .01, -p.y * .01, p.z * .01


def unfold_bevel_corners(mesh):
    """Recover narrow bevel corners where interpolation collapsed the UV onto a line."""
    layer = mesh.uv_layers.active.data
    for polygon in mesh.polygons:
        loops = list(polygon.loop_indices)
        uv = [layer[i].uv.copy() for i in loops]
        if abs((uv[1]-uv[0]).cross(uv[2]-uv[0])) > 1.e-11:
            continue
        pos = [mesh.vertices[mesh.loops[i].vertex_index].co for i in loops]
        i = max(range(3),key=lambda i:(uv[(i+1)%3]-uv[i]).length_squared)
        j, k = (i+1)%3, (i+2)%3
        if (uv[j]-uv[i]).length_squared < 1.e-14:
            i = max(range(3),key=lambda i:(pos[(i+1)%3]-pos[i]).length_squared)
            j,k = (i+1)%3,(i+2)%3
            uv[j] = uv[i]+V(((pos[j]-pos[i]).length/1.03,0))
            layer[loops[j]].uv = uv[j]
        side = (pos[j]-pos[i]).normalized()
        delta = pos[k]-pos[i]
        along = delta.dot(side)
        axis = (uv[j]-uv[i]).normalized()
        perp = V((-axis.y,axis.x))
        layer[loops[k]].uv = uv[i] + (axis*along+perp*(delta-along*side).length)/1.03


class Model:
    def __init__(self, name, seed):
        self.name = 'SM_Tavern' + name
        self.rand = random.Random(seed)
        self.parts = defaultdict(lambda: ([], [], []))
        self.hulls = []
        self.pose = Matrix.Identity(4)

    def solid(self, points, faces, grain, wood, edge, collision=False, draw=True, turned=None):
        """Keep face-grain in V and cross-grain in U, including angled joinery."""
        points = list(map(V, points))
        export_points = [blender_point(self.pose @ p) for p in points]
        if collision:
            self.hulls.append((export_points, [tuple(reversed(f)) for f in faces]))
        if not draw:
            return
        vertices, polys, surfaces = self.parts[edge]
        start = len(vertices)
        vertices.extend(export_points)
        phase_u, phase_v = self.rand.random(), self.rand.random()
        grain = V(grain).normalized()
        for face_index, face in enumerate(faces):
            face = list(reversed(face))
            ps = [points[i] for i in face]
            n = normal(ps)
            is_end = abs(n.dot(grain)) > .76 and wood != 'Iron'
            if is_end:
                u = n.cross(Z if abs(n.z) < .85 else X).normalized()
                v = n.cross(u).normalized()
                # Cropped individual growth rings on exposed tenons and board ends.
                uv = [(.48 + phase_u * .16 + p.dot(u) / 58,
                       .44 + phase_v * .19 + p.dot(v) / 58) for p in ps]
            elif turned and 0 < face_index < len(faces) - 1:
                # Keep fibres continuous around turned legs, rings and the long footrest.
                # Projecting each facet onto a different world plane leaves vertical seams.
                origin, sides, radius = turned
                last = (face_index-1) % sides == sides-1
                uv = []
                for index in face:
                    step = index % sides
                    if last and step == 0:
                        step = sides
                    uv.append((phase_u + math.tau * radius * step / (sides * 103),
                               phase_v + (points[index]-origin).dot(grain) / 103))
            else:
                along = grain - n * n.dot(grain)
                if along.length_squared < .00001:
                    along = n.cross(X if abs(n.x) < .85 else Y)
                v = along.normalized()
                u = n.cross(v).normalized()
                uv = [(phase_u + p.dot(u) / 103, phase_v + p.dot(v) / 103) for p in ps]
            polys.append(tuple(start + j for j in face))
            smooth = turned is not None and 0 < face_index < len(faces)-1 and not is_end
            surfaces.append(('Endgrain' if is_end else wood, uv, smooth))

    def rings(self, rings, grain, wood, edge, collision=False, draw=True, turned=None):
        n = len(rings[0])
        faces = [tuple(reversed(range(n)))]
        for j in range(len(rings) - 1):
            for i in range(n):
                k = (i + 1) % n
                a = j * n
                faces.append((a+i, a+k, a+n+k, a+n+i))
        a = n * (len(rings) - 1)
        faces.append(tuple(a+i for i in range(n)))
        self.solid([p for ring in rings for p in ring], faces, grain, wood, edge, collision, draw, turned)

    def rect(self, center, size, wood='Oak', edge=.35, collision=False, angles=(0, 0, 0), draw=True):
        # Sizes follow world X/Y/Z before rotation.
        dx, dy, dz = (q / 2 for q in size)
        mat = frame(center, angles)
        xy = [(-dx,-dy), (dx,-dy), (dx,dy), (-dx,dy)]
        rings = [[mat @ V((x,y,z)) for x,y in xy] for z in (-dz,dz)]
        axis = (X, Y, Z)[max(range(3), key=lambda i: size[i])]
        self.rings(rings, mat.to_3x3() @ axis, wood, edge, collision, draw)

    def bar(self, a, b, width, depth, wood='Oak', edge=.35, collision=False):
        a, b = V(a), V(b)
        axis = (b-a).normalized()
        across = (Z if abs(axis.z) < .9 else Y).cross(axis).normalized()
        up = axis.cross(across).normalized()
        section = [(-1,-1), (1,-1), (1,1), (-1,1)]
        rings = [[p + across*(w*width/2) + up*(d*depth/2) for w,d in section] for p in (a,b)]
        self.rings(rings, axis, wood, edge, collision)

    def lathe(self, a, b, profile, wood, sides=12, collision=False, draw=True, twist=0):
        a, b = V(a), V(b)
        axis = (b-a).normalized()
        v = (Z if abs(axis.z) < .9 else X).cross(axis).normalized()
        w = axis.cross(v).normalized()
        rings = []
        for t, r in profile:
            rings.append([a.lerp(b, t) + (v*math.cos(i*math.tau/sides+twist)
                          + w*math.sin(i*math.tau/sides+twist))*r for i in range(sides)])
        self.rings(rings, axis, wood, 0, collision, draw, (a,sides,max(r for _,r in profile)))

    def pin(self, xyz, direction, radius=1, iron=False):
        d = V(direction).normalized()
        p = V(xyz)
        self.lathe(p-d*.35, p+d*(.45 if iron else .16),
                   ((0,radius*.85),(.64,radius),(1,radius*(.63 if iron else .86))),
                   'Iron' if iron else 'Sawn', 6 if iron else 10, twist=self.rand.uniform(0, .5))

    def slab(self, poly, z, thick, grain=Y, wood='Oak', edge=.35, collision=False, draw=True):
        area = sum(x*v-y*u for (x,y),(u,v) in zip(poly, poly[1:]+poly[:1]))
        if area < 0:
            poly = list(reversed(poly))
        self.rings([[(x,y,h) for x,y in poly] for h in (z,z+thick)], grain, wood, edge, collision, draw)

    def round_boards(self, radius, height, thick, count, broken=False, collision=True):
        # Saw slots follow restrained circle chords. On broken tops, the split runs
        # parallel to the grain and leaves staggered fibres between the boards.
        for i in range(count):
            a = -radius + 2*radius*i/count + (.12 if i else 0)
            b = -radius + 2*radius*(i+1)/count - (.12 if i+1<count else 0)
            if broken and i == count-1:
                continue
            # Uniform angular sampling preserves curvature right up to the two ends.
            ta = math.asin(max(-1, a/radius))
            tb = math.asin(min(1, b/radius))
            steps = max(3, math.ceil((tb-ta)*radius/3))
            upper, lower = [], []
            for j in range(steps+1):
                t = j/steps
                ang = ta + (tb-ta)*t
                x, y = radius*math.sin(ang), max(0.,radius*math.cos(ang))
                y_end = y
                if broken and i >= count-3:
                    cut = radius*(.04 if i == count-2 else .47)
                    cut += (.15*radius if j%2 else -.035*radius) + math.sin(j*2.42+i)*radius*.05
                    y_end = min(y, cut)
                upper.append((x, y_end))
                lower.append((x,-y))
            contour = []
            for p in lower + upper[::-1]:
                if not contour or math.dist(contour[-1],p) > .001:
                    contour.append(p)
            if math.dist(contour[0],contour[-1]) < .001:
                contour.pop()
            self.slab(contour,height-thick,thick,wood='Rot' if broken else 'OiledOak',edge=.42 if radius>30 else .34,
                      collision=collision and broken)
        if collision and not broken:
            poly = [(radius*math.cos(i*math.tau/20),radius*math.sin(i*math.tau/20)) for i in range(20)]
            self.slab(poly,height-thick,thick,collision=True,draw=False)

    def loose(self, center, length, width, height, yaw, wood='Rot'):
        old = self.pose
        self.pose = old @ frame(center, (0,0,yaw))
        x = width/2
        y = length/2
        self.slab([(-x,-y),(x,-y+1),(x,y-2),(.52*x,y+2),(.24*x,y-5),
                   (-.12*x,y+1),(-.23*x,y-3),(-.52*x,y-1),(-x,y-5)],0,height,
                  wood=wood,edge=.22,collision=width>7)
        self.pose = old

    def export(self, layout):
        objects = []
        for i,(edge,(verts,polys,surfaces)) in enumerate(self.parts.items()):
            mesh = bpy.data.meshes.new(self.name+' Joinery')
            mesh.from_pydata(verts,[],polys)
            mesh.update()
            keys = list(dict.fromkeys(k for k,_,_ in surfaces))
            for k in keys:
                mesh.materials.append(MATS[k])
            uv = mesh.uv_layers.new(name='FaceGrain')
            for poly,(key,coords,smooth) in zip(mesh.polygons,surfaces):
                poly.material_index = keys.index(key)
                poly.use_smooth = smooth
                for idx,coord in zip(poly.loop_indices,coords):
                    uv.data[idx].uv = coord
            obj = bpy.data.objects.new(self.name+' millwork '+str(i),mesh)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            if edge:
                bevel = obj.modifiers.new('Hand-eased arrises','BEVEL')
                bevel.width = edge/100; bevel.segments = 2
                bevel.limit_method = 'ANGLE'; bevel.angle_limit = math.radians(26)
                bevel.harden_normals = True
                bpy.ops.object.modifier_apply(modifier=bevel.name)
            normals = obj.modifiers.new('Broad face normals','WEIGHTED_NORMAL')
            normals.keep_sharp = True
            bpy.ops.object.modifier_apply(modifier=normals.name)
            triang = obj.modifiers.new('FBX triangles','TRIANGULATE')
            triang.keep_custom_normals = True
            bpy.ops.object.modifier_apply(modifier=triang.name)
            unfold_bevel_corners(obj.data)
            objects.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        model = objects[0]
        model.name = self.name
        model.data.name = self.name
        hulls = []
        for i,(verts,faces) in enumerate(self.hulls):
            name = 'UCX_'+self.name+'_'+str(i).zfill(2)
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(verts,[],faces); mesh.update()
            obj = bpy.data.objects.new(name,mesh)
            bpy.context.collection.objects.link(obj)
            obj.select_set(True)
            hulls.append(obj)
        bpy.ops.export_scene.fbx(filepath=str(FBX/(self.name+'.fbx')),use_selection=True,
            object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',
            use_tspace=True,bake_anim=False,add_leaf_bones=False)
        for h in hulls:
            h.hide_render=True; h.display_type='WIRE'; h.hide_set(True); h.location=layout
        model.location=layout


def table(m, broken=False):
    # Two transverse trestles with a pegged longitudinal stretcher.
    deck = frame((0,0,39.52),(-38,0,0)) @ frame((0,0,-76)) if broken else frame()
    m.pose = deck
    m.round_boards(58,76,4.8,7,broken)
    for q in (-1,1):
        y = q*27
        m.rect((0,y,68.15),(79,8.5,6.2),edge=.5,collision=True)
        for x in (-29,29):
            if not (broken and x>0 and y>0):
                m.pin((x,y,75.91),Z,.92)
    m.pose = frame()
    for q in (-1,1):
        y = q*27
        top_y = (deck @ V((0,y,67))).y
        top_z = (deck @ V((0,y,67))).z
        if broken and q>0:
            # This trestle has folded. The ends land under the fallen tabletop.
            for s in (-1,1):
                m.bar((s*39,37,3.6),(s*22,top_y,top_z+1),7,7,collision=True)
            continue
        m.rect((0,y,3.8),(80,10,7.6),edge=.65,collision=True)
        for s in (-1,1):
            m.bar((s*32,y,6.1),(s*23,top_y,top_z+1),8.8,8,collision=True)
            m.pin((s*28,y+q*4,top_z*.5),Y*q,1.05)
        m.bar((-27,y,top_z*.48),(27,y,top_z*.48),7,7)
    if broken:
        m.bar((0,-33,22),(0,44,4),7.5,8,collision=True)
        m.loose((44,8,0),57,10.2,4.5,-8)
        m.loose((32,27,0),32,7.8,3.8,24)
    else:
        m.bar((0,-34,32),(0,34,32),7.5,8,collision=True)
        for y in (-32,32):
            m.rect((0,y,32.2),(2.5,2.8,15),'Sawn',.25,angles=(0,4,0))


def stool(m, broken=False):
    if broken:
        # The surviving seat pivots on its split edge. One broken leg still
        # enters its original mortise and props it up at the opposite edge.
        angle = 52.
        edge_x = 10.-.12
        m.pose = frame((0,0,edge_x*math.sin(math.radians(angle))),(0,angle,0))
        m.round_boards(20,4,4,4,True)
        socket = m.pose @ V((-9.7,-5.6,.8))
        m.rect((-5,-6,-.6),(16,3.2,1.8),'Sawn',.22)
        m.pose=frame()
        # Cut the loaded foot horizontal where it contacts the floor.
        base = V((-24,-8.5,0))
        axis = (socket-base).normalized()
        v = Z.cross(axis).normalized()
        w = axis.cross(v).normalized()
        rings = []
        for t,r in ((0,2.05),(.12,2.18),(.54,2.05),(.70,2.72),(.78,2.35),(.91,2.75),(1,2.45)):
            ring = [base.lerp(socket,t) + (v*math.cos(i*math.tau/14)+w*math.sin(i*math.tau/14))*r for i in range(14)]
            if t == 0:
                for p in ring:
                    p.z = 0
            rings.append(ring)
        m.rings(rings,axis,'Oak',0,turned=(base,14,2.72))
        m.lathe(base+Z*.9,socket,((0,1.45),(1,2.4)),'Oak',8,collision=True,draw=False)
        m.loose((15,2,0),24,6.4,3.4,-12)
        for a,b,r in [((-22,-22,2.65),(15,-19.5,2.65),2.65),((1,13.2,2.05),(15,18,2.05),2.05)]:
            m.lathe(a,b,[(0,r*.73),(.06,r),(.15,r*.84),(.64,r*.70),(.79,r),(.88,r*.79),(1,r*.72)],
                    'Rot',16,collision=True)
        return
    m.round_boards(20,46,3.9,4)
    for y in (-7.8,7.8):
        m.rect((0,y,41.2),(28.8,3.5,2.8),edge=.32)
    feet, necks = [], []
    for i in range(3):
        a = math.radians(90+i*120)
        cx,cy = math.cos(a),math.sin(a)
        foot=V((cx*16.7,cy*16.7,1)); top=V((cx*11.2,cy*11.2,43.6))
        feet.append(foot);necks.append(top)
        profile=[(0,2.08),(.025,2.36),(.075,2.39),(.105,1.96),(.36,2.1),(.61,2.45),
                 (.69,2.64),(.71,2.94),(.755,2.94),(.782,2.4),(.86,2.75),(.91,3.01),(1,2.83)]
        m.lathe(foot,top,profile,'Oak',16)
        m.lathe((foot.x,foot.y,0),(foot.x,foot.y,1.3),((0,2.02),(1,2.13)),'Oak',16)
        m.lathe((foot.x,foot.y,.27),top,((0,2.12),(1,2.85)),'Oak',8,collision=True,draw=False)
        m.pin((top.x,top.y,45.9),Z,.71)
    for i in range(3):
        j=(i+1)%3
        a=feet[i].lerp(necks[i],.34);b=feet[j].lerp(necks[j],.34)
        m.lathe(a,b,((0,1.52),(.14,1.6),(.22,1.33),(.78,1.33),(.86,1.6),(1,1.52)),'Oak')


def counter(m, broken=False, service=None):
    # 3 framed front panels, working shelves to the rear and a projecting oak cap.
    if service:
        service.top(m)
    else:
        for i in range(4):
            x=-27+i*18
            if broken:
                y=(72,53,45,64)[i]
                p=[(x-8.9,-130),(x+8.9,-130),(x+8.9,y),(x+5,y-5),(x+3,y+4),
                   (x+1.4,y-9),(x-.9,y-6),(x-4,y+2),(x-7,y-3),(x-8.9,y+3)]
                m.slab(p,99.4,5.6,wood='Rot',collision=True)
            else:
                m.rect((x,0,102.2),(17.85,260,5.6),'OiledOak',edge=.54)
    if not broken:
        m.rect((0,0,102.15),(72,260,5.7),collision=True,draw=False)
    # Front rails, molded drip lip, inset field uprights and punched wrought nails.
    end=44 if broken else 126
    c=(end-126)/2; length=end+126
    for x,z,w,h in [(26.4,6.2,8,12.4),(27,16.6,5.4,8.5),(27,86.6,6,12),
                      (30,96.5,8.2,5.8),(32.2,99.1,4.6,2.5)]:
        if broken and z == 6.2:
            # The two amputated posts still stand in their continuous sole rail.
            m.rect((x,0,z),(w,252,h),'Rot',.4)
        else:
            m.rect((x,c,z),(w,length,h),edge=.4)
    for y in (-122,-41,41,122):
        intact=not broken or y<60
        for x in (-24,24):
            h=100 if intact else (28 if x>0 else 16)
            if intact:
                m.rect((x,y,h/2),(8,8,h),edge=.53,collision=True)
            else:
                outline=[(-4,-4),(0,-4),(4,-4),(4,1),(4,4),(0,4),(-4,4),(-4,1)]
                bottom=[(x+u,y+v,0) for u,v in outline]
                top=[(x+u,y+v,h+rise) for (u,v),rise in zip(outline,(-2,2,-3,1.8,-4,1,-1,2.7))]
                # Triangulate the fractured crown around the splintered fibres.
                verts=bottom+top+[(x,y,h-2.7)]
                faces=[tuple(reversed(range(8)))]
                for j in range(8):
                    k=(j+1)%8
                    faces.extend(((j,k,k+8,j+8),(j+8,k+8,16)))
                m.solid(verts,faces,Z,'Rot',.18)
                m.rect((x,y,h/2),(8,8,h),collision=True,draw=False)
        if not intact:
            m.rect((0,y,4.2),(48,7,8.4),'Rot',.4,collision=True)
            continue
        m.rect((28,y,53),(4.3,8.2,76),edge=.38)
        for z in (18,87):
            m.pin((30.2,y,z),X,1.04,True)
        m.rect((0,y,95),(52,8,8.8),edge=.35)
        for shelf_z in (15,55):
            m.rect((0,y,shelf_z-4.1),(49,7.5,5.2),edge=.35)
    for bay,y in enumerate((-81.5,0,81.5)):
        if broken and bay==2: continue
        if service:
            service.panel(m,y)
        else:
            for j in range(5):
                yy=y+(j-2)*14.35
                m.rect((23.6,yy,50.5),(4.9,14.12,72),edge=.43)
            for yy in (y-35,y+35):
                m.rect((26.75,yy,50.7),(2.4,2.7,61.5),'Sawn',.62)
            for z in (21,80.4):
                m.rect((26.6,y,z),(2.8,70.5,2.8),'Sawn',.56)
        m.rect((23.6,y,51),(5.2,80.7,96.4),collision=True,draw=False)
        for z in (15,55):
            for x in (-13.9,5.4):
                m.rect((x,y,z),(19.05,79,3.1),edge=.22)
            m.rect((-22,y,z-2.7),(3,79,5.4),edge=.32)
            m.rect((-3,y,z),(45,79,3.1),collision=True,draw=False)
    for s in (-1,1):
        if broken and s>0:continue
        for j in range(4):
            m.rect((-16.7+j*11.2,s*122,50),(10.99,3.2,75),edge=.37)
        for z in (11,86):
            m.rect((0,s*122,z),(52,6,10),edge=.4)
        m.rect((0,s*122,49),(53,4,96),collision=True,draw=False)
    if broken:
        m.loose((17,91,0),60,12,4,12)
        m.loose((-9,94,0),71,11.2,4,-14)
        m.loose((6,109,0),25,7.5,3.4,29)
    else:
        # A low timber footrail and three hand-forged brackets on the guest side.
        for y in (-104,0,104):
            m.rect((30.5,y,8.5),(1.1,3.8,6.8),'Iron',.15)
            m.pin((31.1,y,6.7),X,.68,True)
            m.bar((30.7,y,9.2),(46.3,y,21.8),2.5,2.5,'Iron',.16)
        m.lathe((46.4,-113,22),(46.4,113,22),
                [(0,2.35),(.009,2.85),(.02,2.65),(.98,2.65),(.991,2.85),(1,2.35)],'OiledOak',16)
        m.lathe((46.4,-113,22),(46.4,113,22),((0,2.6),(1,2.6)),'Oak',10,collision=True,draw=False)


def backbar(m):
    # Upper shelves are fully open on the +X service face. The recessed boards
    # and side stops keep the silhouette of each shelf distinct across the room.
    for j in range(13):
        m.rect((-18.5,(j-6)*14.65,90.3),(3.25,14.43,174.6),edge=.32)
    m.rect((-18.7,0,91),(3.8,193,181),collision=True,draw=False)
    for y in (-94.5,94.5):
        for x in (-16.3,14.4):
            m.rect((x,y,89.5),(6.6,7.7,179),edge=.55,collision=True)
        for x in (-8,4):
            m.rect((x,y,91.7),(11.8,3.6,162),edge=.32)
        m.rect((0,y,91),(36,3.6,176),collision=True,draw=False)
        for z in (16,69,112,154):
            m.pin((17.82,y,z),X,.91)
    for k,z in enumerate((12,65,109,151,179)):
        for x in (-9.2,8.5):
            m.rect((x,0,z),(17.54,196,3.7),edge=.36)
        m.rect((15.2,0,z-2.4),(4.8,195,6.9),edge=.65)
        m.rect((-14.4,0,z+3.6),(3.5,184,4.9),edge=.52)
        m.rect((0,0,z),(37,195,4.2),collision=True,draw=False)
        if 0<k<4:
            for yy in (-90.5,90.5):
                m.bar((-13,yy,z-13),(11,yy,z-2.4),3.6,4.9,edge=.4)
    for x in (-9,8.5):
        m.rect((x,0,38.5),(17,3.7,49),edge=.3)
    m.rect((14.2,0,7.5),(6,194,12.4),edge=.7)
    for z,x,w,h,l in [(181.3,0,39.3,3.1,198.4),(183.65,0,42,2.7,200)]:
        m.rect((x,0,z),(w,l,h),edge=.55)


def export_set():
    for idx,(label,fn,damage) in enumerate((('Table',table,False),('Stool',stool,False),
        ('Counter',counter,False),('Backbar',backbar,False),('BrokenTable',table,True),
        ('BrokenStool',stool,True),('BrokenCounter',counter,True))):
        model=Model(label,171901+idx)
        if fn == backbar:
            fn(model)
        else:
            fn(model,damage)
        model.export(((idx%4)*3.8,(idx//4)*3.8,0))
    bind_surfaces(OUT)
    relative_to_blend(OUT)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TavernFurniture.blend'),relative_remap=False)


if __name__ == '__main__':
    export_set()
