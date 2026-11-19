"""Build the two beam-mounted drying rails. Dimensions are centimetres, suspension axis Y."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

out=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/DryingRack'
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
V=Vector
tau=math.tau
material=bpy.data.materials.new('TavernDryGoods')
material.use_nodes=True
nodes,links=material.node_tree.nodes,material.node_tree.links
shader=nodes.get('Principled BSDF')
def image(label,data=False):
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(out/('T_TavernDryGoods_'+label+'.png')))
    if data:tex.image.colorspace_settings.name='Non-Color'
    tex.image.filepath='//'+tex.image.name
    return tex.outputs['Color']
links.new(image('Color'),shader.inputs['Base Color'])
masks=nodes.new('ShaderNodeSeparateColor')
links.new(image('ORM',True),masks.inputs[0])
links.new(masks.outputs[1],shader.inputs['Roughness'])
links.new(masks.outputs[2],shader.inputs['Metallic'])
dx=nodes.new('ShaderNodeVectorMath')
dx.operation='MULTIPLY_ADD'
dx.inputs[1].default_value=(1,-1,1)
dx.inputs[2].default_value=(0,1,0)
links.new(image('Normal',True),dx.inputs[0])
nrm=nodes.new('ShaderNodeNormalMap')
links.new(dx.outputs[0],nrm.inputs[0])
links.new(nrm.outputs[0],shader.inputs['Normal'])


def uv(tile,u,v):
    # Four texels of padding at each border, including both halves of the iron/endgrain tile.
    if tile=='end':
        tile=7
        u=.516+.478*u
    elif tile==7:
        u=.482*u
    return ((tile%4+.012+.976*u)/4,(1-tile//4+.012+.976*v)/2)


class Rail:
    def __init__(self,lod,broken):
        self.lod,self.broken=lod,broken
        self.verts,self.faces,self.uvs,self.smooth=[],[],[],[]
        self.rope_sides=(10,7,5)[lod]

    def vertex(self,p):
        self.verts.append(tuple(v*.01 for v in p))
        return len(self.verts)-1

    def face(self,ids,tile,coords,smooth=False):
        self.faces.append(ids)
        self.uvs.append([uv(tile,u,v) for u,v in coords])
        self.smooth.append(smooth)

    def tube(self,points,radii,tile,sides=None,lobes=0,phase=0.,endgrain=False):
        points=list(map(V,points))
        sides=sides or self.rope_sides
        if isinstance(radii,(int,float)):radii=[radii]*len(points)
        lengths=[0.]
        for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+(b-a).length)
        rings=[]
        previous=None
        for j,(p,r) in enumerate(zip(points,radii)):
            tangent=(points[min(j+1,len(points)-1)]-points[max(0,j-1)]).normalized()
            guide=previous if previous is not None else (V((1,0,0)) if abs(tangent.x)<.86 else V((0,1,0)))
            u=(guide-tangent*guide.dot(tangent)).normalized()
            v=tangent.cross(u)
            previous=u
            ring=[]
            for i in range(sides):
                a=tau*i/sides
                b=r
                if lobes:b*=1+.083*math.cos(lobes*a+phase+.24*lengths[j]/lengths[-1])+.021*math.sin(3*a+phase)
                ring.append(self.vertex(p+b*(math.cos(a)*u+math.sin(a)*v)))
            rings.append(ring)
        for j,(lower,upper) in enumerate(zip(rings,rings[1:])):
            y0,y1=lengths[j]/lengths[-1],lengths[j+1]/lengths[-1]
            for i in range(sides):
                k=(i+1)%sides
                self.face((lower[i],lower[k],upper[k],upper[i]),tile,
                          ((i/sides,y0),((i+1)/sides,y0),((i+1)/sides,y1),(i/sides,y1)),True)
        disk=[(.5+.47*math.cos(tau*i/sides),.5+.47*math.sin(tau*i/sides)) for i in range(sides)]
        tip='end' if endgrain else tile
        self.face(rings[0][::-1],tip,disk[::-1])
        self.face(rings[-1],tip,disk)

    def coil(self,y,z,turns,radius,spread,thickness):
        pts=[]
        steps=round(turns*(13,9,7)[self.lod])
        for j in range(steps+1):
            t=j/steps
            a=tau*t*turns+.23
            pts.append((radius*math.sin(a),y+(t-.5)*spread,z+radius*math.cos(a)))
        self.tube(pts,thickness,1)

    def hanging_pin(self,y,z):
        self.tube([(-3.7,y,1.65),(-3.7,y,-2.4),(-2.9,y,-4.5),(0,y,-5.3),
                   (2.9,y,-4.5),(3.7,y,-2.4),(3.7,y,1.65)],.57,7)
        self.tube([(-.7,y-.4,-4.5),(-1.6,y-1.15,-6.3),(-2.9,y-1.3,z+3.7),
                   (-3.2,y-1.3,z),(-2,y-1.25,z-2.9),(0,y-1.2,z-3.6),
                   (2.8,y-1.0,z-2.4),(3.3,y-.8,z+.5),(2.5,y-.5,z+3.4),
                   (1.1,y+.3,-6.1),(.5,y+.7,-4.35)],.65,1)
        self.coil(y,z,2.35,3.28,4.4,.58)
        self.tube([(2.9,y+.9,z+.9),(2.6,y+2.4,z-2.3),(2.75,y+3.9,z-5.5),
                   (1.9,y+3.6,z-8.6)],[.68,.62,.5,.24],1)

    def z_at(self,y):
        return -21.8-(.15*(y+39.) if self.broken else 0.)+.47*math.cos(y*.071)

    def braid(self,y,drop):
        top=self.z_at(y)
        self.coil(y,top,1.2,3.05,1.65,.46)
        for strand in range(2):
            pts=[]
            for j in range((20,14,9)[self.lod]+1):
                t=j/(20,14,9)[self.lod]
                a=tau*3*t+strand*math.pi
                pts.append((.65*math.cos(a)+1.4*t, y+.65*math.sin(a)+1.2*t,top-2.-drop*t))
            self.tube(pts,.49,5)

    def bulb(self,x,y,z,r,onion,phase):
        h=r*(2.15 if onion else 1.82)
        profile=[(0,.17),(.08,.58),(.24,.88),(.46,1.),(.65,.85),(.79,.52),(.91,.23),(1,.12)]
        if self.lod==2:profile=[profile[i] for i in (0,2,3,5,7)]
        centers=[(x+.12*math.cos(phase)*t*r,y+.11*math.sin(phase)*t*r,z+t*h) for t,_ in profile]
        self.tube(centers,[s*r for _,s in profile],3 if onion else 2,
                  (26,16,10)[self.lod],5 if onion else 8,phase)
        self.tube([(x,y,z+.12),(x,y,z-.38),(x+.12,y-.26,z-.78)],
                  [r*.24,r*.29,r*.14],5,(9,7,5)[self.lod])
        for j in range((6,3,0)[self.lod]):
            a=tau*j/6+phase
            self.tube([(x+.33*math.sin(a),y+.33*math.cos(a),z-.33),
                       (x+.84*math.sin(a),y+.84*math.cos(a),z-.91),
                       (x+1.07*math.sin(a),y+1.19*math.cos(a),z-1.74-.3*math.cos(a))],
                      [.105,.081,.035],5,4)
        return V(centers[-1])

    def fruit_string(self,y,onion):
        count=5 if onion else 9
        self.braid(y,32 if onion else 38)
        for i in range(count):
            angle=i*2.38+(1.05 if onion else .31)
            radius=(4.1+.48*math.cos(3*i)) if onion else (2.88+.34*math.sin(2.1*i))
            z=self.z_at(y)-17-i*(4.6 if onion else 3.3)
            p=V(((3.65 if onion else 2.8)*math.sin(angle),y+(4.29 if onion else 3.15)*math.cos(angle),z))
            neck=self.bulb(*p,radius,onion,angle)
            attach=V((.7,y+.6,max(z+radius*2.6,self.z_at(y)-36)))
            self.tube([neck,neck.lerp(attach,.38)+V((.15,-.12,.38)),attach],
                      [radius*.15,.4,.23],5)

    def leaf(self,p,angle,size,dry):
        axis=V((math.cos(angle),math.sin(angle),-.66)).normalized()
        side=V((-math.sin(angle),math.cos(angle),0))
        up=axis.cross(side).normalized()
        width=size*(.18 if dry else .29)
        verts=[p,p+axis*(size*.44)-side*width,p+axis*(size*.78)-side*width*.64+up*size*.07,
               p+axis*size+up*size*.13,p+axis*(size*.73)+side*width*.73+up*size*.05,
               p+axis*(size*.37)+side*width,p+axis*(size*.49)+up*size*.085,
               p+axis*(size*.49)-up*size*.055]
        ids=list(map(self.vertex,verts))
        coords=[(.5,.02),(.02,.44),(.17,.77),(.5,.98),(.82,.75),(.98,.36),(.50,.48),(.50,.48)]
        for j in range(6):
            k=(j+1)%6
            for tri in ((6,j,k),(7,k,j)):
                self.face([ids[h] for h in tri],5 if dry else 4,[coords[h] for h in tri])

    def herbs(self,y,broken):
        z=self.z_at(y)
        self.coil(y,z,1.4,3.04,1.4,.46)
        base=V((1.,y+.3,z-10.))
        self.tube([(0,y,z-2.2),(.4,y+.5,z-5),base],.44,1)
        rng=random.Random(77 if broken else 217)
        stems=4 if broken else 12
        for i in range(stems):
            a=i*2.4
            L=rng.uniform(16.,25.) if broken else rng.uniform(22.,37.)
            drift=rng.uniform(5.,8.5)
            top=base+V((.82*math.cos(a),.75*math.sin(a),3.))
            end=base+V((drift*math.cos(a),drift*math.sin(a),-L))
            mid=top.lerp(end,.46)+V((-.7*math.sin(a),.8*math.cos(a),.5))
            self.tube([top,base,mid,end],[.24,.26,.18,.07],5,(6,5,4)[self.lod])
            for j in range(4 if not broken else 2):
                if self.lod==2 and j%2:continue
                t=.33+.19*j
                p=base.lerp(end,t)
                for side in ([1] if broken else [-1,1]):
                    self.leaf(p,a+side*1.07+j*.48,(3.1 if broken else 4.4)*(1.13-.58*t),broken)
        # Twine compresses several stems immediately under the eye.
        radius=1.55
        pts=[]
        for i in range((20,15,10)[self.lod]+1):
            t=i/(20,15,10)[self.lod];a=tau*2.25*t
            pts.append((base.x+radius*math.cos(a),base.y+radius*math.sin(a),base.z-2.5+1.45*t))
        self.tube(pts,.32,1)

    def build(self):
        ys=(-55.,-54.5,-46.,-26.,-7.,14.,31.,48.,54.6,55.)
        self.tube([(.34*math.sin(y*.055),y,self.z_at(y)) for y in ys],
                  [2.35,2.82,2.91,2.64,3.04,2.83,3.03,2.71,2.63,2.32],
                  6 if self.broken else 0,(18,12,8)[self.lod],3,.4,True)
        for y in (-45.,44.):self.hanging_pin(y,self.z_at(y))
        if self.broken:
            self.herbs(25.,True)
            for y,length in ((-26.,33.),(-2.,16.)):
                z=self.z_at(y)
                self.coil(y,z,1.5,3.1,2.,.43)
                last=V((2.6,y+2,z-length))
                self.tube([(0,y,z-2),(1.7,y+1,z-7),(-.7,y+3,z-13),last],[.46,.45,.4,.24],1)
                for j in range(3):
                    self.tube([last,last+V((.4*j-.3,-.3*j,-1.6)),last+V((1.05*j-.75,-.58*j,-3.-j*.45))],
                              [.14,.11,.041],5,4)
        else:
            self.fruit_string(-28.,False)
            self.fruit_string(.8,True)
            self.herbs(29.,False)

    def object(self,name):
        self.build()
        me=bpy.data.meshes.new(name)
        me.from_pydata(self.verts,[],self.faces)
        me.update()
        me.materials.append(material)
        layer=me.uv_layers.new(name='DryGoodsAtlas')
        for poly,coords,smooth in zip(me.polygons,self.uvs,self.smooth):
            poly.use_smooth=smooth
            for idx,coordinate in zip(poly.loop_indices,coords):layer.data[idx].uv=coordinate
        obj=bpy.data.objects.new(name,me)
        bpy.context.collection.objects.link(obj)
        obj.modifiers.new('Export triangles','TRIANGULATE')
        return obj


for broken in (False,True):
    name='SM_TavernDryingRack'+('Ruined' if broken else '')
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    children=[]
    for level in range(3):
        obj=Rail(level,broken).object(name+'_LOD'+str(level))
        obj.parent=group
        children.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [group,*children]:obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,
        object_types={'EMPTY','MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',
        use_tspace=True,bake_anim=False,use_custom_props=True,add_leaf_bones=False,path_mode='STRIP')
    for child in children[1:]:
        child.hide_set(True)
        child.hide_render=True
    if broken:group.location.y=1.42
bpy.ops.wm.save_as_mainfile(filepath=str(out/'TavernDryingRail.blend'),relative_remap=False)
