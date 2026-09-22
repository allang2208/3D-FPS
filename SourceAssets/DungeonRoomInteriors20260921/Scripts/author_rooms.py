"""Build the approved two-room art revision in Blender. No preview/test is run.

Coordinates are Blender metres, same base as AtmosphereV2. Workshop u runs from
X=10 toward X=4, v from Y=0 to Y=-4.2. Ruin u/v map to X=15+u, Y=4+v.
"""
import bpy, bmesh, json, math, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
OLD=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
R=random.Random(921255)
recipes=json.loads((OUT/'material-manifest.json').read_text())
MATS={}
for name,rec in recipes.items():
    m=bpy.data.materials.new('Room_'+name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Metallic'].default_value=rec['metallic']
    for ch,pin in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(rec['maps'][ch],check_existing=True)
        tex.image.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
        source=tex.outputs['Color']
        if ch=='Normal':
            n=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(source,n.inputs['Color']);source=n.outputs[0]
        m.node_tree.links.new(source,p.inputs[pin])
    MATS[name]=m

# Modern threshold retains the existing concrete surface family.
m=bpy.data.materials.new('V2_Concrete');m.use_nodes=True
p=m.node_tree.nodes.get('Principled BSDF')
for ch,pin in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OLD/'Authored/Textures'/('Concrete_'+ch+'.png')),check_existing=True)
    tex.image.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
    source=tex.outputs['Color']
    if ch=='Normal':
        n=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(source,n.inputs['Color']);source=n.outputs[0]
    m.node_tree.links.new(source,p.inputs[pin])
