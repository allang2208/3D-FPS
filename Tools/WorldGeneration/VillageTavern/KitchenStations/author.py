"""Build the repaired and abandoned stations as joined game props and editable source."""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.dont_write_bytecode=True
tool=Path(__file__).resolve().parent
src=tool.parents[3]/'SourceAssets/HillsVillageTavern/KitchenStations'
src.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(tool))
from geometry import Station, X, Y, Z

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
colors={'Oak':(.24,.15,.075),'Sawn':(.38,.25,.13),'OiledOak':(.25,.16,.09),
        'Endgrain':(.33,.21,.12),'Rot':(.16,.14,.11),'Iron':(.09,.085,.078),
        'Clay':(.32,.123,.058),'AshGlaze':(.53,.43,.29),'Cloth':(.37,.32,.23),
        'OliveGlaze':(.114,.138,.066),'HoneyGlaze':(.34,.151,.042)}
for name,color in colors.items():
    bpy.data.materials.new(name).diffuse_color=(*color,1)

def pegged(m,x,y,z,mat='Sawn',radius=.92):
    m.turned((x-.2,y,z),(x+.32,y,z),[(0,radius),(1,radius*.89)],mat,9)

def timber_frame(m,depth,length,height,ruin):
    wood='Rot' if ruin else 'Oak'
    dx,dy=depth/2,length/2
    lx,ly=dx-6.7,dy-8.6
    for x in (-lx,lx):
        for y in (-ly,ly):
            m.box((x,y,(height-4)/2),(7.8,8.4,height-4),wood,.42,True)
            pegged(m,x+4,y,height-10,wood if ruin else 'Sawn')
            pegged(m,x+4,y,19,wood if ruin else 'Sawn',.7)
        m.box((x,0,height-10),(4.6,2*ly-5,11.5),wood,.32)
        m.box((x,0,17),(4.6,2*ly-4,6.6),wood,.28)
    for y in (-ly,ly):
        m.box((0,y,height-10),(2*lx-5,4.9,10.5),wood,.3)
        m.box((0,y,17),(2*lx-4,5.1,6.6),wood,.22)
        # Proud tenons and wedges show how the rails lock into the uprights.
        for x in (-lx-4.04,lx+4.04):
            m.box((x,y,17),(1.15,4.8,3.1),wood if ruin else 'Endgrain',.21)
    for i in range(4):
        w=(2*lx-5)/4
        x=(i-1.5)*w
        if ruin and i==3:
            m.slab([(x-w/2,-ly+2),(x+w/2,-ly+2),(x+w/2,ly*.10),(x+w*.16,ly*.15),
                    (x-w*.03,ly*.03),(x-w*.22,ly*.18),(x-w/2,ly*.10)],20.3,2.7,wood)
        else:
            m.box((x,0,21.65),(w-.34,2*ly-2,2.7),wood if ruin else 'Sawn',.18)
    for i in range(4):
        w=depth/4
        x=(i-1.5)*w
        if ruin and i in (2,3):
            end=dy*(.60 if i==2 else .36)
            contour=[(x-w/2+.12,-dy),(x+w/2-.12,-dy),(x+w/2-.12,end-1),
                     (x+w*.31,end+3),(x+w*.22,end-3),(x+w*.03,end+.3),
                     (x-w*.14,end-4),(x-w*.31,end+2),(x-w/2+.12,end-2)]
            m.slab(contour,height-4,4,wood)
            m.box((x,(end-3-dy)/2,height-2),(w,end-3+dy,4),collision=True,draw=False)
        else:
            m.box((x,0,height-2),(w-.23,length,4),wood if ruin else 'OiledOak',.38)
            if ruin:
                m.box((x,0,height-2),(w,length,4),collision=True,draw=False)
        for y in (-ly,ly):
            if ruin and i>=2 and y>0:
                continue
            m.turned((x,y,height-.14),(x,y,height+.02),[(0,.68),(1,.66)],wood if ruin else 'Endgrain',9)
    if not ruin:
        m.box((0,0,height-2),(depth,length,4),collision=True,draw=False)
    for y,sign in ((-ly,1),(ly,-1)):
        m.beam((-lx,y,height-27),(-lx,y+sign*23,height-9),4,5.1,wood)
    # Local split secured with a surface-mounted oak cleat and square nail heads.
    m.box((lx+2.72,-ly*.47,height-10),(1.2,18.6,4.7),wood if ruin else 'Sawn',.25)
    for y in (-ly*.47-6,-ly*.47+6):
        pegged(m,lx+3.45,y,height-10,'Iron',.61)

