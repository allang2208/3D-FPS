"""Build the scoped Kitchen Detail V1, using UE's live positions as anchors.
Never rebuilds the apartment or changes shared refrigerator source assets.
"""
from pathlib import Path
import sys,json,math,bpy,importlib
from mathutils import Vector, Matrix
R=Path(__file__).resolve().parent
sys.path[:0]=[str(R),str(R.parents[2]/'SourceAssets/DungeonReceptionHall20261006/Scripts')]
import spec
importlib.reload(spec)
from spec import PBR,PLACEMENTS,ROOM,COUNTER,INTERFACES
import model
model=importlib.reload(model)
g=model
import materials
materials=importlib.reload(materials)
from materials import all_materials

g.clear()
col=bpy.data.collections.new('KIT_Source');bpy.context.scene.collection.children.link(col)
ctx=bpy.data.collections.new('CTX_KitchenContext');bpy.context.scene.collection.children.link(ctx)
g.M=all_materials(R,PBR)
g.M['Armor']=g.M['Enamel'];g.M['EdgeSteel']=g.M['Steel']
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.

def vessel(k,c,radius,height,material='Porcelain',n=72):
    # One closed meridian: outer foot, belly, rounded rim, inner floor and pole.
    profile=[(0,radius*.29),(height*.055,radius*.34),
             (height*.16,radius*.52),(height*.52,radius*.82),
             (height*.83,radius*.96),(height*.94,radius),
             (height,radius*.98),(height,radius*.925),
             (height*.86,radius*.88),(height*.60,radius*.69),
             (height*.32,radius*.44),(height*.25,radius*.35),(height*.25,0)]
    g.lathe(k,c,(0,0,1),profile,material,n)

def plate(k,c,w,h,thick=.027,body='Enamel',steel='Steel',handle=True):
    x,y,z=c
    g.box(k,c,(w,thick,h),body,.006,4)
    # Inset enamel face leaves a machined, physically separated perimeter seam.
    g.box(k,(x,y-thick/2-.001,z),(w-.035,.003,h-.045),body,.004,3)
    g.box(k,(x,y-thick/2-.003,z),(w-.054,.001,h-.064),'Enamel',.003,3)
    for zz in [z-h/2+.065,z+h/2-.065]:
        g.box(k,(x+.009,y+.017,zz),(.014,.018,.038),'Graphite',.002)
        g.cyl(k,(x+.006,y+.030,zz),(x+.028,y+.030,zz),.0015,'Steel',20)
    if handle:
        hx=x+w/2-.060;zz=z+h/2-.09
        for dz in [-.062,.062]:
            g.cyl(k,(hx,y-thick/2,zz+dz),(hx,y-thick/2-.030,zz+dz),.006,'Steel',20)
        g.box(k,(hx,y-thick/2-.030,zz),(.018,.019,.143),'Steel',.006,4)
        g.box(k,(hx-.016,y-thick/2-.028,zz),(.003,.013,.106),'Graphite',.001)
    g.box(k,(x+w/2-.024,y-thick/2-.004,z-h/2+.082),(.010,.001,.022),'Cyan',.001)
    for sx in [x+.026,x+w/2-.026]:g.bolt(k,(sx,y-thick/2-.001,z-h/2+.028),r=.0025)

# Existing 600 mm cabinet modules. Their local x and z interfaces match UE.
for upper in [False,True]:
    k='Upper' if upper else 'Base';h=.94 if upper else .774;z=h/2 if upper else .477
    depth=.392 if upper else .662;front=-.20 if upper else -.333
    body='KIT_'+k+'Body';door='KIT_'+k+'Front'
    g.box(body,(0,.185 if upper else .317,z),(.590,.032,h),'Wood',.003)
    for x in [-.283,.283]:g.box(body,(x,-.003,z),(.024,depth,h),'Wood',.003)
    for zz in ([.010,.934] if upper else [.085,.865]):
        g.box(body,(0,-.003,zz),(.566,depth,.018),'Wood',.002)
    # Shelves, rear service void, toe recess and subtle machined carcass edges.
    for zz in ([.31,.63] if upper else [.30,.56,.80]):
        g.box(body,(0,-.018,zz),(.538,depth-.035,.015),'Inside',.002)
        g.box(body,(0,front+.008,zz+.009),(.538,.009,.008),'Steel',.001)
    for x in [-.274,.274]:
        for zz in [.06,h-.045]:g.bolt(body,(x,front-.001,zz),r=.003)
    if not upper:
        g.box(body,(0,-.13,.075),(.54,.37,.15),'Graphite',.003)
        for x in [-.235,.235]:
            g.box(body,(x,-.015,.028),(.035,.54,.05),'Graphite',.004)
    # True hinge origin is the left edge, as in the existing container class.
    plate(door,(.2775,.018,z),.555,h,thick=.034,body='Enamel',steel='Steel')

