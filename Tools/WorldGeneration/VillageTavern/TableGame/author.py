"""Folding medieval tables board. Working measurements are in centimetres."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

OUT=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/TableGame'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
material=bpy.data.materials.new('TablesAtlas')
material.use_nodes=True
nodes,links=material.node_tree.nodes,material.node_tree.links
bsdf=nodes.get('Principled BSDF')
def texture(suffix):
    image=bpy.data.images.load(str(OUT/('T_TavernTables_'+suffix+'.png')))
    image.filepath='//'+image.name
    if suffix!='Color': image.colorspace_settings.name='Non-Color'
    node=nodes.new('ShaderNodeTexImage')
    node.image=image
    return node.outputs['Color']
links.new(texture('Color'),bsdf.inputs['Base Color'])
split=nodes.new('ShaderNodeSeparateColor')
links.new(texture('ORM'),split.inputs[0])
links.new(split.outputs[1],bsdf.inputs['Roughness'])
links.new(split.outputs[2],bsdf.inputs['Metallic'])
dx=nodes.new('ShaderNodeVectorMath')
dx.operation='MULTIPLY_ADD'
links.new(texture('Normal'),dx.inputs[0])
dx.inputs[1].default_value=(1,-1,1)
dx.inputs[2].default_value=(0,1,0)
normal=nodes.new('ShaderNodeNormalMap')
links.new(dx.outputs[0],normal.inputs['Color'])
links.new(normal.outputs[0],bsdf.inputs['Normal'])

def atlas(tile,u,v):
    if isinstance(tile,tuple):
        kind,number=tile
        if kind=='field':
            return ((number*1024+4+1016*u)/2048,1-(4+1016*v)/2048)
        c=(number-1)%3
        r=(number-1)//3
        return ((1536+(c+.025+u*.95)*512/3)/2048,1-(1536+(r+.025+v*.95)*256)/2048)
    return ((512*(tile%4)+5+502*u)/2048,1-(1024+512*(tile//4)+5+502*v)/2048)


def rect(x0,y0,x1,y1):
    return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]


class Joinery:
    def __init__(self,level,ruined):
        self.vertices=[]
        self.faces=[]
        self.uv=[]
        self.smooth=[]
        self.level=level
        self.ruined=ruined
        self.rng=random.Random(8165+ruined)

    def vertex(self,x,y,z):
        self.vertices.append((x/100.,y/100.,z/100.))
        return len(self.vertices)-1

    def face(self,points,coords,smooth=False):
        self.faces.append(points)
        self.uv.append(coords)
        self.smooth.append(smooth)

    def board(self,poly,z0,z1,tile,bevel=.075,grain='x',field=None):
        # Four perimeter loops give the wood a narrow planed edge, including on broken outlines.
        p=[Vector(v) for v in poly]
        lo=[min(q[i] for q in p) for i in range(2)]
        hi=[max(q[i] for q in p) for i in range(2)]
        if sum(p[i].x*p[(i+1)%len(p)].y-p[(i+1)%len(p)].x*p[i].y for i in range(len(p)))<0:
            p.reverse()
        inset=[]
        for i,q in enumerate(p):
            prev=(q-p[i-1]).normalized()
            follow=(p[(i+1)%len(p)]-q).normalized()
            left=Vector((-prev.y,prev.x))
            right=Vector((-follow.y,follow.x))
            inset.append(q+(left+right)*min(bevel*2.2,bevel/max(.32,1+left.dot(right))))
        levels=[(inset,z0),(p,z0+bevel),(p,z1-bevel),(inset,z1)] if self.level<2 else [(p,z0),(p,z1)]
        rings=[[self.vertex(*q,z) for q in loop] for loop,z in levels]
        phase=self.rng.uniform(.03,.29)
        def top_uv(q):
            if field:
                xmin,xmax=field
                return atlas(('field',int(self.ruined)),(q.x-xmin)/(xmax-xmin),(q.y+13.38)/26.76)
            along=0 if grain=='x' else 1
            long=(q[along]-lo[along])/max(.01,hi[along]-lo[along])
            across=(q[1-along]-lo[1-along])/max(.01,hi[1-along]-lo[1-along])
            return atlas(tile,phase+across*.43,.04+long*.88)
        self.face(rings[0][::-1],[top_uv(q) for q in levels[0][0][::-1]])
        self.face(rings[-1],[top_uv(q) for q in levels[-1][0]])
        for i,q in enumerate(p):
            j=(i+1)%len(p)
            delta=p[j]-q
            along_long=abs(delta[0 if grain=='x' else 1])>=abs(delta[1 if grain=='x' else 0])
            edgetile=tile if along_long or tile not in (0,1,2) else 3
            for n in range(len(rings)-1):
                zlo=levels[n][1]
                zhi=levels[n+1][1]
                ua=.15+phase+(.40*(zlo-z0)/(z1-z0))
                ub=.15+phase+(.40*(zhi-z0)/(z1-z0))
                extent=.06+min(.86,delta.length/20.)
                self.face([rings[n][i],rings[n][j],rings[n+1][j],rings[n+1][i]],
                          [atlas(edgetile,ua,.045),atlas(edgetile,ua,extent),
                           atlas(edgetile,ub,extent),atlas(edgetile,ub,.045)])

    def turning(self,origin,profile,tile,axis='z',checker=False):
        count=(24,16,10)[self.level] if checker else (12,9,7)[self.level]
        x,y,z=origin
        rings=[]
        for r,h in profile:
            ring=[]
            for k in range(count):
                a=math.tau*k/count
                ra,rb=r*math.cos(a),r*math.sin(a)
                ring.append(self.vertex(x+ra, y+rb, z+h) if axis=='z' else self.vertex(x+ra,y+h,z-rb))
            rings.append(ring)
        for cap in (0,len(rings)-1):
            order=list(range(count))
            if cap==0:order.reverse()
            self.face([rings[cap][k] for k in order],
                      [atlas(tile,.5+.4*math.cos(math.tau*k/count),.5+.4*math.sin(math.tau*k/count)) for k in order])
        extent=max(.1,max(h for _,h in profile)-min(h for _,h in profile))
        for t in range(len(rings)-1):
            for j in range(count):
                k=(j+1)%count
                a=.05+.88*j/count
                b=.05+.88*(j+1)/count
                h0=.06+.86*(profile[t][1]-profile[0][1])/extent
                h1=.06+.86*(profile[t+1][1]-profile[0][1])/extent
                self.face([rings[t][j],rings[t][k],rings[t+1][k],rings[t+1][j]],
                          [atlas(tile,a,h0),atlas(tile,b,h0),atlas(tile,b,h1),atlas(tile,a,h1)],True)

    def die(self,x,y,z,yaw,up):
        # A clipped cube with six atlas faces. The opposing faces always add to seven.
        size=.64
        core=.53
        rot=math.radians(yaw)
        points={}
        def idx(v):
            key=tuple(round(float(q),4) for q in v)
            if key not in points:
                a,b,c=key
                points[key]=self.vertex(x+a*math.cos(rot)-b*math.sin(rot),y+a*math.sin(rot)+b*math.cos(rot),z+size+c)
            return points[key]
        axes=[Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))]
        high=[1,3,2] if up==2 else [2,3,6]
        for axis in range(3):
            u=axes[(axis+1)%3]
            v=axes[(axis+2)%3]
            for sign in (-1,1):
                n=axes[axis]*sign
                vectors=[n*size+u*i*core+v*sign*j*core for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]]
                tile=('dice',high[axis] if sign>0 else 7-high[axis])
                self.face([idx(q) for q in vectors],[atlas(tile,i,j) for i,j in [(0,0),(1,0),(1,1),(0,1)]])
        def corner_face(vertices,normal):
            if (vertices[1]-vertices[0]).cross(vertices[2]-vertices[0]).dot(normal)<0:vertices.reverse()
            self.face([idx(i) for i in vertices],[atlas(5,u,v) for u,v in [(0,0),(1,0),(1,1),(0,1)][:len(vertices)]])
        for a in range(3):
            b=(a+1)%3;c=(a+2)%3
            for sa in (-1,1):
                for sb in (-1,1):
                    n=axes[a]*sa+axes[b]*sb
                    pa=axes[a]*sa*size+axes[b]*sb*core
                    pb=axes[a]*sa*core+axes[b]*sb*size
                    corner_face([pa-axes[c]*core,pb-axes[c]*core,pb+axes[c]*core,pa+axes[c]*core],n)
        for i in (-1,1):
            for j in (-1,1):
                for k in (-1,1):
                    n=Vector((i,j,k))
                    corner_face([n*core+axes[a]*n[a]*(size-core) for a in range(3)],n)

    def build(self):
        oak=2 if self.ruined else 0
        for side in (-1,1):
            lo,hi=(-20.58,-.08) if side<0 else (.08,20.58)
            broken=self.ruined and side>0
            for j in range(4):
                y=-14.55+j*7.275
                top=y+7.267
                outline=rect(lo,y,hi,top)
                if broken and j==3:
                    outline=[(lo,y),(hi,y),(hi,8.25),(17.83,8.8),(18.44,9.79),
                             (16.21,10.18),(16.98,11.35),(14.8,11.91),(15.22,13.19),(13.16,14.55),(lo,14.55)]
                self.board(outline,0.,.88,oak)
            x0,x1=lo+1.,hi-1.
            shape=rect(x0,-13.38,x1,13.38)
            if broken:shape=[(x0,-13.38),(x1,-13.38),(x1,8.1),(17.36,8.55),(17.8,9.13),(15.67,9.96),
                             (15.92,11.34),(14.3,11.48),(14.67,12.66),(13.46,13.38),(x0,13.38)]
            self.board(shape,.879,1.015,6,.035,field=(x0,x1))
            for edge in (-1,1):
                y=edge*14.
                rail_end=13.19 if broken and edge==1 else hi
                rail=rect(lo,y-.55,rail_end,y+.55)
                if broken and edge==1:
                    rail=[(lo,y-.55),(12.86,y-.55),(13.16,y-.28),(12.77,y-.07),(13.06,y+.23),
                          (12.71,y+.55),(lo,y+.55)]
                self.board(rail,.88,2.26,oak,.11)
            for xmid in (lo+.47,hi-.47):
                ymax=7.56 if broken and xmid>15 else 13.45
                self.board(rect(xmid-.47,-13.45,xmid+.47,ymax),.88,2.18,oak,.085,'y')
        for yc in (-9.9,9.9):
            for side in (-1,1):
                self.board(rect(-.84 if side<0 else .18,yc-.66,-.18 if side<0 else .84,yc+.66),2.17,2.25,4,.028)
                self.turning((side*.64,yc,2.25),[(.11,0),(.13,.035),(.082,.09)],4)
            for j in range(3):
                self.turning((0,yc-.64+j*.43,2.27),[(.14,0),(.18,.05),(.18,.36),(.14,.41)],4,'y')
        # A hammered clasp plate and its receiving plate meet when the case is folded.
        for s in (-1,1):
            self.board(rect(s*19.91-.32,-1.1,s*19.91+.32,1.1),2.18,2.275,4,.03,'y')
            for y in (-.82,.82):self.turning((s*19.91,y,2.275),[(.105,0),(.13,.04),(.09,.085)],4)
        if self.ruined:
            stock=[(-12.6,-7.1,1),(-3.3,-10.,5),(9.6,8.5,1),(3.9,-9.6,5),(-14.1,9.7,5)]
        else:
            # Fifteen turned pieces per side; leave two open points for the dice throw.
            groups=[(-1,-1,0,2,5),(-1,-1,4,4,1),(-1,-1,5,1,1),(-1,1,1,3,1),
                    (-1,1,4,3,5),(1,-1,1,4,5),(1,-1,3,1,5),(1,1,0,5,1),
                    (1,1,5,3,5),(-1,1,2,2,1),(1,-1,0,2,5)]
            stock=[]
            for half,edge,column,amount,tile in groups:
                x0=-19.58 if half<0 else 1.08
                x=x0+(column+.5)*18.5/6
                for i in range(amount):
                    stock.append((x+self.rng.uniform(-.09,.09),edge*(11.87-i*2.38)+self.rng.uniform(-.05,.05),tile))
        for x,y,tile in stock:
            profile=[(.96,0),(1.086,.074),(1.098,.18),(1.065,.235),(1.09,.295),(1.04,.395),
                     (.89,.445),(.835,.42),(.78,.394),(.725,.419),(.617,.422)]
            if self.level:profile=[(.97,0),(1.086,.08),(1.085,.29),(.96,.419),(.72,.421)]
            self.turning((x,y,1.015),profile,tile,checker=True)
        self.die(-7.2,-.65,1.015,22,2)
        if not self.ruined:self.die(5.6,1.86,1.015,-16,6)

    def object(self,name):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices,[],self.faces)
        mesh.update()
        uv=mesh.uv_layers.new(name='AtlasUV')
        for poly,coords,smoothing in zip(mesh.polygons,self.uv,self.smooth):
            poly.use_smooth=smoothing
            for i,point in zip(poly.loop_indices,coords):uv.data[i].uv=point
        mesh.materials.append(material)
        obj=bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        obj.modifiers.new('Export triangles','TRIANGULATE')
        return obj


for damaged in (False,True):
    name='SM_TavernTablesBoard'+('Ruined' if damaged else '')
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    for lod in range(3):
        joinery=Joinery(lod,damaged)
        joinery.build()
        joinery.object(name+'_LOD'+str(lod)).parent=group
    bpy.ops.object.select_all(action='DESELECT')
    for o in [group,*group.children]:o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,
        use_custom_props=True,add_leaf_bones=False,path_mode='STRIP')
    for o in group.children:
        if not o.name.endswith('LOD0'):o.hide_set(True);o.hide_render=True
    if damaged:group.location.y=.38
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TavernTablesBoard.blend'),relative_remap=False)