def vessel(m,loc,profile,mat,sy=1,sides=28):
    x,y,z=loc
    rings=[[(x+rad*math.cos(j*math.tau/sides),y+rad*sy*math.sin(j*math.tau/sides),z+elev)
            for j in range(sides)] for elev,rad in profile]
    m.rings(rings,mat,Z)

def coopered(m,loc,rx,ry,height,ruin=False,handle=False):
    x,y,z=loc
    count=15 if handle else 23
    wood='Rot' if ruin else 'Sawn'
    def ring(a,s,h):
        return (x+math.cos(a)*rx*s,y+math.sin(a)*ry*s,z+h)
    for i in range(count):
        if ruin and i in (1,2,count-1):
            continue
        a,b=(i+.012)*math.tau/count,(i+.988)*math.tau/count
        high=height + m.rng.uniform(-.3,.3)
        if ruin and i in (3,4,count-2):
            high*=.46 if i==3 else .72
        thickness=.105 if handle else .067
        # Individual tapered staves with proud ends, inset floor and real lip thickness.
        cut=math.floor(m.rng.uniform(0,3))*.14 if ruin else 0
        layers=[]
        for angle in (a,(a+b)/2,b):
            shell= .83+.17*high/height
            layers.append([ring(angle,.83,0),ring(angle,shell,high-cut),ring(angle,shell-thickness,high-cut),
                           ring(angle,.83-thickness,1)])
        verts=[p for section in layers for p in section]
        faces=[(3,2,1,0),(8,9,10,11)]
        for k in range(2):
            for j in range(4):
                nxt=(j+1)%4
                faces.append((k*4+j,k*4+nxt,k*4+nxt+4,k*4+j+4))
        # Cross section winds towards negative theta, hence reverse all faces.
        m.shape(verts,[tuple(reversed(f)) for f in faces],wood,Z,.11)
    steps=18 if handle else 28
    vessel(m,(x,y,z+1),[(0,rx*.79),(1.35,rx*.79)],wood,ry/rx,steps)
    for frac in (.20,.76):
        if ruin and frac>.5:
            continue
        h=height*frac
        band=1.7 if handle else 2.35
        outer=.83+.17*frac+.016
        angles=[math.tau*j/steps for j in range(steps+1)]
        rings=[[ring(a,outer+r,level) for a in angles[:-1]]
               for r,level in ((-.012,h-band/2),(.001,h-band/2),(0,h+band/2),(-.012,h+band/2))]
        m.rings(rings,'Iron',Z,caps=False)
        for ai in (.22,.22+math.pi):
            px,py,pz=ring(ai,outer,h)
            m.turned((px,py,pz),(px+.34*math.cos(ai),py+.34*math.sin(ai),pz),
                     [(0,.62),(.55,.61),(1,.43)],'Iron',8)
    if handle and not ruin:
        p=[(x,y+ry*.97*math.cos(math.pi*j/15),z+height-1+ry*1.12*math.sin(math.pi*j/15)) for j in range(16)]
        m.tube(p,.44,'Iron')
        m.turned((x,y-2.6,z+height-1+ry*1.12),(x,y+2.6,z+height-1+ry*1.12),
                 [(0,.52),(.12,.8),(.88,.8),(1,.52)],'OiledOak')

def spoon(m,x,y,z,angle,size=1):
    yaw=math.radians(angle)
    def p(a,b,h):
        return (x+size*(a*math.cos(yaw)-b*math.sin(yaw)),y+size*(a*math.sin(yaw)+b*math.cos(yaw)),z+size*h)
    m.turned(p(0,-14,1.3),p(0,2,1.35),[(0,.53),(.05,.81),(.16,.72),(.87,.58),(1,1.05)],'OiledOak')
    rings=[]
    for level,r in [(1.1,.13),(.66,.55),(1.55,1),(1.82,1),(1.62,.83),(1.08,.4),(1.0,.12)]:
        rings.append([p(math.cos(j*math.tau/16)*2.42*r,4.85+math.sin(j*math.tau/16)*4.3*r,level)
                      for j in range(16)])
    m.rings(rings,'OiledOak',Y)