# Counter: a real open sink aperture spanning two modules, not an overlay decal.
k='Counter';top=.947;z=.927
# One closed structural worktop with a real rounded aperture. Decorative module
# seams are only surface grooves; no overlapping slab solids are manufactured.
g.prism(k,[(-1.8,-.325),(1.8,-.325),(1.8,.325),(-1.8,.325)],.907,.947,'Stone')
g.tag(k,'CounterSlab0')
cut_start=len(g.G[k]['v'])
g.prism(k,[(x-1.4,y) for x,y,z in g.rounded_rect(.771,.521,.0465)],.80,1.05,'Stone')
cutter_entry=g.G[k]['audit'].pop()
cutter=g._operand(g.G[k],cutter_entry)
g.G[k]['f']=g.G[k]['f'][:cutter_entry['start']]
g.G[k]['m']=g.G[k]['m'][:cutter_entry['start']];g.G[k]['smooth']=g.G[k]['smooth'][:cutter_entry['start']]
g.G[k]['v']=g.G[k]['v'][:cut_start]
g.boolean_group(k,['CounterSlab0'],'CounterSlab0',operation='DIFFERENCE',cutter=cutter)
bpy.data.objects.remove(cutter,do_unlink=True)
# Hairline modular join and exposed underside rail.
g.box(k,(0,-.352,.901),(3.56,.012,.014),'Steel',.003)
for x in [-1.765,-1.205,-.605,-.005,.595,1.195,1.765]:
    g.box(k,(x,-.34,.871),(.021,.012,.038),'Steel',.002)

# The backsplash has a single closed grout bed and glazed tile units.
k='BackSplash';w=3.60;h=.535
# Single closed bed: front=.004, rear=.0845 (actual wall face).
g.box(k,(0,.04425,h/2),(w,.0805,h),'Inside',0)
g.tag(k,'MountedBackSplashBacking')
# Keep base geometry at local z=0 for FBX/simple transform semantics.
# The single closed mounting back below replaces the former duplicate slab.
step=.20
for row in range(3):
    z=.090+row*.178
    for i in range(18):
        x=-w/2+.10+i*.20
        g.box(k,(x,-.003,z),(.196,.012,.174),'Tile',.005,4)
# The grout bed above is the sole backing; do not create a second solid here.
# Two slim power modules with individual socket apertures and switches.
for x in [-1.24,1.15]:
    z=.505
    g.box(k,(x,-.017,z),(.170,.014,.086),'Graphite',.006,4)
    for dx in [-.045,.012]:
        for dz in [-.013,.013]:g.box(k,(x+dx,-.0234,z+dz),(.004,.001,.013),'Rubber',0)
    g.box(k,(x+.058,-.027,z),(.018,.003,.031),'Enamel',.003)
    g.bolt(k,(x-.073,-.030,z),r=.002)
    g.bolt(k,(x+.073,-.030,z),r=.002)
g.text(k,'230 V  /  SERVICE',(-1.24,-.027,.443),.012,'Paper')

