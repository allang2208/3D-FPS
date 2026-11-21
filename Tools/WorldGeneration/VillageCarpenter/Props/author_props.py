"""Village carpenter loose assemblies. Dimensions and axes are UE local centimetres."""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'SourceAssets/HillsVillageCarpenter/Props'
AUTH = OUT / 'Authored'
AUTH.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0

NAMES = ('Sawn', 'Oak', 'Endgrain', 'Bark', 'Rot', 'Iron', 'Steel', 'Brass', 'Sign')
COLORS = ((.47,.30,.15),(.23,.16,.09),(.48,.34,.20),(.20,.16,.105),(.18,.16,.12),
          (.12,.12,.12),(.51,.54,.54),(.49,.32,.13),(.26,.18,.11))
MATERIALS = {}
for key, color in zip(NAMES, COLORS):
    mat = bpy.data.materials.new(key)
    mat.diffuse_color = (*color, 1)
    MATERIALS[key] = mat

def xf(c=(0,0,0), r=(0,0,0)):
    return Matrix.Translation(Vector(c)) @ Euler(tuple(math.radians(k) for k in r)).to_matrix().to_4x4()

class Mesh:
    def __init__(self, level):
        self.level = level
        self.verts = []
        self.faces = []
        self.info = []
        self.mats = []
        self.origin = Matrix.Identity(4)

    def rings(self, rings, face_mat, cap_mat, frame, repeat=100., phase=0., caps=(True,True), cap_uv=None):
        # Each ring faces along positive local X. Input cross section is Y/Z, counter-clockwise.
        n = len(rings[0])
        base = len(self.verts)
        mat = self.origin @ frame
        for ring in rings:
            for p in ring:
                q = mat @ Vector(p)
                self.verts.append((q.x/100, -q.y/100, q.z/100))
        ymin=min(y for _,y,z in rings[0]); ymax=max(y for _,y,z in rings[0])
        zmin=min(z for _,y,z in rings[0]); zmax=max(z for _,y,z in rings[0])
        def face(ids, tex, surf):
            if surf not in self.mats:self.mats.append(surf)
            self.faces.append(tuple(base+i for i in reversed(ids)))
            self.info.append((self.mats.index(surf),tuple(reversed(tex))))
        for j in range(len(rings)-1):
            for k in range(n):
                k2=(k+1)%n
                surf=face_mat(k,j) if callable(face_mat) else face_mat
                lens=[(Vector(rings[j][v])-Vector(rings[j][(v+1)%n])).length for v in range(n)]
                u0=sum(lens[:k])/repeat+phase; u1=u0+lens[k]/repeat
                idx=(j*n+k,j*n+k2,(j+1)*n+k2,(j+1)*n+k)
                us=(u0,u1,u1,u0)
                tex=[(u,rings[i//n][i%n][0]/repeat+phase) for i,u in zip(idx,us)]
                face(idx,tex,surf)
        for j,enabled in [(0,caps[0]),(len(rings)-1,caps[1])]:
            if not enabled:continue
            ix=list(range(n)) if j else list(reversed(range(n)))
            def uv(p):
                _,y,z = p
                if cap_uv is not None:return cap_uv(y,z)
                return (.5+y/max(.01,ymax-ymin)*.88,.5+z/max(.01,zmax-zmin)*.88)
            face([j*n+k for k in ix],[uv(rings[j][k]) for k in ix],cap_mat)

    def board(self,c,size,material='Sawn',r=(0,0,0),bevel=.3,damage=0.,sign=False):
        length,width,thick=size
        h=width/2; t=thick/2; b=min(h*.26,t*.27,bevel)
        ring=[(-h+b,-t),(h-b,-t),(h,-t+b),(h,t-b),(h-b,t),(-h+b,t),(-h,t-b),(-h,-t+b)]
        phase=rng.random()*2.
        # Stagger the broken fibres across the end; preserve sticker contact on the broad faces.
        splinter=[rng.uniform(.04,.95)*damage for _ in ring]
        rings=[]
        for j,u in enumerate((0.,.22,.58,.82,1.)):
            q=[]
            for k,(y,z) in enumerate(ring):
                y+=math.sin(u*math.pi)*math.cos(k+phase)*min(.21,width*.012)
                x=(u-.5)*length+(splinter[k] if j==0 else 0)
                q.append((x,y,z))
            rings.append(q)
        cap=material if material in ('Iron','Steel','Brass','Rot') else 'Endgrain'
        self.rings(rings,(lambda k,j:'Sign' if k==6 else 'Oak') if sign else material,cap,xf(c,r),phase=phase)

    def turned(self,c,profile,material,r=(0,0,0),n=None,cap=None):
        n=n or (32,20,10)[self.level]
        rings=[[(x,rad*math.cos(k*math.tau/n),rad*math.sin(k*math.tau/n)) for k in range(n)] for x,rad in profile]
        self.rings(rings,material,cap or material,xf(c,r),repeat=45)

    def section(self,c,profile,width,material,r=(0,0,0)):
        # Extrude an X/Z silhouette across Y. This maps local longitudinal X to world Y.
        loop=[(-x,z) for x,z in profile]
        area=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(loop,loop[1:]+loop[:1]))
        if area<0:loop.reverse()
        rings=[[(v,y,z) for y,z in loop] for v in (-width/2,width/2)]
        self.rings(rings,material,material,xf(c,r)@xf(r=(0,0,90)),repeat=32)

    def log(self,c,length,radius,seed,upright=False,stump=False):
        n=(80,40,20)[self.level] if stump else (48,28,16)[self.level]
        smooth=random.Random(seed)
        p=[smooth.random()*math.tau for _ in range(6)]
        rings=[]
        for t in (0,.035,.14,.39,.69,.91,1):
            ring=[]
            for k in range(n):
                a=k*math.tau/n
                knots=1+.055*math.cos(3*a+p[0]+t*.5)+.04*math.cos(5*a+p[1])+.023*math.sin(8*a+p[2]-t)
                flutes=.034*math.sin(17*a+p[2]+.6*math.sin(t*4+p[0]))
                flare=(.17 if stump else .06)*(1-t)**4
                rad=radius*(knots+flutes+flare-.075*t)
                x=(t-.5)*length
                if t==1 or (not stump and t==0):x+=math.sin(a*3+p[1])*(.20 if stump else .65)+math.sin(9*a+p[3])*.13
                ring.append((x,rad*math.cos(a)+.8*math.sin(t*3)*math.cos(p[4]),rad*math.sin(a)+.5*math.sin(t*2+p[5])))
            rings.append(ring)
        self.rings(rings,'Bark','Endgrain',xf(c, (0,-90,0) if upright else (0,0,0)),repeat=112,phase=p[1],cap_uv=lambda y,z:(.5+y/(radius*2.55),.5+z/(radius*2.55)))

    def curl(self,c,length,radius,width,turns,yaw,phase):
        steps=max(5,round(turns*(22,14,8)[self.level]))
        rings=[]
        for j in range(steps+1):
            t=j/steps; a=phase+t*turns*math.tau
            point=(t-.5)*length
            rad=radius*(.68+.32*math.sin(t*math.pi))
            wy=width*(.22+.78*math.sin(.12+t*2.88))
            ring=[]
            for edge,offset in ((-1,-.045),(1,-.045),(1,.045),(-1,.045)):
                ring.append((point+edge*wy*.34,(rad+offset)*math.cos(a)+edge*wy*.42,(rad+offset)*math.sin(a)+radius))
            rings.append(ring)
        self.rings(rings,'Sawn','Sawn',xf(c,(0,0,yaw)),repeat=32,phase=phase)

    def object(self,name):
        data=bpy.data.meshes.new(name)
        data.from_pydata(self.verts,[],self.faces)
        data.update()
        for key in self.mats:data.materials.append(MATERIALS[key])
        uv=data.uv_layers.new(name='Surface')
        paint=data.uv_layers.new(name='Lettering') if 'Sign' in self.mats else None
        for poly,(index,uvs) in zip(data.polygons,self.info):
            poly.material_index=index
            poly.use_smooth=True
            for loop,co in zip(poly.loop_indices,uvs):
                uv.data[loop].uv=co
                if paint:
                    p=data.vertices[data.loops[loop].vertex_index].co
                    paint.data[loop].uv=(.5-p.x/1.26,p.z/.48)
        data.set_sharp_from_angle(angle=math.radians(38))
        data.uv_layers.active=uv;uv.active_render=True
        obj=bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(obj)
        return obj

def drying(m):
    for x in (-95,95):
        m.board((x,0,7),(92,17,14),'Oak',(0,0,90),1.)
        for y in (-37,37):
            m.board((x,y,33),(61,8,8),'Oak',(0,-90,0),.6)
            m.turned((x,y+math.copysign(4,y),17),[(-.5,1.3),(.5,1.3)],'Iron',(0,0,90),8)
    for level in range(7):
        for column in range(4):
            x=rng.uniform(-6,6); y=-25.5+column*17
            m.board((x,y,16+level*8),(rng.uniform(235,267),rng.uniform(15.1,16.6),4),'Sawn',bevel=.38,damage=rng.uniform(.1,2))
        if level<6:
            for x in (-92,0,92):
                m.board((x,0,20+level*8),(71,5.2,4),'Oak',(0,0,90),.25)

def stock(m):
    for x in (-75,74):
        m.board((x,0,4),(106,11,8),'Oak',(0,0,90),.8)
    rows=[(-29,22,14.6,196),(-.5,22,14.3,220),(28,22,14.4,203),
          (-14,45.4,13.7,207),(13.8,46.1,14.0,186),(0,69,13.3,195)]
    for i,(y,z,rad,length) in enumerate(rows):
        m.log(((-1)**i*i*1.7,y,z),length,rad,1003+i)
    # Short split wedges brace the pile against rolling from the two sleepers.
    for x in (-75,74):
        for s in (-1,1):
            m.section((x,41*s,8),[(-8,0),(8,0),(8,9)],7,'Oak',(0,0,-90*s))

def block(m):
    m.log((0,0,22),44,23,192,upright=True,stump=True)
    # Wedge-shaped clefts sink from the scarred chopping face into the crown.
    for i,(x,y,a,ln) in enumerate([(-6,3,-19,15),(5,-5,11,12),(2,8,35,7)]):
        m.section((x,y,44.34),[(-ln/2,-.1),(-ln/2,.025),(ln/2,.02),(ln/2-.4,-.08)],.25 if i else .46,'Rot',(0,0,a))

def tools(m):
    # A wooden jack plane with a genuine open throat between two cheeks, cutter and wedge.
    m.origin=xf((-20,7,0),(0,0,-6))
    sole=[(-15,0),(14.4,0),(15.2,1.3),(14.4,4.7),(12,5.4),(-13.4,5.4),(-15.2,3.1)]
    for side in (-3.25,3.25):m.section((0,side,0),sole,1.15,'Oak')
    for x,l in [(-9,11.7),(8.4,12.8)]:m.board((x,0,2.65),(l,5.4,5.3),'Oak',bevel=.46)
    m.board((.9,0,5.4),(13.,4.4,.55),'Steel',(0,-57,0),.12)
    m.section((.6,0,0),[(-1.9,2),(2.8,7.6),(3.8,9.8),(2.1,9.3),(-2.7,4.4)],3.6,'Sawn')
    m.turned((-.8,0,5.6),[(-3.5,.53),(3.5,.53)],'Iron',(0,0,90))
    m.section((-8.2,0,4.8),[(-4,0),(2,0),(3,2),(1.5,4.3),(3,7),(2.6,8.3),(.7,8.1),(-2,5.7),(-2.2,2)],2.6,'Oak')
    # Three sharp, stepped chisels with turned grips, steel socket and brass ferrule.
    for i,(x,y,a,w) in enumerate([(-21,-7,4,1.8),(-20,-12,1,.9),(-18,-17,-4,1.2)]):
        m.origin=xf((x,y,0),(0,0,a));z=1.35
        m.turned((-5.9,0,z),[(-5.6,1.),(-5.2,1.35),(-4.4,1.47),(-3.8,1.32),(-1,1.15),(1.7,.94),(3,.92),(4.4,1.2),(5.5,1.)],'Oak')
        m.turned((-.2,0,z),[(-.85,1.08),(.8,1.),(1.05,.7)],'Brass')
        m.turned((1.7,0,z),[(-1,.7),(.85,.52),(1.1,.43)],'Iron')
        m.section((2.6,0,0),[(0,.8),(8.6,.28),(9.6,.12),(9.5,.23),(8.0,.63),(1.,1.55),(0,1.6)],w,'Steel')
    # Through-wedged joiner's mallet, tapered head and worn handle.
    m.origin=xf((13,8,0),(0,0,12))
    m.board((-3.8,0,3.25),(27,2.8,2.65),'Oak',bevel=.85)
    m.section((8.4,0,0),[(-6.5,.2),(6.8,0),(7.7,5.7),(7.3,7),(-6.6,7.2),(-7.6,6.1)],9,'Sawn')
    m.board((8.9,0,7.22),(2.9,1.1,.18),'Oak',bevel=.07)
    # Try square: flush steel tongue with two brass rivets and scribed graduation marks.
    m.origin=xf((5,-13,0),(0,0,6))
    m.board((0,0,1.15),(12.5,3.8,2.3),'Oak',bevel=.4)
    m.board((4.8,6.8,1.55),(17.1,2.9,.34),'Steel',(0,0,90),.12)
    for x in (3.9,5.1):m.turned((x,-.8,2.29),[(-.07,.28),(.09,.29)],'Brass',(0,-90,0),12)
    for i in range(3,15):
        if m.level==0:m.board((5.9,i,1.75),(.52 if i%5 else 1.05,.065,.04),'Iron',bevel=.01)
    m.origin=Matrix.Identity(4)

def shavings(m):
    # Position each item deterministically, keeping silhouette consistent when the tiny chips drop out.
    for i in range(108):
        t=rng.random()**.66; a=rng.uniform(0,math.tau)
        x=math.cos(a)*t*41; y=math.sin(a)*t*22+math.sin(a*2)*2.7
        yaw=rng.uniform(-180,180); length=rng.uniform(1.2,6.7)
        width=rng.uniform(.35,1.1);r=rng.uniform(.13,1.1)
        phase=rng.uniform(0,6);turns=rng.uniform(.5,1.8)
        if i%3==0:
            if m.level<2 or i%2==0:m.curl((x,y,.04),length,r,width,turns,yaw,phase)
        elif i%(1+m.level)==0:
            m.section((x,y,.04),[(-length/2,0),(length/3,0),(length/2,.12),(0,.32)],width,'Sawn',(0,0,yaw))

def spoiled(m):
    for x,y,z,l,w,yaw,dmg in [(-5,-12,2.3,158,17,2,12),(12,10,2.4,143,19,-7,25),
          (-5,21,7,98,11,15,14),(-6,-4,7.4,141,15,-11,21),(28,6,12.5,103,9,16,26),
          (-28,-5,12,105,11,-1,17),(14,5,17.0,85,6,-10,25)]:
        m.board((x,y,z),(l,w,4.7),'Rot',(0,0,yaw),.8,dmg)
    for i in range(12):
        x=rng.uniform(-72,63);y=rng.choice((-1,1))*rng.uniform(17,31)
        length=rng.uniform(7,27);yaw=rng.uniform(-70,70)
        m.section((x,y,.1),[(-length/2,0),(length*.46,0),(length/2,.37),(-length*.19,2.7)],rng.uniform(.9,3.4),'Sawn' if i%5==0 else 'Rot',(0,0,yaw))

def sign(m):
    for j in range(3):
        m.board((0,0,8+j*16),(126,4.2,15.85),'Oak',bevel=.48,sign=True)
    for x in (-46,46):
        m.board((x,2.85,24),(44,4.8,1.7),'Oak',(90,-90,0),.2)
        m.board((x,0,49.1),(11,2.9,.8),'Iron',(90,-90,0),.18)
        for z in (5.4,24,42.5):
            m.turned((x,-2.12,z),[(-.20,.88),(.14,.95),(.44,.47)],'Iron',(0,0,-90),12)

roles=[
    ('DryingRack',drying,[([0,0,40],[245,68,52]),([-95,0,7],[17,91,14]),([95,0,7],[17,91,14])]),
    ('LogStack',stock,[([0,0,23],[192,83,45]),([0,0,52],[182,54,27]),([0,0,70],[179,23,24])]),
    ('Block',block,[([0,0,21.8],[35,26,43.6]),([0,0,21.8],[25,36,43.6]),([0,0,21.8],[39,15,43.6])]),
    ('Tools',tools,[]),('Shavings',shavings,[]),
    ('SpoiledStock',spoiled,[([0,0,8],[128,36,16])]),('Sign',sign,[])]
assets=[]
for i,(suffix,build,boxes) in enumerate(roles):
    name='SM_Carpenter'+suffix
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup';bpy.context.collection.objects.link(group)
    children=[]
    for level in range(3):
        rng=random.Random(180634+i)
        model=Mesh(level);build(model)
        obj=model.object(name+'_LOD'+str(level))
        if level and suffix in ('DryingRack','SpoiledStock','Sign'):
            bpy.context.view_layer.objects.active=obj
            mod=obj.modifiers.new('Reduce longitudinal cuts','DECIMATE');mod.ratio=(.6,.29)[level-1]
            bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.modifiers.new('Triangulated game export','TRIANGULATE')
        obj.parent=group;children.append(obj)
        if level==0:
            low=[round(min(p[k] for p in model.verts)*100,2) for k in range(3)]
            high=[round(max(p[k] for p in model.verts)*100,2) for k in range(3)]
            bounds=[[low[0],-high[1],low[2]],[high[0],-low[1],high[2]]]
    bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
    for obj in children:obj.select_set(True)
    fbx=AUTH/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Y',
        axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,use_custom_props=True,add_leaf_bones=False)
    assets.append(dict(name=name,bounds_cm=bounds,boxes=boxes,fbx=str(fbx)))
    group.location=(0,i*3,0)
    for obj in children[1:]:obj.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'CarpenterProps.blend'))
(OUT/'models.json').write_text(json.dumps(assets,indent=2),encoding='utf-8')
