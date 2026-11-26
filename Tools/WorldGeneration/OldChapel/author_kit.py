"""Build the reusable stone, slate, oak and leadwork kit in UE centimetres."""
from collections import defaultdict
from pathlib import Path
import math
import os
import random
import runpy
import bpy
import bmesh
from mathutils import Vector

OUT=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsOldChapel/Concept01/Authored'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
rng=random.Random(1753)
make_relief=runpy.run_path(str(Path(__file__).with_name('relief_mesh.py')))['surface_mesh']
wood_directions={}
yard_offsets={}
verts=[];faces=[];slots=[]
def solid(points, rings, material):
    start=len(verts)
    verts.extend((x/100,-y/100,z/100) for x,y,z in points)
    for ring in rings:
        faces.append(tuple(start+i for i in ring))
        slots.append(material)
def extrusion(lower,upper,material):
    n=len(lower)
    rings=[list(reversed(range(n))),list(range(n,n*2))]
    rings.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    solid(lower+upper,rings,material)
def section(yz,a,b,material):
    extrusion([(a,y,z) for y,z in yz],[(b,y,z) for y,z in yz],material)
def block(x0,x1,y0,y1,z0,z1,mat):
    section([(y0,z0),(y1,z0),(y1,z1),(y0,z1)],x0,x1,mat)
def strip(x0,x1,y0,y1,bottom,top,mat):
    q=[(y0,bottom(y0)),(y1,bottom(y1)),(y1,top(y1)),(y0,top(y0))]
    remove=[]
    for p in q:
        if not remove or p!=remove[-1]:remove.append(p)
    if remove[0]==remove[-1]:remove.pop()
    if len(remove)>=3:section(remove,x0,x1,mat)
def arch(u,r,s,h):
    # Tip shape of the dressed stone surround.
    return s+(h-s)*math.sqrt(max(0,1-abs(u/r))) if abs(u)<r else s
def wall(half,depth,outline,breaks,opening=None):
    # Divide around the exact opening so the collision and both faces have real holes.
    steps=set([-half,half]+breaks)
    if opening:
        rad,sill,s,h=opening
        steps.update(rad*j/10 for j in range(-10,11))
    for l,r in zip(sorted(steps),sorted(steps)[1:]):
        if opening and abs((l+r)*.5)<rad:
            if sill>0:strip(-depth/2,depth/2,l,r,lambda u:0,lambda u:sill,'Wall')
            strip(-depth/2,depth/2,l,r,lambda u:arch(u,rad,s,h),outline,'Wall')
        else:strip(-depth/2,depth/2,l,r,lambda u:0,outline,'Wall')
def rod(p,q,width,depth,mat):
    a,b=Vector(p),Vector(q);v=(b-a).normalized()
    helper=Vector((1,0,0)) if abs(v.x)<.9 else Vector((0,1,0))
    h=v.cross(helper).normalized()*(width/2);n=v.cross(h).normalized()*(depth/2)
    offsets=[h+n,h-n,-h-n,-h+n]
    first=len(faces)
    extrusion([tuple(a+off) for off in offsets],[tuple(b+off) for off in offsets],mat)
    if mat=='Timber':
        for index in range(first,len(faces)):
            wood_directions[index]=Vector((v.x,-v.y,v.z))