# Fixed sink assembly. Local zero is counter support datum.
k='Sink'
g.rounded_basin(k,(-.330,0,0),[(.768,.518,.045,.007),(.712,.470,.043,-.005),(.651,.410,.065,-.170),(.555,.320,.095,-.192)],'Steel')
g.tag(k,'BasinShell')
# The basin has a continuous horizontal drop-in flange at counter datum.
# No separate loose mounting shoes are needed below this supported rim.
# A real 68 mm drain aperture: ring and pipe meet the cut edge, not the bowl.
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.034,depth=.040,location=(7.50,13.12,.947-.194))
cutter=bpy.context.object
g.boolean_group(k,['BasinShell'],'BasinShell',operation='DIFFERENCE',cutter=cutter,source_transform=Matrix.Translation(PLACEMENTS['Sink']))
bpy.data.objects.remove(cutter,do_unlink=True)
# Flush drop-in drain: rim, sleeve and perforated strainer form one assembly.
# The rim outer radius stays inside the 34 mm cut edge, and the sleeve is
# seated directly on the rim so the group shares one contact datum.
g.ring(k,(-.330,0,-.19625),(0,0,1),.0337,.022,.0032,'Steel');g.tag(k,'DrainRim')
g.ring(k,(-.330,0,-.1975),(0,0,1),.0205,.0180,.003,'Graphite',48);g.tag(k,'DrainSleeve')
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.0175,depth=.002,location=(7.50,13.12,.947-.1995))
filter_cutter=bpy.context.object
for i in range(8):
    a=i*math.tau/8
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=.0018,depth=.008,location=(7.50+.011*math.cos(a),13.12+.011*math.sin(a),.947-.1995))
    drill=bpy.context.object
    mod=filter_cutter.modifiers.new('Filter aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=drill
    bpy.context.view_layer.objects.active=filter_cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(drill,do_unlink=True)
g.poly(k,[filter_cutter.matrix_world@v.co-Vector(PLACEMENTS['Sink']) for v in filter_cutter.data.vertices],[tuple(p.vertices) for p in filter_cutter.data.polygons],'Steel',True);g.tag(k,'DrainStrainer')
bpy.data.objects.remove(filter_cutter,do_unlink=True)
g.join(k,['DrainRim','DrainSleeve','DrainStrainer'],'DrainAssembly')
# Mixer pedestal, curved spout, lever, aerator and gasket.
g.lathe(k,(-.330,.294,.0012),(0,0,1),[(0,.030),(.002,.030),(.006,.031),(.014,.025),(.200,.019),(.220,.024)],'Steel',48);g.tag(k,'TapPedestal')
g.pipe(k,[(-.330,.274,.210),(-.330,.274,.305),(-.330,.250,.333),(-.330,.143,.333),(-.330,.103,.285)],.012,'Steel',32);g.tag(k,'TapSpout')
g.boolean_group(k,['TapPedestal','TapSpout'],'TapBody',source_transform=Matrix.Translation(PLACEMENTS['Sink']))
g.lathe(k,(-.330,.103,.297),(0,0,1),[(0,.014),(.003,.014),(.004,.011)],'Graphite',32);g.tag(k,'TapAerator')
# The seal sits on the countertop; the pedestal foot starts above it.
g.ring(k,(-.330,.294,.0006),(0,0,1),.0295,.0275,.001,'Rubber');g.tag(k,'TapGasket')
g.cyl(k,(-.220,.274,.019),(-.220,.274,.066),.018,'Steel',32);g.tag(k,'TapLever')
g.pipe(k,[(-.220,.274,.060),(-.180,.274,.077)],.007,'Steel',20);g.tag(k,'TapLeverStem')
g.boolean_group(k,['TapBody','TapAerator','TapLever','TapLeverStem'],'TapAssembly',source_transform=Matrix.Translation(PLACEMENTS['Sink']))
# Keep the thin gasket as its own closed solid, joined only at the mounting
# face of the pedestal; no zero-thickness Boolean slivers.
g.boolean_group(k,['TapAssembly'],'TapWithGasket',source_transform=Matrix.Translation(PLACEMENTS['Sink']))
# Put the mixer on the solid rear deck; the gasket must not touch the bowl.
for i,e in enumerate(g.G[k]['audit']):
    if e['label'] in ['TapWithGasket','TapGasket']:
        used={vi for face in g.G[k]['f'][e['start']:e['start']+e['count']] for vi in face}
        for j in used:
            x,y,z=g.G[k]['v'][j];g.G[k]['v'][j]=(x,y+.021,z)
# Soap sits entirely on the solid counter outside the basin rim (rim ends y=.259).
vessel(k,(-.012,.320,0),.054,.095,'Porcelain',64);g.tag(k,'SoapBottle')
g.pipe(k,[(-.012,.320,.084),(-.012,.320,.125),(-.062,.320,.125)],.005,'Steel',20);g.tag(k,'SoapPump')
g.boolean_group(k,['SoapBottle','SoapPump'],'SoapDispenser',source_transform=Matrix.Translation(PLACEMENTS['Sink']))
# Folded linen is supported on the front-right solid counter, never over the hole.
for j in range(3):
    z=.001+j*.0022
    g.box(k,(.640,-.275,z),(.180,.090,.002),'Linen',.0008,4)
for y in [-.280,-.270]:g.box(k,(.640,y,.0072),(.165,.002,.001),'Paper')

# Rail, hooks, utensil crock and supported utensils.
k='UtilityRail'
# Steel backplates, studs, bar, hooks and rings share one welded solid.
for x in [-.65,.65]:
    g.box(k,(x,-.004,0),(.045,.008,.058),'Steel',0)
g.cyl(k,(-.68,-.022,0),(.68,-.022,0),.010,'Steel',28);g.tag(k,'RailBar')
for x in [-.65,.65]:
    g.cyl(k,(x,-.022,0),(x,0,0),.008,'Steel',24)
for x in [-.51,-.32,-.10,.13,.35,.55]:
    g.pipe(k,[(x,-.031,-.010),(x,-.040,-.027),(x,-.040,-.041)],.003,'Steel',12)
    g.ring(k,(x,-.025,-.063),(0,1,0),.016,.012,.004,'Steel',32)
# A single continuous steel support avoids intersecting independent pipe shells.
# Foot solids remain separate graphite plates; all pipe/stud pieces are unioned.
labels=[e['label'] for e in g.G[k]['audit']]
g.boolean_group(k,labels,'ContinuousRail',source_transform=Matrix.Translation(PLACEMENTS['UtilityRail']))
# Utensil cup bottom sits on the support datum separately through Prep.
k='Cooking'
# Induction glass is counter-supported; oven is a separate low-mounted assembly.
g.box(k,(-.08,.025,.009),(.60,.52,.018),'Graphite',.009,4)
for x in [-.225,.055]:
    for y in [-.095,.135]:
        g.ring(k,(x,y,.019),(0,0,1),.091,.087,.0015,'Steel',72)
        g.ring(k,(x,y,.0195),(0,0,1),.058,.056,.001,'Graphite',64)
for i in range(5):
    g.box(k,(.158,-.14+i*.033,.020),(.012,.019,.002),'Graphite',.001)
g.box(k,(.172,.15,.020),(.032,.043,.002),'Glass',.003)
# The hob legend is a thin horizontal enamel inlay, not a vertical raised label.
g.text(k,'INDUCTION',(-.08,-.236,.01812),.014,'Paper',normal=(0,0,1))
# Oven front stays in its module, behind the independent counter nosing.
# Its front surface is 5 mm behind the worktop front, not through the rail.
g.box(k,(-.08,-.307,-.435),(.555,.026,.615),'Steel',.004,4);g.tag(k,'OvenSteelFace')
for x in [-.3315,.1715]:g.box(k,(x,-.323,-.421),(.003,.001,.480),'Graphite',0)
for z in [-.6595,-.1825]:g.box(k,(-.08,-.323,z),(.497,.001,.003),'Graphite',0)
g.box(k,(-.08,-.321,-.421),(.460,.001,.474),'Glass',0)
# Handle feet meet the steel face at y=-.320, not the inset glass edge.
g.pipe(k,[(-.305,-.310,-.115),(-.305,-.353,-.115),(.145,-.353,-.115),(.145,-.310,-.115)],.010,'Steel',24)
g.tag(k,'OvenHandle')
g.boolean_group(k,['OvenHandle','OvenSteelFace'],'OvenSteelFront',source_transform=Matrix.Translation(PLACEMENTS['Cooking']))
for x in [-.255,.095]:
    g.lathe(k,(x,-.320,-.098),(0,-1,0),[(0,.024),(.018,.024),(.022,.017)],'Graphite',40)
    # Indicator is a flat inlay recessed into the knob's front face.
    g.box(k,(x,-.3405,-.112),(.0022,.0010,.006),'Paper',0)
for x in [-.23,-.15,-.07,.01,.09]:g.box(k,(x,-.323,-.718),(.046,.004,.002),'Graphite',.001)
oven_data=g.G.pop(k)
g.G['OvenFront']=oven_data

# Preparation group. Keep the board clear of the induction module at X=9.44m.
# The knife block, herb pot and jars sit BEHIND it, never on top of the board.
k='Prep'
g.box(k,(-.035,-.035,.017),(.330,.270,.034),'Wood',.010,4);g.tag(k,'ChoppingBoard')
# The board's perimeter is its finished edge; no intersecting metal inset.
# Exact non-overlapping comb slots. Ribs are BETWEEN the knife axes.
g.box(k,(.0805,.179,.009),(.111,.066,.018),'Wood')
g.box(k,(.0805,.2135,.067),(.111,.003,.098),'Wood')
for x in [.0325,.1275]:g.box(k,(x,.179,.067),(.005,.066,.098),'Wood')
for x in [.052,.080,.108]:g.box(k,(x,.179,.067),(.022,.066,.098),'Wood')
for i in range(4):
    x=.038+i*.028
    g.box(k,(x,.179,.110+i*.004),(.006,.015,.096),'Steel');g.tag(k,'KnifeBlade')
    g.box(k,(x,.179,.1805+i*.004),(.013,.021,.045),'Graphite')
# Small herb pot is separated from the board by more than its full radius.
px,py=-.200,.168
profile=[(0,.035),(.006,.040),(.014,.044),(.062,.050),(.068,.052),(.072,.050),(.072,.044),(.066,.044),(.018,.036),(.016,0)]
g.lathe(k,(px,py,0),(0,0,1),profile,'Porcelain',64)
g.lathe(k,(px,py,.018),(0,0,1),[(0,.035),(.050,.036),(.050,.040)],'Soil',48)
for i in range(9):
    a=i*math.tau/9;root=(px+.005*math.cos(a),py+.005*math.sin(a),.068)
    tip=(px+.040*math.cos(a),py+.040*math.sin(a),.112)
    radial=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
    centers=[Vector(root),Vector(root)+Vector((0,0,.003)),Vector(tip)-radial*.012-Vector((0,0,.016)),Vector(tip)+radial*.006+Vector((0,0,.022))]
    widths=[0,.0012,.007,0];verts=[]
    for c,w in zip(centers,widths):
        if w==0:verts.append(c)
        else:verts.extend([c+side*w,c+radial*.0008,c-side*w,c-radial*.0008])
    faces=[(0,2,1),(0,3,2),(0,1,4),(0,4,3)]
    for i in range(4):j=(i+1)%4;faces.append((1+i,1+j,5+j,5+i))
    faces.extend([(5,6,9),(6,7,9),(7,8,9),(8,5,9)])
    g.poly(k,verts,faces,'Leaf')
for x in [-.114,-.032]:
    y=.184
    # Jar: outer wall up to the rim, then one return to the inner wall. No
    # second ring at the same height, which would self-intersect.
    # Jar: base disc, outer wall, rim return, inner wall, inner floor disc.
    g.lathe(k,(x,y,0),(0,0,1),[(0,.029),(.004,.033),(.006,.035),(.064,.035),(.072,.030),(.076,.030),(.076,.024),(.070,.024),(.010,.025),(0,.025)],'Glass',48)
    # Lid: underside ring at the mouth, straight wall, closed top disc.
    g.lathe(k,(x,y,.0760),(0,0,1),[(0,.0235),(.0055,.0235),(.0055,.0275),(.0275,0)],'Steel',48)
    g.lathe(k,(x,y,.0090),(0,0,1),[(0,.024),(.045,.024)],'Food',32)
    g.box(k,(x,y-.03501,.039),(.034,.00002,.027),'Paper')

# Closed pottery. A continuous meridian runs from the outer foot around the rim
# to the inner floor and axis, so there is no disconnected ring/disc annulus.
def vessel(k,c,radius,height,material='Porcelain',n=72):
    profile=[(0,radius*.29),(height*.055,radius*.34),
             (height*.16,radius*.52),(height*.52,radius*.82),
             (height*.83,radius*.96),(height*.94,radius),
             (height,radius*.98),(height,radius*.925),
             (height*.86,radius*.88),(height*.60,radius*.69),
             (height*.32,radius*.44),(height*.25,radius*.35),(height*.25,0)]
    g.lathe(k,c,(0,0,1),profile,material,n)

# Vertical plates and front mugs occupy separate Y envelopes. The rack has
# low support rails under each plate foot, not rails through the plate face.
k='Dishes'
g.box(k,(0,0,.008),(.405,.300,.0155),'Graphite',.005,3)
def upright_plate(k,c):
    # Closed section: back foot -> outer rim -> inner floor -> axis.
    profile=[(0,.029),(-.002,.029),(-.002,.032),(.001,.033),(.002,.040),
             (.012,.072),(.015,.079),(.017,.080),(.019,.078),(.019,.074),
             (.007,.041),(.003,.030),(.003,0)]
    g.lathe(k,c,(1,0,0),profile,'Porcelain',72)
for y,z in [(.083,.104),(.125,.104)]:
    g.pipe(k,[(-.154,y,.016),(-.154,y,z),(.078,y,z),(.078,y,.016)],.003,'Steel',14)
# Four short saddles support each outer foot independently. Their tops are
# 0.02 mm below the measured plate minimum, avoiding coplanar FBX contact.
for i in range(4):
    x=-.114+i*.060
    g.box(k,(x+.017,0,.02),(.004,.016,.008),'Steel')
    upright_plate(k,(x,0,.104))
for x in [-.085]:
    g.box(k,(x,-.112,.017),(.095,.074,.002),'Steel')
    if x>0:continue
    vessel(k,(x,-.112,.0182),.031,.071,'Porcelain',56);g.tag(k,'CupBody')
    g.pipe(k,[(x+.027,-.112,.0795),(x+.043,-.112,.0795),(x+.047,-.112,.0675),(x+.035,-.112,.0515),(x+.027,-.112,.0515)],.003,'Porcelain',16);g.tag(k,'CupHandle')
    g.boolean_group(k,['CupBody','CupHandle'],'CupWithHandle',source_transform=Matrix.Translation(PLACEMENTS['Dishes']))
# Low bowl has its own flat tray and is outside the last plate's X envelope.
g.box(k,(.145,.040,.017),(.105,.105,.002),'Steel')
vessel(k,(.145,.040,.0182),.046,.045,'Porcelain',64)

# Dining uses measured table-top z=0. The two place settings have separate
# mat/dish/glass/utensil bays; the centrepiece is below the plate rim height.
k='DiningDressing'
for x in [-.50,.50]:
    g.box(k,(x,0,.00175),(.430,.400,.0035),'Linen',.004,3)
    vessel(k,(x,-.020,.0036),.102,.019,'Porcelain',72)
    vessel(k,(x,.155,.0036),.028,.080,'Glass',56)
    g.lathe(k,(x,.155,.0261),(0,0,1),[(0,.010),(.021,.010)],'Coffee',48)
    for dx in [-.150,.150]:
        g.box(k,(x+dx,-.008,.0070),(.014,.230,.006),'Steel',.002);g.tag(k,'UtensilShaft')
        g.box(k,(x+dx,.103,.0070),(.027,.021,.006),'Steel',.002);g.tag(k,'UtensilHead')
        g.boolean_group(k,['UtensilShaft','UtensilHead'],'Utensil',source_transform=Matrix.Translation((8.075,8.69,.7825)));g.tag(k,'UtensilRight' if x>0 else 'UtensilLeft')
# A single folded napkin is off the two place-setting envelopes.
g.box(k,(0,.0,.009),(.145,.400,.018),'Linen',.004,3)
vessel(k,(0,.295,0),.039,.137,'Porcelain',64)
g.lathe(k,(0,.295,.03425),(0,0,1),[(0,.011),(.00575,.011)],'Steel',40)
for i in range(3):
    a=i*math.tau/3;radial=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
    centers=[Vector((.006*math.cos(a),.295+.006*math.sin(a),.040)),Vector((.006*math.cos(a),.295+.006*math.sin(a),.042)),Vector((.020*math.cos(a),.295+.020*math.sin(a),.120)),Vector((.052*math.cos(a),.295+.052*math.sin(a),.218)),Vector((.068*math.cos(a),.295+.068*math.sin(a),.242))]
    widths=[0,.0018,.0018,.009,0];verts=[]
    for c,w in zip(centers,widths):
        if w==0:verts.append(c)
        else:verts.extend([c+side*w,c+radial*.0008,c-side*w,c-radial*.0008])
    faces=[(0,2,1),(0,3,2),(0,1,4),(0,4,3)]
    for ring in range(2):
        a0=1+ring*4;b0=a0+4
        for j in range(4):nj=(j+1)%4;faces.append((a0+j,a0+nj,b0+nj,b0+j))
    faces.extend([(9,10,13),(10,11,13),(11,12,13),(12,9,13)])
    g.poly(k,verts,faces,'Leaf')

# Cabinet internals: keep the sink cavity open. The old full-width bottom shelf
# filled the basin at z=0.30m; a lower floor and two service-side returns instead
# support stored goods without intersecting the sink or its drain.
g.box('KIT_BaseBody',(0,-.025,.175),(.548,.555,.018),'Inside',.002)
for x in [-.266,.266]:g.box('KIT_BaseBody',(x,-.065,.340),(.025,.43,.15),'Inside',.002)
g.box('KIT_BaseBody',(0,-.280,.465),(.535,.030,.045),'Steel',.002)

# Append existing detailed assets, but assign kitchen-local material instances.
# Append only the source object's data and transform, not unrelated source scene.
def append_mesh(file,name,location,scale=1.):
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
    o=dst.objects[0];o.name='KIT_'+name;col.objects.link(o);o.location=location;o.scale=(scale,)*3;o.rotation_euler=(0,0,0)
    # Data copies prevent a Blender-side recolour from mutating the appended source.
    o.data=o.data.copy()
    # Bake a reuse instance's scale into its local mesh before component export.
    if scale!=1:
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for i,m in enumerate(o.data.materials):
        n=m.name if m else ''
        role='Steel' if any(s in n.lower() for s in ['stainless','steel','metal']) else 'Rubber' if any(s in n.lower() for s in ['rubber']) else 'Enamel' if any(s in n.lower() for s in ['coat','ceramic','plastic']) else None
        if role:o.data.materials[i]=g.M[role]
    o['ReusedSource']=str(file);return o

coffee=append_mesh(R.parents[2]/'SourceAssets/DungeonStaffLiving20261002/CoffeePolishV7/Authored/StaffLivingTheme_CoffeePolishV7.blend','SM_Staff_CoffeeMachine_V7',(10.33,13.06,.947),.75)
kettle=append_mesh(R.parents[2]/'SourceAssets/DungeonStaffLiving20261002/WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend','SM_Staff_ElectricKettle_V6',(8.73,13.16,.947),1.)

# Preserve actual fridge interiors/moving doors; only add replaceable outer detail.
source=R.parents[2]/'SourceAssets/DungeonStaffLiving20261002/RoomDetailsV5/Authored/StaffLivingTheme_RoomDetailsV5.blend'
for name in ['SM_Staff_FridgeLowerBody_V5','SM_Staff_FridgeUpperBody_V5','SM_Staff_FridgeLowerDoor_V5','SM_Staff_FridgeUpperDoor_V5']:
    o=append_mesh(source,name,(0,0,0))
    key=name.replace('SM_Staff_','').replace('_V5','')
    for i,m in enumerate(o.data.materials):
        n=m.name if m else ''
        if 'Ceramic' in n or 'Painted' in n:o.data.materials[i]=g.M['Enamel']
        elif 'Steel' in n:o.data.materials[i]=g.M['Steel']
        elif any(s in n for s in ['PoolIvory','FreshPlastic']):
            pass  # Local geometry audits retain the native interior material IDs.
    if 'Body' in key:
        trim='KIT_'+key+'Trim'
        # Side rails seat into the shell. Keep original feet, interior shelves,
        # door bins and handles; do not add duplicate feet or a floating grille.
        for x in [-.376,.376]:
            g.box(key,(x,-.363,.555 if 'Lower' in key else 1.38),(.014,.010,.80 if 'Lower' in key else .56),'Steel',.003)
    else:
        # Blender +Y maps to UE -Y through the FBX axis conversion, so the
        # trim face is authored at +Y to land on the door's UE front (-Y).
        key='KIT_'+key+'Trim'
        z0=.13 if 'Lower' in key else 1.10;z1=.97 if 'Lower' in key else 1.64
        g.box(key,(.693,.0345,(z0+z1)/2),(.009,.004,z1-z0),'Steel',.001)
        for z in [z0+.05,z1-.05]:g.box(key,(.691,.0340,z),(.026,.003,.020),'Steel',.001)
        if 'Upper' in key:
            g.box(key,(.11,.0345,1.25),(.118,.004,.105),'Graphite',.001)
            g.box(key,(.11,.0366,1.25),(.104,.001,.090),'Glass',.0002)
            g.text(key,'04°',(.11,.0373,1.238),.035,'Paper')
            g.box(key,(.11,.0372,1.211),(.052,.0005,.003),'Steel',.0001)
        g.text(key,'COLD / STORAGE',(.49,.0332,z1-.048),.010,'Paper')

# Finish source meshes and export individually. Added fridge parts are exported by role.
rows=g.finish(g.M,R)
# Door trim is a new asset, not the reused refrigerator door itself. Keep the
# exported FBX name stable and only drop the Trim suffix from the asset key.
for row in rows:
    if row['key'].endswith('DoorTrim'):
        row['key']=row['key'].removesuffix('Trim')
        row['name']='SM_KP_'+row['key'];row['reused']=False;row['source']=None
        bpy.data.objects['KIT_'+row['key']+'Trim'].name='KIT_'+row['key']
# Production uses native shared fridge/cabinet/appliance assets. Never export a
# second full fridge door or a duplicate coffee/kettle into the apartment.
# The reused mesh instances below are for local, read-only clearance analysis.
for o in list(col.objects):
    if o.get('ReusedSource'):o['LocalAuditOnly']=True
rows=[row for row in rows if not row.get('reused')]
for o in list(col.objects):
    if o.get('ReusedSource') and any(n in o.name for n in ['Fridge','Coffee','Kettle']):
        if 'Fridge' in o.name:
            for i,m in enumerate(o.data.materials):
                n=m.name if m else ''
                if any(s in n for s in ['Ceramic','PoolIvory','FreshPlastic','Painted']):o.data.materials[i]=g.M['Enamel']
                elif 'Steel' in n:o.data.materials[i]=g.M['Steel']
        rows.append(dict(key=o.name[4:],name='NATIVE_'+o.name[4:],fbx=None,
                         reused=True,source=o.get('ReusedSource'),local_audit_only=True))

# Context is explicitly for source preview only, not exported to UE as a replacement.
def context_box(name,c,s,m):
    bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.name='CTX_'+name;o.dimensions=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for old in list(o.users_collection):old.objects.unlink(o)
    ctx.objects.link(o);o.data.materials.append(g.M[m]);o['PreviewOnly']=True
for name,c,s,m in [
    ('BackWall',(8.4,13.56,1.84),(4.85,.12,3.6875),'Inside'),
    ('Floor',(8.4,11.075,-.035),(4.85,4.85,.05),'Stone'),
    ('Ceiling',(8.4,11.075,3.72),(4.85,4.85,.05),'Inside'),
    ('RightReturn',(10.81,11.075,1.84),(.12,4.85,3.6875),'Inside'),
    ('LightHousing',(8.40,10.90,3.65),(2.25,.36,.07),'Graphite'),
    ('LightDiffuser',(8.40,10.90,3.608),(2.13,.26,.013),'Warm'),
]:context_box(name,c,s,m)

# UE coordinate calibrated instances (Blender +Y maps UE -Y).
by_key={r['key']:r for r in rows}
for key,loc in PLACEMENTS.items():
    ob=bpy.data.objects.get('KIT_'+key)
    if ob:ob.location=loc
for key,loc in [('FridgeLowerBody',(6.52,13.10,0)),('FridgeUpperBody',(6.52,13.10,0)),('FridgeLowerDoor',(6.165,12.717,0)),('FridgeUpperDoor',(6.165,12.717,0))]:
    for ob in [bpy.data.objects.get('KIT_SM_Staff_'+key+'_V5'),bpy.data.objects.get('KIT_'+key)]:
        if not ob:continue
        ob.location=loc
        if ob.name.startswith('KIT_SM_Staff_'):
            # Preview only: convert native Blender source front -Y to the
            # formal component's +Y, which source_to_ue_cm then maps to UE -Y.
            for v in ob.data.vertices:v.co.y=-v.co.y
            for poly in ob.data.polygons:poly.flip()
            ob.data.update()
            ob['LocalAuditOnly']=True
        ob['UE_Component_Axes']='Measured native component; new trim front=-Y'

# Preview-only lights/cameras, deliberately not sent to UE.
world=bpy.data.worlds.new('KIT_ReviewWorld');world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.22,.29,.36,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.32;bpy.context.scene.world=world
for name,loc,target,power,size,color in [
    ('Key',(8.3,10.8,3.53),(8.4,13.1,1.0),520,2.3,(1,.89,.75)),
    ('Fill',(10.3,10.1,2.7),(8.4,13.0,1.2),280,2.,(.68,.83,1)),
    ('Task',(8.0,13.07,1.65),(8.0,13.1,.95),32,1.2,(1,.88,.69)),
]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new('CTX_Light_'+name,data);ctx.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,target,lens in [
    ('Hero',(9.76,8.86,2.15),(8.37,13.05,1.22),22),
    ('Counter',(9.45,11.68,1.72),(9.18,13.10,1.17),37),
    ('Sink',(7.55,11.86,1.82),(7.80,13.12,1.17),38),
]:
    data=bpy.data.cameras.new(name);data.lens=lens
    o=bpy.data.objects.new('CAM_'+name,data);ctx.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.clip_start=.03
bpy.context.scene.camera=bpy.data.objects['CAM_Hero']
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=48;bpy.context.scene.cycles.use_denoising=True
bpy.context.scene.render.resolution_x=1400;bpy.context.scene.render.resolution_y=1050;bpy.context.scene.render.resolution_percentage=100
bpy.context.scene.render.image_settings.file_format='PNG'
# Source is a separately deliverable kitchen-only scene. No overwrite of apartment blend.
for image in bpy.data.images:
    if image.source=='FILE' and not image.packed_file:
        try:image.pack()
        except RuntimeError:pass
manifest=dict(stage='source_and_fbx_saved',units='m',blender_y_to_ue='-Y',ue_scale=100,
              coordinate_scope='measured current UE anchors and native component bounds',asset_base='/Game/Props/CyberpunkApartmentKitchen20261024',
              revision='V2_black_grey_contact_repair',local_dining_location=(8.075,8.69,.7825),interfaces=INTERFACES,
              meshes=rows,placements=PLACEMENTS,container_contracts=json.loads((R/'current-interfaces-v2.json').read_text())['targets'],
              current_interface_read=json.loads((R/'current-interfaces-v2.json').read_text())['stage'],
              not_a_map_replacement=True,tests_run=False,rendered=False)
(R/'assembly.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'KitchenDetailV1.blend'))
print('KITCHEN_SOURCE_SAVED',len(rows),'component meshes; apartment untouched')
