"""Build a projecting masonry cook hearth on the east gable. Inputs in Unreal local cm."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


out = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/KitchenHearth'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
palette = {
    'HearthStone': (.35, .32, .27), 'Soot': (.075, .068, .058),
    'Iron': (.14, .12, .105), 'Wood': (.22, .135, .075),
    'Ash': (.34, .31, .27), 'Coal': (.06, .05, .045), 'Ember': (.93, .18, .019),
}
materials = {}
for key, color in palette.items():
    materials[key] = bpy.data.materials.new(key)
    materials[key].diffuse_color = (*color, 1)


class Hearth:
    def __init__(self, ruined, lod):
        self.ruined, self.lod = ruined, lod
        self.rng = random.Random(72930)
        self.verts, self.faces, self.slots, self.smoothing = [], [], [], []

    def ring(self, points):
        start = len(self.verts)
        self.verts.extend(points)
        return list(range(start, len(self.verts)))

    def face(self, ids, mat, smooth=False):
        self.faces.append(tuple(ids))
        self.slots.append(mat)
        self.smoothing.append(smooth)

    def band(self, lo, hi, mat, smooth=False):
        for i in range(len(lo)):
            j = (i+1) % len(lo)
            self.face((lo[i], lo[j], hi[j], hi[i]), mat, smooth)

    def stone(self, x1, x2, y1, y2, z1, z2, mat='HearthStone', wear=1.25):
        # An eight-sided drafted block with three different chipped arrises.
        rng = self.rng
        dx, dy, dz = x2-x1, y2-y1, z2-z1
        radius = min(wear, min(dx, dy, dz)*.18)
        cuts = [radius*rng.uniform(.6, 1.5) for _ in range(4)]
        layers = []
        profiles=((z1,radius*.6),(z1+radius,0),(z2-radius,0),(z2,radius*.65))
        if self.lod==1:
            profiles=((z1,radius*.5),(z1+radius,0),(z2,radius*.5))
        elif self.lod==2:
            profiles=((z1,.12),(z2,.12))
        for height,inset in profiles:
            a, b, c, d = x1+inset, x2-inset, y1+inset, y2-inset
            p, q, r, s = cuts
            ring = [(a+p,c), (b-q,c), (b,c+q), (b,d-r), (b-r,d), (a+s,d), (a,d-s), (a,c+p)]
            layers.append(self.ring([(x,y,height) for x,y in ring]))
        self.face(reversed(layers[0]), mat)
        for lower, upper in zip(layers, layers[1:]):
            self.band(lower, upper, mat)
        self.face(layers[-1], mat)

    def side_course(self, ya, yb, z, z2, n, x1=0.6, x2=76.6):
        steps = [x1] + [x1+(x2-x1)*i/n+self.rng.uniform(-5,5) for i in range(1,n)] + [x2]
        for a,b in zip(steps,steps[1:]):
            self.stone(a+.2,b-.2,ya,yb,z+.16,z2-.16)

    def transverse_course(self, x1,x2,y1,y2,z1,z2,n):
        steps = [y1] + [y1+(y2-y1)*i/n+self.rng.uniform(-6,6) for i in range(1,n)] + [y2]
        for a,b in zip(steps,steps[1:]):
            self.stone(x1,x2,a+.22,b-.22,z1+.15,z2-.15)

    def rect(self, x1,x2,width,z):
        return self.ring([(x1,-width,z),(x2,-width,z),(x2,width,z),(x1,width,z)])

    def duct(self, profiles):
        # Outer stone skin, inner soot-blackened bore and two annular end faces.
        outs, ins = [], []
        for z,xa,xb,w,gauge in profiles:
            outs.append(self.rect(xa,xb,w,z))
            ins.append(self.rect(xa+gauge,xb-gauge,w-gauge,z))
        for low, high in zip(outs,outs[1:]):
            self.band(low,high,'HearthStone')
        for low, high in zip(ins,ins[1:]):
            self.band(high,low,'Soot')
        self.band(ins[0],outs[0],'Soot')
        self.band(outs[-1],ins[-1],'HearthStone')

    def tube(self, points, radii, mat, sides=None, loop=False):
        points = [Vector(p) for p in points]
        sides = sides or (9,7,5)[self.lod]
        radii = [radii]*len(points) if isinstance(radii,(int,float)) else radii
        rings, guide = [], None
        for i,(p,radius) in enumerate(zip(points,radii)):
            a = points[i-1] if loop or i else p
            b = points[(i+1)%len(points)] if loop or i<len(points)-1 else p
            direction = (b-a).normalized()
            if guide is None:
                guide = Vector((1,0,0)) if abs(direction.x)<.92 else Vector((0,1,0))
            guide = (guide-direction*guide.dot(direction)).normalized()
            v = direction.cross(guide)
            rings.append(self.ring([p+radius*(guide*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))
                                    for i in range(sides)]))
        for lo,hi in zip(rings,rings[1:]):
            self.band(lo,hi,mat,True)
        if loop:
            self.band(rings[-1],rings[0],mat,True)
        else:
            self.face(reversed(rings[0]),mat)
            self.face(rings[-1],mat)

    def link(self, x,y,z, rotate=False):
        n = (18,12,8)[self.lod]
        pts=[]
        for i in range(n):
            a=math.tau*i/n
            horiz=1.38*math.cos(a)
            pts.append((x+(horiz if rotate else 0),y+(0 if rotate else horiz),z+2.05*math.sin(a)))
        self.tube(pts,.39,'Iron',loop=True)

    def pot(self):
        x,y = 47,0
        # Cast-iron belly rolls around the lip and descends into the hollow pot.
        sections=[(.8,48),(7,48),(12.3,50.2),(15.2,55.5),(17,63),(16.6,68.1),
                  (15.8,71.7),(16.1,72.4),(16.9,72.8),(16.85,73.7),(16.2,74.3),
                  (15.1,74.3),(14.7,73.7),(14.95,71.8),(15.5,68),(15.65,63),
                  (14.1,55.7),(11.4,51.3),(7,49.2),(.8,49.2)]
        rings=[]
        n=(62,38,22)[self.lod]
        for radius,z in sections:
            rings.append(self.ring([(x+radius*math.cos(i*math.tau/n), y+radius*math.sin(i*math.tau/n),z)
                                    for i in range(n)]))
        for lo,hi in zip(rings,rings[1:]):
            self.band(lo,hi,'Iron',True)
        self.face(reversed(rings[0]),'Iron')
        self.face(rings[-1],'Iron')
        for sign in (-1,1):
            self.tube([(x-3,sign*15.8,67),(x-2.6,sign*17.5,71.4),(x-1.7,sign*17.7,75.2),
                       (x+1.7,sign*17.7,75.2),(x+2.6,sign*17.5,71.4),(x+3,sign*15.8,67)],1.0,'Iron')
        n=(26,16,10)[self.lod]
        self.tube([(x+.6*math.sin(math.pi*i/n),y+17.4*math.cos(math.pi*i/n),73.7+18.9*math.sin(math.pi*i/n))
                   for i in range(n+1)],.66,'Iron')
        self.tube([(x,0,97),(x,0,93),(x+.8,0,92),(x+1.8,0,93),(x+1.9,0,94.4)],.62,'Iron')

    def ember_bed(self):
        # An ash blanket with locally collapsed slivers of carbon, resting inside the chamber.
        rng = self.rng
        rng.seed(2161)
        def clink(x,y,z,rx,ry,h,mat):
            n=(10,8,6)[self.lod]
            phase=rng.uniform(-.3,.3)
            contour=[(math.cos(phase+math.tau*i/n)*rx*rng.uniform(.83,1),
                      math.sin(phase+math.tau*i/n)*ry*rng.uniform(.83,1)) for i in range(n)]
            base=self.ring([(x+a,y+b,z) for a,b in contour])
            crown=self.ring([(x+.63*a,y+.63*b,z+h*rng.uniform(.72,1)) for a,b in contour])
            self.face(reversed(base),mat)
            self.band(base,crown,mat)
            tip=self.ring([(x+.06*rx,y,z+h)])[0]
            for i in range(n):
                self.face((crown[i],crown[(i+1)%n],tip),mat)
        clink(46,0,26.3,32,50,2.5,'Ash' if self.ruined else 'Coal')
        for i in range((31,22,14)[self.lod]):
            a=i*2.39996
            r=math.sqrt(rng.random())
            x=47+26*r*math.cos(a)
            y=44*r*math.sin(a)
            clink(x,y,27,rng.uniform(2.8,6),rng.uniform(3,8),rng.uniform(2.1,4.4),
                  ('Ash' if i%3 else 'Coal') if self.ruined else 'Coal')
            if not self.ruined and i%3==0:
                clink(x+1.4,y-.5,29.25,2.3,3.4,1.55,'Ember')
        if not self.ruined:
            for a,b in [((32,-20,31),(56,14,32)),((42,-26,32),(65,12,33)),((51,-20,36),(25,14,35))]:
                self.tube([a,b],[3.15,2.7],'Wood',sides=(10,8,6)[self.lod])
                p,q=Vector(a),Vector(b)
                self.tube([p.lerp(q,.26),p.lerp(q,.69)],[3.32,3.1],'Coal')
        else:
            self.tube([(52,22,28),(54,7,29),(62,-8,27.9)],[2.8,2.3,.7],'Coal')

    def build(self):
        # Foundation and an exposed staggered front apron, with a recessed solid mortar bed.
        self.stone(0,103.2,-71.9,71.9,0,7.7,'Soot',.75)
        self.transverse_course(.2,61,-73,73,0,10,4)
        self.transverse_course(61,104.8,-73,73,0,10,3)
        self.stone(0,83.5,-70.2,70.2,9,23.8,'Soot',.5)
        self.transverse_course(.6,38,-71.3,71.3,9,26.5,4)
        self.transverse_course(38,84.8,-71.3,71.3,9,26.5,3)
        # Staggered rear fireback, jambs, dark firebrick faces and projecting corbels.
        self.stone(.7,11.6,-68,68,25.9,137.5,'Soot',.6)
        for sign in (-1,1):
            ya,yb=sorted((sign*52.1,sign*69.2))
            self.stone(.9,74.7,ya+.8,yb-.8,25.9,135,'Soot',.65)
        for course in range(7):
            z=26.5+course*14.8
            self.transverse_course(.8,12.45,-54,54,z,z+14.8,3+course%2)
            for ya,yb in ((-69.8,-51.9),(51.9,69.8)):
                self.side_course(ya,yb,z,z+14.8,2+course%2)
        # Replace the hottest inner faces with an articulated blackened liner.
        for course in range(6):
            z=27+15*course
            edges=[-51.85,-21,14,51.85] if course%2==0 else [-51.85,-37,-2,30,51.85]
            for a,b in zip(edges,edges[1:]):
                self.stone(12.05,13.3,a+.27,b-.27,z+.32,z+14.65,'Soot',.31)
        for side in (-1,1):
            ya,yb=sorted((side*49.6,side*71.4))
            for n in range(2):
                self.stone(5,77.2+n*3.6,ya,yb,129.9+n*5.7,135.7+n*5.7)
        self.duct([(140.9,.6,84.5,71,6.5),(149.2,.6,84.5,71,6.5),
                   (184,4.1,69.5,51.3,6.2),(222,12.9,55.2,22,6.2),(229,13.1,55.1,21.6,6.2)])
        # Mantel stones remain outside the open throat.
        self.transverse_course(79,85.3,-71.9,71.9,140.7,152.7,5)
        for ya,yb in ((-71.9,-65.1),(65.1,71.9)):
            self.side_course(ya,yb,140.7,152.7,3,.4,79)
        # Continuous open shaft up through the gable roof. External courses ride the inner sleeve.
        self.duct([(225,13.9,54.1,20.6,5.4),(659.8,13.9,54.1,20.6,5.4)])
        height=17.4
        for course in range(25):
            z=225+height*course
            if course%2:
                for ya,yb in ((-21.8,-15.1),(15.1,21.8)):
                    self.stone(13,55,ya,yb,z+.14,z+height-.16,wear=.83)
                for xa,xb in ((13,19),(49,55)):
                    self.stone(xa,xb,-15.3,15.3,z+.14,z+height-.16,wear=.83)
            else:
                for xa,xb in ((13,19.6),(48.4,55)):
                    self.stone(xa,xb,-21.8,21.8,z+.14,z+height-.16,wear=.83)
                for ya,yb in ((-21.8,-15.4),(15.4,21.8)):
                    self.stone(19.3,48.7,ya,yb,z+.14,z+height-.16,wear=.83)
        self.duct([(654,12,56,22.7,7.1),(657.8,10.6,57.4,24.1,8.4),
                   (663.3,10.6,57.4,24.1,8.4),(665,12,56,22.7,7.1)])
        self.ember_bed()
        # Tripod feet are individually forged and seated in the raised fire floor.
        # A wrought crossbar stays under the hood, independent of the cooking tripod.
        self.tube([(45,-54,116),(45,-44,116.7),(46,0,116.2),(45.6,53.5,116)],1.5,'Iron')
        if not self.ruined:
            for angle in (0.12,2.25,4.28):
                angle_offset=angle+.10
                self.tube([(47+28*math.cos(angle),28*math.sin(angle),26.45),
                           (47+24*math.cos(angle_offset),24*math.sin(angle_offset),43),
                           (47+4*math.cos(angle),4*math.sin(angle),103),
                           (47+1.2*math.cos(angle),1.2*math.sin(angle),110.9)],
                          [1.47,1.22,.93,.76],'Iron')
            self.link(47,0,110.7)
            for i in range(5):
                self.link(47,0,108.1-i*2.75,bool(i%2))
            self.pot()
        else:
            for i in range(3):
                self.link(45.6,-25,114.8-i*2.82,bool(i%2))
            self.tube([(28,-35,26.75),(38,-41,27.5),(66,-44,28.5)],[1.2,1.1,.65],'Iron')

    def object(self, name):
        self.build()
        # UE's legacy FBX importer mirrors Y. Reverse the loop winding with the authored mirror.
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in self.verts],[],
                         [tuple(reversed(f)) for f in self.faces])
        mesh.update()
        used=list(dict.fromkeys(self.slots))
        for mat in used:
            mesh.materials.append(materials[mat])
        uv=mesh.uv_layers.new(name='MetricUV')
        for poly,slot,smooth in zip(mesh.polygons,self.slots,self.smoothing):
            poly.material_index=used.index(slot)
            poly.use_smooth=smooth
            axis=max(range(3),key=lambda i:abs(poly.normal[i]))
            axes=((1,2),(0,2),(0,1))[axis]
            scale=.64 if slot in ('HearthStone','Soot') else .22
            for loop in poly.loop_indices:
                p=mesh.vertices[mesh.loops[loop].vertex_index].co
                uv.data[loop].uv=(p[axes[0]]/scale,p[axes[1]]/scale)
        obj=bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        obj.modifiers.new('Export triangles','TRIANGULATE')
        return obj


for ruined in (False,True):
    name='SM_TavernCookHearth'+('Ruined' if ruined else '')
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    items=[]
    for level in range(3):
        item=Hearth(ruined,level).object(name+'_LOD'+str(level))
        item.parent=group
        items.append(item)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [group,*items]:
        obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,
        object_types={'EMPTY','MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',
        use_tspace=True,bake_anim=False,use_custom_props=True,add_leaf_bones=False,path_mode='STRIP')
    for child in items[1:]:
        child.hide_set(True)
        child.hide_render=True
    if ruined:
        group.location.y=1.7
bpy.ops.wm.save_as_mainfile(filepath=str(out/'TavernCookHearth.blend'),relative_remap=False)