def finish(name):
    selected=os.environ.get('CHAPEL_UPDATE','').split()
    if selected and name not in selected:
        verts.clear();faces.clear();slots.clear();wood_directions.clear();yard_offsets.clear()
        return
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    unique=list(dict.fromkeys(slots))
    for m in unique:mesh.materials.append(bpy.data.materials.get(m) or bpy.data.materials.new(m))
    for f,m in zip(mesh.polygons,slots):f.material_index=unique.index(m)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    uv=mesh.uv_layers.new(name='SurfaceMetres')
    for f in mesh.polygons:
        n=f.normal;axis=max(range(3),key=lambda i:abs(n[i]))
        for idx in f.loop_indices:
            x,y,z=mesh.vertices[mesh.loops[idx].vertex_index].co
            uv.data[idx].uv=((y,z) if axis==0 else ((x,z) if axis==1 else (x,y)))
    if name.startswith('Yard') or name in ('SolidBay','WindowBay','EastGable','WestGable','FloorBay','SlateRoofBay','OakTruss','PurlinBay','Foundation','SanctuarySteps'):
        old_mesh=mesh
        mesh=make_relief(mesh,name,OUT.parent/'Surfaces/Prepared',wood_directions,yard_offsets)
        bpy.data.meshes.remove(old_mesh)
    obj=bpy.data.objects.new('SM_Chapel'+name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    verts.clear();faces.clear();slots.clear();wood_directions.clear();yard_offsets.clear()
def const(v):return lambda y:v
wall(200,50,const(450),[]);finish('SolidBay')
wall(200,50,const(450),[],(34,144,277,333));finish('WindowBay')
# West gable: a raised masonry saddle supports the full width of the bellcote.
def west(y):return 850 if abs(y)<=150 else 850-abs(y)
# Flat 150 cm shoulders step up to a level seat, without diagonal gaps.
def upper_west(y):return 850-abs(y)
for lo,hi in [(-400,-150),(150,400)]:
    strip(-34,34,lo,hi,const(0),upper_west,'Wall')
# Lower central part contains the pointed door. Upper part leaves the round oculus.
wall(150,68,const(440),[],(87,0,210,296))
radius=34
uvals=sorted({-150,150,*[radius*math.cos(math.pi*i/24) for i in range(25)]})
for l,r in zip(uvals,uvals[1:]):
    if abs((l+r)/2)<radius:
        arc=lambda y:math.sqrt(max(0,radius**2-y*y))
        strip(-34,34,l,r,const(440),lambda y:532-arc(y),'Wall')
        strip(-34,34,l,r,lambda y:532+arc(y),const(850),'Wall')
    else:strip(-34,34,l,r,const(440),const(850),'Wall')
finish('WestGable')
wall(400,50,lambda u:850-abs(u),[0],(34,268,401,457));finish('EastGable')
# One 4 m slate roof bay, mirrored at the ridge by placement. Includes overlapping courses,
# broken bonds and solid board soffit. Tile rows run across the pitch.
def roof_z(y):return 849-y
# Split the soffit into weatherboards running along the nave. A recessed backing closes the narrow joints.
section([(0,roof_z(0)-10),(425,roof_z(425)-10),(425,roof_z(425)),(0,roof_z(0))],-200,200,'Timber')
board_rng=random.Random(471)
for j in range(31):
    lo=425*j/31;hi=425*(j+1)/31
    thick=board_rng.uniform(12.4,13.5)
    first=len(faces)
    section([(lo,roof_z(lo)-thick+.36),(lo+.38,roof_z(lo+.38)-thick),
             (hi-.51,roof_z(hi-.51)-thick),(hi-.16,roof_z(hi-.16)-thick+.48),
             (hi-.16,roof_z(hi-.16)-9.9),(lo,roof_z(lo)-9.9)],-200,200,'Timber')
    for index in range(first,len(faces)):wood_directions[index]=Vector((1,0,0))
for row in range(19):
    a=row*22.4;b=min(428,a+24.5)
    edges=[-200]+[t for t in range(-200+(16 if row%2 else 32),200,32)]+[200]
    for l,r in zip(edges,edges[1:]):
        dz=rng.uniform(1.3,2.4)
        # Vary the exposed slate noses; the underlying weatherboards close the full pitch.
        lip=b+rng.uniform(-.8,1.6)
        chip=rng.uniform(1.4,4.5) if rng.random()<.18 else rng.uniform(.15,.8)
        outline=[(l+.25,a),(r-.25,a),(r-.25,lip-chip*.58),(r-.25-chip,lip),(l+.25,lip-.4)]
        lower=[(x,y,roof_z(y)+.2) for x,y in outline]
        upper=[(x,y,roof_z(y)+1.7+(dz+.3)*(y-a)/(lip-a)) for x,y in outline]
        extrusion(lower,upper,'Slate')
finish('SlateRoofBay')
# Exposed tie beam, rafters, king post, braces and pegs.
rod((0,-375,455),(0,375,455),22,24,'Timber')
for sign in [-1,1]:
    rod((0,sign*381,454),(0,0,829),19,22,'Timber')
    rod((0,sign*199,468),(0,0,672),15,17,'Timber')
    # Shaped oak knees carry each tie down to a wall post.
    block(-12,12,min(sign*351,sign*333),max(sign*351,sign*333),343,453,'Timber')
    profile=[(343,357),(343,393),(285,446),(243,446),
             (269,438),(294,426),(316,406),(332,381)]
    section([(sign*y,z) for y,z in profile],-10,10,'Timber')
rod((0,0,464),(0,0,825),19,21,'Timber')
for y,z in [(-353,459),(353,459),(0,477),(0,800),(-189,470),(189,470)]:
    rod((-13,y,z),(13,y,z),4.5,4.5,'Iron')
finish('OakTruss')
# One long purlin & ridge-cap set per 4 m bay; end to end continuity.
for side in [-1,1]:
    for dy in [104,231,356]:
        rod((-200,side*dy,829-dy),(200,side*dy,829-dy),13,14,'Timber')
    for pos in [-150,-50,50,150]:
        rod((pos,0,833),(pos,side*411,422),8,9,'Timber')
for j in range(8):
    section([(-13,839),(0,855),(13,839),(13,845),(0,862),(-13,845)],-200+j*50+.2,-150+j*50-.2,'Coping')
finish('PurlinBay')
# The scanned slab joints and the displaced walking surface share one continuous profile.
block(-100,100,-100,100,-12,0,'Flagstone')
finish('FloorBay')
# Facing oculus stones around the real through-hole.
for j in range(16):
    a=2*math.pi*(j+.018)/16;b=2*math.pi*(j+.982)/16
    def ring(rad,theta):return rad*math.cos(theta),rad*math.sin(theta)
    section([ring(27,a),ring(42,a),ring(42,b),ring(27,b)],-36,36,'Coping')
finish('Oculus')
# Standalone translucent panes and thin lead kames keep daylight in the room.
rad,s,h=34,139,191
for i in range(-10,10):
    l=rad*i/10;r=rad*(i+1)/10
    strip(-.22,.22,l,r,const(12),lambda y:arch(y,rad,s,h),'Glass')
# Clip each diagonal lead came to the polygonal outline of the glazing.
outline=[(-rad,12),(rad,12)]+[(rad*i/10,arch(rad*i/10,rad,s,h)) for i in range(10,-11,-1)]
for slope in (-1.65,1.65):
    for intercept in range(-50,260,31):
        hits=[]
        for a,b in zip(outline,outline[1:]+outline[:1]):
            va=a[1]-slope*a[0]-intercept;vb=b[1]-slope*b[0]-intercept
            if (va<0)==(vb<0):continue
            f=va/(va-vb)
            hits.append((a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])))
        if len(hits)==2 and math.dist(*hits)>1:
            rod((-.55,*hits[0]),(-.55,*hits[1]),.85,.65,'Lead')