MATS['Concrete']=m
for name,color,rough,emit in [('WarmGlass',(1,.67,.36),.36,3),('Paper',(.53,.48,.34),.94,0)]:
    m=bpy.data.materials.new('Room_'+name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emit
    MATS[name]=m

groups={}
def world(name,p):
    x,y,z=p
    return (10-x,-y,z) if name.startswith('WS_') else (15+x,4+y,z) if name.startswith('RU_') else (x,y,z)
def add(name,verts,faces,mat='Iron',tint=None):
    g=groups.setdefault(name,{'v':[],'f':[],'m':[],'colors':[]});o=len(g['v'])
    g['v'].extend(world(name,p) for p in verts);g['f'].extend(tuple(o+i for i in f) for f in faces)
    g['m'].extend([mat]*len(faces));value=R.uniform(.84,1.0) if tint is None else tint
    g['colors'].extend([(value,value,value,1)]*len(faces))

def box(name,c,size,mat='Iron',rz=0):
    x,y,z=c;a,b,d=[v/2 for v in size];co,si=math.cos(rz),math.sin(rz)
    v=[(x+i*co-j*si,y+i*si+j*co,z+k) for i,j,k in [(-a,-b,-d),(a,-b,-d),(a,b,-d),(-a,b,-d),(-a,-b,d),(a,-b,d),(a,b,d),(-a,b,d)]]
    add(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def tube(name,points,radius,mat='Iron',sides=12,cap=True):
    vs=[];ps=[Vector(p) for p in points]
    for i,p in enumerate(ps):
        t=(ps[min(i+1,len(ps)-1)]-ps[max(i-1,0)]).normalized()
        h=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
        a=t.cross(h).normalized();b=t.cross(a).normalized()
        vs.extend(tuple(p+radius*(math.cos(j*math.tau/sides)*a+math.sin(j*math.tau/sides)*b)) for j in range(sides))
    fs=[]
    for i in range(len(ps)-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    if cap:fs.extend([tuple(reversed(range(sides))),tuple((len(ps)-1)*sides+j for j in range(sides))])
    add(name,vs,fs,mat)

def ring(name,c,axis,radius,thick,mat='Iron',segments=24):
    axis=Vector(axis).normalized();a=axis.cross(Vector((0,0,1)) if abs(axis.z)<.9 else Vector((0,1,0))).normalized();b=axis.cross(a)
    points=[Vector(c)+radius*(math.cos(i*math.tau/segments)*a+math.sin(i*math.tau/segments)*b) for i in range(segments+1)]
    tube(name,[tuple(p) for p in points],thick,mat,8,False)

def plate(name,points,z,depth,mat='OldStone'):
    area=sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))
    if area<0:points=list(reversed(points))
    n=len(points);v=[(x,y,z+d) for d in (-depth,0) for x,y in points]
    fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    add(name,v,fs,mat)

def stone(name,c,size,mat='OldStone',angle=0):
    # Chamfered irregular block with independent top/bottom corners and small face
    # deviation. Mortar gaps remain structural rather than painted black seams.
    sx,sy,sz=size;cut=R.uniform(.13,.22);corners=[(-.5+cut,-.5),(.5-cut,-.5),(.5,-.5+cut),(.5,.5-cut),(.5-cut,.5),(-.5+cut,.5),(-.5,.5-cut),(-.5,-.5+cut)]
    vs=[];co,si=math.cos(angle),math.sin(angle)
    for k in (-.5,.5):
        for x,y in corners:
            px=(x+R.uniform(-.025,.025))*sx;py=(y+R.uniform(-.025,.025))*sy
            vs.append((c[0]+px*co-py*si,c[1]+px*si+py*co,c[2]+k*sz+R.uniform(-.017,.017)))
    fs=[tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    add(name,vs,fs,mat,R.uniform(.77,1))

def crate(name,x,y,z,w=.44,d=.34,h=.28,mat='GreenPaint',angle=0):
    # Open-topped box with actual internal negative space.
    def b(cx,cy,cz,sx,sy,sz,m=mat):
        co,si=math.cos(angle),math.sin(angle)
        box(name,(x+cx*co-cy*si,y+cx*si+cy*co,z+cz),(sx,sy,sz),m,angle)
    b(0,0,.013,w,d,.026)
    for side in (-1,1):
        b(side*(w/2-.012),0,h/2,.024,d,h)
        b(0,side*(d/2-.012),h/2,w,.024,h)
        b(side*(w/2-.038),0,h-.035,.013,d*.65,.035,'Iron')

def bolt(name,p,axis=(0,0,1),radius=.009):
    a=Vector(p);b=a+Vector(axis)*.009;tube(name,[a,b],radius,'Iron',6)

# Workshop: 2.6 m return and a 2.2 m side bench, manufactured frame and individual timber boards.
def bench_section(x,y,w,d):
    for i in range(3):
        box('WS_Workbench',(x,y-d/2+(i+.5)*d/3,.908),(w,d/3-.006,.062),'Timber')
    for dx in (-w/2+.065,w/2-.065):
        for dy in (-d/2+.055,d/2-.055):
            box('WS_Workbench',(x+dx,y+dy,.444),(.065,.065,.86),'GreenPaint')
            box('WS_Workbench',(x+dx,y+dy,.021),(.11,.10,.025),'Iron')
            bolt('WS_BenchDetail',(x+dx,y+dy,.945))
    for dy in (-d/2+.04,d/2-.04):box('WS_Workbench',(x,y+dy,.817),(w,.046,.098),'GreenPaint')
    for dx in (-w/2+.025,w/2-.025):box('WS_Workbench',(x+dx,y,.817),(.046,d,.098),'GreenPaint')
    box('WS_Workbench',(x,y,.21),(w-.06,d-.08,.037),'GreenPaint')
    box('WS_Workbench',(x,y+d/2-.04,.13),(w-.05,.035,.065),'Iron')
bench_section(.55,2.61,.76,2.26)
bench_section(1.77,3.73,1.64,.68)
# Vise on return bench: base, jaws, screw and adjustable tommy bar.
box('WS_BenchDetail',(2.28,3.56,.97),(.24,.23,.05),'Iron')
box('WS_BenchDetail',(2.28,3.56,1.055),(.20,.15,.14),'GreenPaint')
for xx in (2.18,2.38):box('WS_BenchDetail',(xx,3.55,1.14),(.043,.21,.075),'Iron')
tube('WS_BenchDetail',[(2.11,3.56,1.05),(2.48,3.56,1.05)],.016,'Iron',14)
tube('WS_BenchDetail',[(2.49,3.47,.997),(2.49,3.67,1.11)],.009,'Iron',10)

# Pegboard on left wall: true holes, some unused. Sheets stay regular; tools vary.
for iz in range(9):
    for iy in range(19):
        cy=1.70+iy*.11;cz=1.22+iz*.11;a=.055;r=.008
        outer=[(-a,-a),(0,-a),(a,-a),(a,0),(a,a),(0,a),(-a,a),(-a,0)]
        inner=[(math.cos(-3*math.pi/4+i*math.pi/4)*r,math.sin(-3*math.pi/4+i*math.pi/4)*r) for i in range(8)]
        vs=[(xx,cy+y,cz+z) for xx in (.168,.176) for y,z in outer+inner]
        fs=[]
        for j in range(8):
            k=(j+1)%8;fs.extend([(j,k,8+k,8+j),(16+j,24+j,24+k,16+k),(8+j,8+k,24+k,24+j)])
        add('WS_Toolboard',vs,[tuple(reversed(f)) for f in fs],'GreenPaint')
for z in (1.16,2.21):box('WS_Toolboard',(.171,2.69,z),(.046,2.20,.030),'Iron')
for y in (1.61,3.78):box('WS_Toolboard',(.171,y,1.685),(.046,.030,1.07),'Iron')
# Hanging hand tools with distinctly different silhouettes and retained empty hooks.
for i in range(10):
    y=1.78+i*.183;top=2.055-R.uniform(0,.10);length=R.uniform(.21,.37)
    tube('WS_HandTools',[(.179,y,top),(.24,y,top),(.25,y,top+.026)],.004,'Iron',8)
    if i in (3,8):continue
    if i%3==0:
        tube('WS_HandTools',[(.237,y,top-.016),(.24,y+.018,top-length)],.010,'Iron',8)
        ring('WS_HandTools',(.24,y,top-.035),(1,0,0),.028,.008,'Iron',14)
    elif i%3==1:
        box('WS_HandTools',(.24,y,top-length*.63),(.026,.027,length*.52),'RedPaint')
        tube('WS_HandTools',[(.24,y,top-.027),(.24,y,top-length*.40)],.005,'Iron',8)
    else:
        tube('WS_HandTools',[(.238,y-.025,top-length),(.24,y,top-.08),(.24,y+.03,top-.015)],.010,'GreenPaint',8)
        tube('WS_HandTools',[(.238,y+.038,top-length),(.24,y,top-.08),(.24,y-.025,top-.015)],.010,'Iron',8)

# Wheeled drawer cabinet at the side of the work area, slightly misaligned.
cx,cy=.55,1.02
box('WS_ToolCart',(cx,cy,.505),(.68,.50,.72),'RedPaint',-.07)
box('WS_ToolCart',(cx,cy,.884),(.73,.55,.035),'Rubber',-.07)
for i in range(6):
    z=.24+i*.10;pull=.065 if i==4 else 0
    box('WS_CartDetail',(cx+.353+pull,cy,z),(.025,.43,.087),'RedPaint',-.07)
    tube('WS_CartDetail',[(cx+.39+pull,cy-.145,z+.011),(cx+.418+pull,cy-.145,z+.011),(cx+.418+pull,cy+.125,z+.011),(cx+.39+pull,cy+.125,z+.011)],.007,'Iron',8)
for dx in (-.245,.245):
    for dy in (-.16,.16):
        tube('WS_ToolCart',[(cx+dx-.032,cy+dy,.083),(cx+dx+.032,cy+dy,.083)],.069,'Rubber',18)
        box('WS_CartDetail',(cx+dx,cy+dy,.151),(.034,.08,.052),'Iron')
tube('WS_CartDetail',[(.36,.728,.78),(.36,.65,.82),(.74,.65,.82),(.74,.728,.78)],.012,'Iron',12)

# A shallow parts rack, with feet, rivets, shelf lips and deliberately empty bays.
for x in (5.34,5.85):
    for y in (.50,2.23):
        box('WS_PartsRack',(x,y,1.01),(.045,.046,2.0),'GreenPaint')
        box('WS_PartsRack',(x,y,.016),(.10,.10,.024),'Iron')
        for z in (.27,.75,1.26,1.78):bolt('WS_RackContents',(x+.026,y,z),(1,0,0),.007)
for z in (.24,.74,1.24,1.74):
    box('WS_PartsRack',(5.595,1.365,z),(.56,1.80,.029),'GreenPaint')
    box('WS_PartsRack',(5.31,1.365,z+.016),(.020,1.81,.056),'Iron')
for y,z,w,d,h,mat in [(.77,.77,.40,.43,.28,'GreenPaint'),(1.34,.77,.42,.49,.31,'GreenPaint'),(1.91,.27,.43,.46,.28,'Timber'),(.95,1.27,.39,.66,.22,'GreenPaint'),(1.88,1.77,.40,.49,.18,'Timber')]:
    crate('WS_RackContents',5.59,y,z,w,d,h,mat,R.uniform(-.035,.035))
    if z<1:
        for i in range(3):tube('WS_RackContents',[(5.48,y-.12+i*.08,z+.10),(5.72,y-.12+i*.08,z+.12)],.025,'Iron',10)
for x,y in [(.52,2.02),(.53,3.15),(1.46,3.77)]:crate('WS_BenchStorage',x,y,.238,.46,.39,.30,'GreenPaint',R.uniform(-.025,.025))

# Small bench items: canisters with seams, fastener tray and folded cloth.
for x,y,z,r,h in [(1.29,3.79,.94,.040,.18),(1.41,3.75,.94,.035,.24),(.63,1.64,.94,.040,.11)]:
    tube('WS_BenchDetail',[(x,y,z),(x,y,z+h)],r,'YellowPaint',18)
    ring('WS_BenchDetail',(x,y,z+h-.004),(0,0,1),r,.0028,'Iron',18)
    tube('WS_BenchDetail',[(x,y,z+h),(x,y,z+h+.018)],r*.44,'Iron',12)
crate('WS_BenchDetail',.61,3.44,.94,.30,.19,.035,'Iron',.08)
for i in range(16):
    x=R.uniform(.49,.72);y=R.uniform(3.38,3.50)
    tube('WS_BenchDetail',[(x,y,.951),(x+.035,y+.005,.953)],.004,'Iron',6)
# Folded/draped rag using a shallow grid, hanging over bench inside edge.
v=[];f=[]
for iy in range(12):
    for ix in range(9):
        x=.63+ix*.042;y=2.10+iy*.030
        z=.947 if x<.93 else .947-(x-.93)*3.1
        v.append((x,y,z+.008*math.sin(ix*1.7+iy*.55)))
for j in range(11):
    for i in range(8):a=j*9+i;f.append((a,a+1,a+10,a+9))
add('WS_Cloth',v,f,'Canvas')

# Separate functional pipe continuations, power conduit and cable tray.
for h,r in [(2.78,.065),(3.03,.046)]:
    tube('WS_Utilities',[(3.15,3.42,h-.33),(3.15,3.42,h-.10),(3.17,3.47,h),(3.26,3.60,h),(3.40,3.81,h),(5.74,3.81,h),(5.81,3.72,h),(5.81,.0,h)],r,'GreenPaint',16)
    for x in (3.54,4.52,5.38):
        ring('WS_UtilityDetail',(x,3.81,h),(1,0,0),r+.006,.008,'Iron',20)
        box('WS_UtilityDetail',(x,4.025,h),(.09,.22,.035),'Iron')
for u in (4.47,5.04):
    tube('WS_Utilities',[(u,3.90,2.1),(u,3.99,2.56),(u,3.99,3.12),(u,3.89,3.16),(.45,3.89,3.16),(.19,3.68,3.16),(.19,2.62,3.16),(.19,2.62,1.35)],.017,'Iron',12)
for u in (.65,5.3):
    for du in (-.15,.15):box('WS_CableTray',(u+du,2.00,3.10),(.025,4.0,.065),'Iron')
    for j in range(25):box('WS_CableTray',(u,(j+.5)*.16,3.075),(.31,.021,.018),'Iron')
    for v in (.6,1.8,3.0):tube('WS_CableTray',[(u,v,3.1),(u,v,3.28)],.009,'Iron',8)
    for j in range(3):tube('WS_Cables',[(u-.07+j*.065,0,3.11),(u-.07+j*.065,3.65,3.11),(u+.13,3.90,3.04)],.012,'Rubber',10)
box('WS_UtilityDetail',(.203,2.65,1.31),(.055,.25,.12),'GreenPaint')
for y in (2.59,2.71):ring('WS_UtilityDetail',(.236,y,1.31),(1,0,0),.022,.007,'Rubber',14)

# Articulated task light: wall clamp, two arms and a proper tapered shade.
box('WS_TaskLight',(.26,2.13,.962),(.12,.13,.035),'Iron')
tube('WS_TaskLight',[(.25,2.13,.98),(.39,2.13,1.33),(.68,2.17,1.65),(.86,2.20,1.48)],.012,'Iron',12)
for p in [(.39,2.13,1.33),(.68,2.17,1.65)]:tube('WS_TaskLight',[(p[0],p[1]-.025,p[2]),(p[0],p[1]+.025,p[2])],.031,'Iron',14)
vs=[]
for z,r in [(1.50,.034),(1.40,.108),(1.493,.028),(1.403,.102)]:vs.extend((.86+r*math.cos(i*math.tau/24),2.20+r*math.sin(i*math.tau/24),z) for i in range(24))
shade_faces=[tuple(range(24)),tuple(reversed(range(48,72)))]
for i in range(24):
    j=(i+1)%24
    shade_faces.extend([(i,i+24,j+24,j),(48+i,48+j,72+j,72+i),(24+i,72+i,72+j,24+j)])
add('WS_TaskLight',vs,shade_faces,'GreenPaint')
tube('WS_TaskLight',[(.86,2.20,1.402),(.86,2.20,1.409)],.079,'WarmGlass',24)
tube('WS_Cables',[(.20,2.64,1.31),(.25,2.6,1.10),(.23,2.45,.76),(.34,2.21,.83),(.26,2.13,.98)],.006,'Rubber',8)

# Coiled replacement cable under the bench; restrained workshop floor detail.
for k in range(5):
    ring('WS_BenchStorage',(.53,2.95,.28+k*.018),(0,0,1),.16,.009,'Rubber',30)
box('WS_FloorDetails',(1.19,2.73,.009),(.53,1.05,.018),'Rubber',.026)
for j in range(22):box('WS_FloorDetails',(1.19,2.25+j*.044,.02),(.49,.006,.006),'Rubber',.026)

# Handling wear is grouped on reachable edges, drawer fronts and working timber.
for i in range(31):
    y=R.uniform(1.59,3.66);z=R.uniform(.803,.861);w=R.uniform(.012,.056);h=R.uniform(.002,.008)
    add('WS_LocalWear',[(.9305,y-w,z),(.9305,y+w,z+h*.3),(.9305,y+w*.35,z+h),(.9305,y-w*.8,z+h*.7)],[(0,1,2,3)],'Rust' if i%4==0 else 'Iron')
for i in range(17):
    x=R.uniform(.25,.81);y=R.uniform(1.76,3.44);length=R.uniform(.025,.11)
    add('WS_LocalWear',[(x,y,.940),(x+length,y+.004,.940),(x+length*.6,y+.0057,.940),(x+.01,y+.0021,.940)],[(0,1,2,3)],'Rust')
for i in (0,2,4):
    z=.24+i*.10;pull=.065 if i==4 else 0
    box('WS_LocalWear',(.55+.368+pull,.87,z+.035),(.001,.043,.005),'Iron')

# Ruin room geometry follows below; all new surfaces stay inside the existing envelope.

# Replace only this room's slab: modern threshold to a shallow, exposed old floor.
box('RU_ModernCeiling',(3.25,.81,4.67),(6.5,1.66,.20),'Concrete')
box('RU_ModernCeiling',(3.25,.03,4.23),(6.5,.22,.66),'Concrete')
threshold=[(0,0),(6.5,0),(6.5,1.40),(5.66,1.56),(5.10,1.29),(4.32,1.62),(3.73,1.44),(3.02,1.60),(2.40,1.28),(1.77,1.49),(.98,1.29),(0,1.46)]
plate('RU_Threshold',threshold,0,.22,'Concrete')
box('RU_Foundation',(3.25,4.46,-.40),(6.48,6.02,.30),'Soil')
for row in range(8):
    y=1.62+row*.70;x=-.20 if row%2 else 0
    while x<6.45:
        width=R.uniform(.64,1.12);x0=max(.03,x);x1=min(6.46,x+width-.018)
        if x1>x0:
            points=[(x0+.03,y),(x1-.055,y+R.uniform(-.02,.02)),(x1,y+.065),(x1-.025,y+.63),(x0+.045,y+.65),(x0,y+.58)]
            plate('RU_OldFlagstones',points,-.178+R.uniform(-.01,.01),.105,'OldStone')
        x+=width
# Graded earth edge reaches the old floor, avoiding a sharp step across the route.
vs=[];fs=[]
for j in range(5):
    v=1.30+j*.14
    for i in range(27):
        u=i*6.5/26;z=-.18*j/4+.008*math.sin(i*1.6+j*.7)
        vs.append((u,v,z))
for j in range(4):
    for i in range(26):a=j*27+i;fs.extend([(a,a+1,a+28),(a,a+28,a+27)])
add('RU_ThresholdEarth',vs,fs,'Soil')

def side_masonry(side):
    z=-.15;row=0
    while z<3.38:
        h=R.uniform(.28,.44);v=1.73 if row%2 else 1.94
        while v<7.35:
            length=R.uniform(.46,.90);end=min(7.36,v+length)
            depth=R.uniform(.35,.56);x=depth/2 if side==0 else 6.5-depth/2
            stone('RU_OldMasonry',(x,(v+end)/2,z+h/2),(depth,end-v-.025,h-.026),'OldStone',R.uniform(-.015,.015))
            v=end+.018
        z+=h;row+=1
side_masonry(0);side_masonry(1)
z=-.15;row=0
while z<4.24:
    h=R.uniform(.28,.43);x=.12
    while x<6.39:
        length=R.uniform(.46,.94);end=min(6.40,x+length)
        stone('RU_BackMasonry',((x+end)/2,7.25,z+h/2),(end-x-.02,.45,h-.021),'OldStone',R.uniform(-.012,.012))
        x=end+.02
    z+=h;row+=1

# Elliptical buried vault, below the old 4.6 m ceiling envelope. Continuous backing
# is separate from masonry courses so tiny mortar gaps don't open into the sky.
for layer in ('Backing','Stones'):
    for j in range(7):
        ya=1.60+j*.82;yb=min(7.38,ya+.82)
        for i in range(17):
            a0=i*math.pi/17; a1=(i+1)*math.pi/17
            inset=.009 if layer=='Stones' else 0
            a0+=inset;a1-=inset
            if layer=='Backing':rx,rz,base=3.31,1.20,3.25
            else:rx,rz,base=3.17,1.20,3.25
            v=[]
            for yv in (ya+(0.012 if layer=='Stones' else 0),yb-(.012 if layer=='Stones' else 0)):
                for aa,rr,zz in [(a0,rx,rz),(a1,rx,rz),(a1,rx+.13,rz+.12),(a0,rx+.13,rz+.12)]:
                    v.append((3.25+rr*math.cos(aa),yv,base+zz*math.sin(aa)))
            faces=[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
            add('RU_Vault'+layer,v,[tuple(reversed(f)) for f in faces],'Soil' if layer=='Backing' else 'OldStone')

# Excavated bank geometry forms continuous slopes. Scattered pieces stay on the
# bank and foot, with a deliberate open approach around u=3.0..4.8.
vs=[];fs=[]
for j in range(27):
    v=1.54+j*.215;width=1.34+.32*math.sin(j*.28)+.15*math.cos(j*.74)
    for i in range(8):
        t=i/7;u=.15+t*width
        h=(1-t)**1.15*(.62+.37*math.sin(j*.14+.1)+.22*math.sin(j*.43))
        vs.append((u,v,-.15+max(.015,h)+R.uniform(-.025,.025)*(1-t)))
for j in range(26):
    for i in range(7):a=j*8+i;fs.extend([(a,a+1,a+9),(a,a+9,a+8)])
add('RU_EarthBank',vs,fs,'Soil')
for i in range(130):
    y=R.uniform(1.75,7.10);x=R.uniform(.32,1.50)
    z=-.13+max(0,1-x/1.65)*(.54+.20*math.sin(y*1.4))
    s=R.uniform(.045,.20)
    stone('RU_BankFragments',(x,y,z),(s*R.uniform(1,2.4),s*R.uniform(1,2),s*.8),'OldStone',R.uniform(-1,1))
for i in range(24):
    x=R.uniform(5.78,6.13);y=R.uniform(2.0,7.05);s=R.uniform(.055,.17)
    stone('RU_BankFragments',(x,y,-.12),(s*1.8,s*1.4,s),'OldStone',R.uniform(-2,2))

# Low damaged pedestal keeps the existing statue identity while embedding its base.
for c,size in [((4.10,5.95,-.05),(1.66,1.40,.26)),((4.10,5.95,.19),(1.32,1.13,.25)),((4.10,5.95,.416),(1.12,.96,.185))]:
    stone('RU_EmbeddedPlinth',c,size,'OldStone',.007)
for i in range(10):
    x=R.uniform(3.16,3.47);y=R.uniform(5.28,6.57);s=R.uniform(.09,.20)
    stone('RU_BankFragments',(x,y,-.10),(s*1.9,s*1.3,s),'OldStone',R.uniform(-1,1))

# Industrial shoring at the modern edge: telescopic uprights, baseplates,
# collars, screw threads and timber packing under the short steel crossbeam.
for y in (.24,1.10):
    x=1.17;top=3.17
    box('RU_Shoring',(x,y,.022),(.23,.22,.04),'Iron')
    tube('RU_Shoring',[(x,y,.04),(x,y,1.66)],.044,'GreenPaint',20)
    tube('RU_Shoring',[(x,y,1.53),(x,y,top)],.031,'Iron',20)
    for z in (1.40,1.63):ring('RU_ShoringDetail',(x,y,z),(0,0,1),.052,.012,'Iron',24)
    for i in range(11):ring('RU_ShoringDetail',(x,y,1.68+i*.018),(0,0,1),.033,.0023,'Iron',18)
    tube('RU_ShoringDetail',[(x-.14,y,1.61),(x+.14,y,1.61)],.009,'Iron',12)
    for z in (1.90,2.18,2.46):bolt('RU_ShoringDetail',(x+.035,y,z),(1,0,0),.007)
    box('RU_Shoring',(x,y,top+.025),(.28,.25,.050),'Iron')
    box('RU_Shoring',(x,y,top+.08),(.30,.34,.06),'Timber')
    for a in (-.08,.08):
        for b in (-.07,.07):bolt('RU_ShoringDetail',(x+a,y+b,.048))
for z in (3.225,3.415):box('RU_EntryBeam',(2.85,1.19,z),(3.71,.24,.028),'Iron')
box('RU_EntryBeam',(2.85,1.19,3.32),(3.71,.028,.19),'Iron')
for x in (1.14,4.54):box('RU_EntryBeam',(x,1.19,3.465),(.32,.28,.075),'Timber')
for z in (3.295,3.405):box('RU_EntryBeam',(1.17,.71,z),(.18,1.26,.026),'Iron')
box('RU_EntryBeam',(1.17,.71,3.35),(.024,1.26,.11),'Iron')
plate('RU_Overhang',[(.77,0),(4.79,0),(4.73,1.36),(4.24,1.46),(3.82,1.34),(3.28,1.47),(2.65,1.40),(2.24,1.48),(.88,1.40)],3.66,.21,'Concrete')

# Temporary construction lamp and physical cable running along the entrance edge.
cx,cy=1.63,.96
for a in (0,math.tau/3,math.tau*2/3):
    tube('RU_WorkLamp',[(cx,cy,.57),(cx+math.cos(a)*.28,cy+math.sin(a)*.28,.06)],.016,'YellowPaint',12)
tube('RU_WorkLamp',[(cx,cy,.06),(cx,cy,1.12)],.018,'YellowPaint',14)
box('RU_WorkLamp',(cx,cy,1.245),(.31,.095,.28),'YellowPaint')
box('RU_WorkLamp',(cx,cy+.050,1.245),(.265,.013,.23),'Rubber')
box('RU_WorkLamp',(cx,cy+.060,1.245),(.238,.006,.20),'WarmGlass')
for x in (cx-.107,cx+.107):box('RU_WorkLamp',(x,cy+.07,1.245),(.006,.009,.217),'Iron')
tube('RU_WorkLamp',[(cx-.19,cy,1.24),(cx-.19,cy,1.43),(cx+.19,cy,1.43),(cx+.19,cy,1.24)],.009,'Iron',10)
tube('RU_Cable',[(cx,cy-.04,1.17),(cx-.07,cy-.10,.53),(cx-.21,cy-.14,.035),(1.29,.56,.024),(1.05,.33,.023),(1.02,.07,.022)],.009,'Rubber',12)
for i in range(3):ring('RU_Cable',(1.60,.43,.020+i*.02),(0,0,1),.19,.009,'Rubber',32)

# Reuse the original arch geometry, retain its silhouette, adapt only this copy.
with bpy.data.libraries.load(str(OLD/'Authored/DungeonAtmosphereV2_Structure.blend'),link=False) as (src,dst):
    dst.objects=['SM_V2_AncientArch']
arch=dst.objects[0];scene.collection.objects.link(arch)
arch.name='SM_Room_RU_AncientArch';arch.data.materials.clear();arch.data.materials.append(MATS['OldStone'])
for v in arch.data.vertices:
    v.co.x+=.85;v.co.y+=.53;v.co.z-=.18
for p in arch.data.polygons:p.material_index=0

objects=[arch]
NONCOLLISION={'WS_BenchDetail','WS_Toolboard','WS_HandTools','WS_CartDetail','WS_RackContents','WS_RackContents','WS_LocalWear','WS_Cloth','WS_Cables','WS_TaskLight','WS_FloorDetails','WS_UtilityDetail','WS_CableTray','RU_BankFragments','RU_ShoringDetail','RU_WorkLamp','RU_Cable'}
for name,g in groups.items():
    mesh=bpy.data.meshes.new('SM_Room_'+name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    obj=bpy.data.objects.new('SM_Room_'+name,mesh);scene.collection.objects.link(obj)
    used=list(dict.fromkeys(g['m']))
    for key in used:mesh.materials.append(MATS[key])
    colors=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    uv=mesh.uv_layers.new(name='UVMap')
    for face,key,color in zip(mesh.polygons,g['m'],g['colors']):
        face.material_index=used.index(key)
        axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(p[dims[0]]/.8,p[dims[1]]/.8)
            colors.data[li].color=color
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if name not in ('WS_Cloth','WS_HandTools','WS_LocalWear','RU_EarthBank','RU_ThresholdEarth','WS_Toolboard','WS_Cables','RU_Cable'):
        bevel=obj.modifiers.new('Physical edge radius','BEVEL');bevel.width=.007 if name.startswith('RU_') else .0025;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.62
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    # Do not smooth entire mechanical assemblies; retain their planar normals.
    for f in mesh.polygons:f.use_smooth=False
    tri=obj.modifiers.new('Tangent triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    obj.select_set(False);objects.append(obj)

# Surgical source copy: remove only the ruin's fluorescent fixture from its
# combined mesh. All eight unrelated fixtures retain source geometry/materials.
with bpy.data.libraries.load(str(OLD/'Authored/DungeonAtmosphereV2_Structure.blend'),link=False) as (src,dst):dst.objects=['SM_V2_LightFixtures']
fixtures=dst.objects[0];scene.collection.objects.link(fixtures);fixtures.name='SM_Room_FixturesWithoutRuin'
bm=bmesh.new();bm.from_mesh(fixtures.data)
faces=[f for f in bm.faces if 17.7<f.calc_center_median().x<19.3 and 8.7<f.calc_center_median().y<9.7 and f.calc_center_median().z>3.7]
bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(fixtures.data);bm.free();objects.append(fixtures)

# Make a focused editable source, with generated placements attached separately.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonRooms_Authored.blend'))
manifest=[]
for obj in objects:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    name=obj.name;path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    short=name.removeprefix('SM_Room_')
    manifest.append({'name':name,'fbx':str(path),'collision':short not in NONCOLLISION and short!='FixturesWithoutRuin','materials':[s.material.name for s in obj.material_slots],
        'actor_label':'DGN_Room_'+short,'replace_actor':'DGN_AV2_LightFixtures' if short=='FixturesWithoutRuin' else None})
data={'objects':manifest,'seed':921255,'coordinate_system':'Blender metres, world baked, UE Y mirrored','tests_run':False,
    'hidden_existing':['DGN_AV2_RuinNiche_Floor','DGN_AV2_RuinNiche_Ceiling','DGN_AV2_AncientArch','DGN_AV2_AncientPlinth','DGN_AV2_Collapse_2','DGN_AV2_Collapse_3','DGN_AV2_Damp_4','DGN_AV2_Damp_8'],
    'statue_anchor_blender_cm':[1910,995,51],
    'prop_moves':[{'label':'DGN_AV2_Workshop_Electrical','cm':[503,-378,0],'yaw':180,'scale':[.92,1,.96]},
                  {'label':'DGN_AV2_Workshop_Bypass','cm':[682,-345,0],'yaw':185,'scale':[.72,.72,.90]}],
    'new_generated':[
                     {'id':'buried_masonry_bank','cm':[1588,818,-17],'yaw':-90,'scale':[1,.85,.80],'label':'DGN_Room_RU_MasonryBank_A'},
                     {'id':'buried_masonry_bank','cm':[1590,1015,-17],'yaw':-83,'scale':[.80,.74,.64],'label':'DGN_Room_RU_MasonryBank_B'}],
    'lights':[{'label':'DGN_Room_WS_TaskLightSource','cm':[916,-220,138],'intensity':180,'radius':230,'color':[1,.76,.51]},
              {'label':'DGN_Room_RU_WorkLightSource','cm':[1663,511,124.5],'intensity':1250,'radius':820,'color':[1,.77,.52]}],
    'decals':[{'label':'Oil_Cart','material':'Oil','cm':[937,-104,2],'extent':[4,31,41],'yaw':0,'pitch':-90},
              {'label':'Oil_Bench','material':'Oil','cm':[892,-286,2],'extent':[4,17,29],'yaw':0,'pitch':-90},
              {'label':'Dust_Shelf','material':'Dust','cm':[442,-142,2],'extent':[4,32,85],'yaw':0,'pitch':-90},
              {'label':'Leak_Valve','material':'Leak','cm':[682,-405,154],'extent':[4,30,101],'yaw':90,'pitch':0}]}
(OUT/'room-manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('ROOM_GEOMETRY_AUTHORED',len(manifest),'mesh groups; no preview/test')