def linen(m,x,y,z,dx,dy,drop,ruin=False):
    # Continuous warp runs from the worktop over the rounded front edge.
    rows=[(-dx,0),(-dx*.64,.15),(-dx*.32,.25),(-2,.31),(-.45,.15),(.15,-.55),
          (.35,-drop*.17),(.18,-drop*.39),(.0,-drop*.68),(-.15,-drop)]
    ny=18
    grid=[]
    for k,(xx,zz) in enumerate(rows):
        free=max(0,k-4)/5
        for i in range(ny+1):
            v=i/ny
            ripple=math.sin(v*math.pi*5.3+.44*k)+.42*math.sin(v*math.pi*9.1-.12*k)
            fray= (1.2*math.sin(i*1.9)+.65*math.cos(i*.9) if ruin else .30*math.sin(i*1.1))
            grid.append((x+xx+free*.75*ripple,y+(v-.5)*dy+.25*math.sin(.45*k),
                         z+zz+(.19*(1-free))*ripple+(fray if k==len(rows)-1 else 0)))
    faces=[]
    for k in range(len(rows)-1):
        for i in range(ny):
            if ruin and k>6 and i in (4,12) and k-6>abs(i-4)*.08:
                continue
            a=k*(ny+1)+i
            faces.append((a,a+ny+1,a+ny+2,a+1))
    # Reversed shell gives the hanging fabric a visible underside in a one-sided shader.
    n=len(grid)
    back=[(xx-.07,yy,zz-.09) for xx,yy,zz in grid]
    m.shape(grid+back,faces+[tuple(n+j for j in reversed(f)) for f in faces],'Cloth',Y,0,False,True)

def fractured_pottery(m,x,y,z):
    for q in range(3):
        theta=q*2.0
        pieces=[]
        for j in range(5):
            a=theta+(j/4)*.83
            pieces.extend([(x+math.cos(a)*4,y+math.sin(a)*4,z+.14),
                           (x+math.cos(a)*8,y+math.sin(a)*8,z+1.9+.5*math.sin(q+j)),
                           (x+math.cos(a)*7.6,y+math.sin(a)*7.6,z+2.0+.5*math.sin(q+j))])
        faces=[]
        for j in range(4):
            n=j*3
            faces.extend([(n,n+3,n+4,n+1),(n+1,n+4,n+5,n+2),(n+2,n+5,n+3,n)])
        m.shape(pieces,faces,'Clay',Y,0,False)

def prep(m,ruin):
    timber_frame(m,65,158,88,ruin)
    if ruin:
        m.slab([(-14,-34),(14,-34),(14,-14),(9,-11),(6,-16),(3,-13),
                (-2,-15),(-6,-11),(-9,-15),(-14,-12)],88,2.8,'Rot')
        fractured_pottery(m,-9,52,88)
        linen(m,31.0,-54,88.37,11,17,17,True)
        coopered(m,(-1,-29,23),10.5,13,14,True)
        m.beam((-7,36,.9),(10,62,3.8),4.3,1.8,'Rot')
        return
    # Heavy cross-grain slab. Its entire 32 x 58 cm crown is clear and at z=91.
    contour=[(-16,-25),(-14,-29),(13,-29),(16,-26),(16,25.5),(13,29),(-13.5,29),(-16,26)]
    m.slab(contour,88,3,'Endgrain',Y,.46)
    for yy in (-21,21):
        m.box((16.02,yy,89.35),(.12,2.5,.65),'Sawn',.08)
    # Turned rolling pin lies across the oak boards, with distinct bearing shoulders.
    m.turned((-23,-51,91.35),(13,-55,91.35),[(0,1.15),(.025,1.37),(.16,1.28),(.19,.92),
             (.21,2.47),(.25,3.34),(.75,3.34),(.79,2.47),(.81,.92),(.84,1.28),(.975,1.37),(1,1.15)],
             'OiledOak',20)
    spoon(m,-17,43,87.8,-77,.84)
    vessel(m,(.8,60,88),[(0,3.7),(.65,4.1),(.95,5.1),(2.3,7.85),(4.15,10.2),
           (4.8,10.3),(4.95,9.8),(4.15,9.38),(2.25,6.7),(1.5,3.2)],'AshGlaze')
    linen(m,31.1,-57,88.38,13,18.8,17.4)
    # Lower shelf stores a small covered earthenware crock and a stave measure.
    vessel(m,(0,31,23),[(0,7.1),(1,7.9),(3,8.4),(7.8,10),(12,9.4),(15.1,7.85),
           (16.3,8.4),(16.9,8.5),(17.1,7.8),(16.5,7.45),(2.1,6.3)],'Clay')
    vessel(m,(0,31,40.1),[(0,7.9),(.53,8.1),(1.05,7.1),(1.73,2.1),(2.75,1.3),(3.4,1.85)],'AshGlaze')
    coopered(m,(-1,-32,23),10.5,13,14,handle=True)