finish('LancetGlass')
ring=[(27*math.cos(2*math.pi*j/48),27*math.sin(2*math.pi*j/48)) for j in range(48)]
section(ring,-.22,.22,'Glass')
for y in [-12,0,12]:
    z=math.sqrt(27**2-y**2);rod((-.6,y,-z),(-.6,y,z),1.1,1.1,'Lead')
for z in [-10,10]:
    y=math.sqrt(27**2-z**2);rod((-.6,-y,z),(-.6,y,z),1.1,1.1,'Lead')
finish('OculusGlass')
# Recessed bed and two bonded courses. Cut corners and worn arrises survive at grazing angles.
stone_rng=random.Random(1837)
def footing_stone(x0,x1,y0,y1,base,top):
    cuts=[stone_rng.uniform(2.1,5.8) for _ in range(4)]
    lip=stone_rng.uniform(.9,1.55)
    def ring(inset,z):
        l,r,b,t=x0+inset,x1-inset,y0+inset,y1-inset
        a,c,d,e=cuts
        return [(l+a,b,z),(r-c,b,z),(r,b+c,z),(r,t-d,z),
                (r-d,t,z),(l+e,t,z),(l,t-e,z),(l,b+a,z)]
    rings=[ring(.8,base),ring(0,base+1.6),ring(0,top-2.),ring(lip,top)]
    walls=[tuple(reversed(range(8))),tuple(range(24,32))]
    for row in (0,8,16):
        walls.extend((row+i,row+(i+1)%8,row+(i+1)%8+8,row+i+8) for i in range(8))
    solid(sum(rings,[]),walls,'Footing')

