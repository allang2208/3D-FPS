"""Author the apothecary's drying horse, botanical specimens, wicker sieve and pots."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


OUT = Path(__file__).resolve().parent
TAU = math.tau
bpy.ops.wm.read_factory_settings(use_empty=True)


class Mesh:
    def __init__(self):
        self.vertices,self.faces,self.regions,self.uvs = [],[],[],[]

    def vertex(self,xyz):
        self.vertices.append(tuple(v/100 for v in xyz))
        return len(self.vertices)-1

    def poly(self,indices,region,uv=None,smooth=True):
        indices=tuple(indices)
        if len(indices)>4:
            # Flat end grain and reed caps are convex. Triangulate before FBX
            # export so Blender writes the same tangent basis as the UE mesh.
            for j in range(1,len(indices)-1):
                self.poly((indices[0],indices[j],indices[j+1]),region,
                          (uv[0],uv[j],uv[j+1]),False)
            return
        self.faces.append(indices)
        self.regions.append((region,smooth))
        self.uvs.append(uv or [(0,0),(1,0),(1,1),(0,1)][:len(indices)])

    def tube(self,points,radii,region,sides=7):
        points = [Vector(p) for p in points]
        if isinstance(radii,(int,float)):
            radii = [radii]*len(points)
        rings,first_axis,distance = [],None,0.
        for i,(center,radius) in enumerate(zip(points,radii)):
            tangent = (points[min(len(points)-1,i+1)]-points[max(0,i-1)]).normalized()
            if first_axis is None:
                first_axis = tangent.cross(Vector((1,0,0)) if abs(tangent.x)<.8 else Vector((0,0,1))).normalized()
            side = (first_axis-first_axis.dot(tangent)*tangent).normalized()
            across = tangent.cross(side).normalized()
            first_axis = side
            ring = [self.vertex(center+radius*(side*math.cos(TAU*j/sides)+across*math.sin(TAU*j/sides))) for j in range(sides)]
            if rings:
                old = rings[-1]
                next_distance = distance+(center-points[i-1]).length/24
                for j in range(sides):
                    k=(j+1)%sides
                    self.poly((old[j],old[k],ring[k],ring[j]),region,
                              ((j/sides,distance),((j+1)/sides,distance),((j+1)/sides,next_distance),(j/sides,next_distance)))
                distance = next_distance
            rings.append(ring)
        self.poly(reversed(rings[0]),region,[(.5+.5*math.cos(TAU*i/sides),.5+.5*math.sin(TAU*i/sides)) for i in range(sides)])
        self.poly(rings[-1],region,[(.5+.5*math.cos(TAU*i/sides),.5+.5*math.sin(TAU*i/sides)) for i in range(sides)])

    def circle(self,r,z,thickness,material,phase=0,ripple=0):
        self.tube([((r+ripple*math.cos(23*a))*math.cos(a),(r+ripple*math.cos(23*a))*math.sin(a),z)
                   for a in (phase+TAU*i/96 for i in range(97))],thickness,material)

    def lathe(self,profile):
        old = []
        n = 64
        for radius,z,material in profile:
            ring = []
            for j in range(n):
                a=TAU*j/n
                r = radius*(1+.009*math.sin(3*a+.04*z)+.006*math.cos(7*a))
                ring.append(self.vertex((r*math.cos(a),r*math.sin(a),z)))
            if old:
                for j in range(n):
                    k=(j+1)%n
                    self.poly((old[j],old[k],ring[k],ring[j]),material,
                              ((j/n,oldz/28),((j+1)/n,oldz/28),((j+1)/n,z/28),(j/n,z/28)))
            old,oldz = ring,z

    def beam(self,start,end,width,depth,material):
        # A chamfered, slightly irregular octagonal cross-section catches edge light.
        a,b = Vector(start),Vector(end)
        axis=(b-a).normalized()
        up=Vector((0,1,0)) if abs(axis.y)<.8 else Vector((0,0,1))
        vx=axis.cross(up).normalized()
        vy=axis.cross(vx).normalized()
        h,w=depth*.5,width*.5
        c=min(w,h)*.19
        profile=[(-w+c,-h),(w-c,-h),(w,-h+c),(w,h-c),(w-c,h),(-w+c,h),(-w,h-c),(-w,-h+c)]
        rings=[[self.vertex(pos+vx*x+vy*y) for x,y in profile] for pos in (a,b)]
        for i in range(8):
            j=(i+1)%8
            self.poly((rings[0][i],rings[0][j],rings[1][j],rings[1][i]),material,
                      ((0,0),(.24,0),(.24,(b-a).length/45),(0,(b-a).length/45)),False)
        for ids in (rings[0][::-1],rings[1]):
            self.poly(ids,material,[(x/15,y/15) for x,y in profile],False)

    def export(self,role):
        name='SM_Herbalist'+role
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices,[],self.faces)
        mesh.update()
        slots=list(dict.fromkeys(slot for slot,_ in self.regions))
        for slot in slots:
            mesh.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
        uv=mesh.uv_layers.new(name='SurfaceUV')
        for p,(material,smooth),corners in zip(mesh.polygons,self.regions,self.uvs):
            p.material_index=slots.index(material)
            p.use_smooth=smooth
            for index,coord in zip(p.loop_indices,corners):
                uv.data[index].uv=coord
        obj=bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
                                 axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False)


def pot():
    m=Mesh()
    # A hollow, wheel-thrown clay body with glazed shoulder and a recessed earth bed.
    m.lathe([(.001,0,'Clay'),(8.7,0,'Clay'),(9.3,.55,'Clay'),(9.2,1.2,'Clay'),
             (8.75,1.62,'Clay'),(9.5,2.7,'Clay'),(12.14,8.8,'Clay'),(13.63,15,'Clay'),
             (13.71,15.6,'Slip'),(13.35,16.15,'Slip'),(13.47,16.6,'Slip'),(14.12,17.3,'Clay'),
             (14.22,18.1,'Slip'),(13.89,18.56,'Slip'),(12.82,18.53,'Slip'),
             (12.39,18.06,'Slip'),(12.38,17.3,'Clay'),(12.13,16.5,'Clay'),
             (10.8,10.7,'Clay'),(7.9,2.5,'Clay'),(.001,2.5,'Clay')])
    m.lathe([(12.28,16.55,'Earth'),(10.4,16.64,'Earth'),(6.8,16.92,'Earth'),(.001,16.8,'Earth')])
    return m


def sieve():
    m=Mesh()
    # Warp and weft truly weave above and below one another; light passes through the bottom.
    for axis in range(2):
        for i in range(-8,9):
            v=i*1.64
            half=math.sqrt(15.05**2-v*v)
            points=[]
            for j in range(25):
                u=-half+2*half*j/24
                z=1.0+.26*math.cos(math.pi*(u/1.64+i)+axis*math.pi)+.006*(u*u+v*v)
                points.append((u,v,z) if axis==0 else (v,u,z))
            m.tube(points,.43,'Wicker',5)
    for i in range(23):
        a=TAU*i/23
        m.tube([(r*math.cos(a),r*math.sin(a),z) for r,z in ((14.4,1.7),(15,3.0),(15.8,5.2),(16.3,7.5))],.46,'Wicker')
    for i in range(5):
        m.circle(14.8+i*.38,2.9+i*.88,.50,'Wicker',0,.37*(-1)**i)
    for z in (6.8,7.6):
        m.circle(16.3,z,.60,'Wicker')
    for i in range(23):
        a=TAU*i/23
        m.tube([((16.3+.72*math.cos(b))*math.cos(a+.014*math.sin(b)),
                 (16.3+.72*math.cos(b))*math.sin(a+.014*math.sin(b)),7.2+1.02*math.sin(b))
                 for b in (TAU*j/12 for j in range(13))],.20,'Twine',5)
    return m


def leaf(m,base,out,side,length,width):
    # Closed folded leaf with a raised midrib, curled blade, and asymmetric margin.
    rows=[]
    for t,w in ((0,.03),(.16,.49),(.39,1.),(.61,.87),(.84,.49),(1.,.015)):
        center=base+out*(t*length)+Vector((0,0,-2.8*t*t))
        ridge=Vector((0,0,.27*width*w))
        rows.append([m.vertex(center-side*(w*width)),m.vertex(center+ridge),
                     m.vertex(center+side*(w*width*.91)),m.vertex(center-ridge*.48)])
    for i in range(len(rows)-1):
        for j in range(4):
            m.poly((rows[i][j],rows[i+1][j],rows[i+1][(j+1)%4],rows[i][(j+1)%4]),'Leaf')


def herbs(blossoms):
    rng=random.Random(114 if blossoms else 213)
    m=Mesh()
    # Hanging loop is centred on the rail; cord twists and knots hold all stems together.
    m.tube([(0,2.9*math.cos(a),2.7*math.sin(a)-.1) for a in (TAU*i/23 for i in range(24))],.35,'Twine')
    m.tube([(0,-.5,-2.4),(-.27,.7,-5.5),(0,.25,-9.4)],.37,'Twine')
    for i in range(9):
        a=TAU*i/9+rng.uniform(-.16,.16)
        spread=rng.uniform(4,9)
        length=rng.uniform(26,38)
        ox,oy=rng.uniform(-1.1,1.1),rng.uniform(-1.1,1.1)
        def stem(t):
            return Vector((ox+math.cos(a)*spread*t*t,oy+math.sin(a)*spread*t*t,-5.3-length*t))
        m.tube([stem(j/8) for j in range(9)],[.29-.16*j/8 for j in range(9)],'Wicker',6)
        for j in range(2,7):
            direction=a+(-1 if j%2 else 1)*1.06+rng.uniform(-.14,.14)
            out=Vector((math.cos(direction),math.sin(direction),-.75)).normalized()
            side=Vector((-math.sin(direction),math.cos(direction),.10)).normalized()
            leaf(m,stem(j/8.2),out,side,rng.uniform(3.7,6.5) if blossoms else rng.uniform(5.0,9.1),
                 rng.uniform(.45,.82) if blossoms else rng.uniform(1.0,1.7))
        if blossoms:
            for j in range(9):
                t=.77+j*.027
                b=stem(t)
                side=Vector((math.cos(j*2.4),math.sin(j*2.4),-.4))
                # Papery mature seed calyces cluster around the dried flowering spike.
                m.tube([b,b+side*.89,b+side*1.64],[.19,.64,.12],'Twine',6)
    for i in range(4):
        m.circle(1.72,-9.3-i*.45,.28,'Twine')
    m.tube([(1.4,.5,-10.0),(2.4,.8,-11.1),(2.2,1.6,-12.0),(1.7,.9,-11.6),(2.9,2,-15)],.31,'Twine')
    return m


def horse():
    m=Mesh()
    for x in (-61,61):
        m.beam((x,-17,2.4),(x,17,2.4),8,4.8,'Oak')
        m.beam((x,0,2.4),(x,0,165),6,6,'Oak')
        m.beam((x,-14,5),(x,-1,36),3.0,4.1,'Oak')
        m.beam((x,14,5),(x,1,36),3.0,4.1,'Oak')
        for z in (18,137,158.9):
            m.tube([(x,-3.35,z),(x,3.35,z)],.73,'Wicker')
    for y in (-11,0,11):
        m.beam((-65,y,18.5),(65,y,18.5),3.,10.4,'Oak')
    for x in (-61,61):
        m.beam((x,-16,15.6),(x,16,15.6),5.5,3,'Oak')
    m.beam((-61,0,130),(-34,0,158),3.2,3.7,'Oak')
    m.beam((61,0,130),(34,0,158),3.2,3.7,'Oak')
    m.tube([(-68,0,162),(-66,0,162),(66,0,162),(68,0,162)],[1.7,2.15,2.15,1.7],'Oak',16)
    return m


def lip():
    m=Mesh()
    m.beam((-66,0,2.2),(66,0,2.2),4.4,1.7,'Oak')
    for x in (-61,0,61):
        m.tube([(x,-1.1,1.8),(x,1.1,1.8)],.39,'Wicker')
    return m


for role,make in (('WindowPot',pot),('GatheringSieve',sieve),('DryingStand',horse),
                  ('DryBunch',lambda:herbs(False)),('FlowerBunch',lambda:herbs(True)),('ShelfLip',lip)):
    make().export(role)