def wash(m,ruin):
    timber_frame(m,62,100,68,ruin)
    coopered(m,(-3,-11,68),22.0,26.5,20.5,ruin)
    if ruin:
        fractured_pottery(m,-16,36,68)
        coopered(m,(-1,-17,23),10.7,11.1,18,True,True)
        linen(m,29.95,-35,68.42,11.5,11.4,13,True)
        m.beam((9,17,1.1),(12,39,1.6),2.8,2.2,'Rot')
    else:
        linen(m,29.95,31,68.37,20,26,19.1)
        spoon(m,-12,32,68.04,80,1.24)
        coopered(m,(1,-18,23),10.7,11.1,18,False,True)
        vessel(m,(-2,18,23),[(0,4.5),(.8,5.0),(1.25,6.9),(3.5,8.65),(3.9,8.7),
                               (4.12,8.16),(3.0,7.65),(1.45,4.2)],'Clay')

for i,(name,fn,ruin) in enumerate([('PrepBench',prep,False),('PrepBenchRuined',prep,True),
                                    ('WashStand',wash,False),('WashStandRuined',wash,True)]):
    model=Station(name,63841+i)
    fn(model,ruin)
    model.export(src,((i%2)*1.35,(i//2)*2.1,0))

# The blend references precisely the same village wood and kettle-fired ceramics as UE.
sys.path.insert(0,str(tool.parent/'Service'))
from source_surfaces import bind_service_surfaces
bind_service_surfaces(src.parent/'Service')
for image in bpy.data.images:
    if image.source=='FILE' and image.filepath.startswith('//'):
        path=((src.parent/'Service')/image.filepath[2:]).resolve()
        image.filepath=str(path)
cloth=bpy.data.materials['Cloth']
cloth.use_nodes=True
nodes=cloth.node_tree.nodes
shader=nodes.get('Principled BSDF')
for suffix,socket in (('Color','Base Color'),('Normal','Normal'),('Rough','Roughness')):
    node=nodes.new('ShaderNodeTexImage')
    node.image=bpy.data.images.load(str(src/('T_KitchenLinen_'+suffix+'.png')),check_existing=True)
    if suffix!='Color':
        node.image.colorspace_settings.name='Non-Color'
    srcsocket=node.outputs[0]
    if suffix=='Normal':
        dx=nodes.new('ShaderNodeVectorMath')
        dx.operation='MULTIPLY_ADD'
        dx.inputs[1].default_value=(1,-1,1)
        dx.inputs[2].default_value=(0,1,0)
        cloth.node_tree.links.new(srcsocket,dx.inputs[0])
        nm=nodes.new('ShaderNodeNormalMap')
        cloth.node_tree.links.new(dx.outputs[0],nm.inputs['Color'])
        srcsocket=nm.outputs[0]
    cloth.node_tree.links.new(srcsocket,shader.inputs[socket])
from source_materials import relative_to_blend
relative_to_blend(src)
bpy.ops.wm.save_as_mainfile(filepath=str(src/'TavernKitchenStations.blend'),relative_remap=False)