def course(start,end,fixed,depth,base,top,along_x):
    length=end-start
    count=max(1,round(length/stone_rng.uniform(86.,108.)))
    joints=[start]+[start+length*i/count+stone_rng.uniform(-13.,13.) for i in range(1,count)]+[end]
    for a,b in zip(joints,joints[1:]):
        edge=fixed+stone_rng.uniform(-1.1,1.1)
        lo,hi=sorted((edge,depth))
        bounds=(a+.35,b-.35,lo,hi) if along_x else (lo,hi,a+.35,b-.35)
        footing_stone(*bounds,base,top+stone_rng.uniform(-.4,.3))

block(-799,799,-399,399,-136,-2,'Mortar')
for outside_x,outside_y,base,top in [(820,423,-51,-16.8),(813,416,-17.3,.25)]:
    for sign in (-1,1):
        # Long and short return stones exchange the corner joint between courses.
        wraps=base < -30
        course(-outside_x if wraps else -773,outside_x if wraps else 773,
               sign*outside_y,sign*368,base,top,True)
        stop=368 if wraps else outside_y
        runs=[(-stop,-88),(88,stop)] if sign<0 else [(-stop,stop)]
        for low,high in runs:
            course(low,high,sign*outside_x,sign*773,base,top,False)
for x in (-754,-400,0,400,754):
    for sign in (-1,1):
        for width,inner,outer,base,top in [(48,420,504,-47,-18),(44,414,498,-18.5,-6)]:
            y0,y1=sorted((sign*inner,sign*outer))
            footing_stone(x-width,x+width,y0,y1,base,top)
# Three low rises in the 34 cm plinth. The upper tread continues into the doorway.
footing_stone(-837,-732,-89,89,-36,.15)
footing_stone(-876,-834,-93,93,-37,-11.)
footing_stone(-920,-873,-98,98,-40,-23.)
for x,y,w,d,top in [(-948,-18,22,28,-31.6),(-999,11,18,22,-32.3),(-1036,-22,14,17,-32.8)]:
    footing_stone(x-w,x+w,y-d,y+d,-43,top)
finish('Foundation')

# Split fieldstones have a bed, a bulging exposed face, battered arrises and a chipped crown.
# Their end planes stay within the 180 cm module so adjoining segments can still step on hills.
def fieldstone(x0,x1,y0,y1,low,high,slot):
    gen=stone_rng
    cx,cy=(x0+x1)*.5,(y0+y1)*.5
    rx,ry=(x1-x0)*.5,(y1-y0)*.5
    outline=[(-.64,-1),(.10,-1),(.74,-.96),(1,-.57),(1,.26),(.76,.93),
             (.16,1),(-.68,.96),(-.98,.6),(-1,-.10),(-.95,-.68)]
    profile=[(x*gen.uniform(.91,1.),y*gen.uniform(.90,1.)) for x,y in outline]
    height=high-low
    tilt=gen.uniform(-.09,.09)*min(x1-x0,45)
    rings=[]
    for factor,t in [(.87,0.),(.99,.15),(1.,.74),(.87,.96)]:
        ring=[]
        for x,y in profile:
            r=factor*gen.uniform(.94,1.)
            ring.append((cx+rx*x*r,cy+ry*y*r,low+height*(t+gen.uniform(-.055,.055))+tilt*x))
        rings.extend(ring)
    n=len(profile)
    top=len(rings)
    rings.append((cx+rx*gen.uniform(-.25,.25),cy+ry*gen.uniform(-.2,.2),high))
    faces=[tuple(reversed(range(n)))]
    for row in range(3):
        for i in range(n):
            a=row*n+i;b=row*n+(i+1)%n
            faces.extend([(a,b,b+n),(a,b+n,a+n)])
    faces.extend((3*n+i,3*n+(i+1)%n,top) for i in range(n))
    first=len(slots)
    offset=(gen.random(),gen.random())
    solid(rings,faces,slot)
    for i in range(first,len(slots)):yard_offsets[i]=offset

stone_rng.seed(81930)
fieldstone(-21,21,-14,14,-6,2,'YardCap')
finish('YardPathStone')

for variant,seed in [('YardWallA',6431),('YardWallB',2287)]:
    stone_rng.seed(seed)
    block(-90,90,-13.,13.,-52,67,'Mortar')
    for side in (-1,1):
        # Different joint stations on each face; split taller stones with occasional packing slates.
        phase=stone_rng.uniform(-3.1,3.1)
        def bed(x,row):
            base=(-53.,8.,34.,53.,70.)[row]
            return base+(0. if row==0 else (3.5 if row in (1,2,3) else 1.1)*math.sin(x*.049+row+phase))
        for row in range(4):
            count=stone_rng.choice((3,4)) if row in (0,1) else stone_rng.choice((4,5,6))
            cuts=[-90]+[-90+180*i/count+stone_rng.uniform(-9.,9.) for i in range(1,count)]+[90]
            for left,right in zip(cuts,cuts[1:]):
                x=(left+right)*.5
                y0,y1=sorted((side*7.,side*(24.-row*.65+stone_rng.uniform(-2.2,2.8))))
                low,high=bed(x,row)-1.0,bed(x,row+1)+1.
                if high-low>21 and right-left>38 and stone_rng.random()<.34:
                    fieldstone(left-.5,right+.5,y0,y1,low,low+7,'YardSlate')
                    low+=6.
                slot='YardSlate' if stone_rng.random()<.26 else 'YardField'
                fieldstone(left-.65,right+.65,y0,y1,low,high,slot)
    cuts=[-90,-53+stone_rng.uniform(-7,7),-12+stone_rng.uniform(-8,8),38+stone_rng.uniform(-8,8),90]
    for left,right in zip(cuts,cuts[1:]):
        fieldstone(left-1,right+1,-25.5,25.5,67.,stone_rng.uniform(81.,86.),'YardCap')
    finish(variant)

stone_rng.seed(815)
block(-23,23,-23,23,-52,89,'Mortar')
fieldstone(-33,33,-33,33,-54,13,'YardField')
for row,(low,high) in enumerate([(10,29),(27,48),(46,67),(65,85)]):
    joint=stone_rng.uniform(-6.,6.)
    for a,b in [(-30,joint+.6),(joint-.6,30)]:
        bounds=(a,b,-30,30) if row%2 else (-30,30,a,b)
        fieldstone(*bounds,low,high,'YardField' if row!=2 else 'YardSlate')
fieldstone(-33,33,-33,33,82,94,'YardSlate')
fieldstone(-35,35,-35,35,91,105,'YardCap')
finish('YardPier')
# Preserve both riser heights; use the same scan joint pattern across the sanctuary.
for x0,x1,height in [(0,44,10),(44,400,20)]:
    cut=[(x0,0),(x1,0),(x1,height),(x0+.8,height),(x0,height-.8)]
    extrusion([(x,-350,z) for x,z in cut],[(x,350,z) for x,z in cut],'Flagstone')
finish('SanctuarySteps')
# A 1.9 m weathered path tile. Deeper sides accommodate small terrain variation.
section([(-108,-24),(108,-24),(101,-1),(76,0),(-74,0),(-103,-2)],-100,100,'Trail')
finish('Path')

