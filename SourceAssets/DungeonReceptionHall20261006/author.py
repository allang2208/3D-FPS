"""Dimensioned architecture and bespoke reception details; background FBX export."""
import bpy,bmesh,json,math,sys,hashlib,random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
refinement=ROOT/'Refine20261007'
if __name__=='__main__' and (refinement/'Receipts/install.json').exists() and json.loads((refinement/'Receipts/install.json').read_text('utf8')).get('stage')=='map_saved':
    import runpy
    runpy.run_path(str(refinement/'author.py'),run_name='__main__')
    runpy.run_path(str(refinement/'author_electronics.py'),run_name='__main__')
    upper=ROOT/'UpperProps20261007'
    if (upper/'Receipts/install.json').exists() and json.loads((upper/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':
        runpy.run_path(str(upper/'author.py'),run_name='__main__')
        runpy.run_path(str(upper/'layout.py'))['source_sync']()
    raise SystemExit(0)
sys.path.insert(0,str(ROOT/'Scripts'));import geometry as g
CFG=json.loads((ROOT/'Config/layout.json').read_text('utf8'));ROLES=json.loads((ROOT/'Config/materials.json').read_text('utf8'));ATLAS=json.loads((ROOT/'Config/atlas.json').read_text('utf8'))
BASE=CFG['base'];g.ROOM='Reception'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
materials={}
for k,r in ROLES.items():
    m=bpy.data.materials.new('RH_'+k);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*r['basecolor_linear'],1);bs.inputs['Roughness'].default_value=r['roughness'];bs.inputs['Metallic'].default_value=r['metallic']
    if k in ('Labels','Floor','Stone'):
        t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/'Textures'/('T_Reception_Signs.png' if k=='Labels' else 'T_Reception_Terrazzo_BaseColor.png')),check_existing=True);m.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color'])
    materials[k]=m
B=g.box
def box(kind,c,s,mat='Concrete',col=False):B(kind,c,s,mat,collision=col)
def rail(a,b):g.rail(a,b,'Balustrades',1.10)
def sign(key,c,w,normal=(0,-1,0)):
    g.plate(c,w,w*304/984,key,normal,ATLAS)
def tile_rect(name,x0,y0,x1,y1,z):
    nx=math.ceil((x1-x0)/1.2);ny=math.ceil((y1-y0)/1.2);dx=(x1-x0)/nx;dy=(y1-y0)/ny
    for i in range(nx):
        for j in range(ny):box(name,(x0+(i+.5)*dx,y0+(j+.5)*dy,z-.018),(dx-.008,dy-.008,.036),'Floor')
def deck(x0,y0,x1,y1):
    box('MezzanineStructure',((x0+x1)/2,(y0+y1)/2,4.29),(x1-x0,y1-y0,.34),'Concrete',True)
    tile_rect('UpperFloor',x0,y0,x1,y1,4.5)
    g.box(None,((x0+x1)/2,(y0+y1)/2,4.48),(x1-x0,y1-y0,.04),collision='MezzanineStructure')

# Continuous slab, honest floor build-up and four complete walls.
box('Foundations',(0,0,-.22),(48.6,33.6,.36),'Concrete',True)
g.box(None,(0,0,-.02),(48,33,.04),collision='Foundations')
tile_rect('GroundFloor',-24,-16.5,24,16.5,0)
for side in (-1,1):
    box('OuterWalls',(0,side*16.66,5),(48.6,.32,10),'Concrete',True)
    for x,width,height in [(-24,4,3.4),(24,3,3)]:
        span=16.5-width/2
        box('OuterWalls',(x,side*(width/2+span/2),5),(.36,span,10),'Concrete',True)
    for z in (.10,1.18,4.65,5.65):box('WallTrim',(0,side*16.48,z),(47.7,.038,.09 if z in (.1,4.65) else .032),'Teal')
for x,width,height in [(-24,4,3.4),(24,3,3)]:
    box('OuterWalls',(x,0,(height+10)/2),(.36,width,10-height),'Concrete',True)
    for sy in (-1,1):box('PortalFrames',(x,sy*(width/2-.025),height/2),(.49,.08,height),'Teal',True)
    box('PortalFrames',(x,0,height+.04),(.49,width+.16,.08),'Teal',True)
    outer=-27 if x<0 else 27;cx=(x+outer)/2
    box('Vestibules',(cx,0,-.14),(3,width+.6,.28),'Concrete',True)
    for sy in (-1,1):box('Vestibules',(cx,sy*(width/2+.12),height/2),(3,.24,height),'Concrete',True)
    box('Vestibules',(cx,0,height+.12),(3,width+.6,.24),'Concrete',True)
    # Preview caps are kept separate and excluded from the future room draft.
    box('PreviewCaps',(outer+(-.15 if x<0 else .15),0,height/2),(.30,width+.5,height),'Concrete',True)
    for sy in (-1,1):box('VestibuleDetails',(cx,sy*(width/2-.02),1.05),(2.98,.042,.075),'Steel')
box('Roof',(0,0,10.15),(48.6,33.6,.30),'Concrete',True)
for x in (-23,-15,-7,1,9,17,23):
    box('RoofBeams',(x,0,9.53),(.30,33.1,.80),'Teal')
    box('RoofBeams',(x,0,9.11),(.48,33.1,.045),'Steel')
    for y in (-16.20,16.20):
        box('Columns',(x,y,4.52),(.42,.42,9.04),'Teal',True)
        box('Columns',(x,y,.07),(.66,.66,.14),'Steel',True)
        for a in (-.24,.24):
            for b in (-.24,.24):g.bolt('Fasteners',(x+a,y+b,.14),(0,0,1),.022)
# A 34x21m open void; no second-floor slab over the atrium.
deck(-24,-16.5,-18,16.5);deck(16,-16.5,24,16.5)
deck(-18,-16.5,16,-10.5);deck(-18,10.5,16,16.5)
for side in (-1,1):
    y=side*10.5
    for x in (-18,-10,-2,6,16):
        box('GalleryColumns',(x,y,2.05),(.36,.36,4.10),'Teal',True)
        box('GalleryColumns',(x,y,.07),(.56,.56,.14),'Steel',True)
    box('GalleryFascia',(-1,y,4.27),(34,.14,.44),'Teal')
    box('GalleryFascia',(-1,y-side*.081,4.08),(34,.015,.055),'Brass')
    # Preserve an open stair landing gap between 3.12 and 5.52m.
    rail((-18,y,4.5),(3.12,y,4.5));rail((5.52,y,4.5),(16,y,4.5))
rail((-18,-10.5,4.5),(-18,10.5,4.5));rail((16,-10.5,4.5),(16,10.5,4.5))
for x in (-18,16):box('GalleryFascia',(x,0,4.27),(.14,21,.44),'Teal')

# Paired 3m clear stairs, intermediate landings and solid concrete carriage.
rise=4.5/28;going=.34
for side in (-1,1):
    yc=side*8.8;w=3.0
    for flight,(x0,z0) in enumerate([(-8,0),(-1.64,2.25)]):
        for i in range(14):
            x=x0+(i+.5)*going;top=z0+(i+1)*rise
            box('StairTreads',(x,yc,top-.075),(going,w,.15),'Stone')
            box('StairNosings',(x0+i*going+.028,yc,top+.004),(.056,w-.08,.008),'Dark')
        # One exact ramp support convex hull per flight, top follows noses.
        x1=x0+14*going;z1=z0+14*rise
        vs=[(xx,yy,zz) for yy in (yc-w/2,yc+w/2) for xx,zz in [(x0,z0-.20),(x1,z1-.20),(x1,z1),(x0,z0)]]
        fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        g.poly('StairCarriages',vs,fs,'Concrete')
        # Collision reaches the first and final step tops, avoiding riser snagging.
        cvs=[(xx,yy,zz+(rise if k%4==3 else 0)) for k,(xx,yy,zz) in enumerate(vs)]
        g.hull('StairCarriages',cvs,fs)
        for sy in (-1,1):rail((x0,yc+sy*1.56,z0+rise),(x1,yc+sy*1.56,z1))
    box('StairLandings',(-2.44,yc,2.12),(1.6,3.20,.26),'Stone',True)
    box('StairSupports',(-2.44,yc,1.025),(.40,2.95,2.05),'Concrete',True)
    box('StairLandings',(4.32,side*8.75,4.36),(2.40,3.50,.28),'Stone',True)
    for sy in (-1,1):rail((-3.24,yc+sy*1.56,2.25),(-1.64,yc+sy*1.56,2.25))
    rail((3.12,side*7.0,4.5),(5.52,side*7.0,4.5));rail((5.52,side*7.0,4.5),(5.52,side*10.5,4.5))
    for x in (3.4,5.24):box('StairSupports',(x,side*8.85,2.11),(.26,3.0,4.22),'Teal',True)

# Real upstairs glazed office walls. Each front interval is interrupted by its door.
for side in (-1,1):
    y0,y1=(-14.8,-1.2) if side==-1 else (1.2,14.8);dy=side*8
    for y in (y0,y1):box('OfficeWalls',(21.5,y,6.65),(5,.16,4.3),'Concrete',True)
    box('OfficeCeilings',(21.5,(y0+y1)/2,8.86),(5,y1-y0+.16,.12),'White',True)
    for lo,hi in [(y0,dy-.615),(dy+.615,y1)]:
        box('OfficeWalls',(19,(lo+hi)/2,4.97),(.16,hi-lo,.94),'Stone',True)
        box('OfficeWalls',(19,(lo+hi)/2,8.13),(.16,hi-lo,1.34),'Concrete',True)
        for z in (5.45,7.45):box('OfficeFrames',(19,(lo+hi)/2,z),(.19,hi-lo,.055),'Teal',True)
    box('OfficeWalls',(19,dy,7.87),(.16,1.23,1.86),'Concrete',True)
    for sy in (-1,1):box('OfficeFrames',(19,dy+sy*.593,5.7),(.23,.065,2.4),'Teal',True)
    box('OfficeFrames',(19,dy,6.93),(.23,1.25,.06),'Teal',True)
    sign('officeA' if side<0 else 'officeB',(18.863,dy,7.70),2.2,(-1,0,0))
for pane in CFG['glass']:
    x,y,z=pane['position_m'];w=pane['width_m']
    for sy in (-1,1):box('OfficeFrames',(x,y+sy*(w/2+.018),z),(.19,.034,2.0),'Teal',True)

# Reception counter: seated worktop, standing ledge, accessible lower station,
# recessed kick, wood fins, stainless toe rail, cable grommets and tray furniture.
for lo,hi in [(-12,-5.2),(-5.2,-3.0)]:
    accessible=lo>-6;top=.775 if accessible else 1.075;cx=(lo+hi)/2
    box('ReceptionCounter',(cx,12.2,.38),(hi-lo-.02,.18,.76),'Wood',True)
    box('ReceptionCounter',(cx,12.25,.07),(hi-lo-.05,.62,.14),'Dark',True)
    if accessible:
        # Continuous accessible stone worktop; no coplanar wood underneath its face.
        box('ReceptionCounter',(cx,12.79,top-.033),(hi-lo,1.64,.066),'Stone',True)
    else:
        box('ReceptionCounter',(cx,12.3,top-.033),(hi-lo,.66,.066),'Stone',True)
        box('ReceptionCounter',(cx,12.99,.7475),(hi-lo,1.24,.055),'Wood',True)
    for x in (lo+.06,hi-.06):box('ReceptionCounter',(x,13.07,.365),(.08,1.14,.73),'Teal',True)
    for x in [lo+.11+i*.16 for i in range(int((hi-lo-.18)/.16))]:box('ReceptionFluting',(x,12.096,.46),(.052,.035,.56),'Wood')
    if not accessible:
        box('ReceptionCounter',(cx,12.305,.894),(hi-lo-.12,.04,.29),'Teal',True)
        box('ReceptionCounter',(cx,11.995,.74),(hi-lo-.12,.028,.027),'Brass')
    g.cylinder('ReceptionHardware',(lo+.15,11.94,.23),(hi-.15,11.94,.23),.025,'Steel',20)
    for x in (lo+.25,hi-.25):g.beam('ReceptionHardware',(x,12.15,.23),(x,11.94,.23),.025,.025,'Steel')
for x in (-10.1,-6.7):
    g.ring('ReceptionHardware',(x+.72,13.27,.778),(0,0,1),.045,.031,.008,'Dark',32)
    for y in (13.05,13.32):box('ReceptionHardware',(x-.64,y,.792),(.20,.22,.025),'Teal')
    for i in range(4):box('ReceptionHardware',(x-.64,13.05,.808+i*.003),(.15,.18,.003),'White')
    sign('desk1' if x<-9 else 'desk2',(x,12.055,.54),1.1)
sign('accessible',(-4.1,12.084,.50),1.35)
sign('registration',(-10.9,16.475,2.42),4.8)
sign('guide',(-4.1,16.475,2.42),3.1)
# Short overhead reception canopy supported on wall and two real hangers.
box('ReceptionCanopy',(-7.5,13.65,3.55),(10.1,3.5,.18),'Teal')
box('ReceptionCanopy',(-7.5,11.89,3.56),(10.1,.022,.055),'Brass')
for x in (-11.8,-3.2):
    for y in (12,15.2):
        g.cylinder('ReceptionCanopy',(x,y,3.64),(x,y,4.12),.018,'Steel',16)
        box('ReceptionCanopy',(x,y,4.11),(.09,.09,.03),'Steel')

# Queue stanchions, 1.8m clear switchback lanes, no obstacles on centre spine.
for y in (6.5,8.3,10.1):
    for x in (-16.9,-14.1,-11.3):
        g.lathe('QueueBases',(x,y,.0),(0,0,1),[(0,.18),(.025,.18),(.05,.13),(.06,.031),(.92,.031),(.97,.055),(1.025,.055)],'Steel',32,True)
    for a,b in [(-16.9,-14.1),(-14.1,-11.3)]:box('QueueBelts',((a+b)/2,y,.945),(b-a,.012,.052),'Teal')
box('QueueBelts',(-16.9,9.2,.945),(.012,1.8,.052),'Teal')
box('QueueBelts',(-11.3,7.4,.945),(.012,1.8,.052),'Teal')

# Two full-height inspection arches, baggage belt with rollers and actual apertures.
for side in (-1,1):
    yc=side*2.55
    for yy in (yc-.99,yc+.99):
        box('SecurityArches',(14,yy,1.30),(.48,.19,2.60),'Teal',True)
        box('SecurityDetails',(13.743,yy,1.38),(.018,.12,2.14),'Dark')
        for z in (.45,.95,1.45,1.95,2.35):box('SecurityDetails',(13.73,yy,z),(.009,.08,.025),'Glow')
        box('SecurityArches',(14,yy,.025),(.76,.36,.05),'Steel',True)
    box('SecurityArches',(14,yc,2.66),(.50,2.18,.19),'Teal',True)
    sign('lane1' if side<0 else 'lane2',(13.735,yc,2.66),1.65,(-1,0,0))
    box('SecurityDetails',(13.68,yc-.98,1.17),(.12,.20,.30),'Dark')
    for z in (1.14,1.24):g.cylinder('SecurityDetails',(13.61,yc-.98,z),(13.595,yc-.98,z),.018,'Brass',20)
box('BaggageConveyor',(14,0,.71),(4.6,1.35,.20),'Teal',True)
box('BaggageConveyor',(14,0,.828),(4.56,1.13,.036),'Rubber',True)
for x in (12.05,15.95):
    for y in (-.51,.51):box('BaggageConveyor',(x,y,.30),(.095,.095,.60),'Steel',True)
for x in [11.75+i*.17 for i in range(27)]:g.cylinder('ConveyorDetails',(x,-.55,.842),(x,.55,.842),.018,'Dark',16)
for y in (-.72,.72):box('BaggageScanner',(14,y,1.30),(1.8,.13,.96),'Stone',True)
box('BaggageScanner',(14,0,1.83),(1.8,1.57,.15),'Stone',True)
for x in (13.08,14.92):
    for j in range(12):box('ScannerCurtains',(x,-.60+j*.11,1.32),(.018,.115,.90),'Rubber')
for x in (12.2,15.8):
    box('InspectionTrays',(x,0,.894),(.51,.42,.04),'White')
    for sy in (-1,1):box('InspectionTrays',(x,sy*.225,.932),(.55,.035,.10),'White')
    for sx in (-1,1):box('InspectionTrays',(x+sx*.272,0,.932),(.035,.48,.10),'White')
sign('security',(11.8,0,3.35),3.6,(-1,0,0))
for y in (-1.68,1.68):g.cylinder('SignHangers',(11.81,y,3.89),(11.81,y,10.0),.011,'Steel',12)

# Planters: hollow tapered stone bodies, soil below rim and rooted existing foliage.
for x,y,z in CFG['pots']:
    g.lathe('Planters',(x,y,z),(0,0,1),[(0,.40),(.045,.43),(.57,.49),(.63,.49),(.63,.455),(.58,.455),(.08,.36)],'Stone',48,True)
    g.cylinder('PlanterSoil',(x,y,z+.54),(x,y,z+.59),.446,'Soil',40)
    g.ring('PlanterTrim',(x,y,z+.612),(0,0,1),.495,.45,.018,'Brass',48)

# Fixture geometry is reused; bespoke canopy and main atrium luminaires are detailed.
for p in CFG['lights']:
    x,y,z=p['position_m'];main=p['role']=='main';length=2.8 if main else 1.35
    box('LightFixtures',(x,y,z+.23),(length,.42,.16),'Teal')
    box('LightDiffusers',(x,y,z+.144),(length-.12,.32,.012),'Glow')
    for xx in (x-length*.39,x+length*.39):
        target=10.0 if main or z>4 and x<19 else 8.80 if z>4 else 3.46 if z<3.2 and abs(x)<24 else 4.12 if abs(x)<24 else 3.4 if x<0 else 3.0
        if target>z+.33:
            g.cylinder('LightHangers',(xx,y,z+.30),(xx,y,target),.01,'Steel',10)
            box('LightHangers',(xx,y,target-.008),(.10,.10,.022),'Steel')
    for xx in (x-length/2+.035,x+length/2-.035):box('LightFixtures',(xx,y,z+.23),(.045,.48,.16),'Steel')

# Reception quality details: directional wayfinding, wall panels, clock, bins,
# terminal directory, upper lounge rails, ducts, grilles and fitted conduit.
sign('welcome',(-17.90,0,6.85),6.2,(-1,0,0))
for y in (-2.65,2.65):g.cylinder('SignHangers',(-17.887,y,7.795),(-17.887,y,10.0),.014,'Steel',12)
sign('waiting',(-17.7,-16.475,2.6),3.5,(0,1,0))
sign('upper',(-3.15,0,8.2),3.8,(-1,0,0))
for y in (-1.55,1.55):g.cylinder('SignHangers',(-3.139,y,8.777),(-3.139,y,10.0),.011,'Steel',12)
sign('exit',(23.79,0,3.62),3.0,(-1,0,0));sign('storage',(23.79,-12.8,2.20),2.3,(-1,0,0))
sign('meeting',(-23.79,0,6.9),3.6,(1,0,0));sign('return',(-23.79,0,3.92),3.2,(1,0,0))
for x,y,normal in [(-12,-16.475,(0,1,0)),(0,16.475,(0,-1,0))]:sign('water',(x,y,2.3),1.65,normal)
for x in (-22.8,-17,-11,-5,1,7,13,20):
    for side in (-1,1):
        # Wall-mounted information / acoustic panels stay off outer columns.
        box('AcousticBacking',(x,side*16.445,7.15),(3.1,.045,1.55),'Dark')
        for j in range(20):box('AcousticSlats',(x-1.47+j*.154,side*16.407,7.15),(.055,.052,1.52),'Wood')
for x,y in [(-23,4.8),(-23,-4.8),(18,13.4),(18,-13.4)]:
    box('DirectoryStand',(x,y,.035),(.65,.66,.07),'Steel',True)
    box('DirectoryStand',(x,y,.85),(.12,.18,1.63),'Teal',True)
    box('DirectoryStand',(x,y,1.4),(.16,.72,.85),'Teal',True)
    sign('map',(x-.09,y,1.55),.67,(-1,0,0));sign('notice',(x-.09,y,1.21),.67,(-1,0,0))
for i,(x,y,z) in enumerate([(-14,-15.9,0),(-1,15.9,0),(22.9,12,0),(-22.5,-15.8,4.5),(-22.5,15.8,4.5)]):
    g.lathe('WasteBins',(x,y,z),(0,0,1),[(0,.20),(.04,.22),(.61,.22),(.68,.20),(.68,.13),(.60,.13),(.08,.17)],'Steel',40,True)
    g.ring('WasteBinTrim',(x,y,z+.30),(0,0,1),.224,.217,.04,'Teal',40)
for side in (-1,1):
    y=side*15.6
    box('Ventilation',(-1,y,9.50),(43,.55,.35),'Steel')
    for x in (-18,-10,-2,6,14):
        box('VentGrilles',(x,y,9.31),(1.2,.44,.028),'Dark')
        for i in range(18):box('VentGrilles',(x-.55+i*.065,y,9.285),(.022,.43,.025),'Steel')
        for sx in (-.59,.59):g.cylinder('MechanicalHangers',(x+sx,y-.25,9.7),(x+sx,y-.25,9.97),.014,'Steel',12)
    g.rounded_pipe('Conduit',[(-23,side*16.35,2.95),(-23,side*16.35,3.90),(22,side*16.35,3.90)],.016,'Steel',12)
    for x in (-21,-9,3,15):
        box('ElectricalJunctions',(x,side*16.405,3.90),(.17,.14,.18),'Teal')
        for dx in (-.055,.055):g.bolt('Fasteners',(x+dx,side*16.32,3.95),(0,-side,0),.004)
# Clock above reception: readable dial geometry, no floating black plane.
g.cylinder('WallClock',(-1.3,16.38,2.55),(-1.3,16.26,2.55),.39,'Teal',64)
g.cylinder('WallClock',(-1.3,16.257,2.55),(-1.3,16.25,2.55),.34,'White',64)
for i in range(12):
    a=i*math.tau/12;g.beam('ClockHands',(-1.3+math.sin(a)*.274,16.239,2.55+math.cos(a)*.274),(-1.3+math.sin(a)*.318,16.239,2.55+math.cos(a)*.318),.018,.010,'Dark')
g.beam('ClockHands',(-1.3,16.225,2.55),(-1.44,16.225,2.73),.023,.012,'Dark')
g.beam('ClockHands',(-1.3,16.212,2.55),(-1.03,16.212,2.55),.016,.01,'Dark')

# Meshes are spatially split by function; floors have explicit real-world UV scale.
records=[]
def export(obj,kind,hulls,mapping,nanite=True,**extra):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    if kind not in ('Signs','GroundFloor','UpperFloor','Glass','Fracture','PlanterSoil'):
        mod=obj.modifiers.new('Machined edge radii','BEVEL');mod.width=.006 if kind in ('OuterWalls','Columns','StairTreads','ReceptionCounter') else .0025;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=math.radians(36)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('Area weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Export triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    cols=[]
    for i,(vs,fs) in enumerate(hulls):
        mesh=bpy.data.meshes.new('UCX_'+obj.name+'_%03d'%i);mesh.from_pydata(vs,[],fs);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        co=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
    obj.data.update();fbx=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for co in cols:co.hide_set(True);co.hide_render=True
    placement=[0,.12,0] if kind in ('WallClock','ClockHands') else [0,0,0]
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,position_m=placement,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),materials=mapping,
        triangles=len(obj.data.polygons),collision=bool(hulls),collision_hulls=len(hulls),nanite=nanite,cast_shadow=kind not in ('Signs','LightDiffusers','Conduit','LightHangers','Fasteners','Glass','Fracture'),**extra))
    obj.location=placement
    print('RECEPTION_EXPORTED',obj.name,len(obj.data.polygons),flush=True)
for (room,kind),data in g.G.items():
    name='SM_Reception_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    order=list(dict.fromkeys(data['m']))
    for role in order:mesh.materials.append(materials[role])
    mesh.uv_layers.new(name='UVMap');color=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER');uv=mesh.uv_layers['UVMap']
    for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(role);face.use_smooth=smooth;axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))];s=ROLES[role].get('uv_meters_override',ROLES[role].get('uv_meters',1))
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords else (p[axes[0]]/s,p[axes[1]]/s)
            color.data[li].color=(.018+.07*math.exp(-max(0,p.z)/.3),0,0,1)
    export(obj,kind,g.C.get((room,kind),[]),{'RH_'+r:ROLES[r]['existing_ue_path'] for r in order},nanite=kind not in ('Signs','LightDiffusers'))

# Exact office pane sizes, native glass fragment UV data and the accepted shader.
stock=json.loads((PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/manifest.json').read_text('utf8'))
glasspath=next(iter(next(x for x in stock['objects'] if x['name']=='SM_SW_WindowPaneV5')['materials'].values()))
glass=bpy.data.materials.new('RH_Glass')
def cube(name,center,size,material=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:o.data.materials.append(material)
    return o
def export_glass(obj,kind,boxes=(),shards=0):
    obj.name='SM_Reception_'+kind;hulls=[]
    for c,s in boxes:
        co=cube('CollisionTemporary',c,s);hulls.append(([tuple(v.co) for v in co.data.vertices],[tuple(p.vertices) for p in co.data.polygons]));bpy.data.objects.remove(co,do_unlink=True)
    export(obj,'Fracture' if shards else 'Glass',hulls,{'RH_Glass':glasspath},nanite=False,shards=shards)
text=(PROJECT/'SourceAssets/DungeonIsolationWard20260929/Scripts/author_breakable_glass.py').read_text('utf8');text=text[text.index('def clipped('):text.index("panes('Door'")]
text=text.replace(' for face,attr in zip(mesh.polygons,attributes):'," uv0=mesh.uv_layers['UVMap'];uv1=mesh.uv_layers['ShardCenter'];uv2=mesh.uv_layers['ShardSeed']\n for face,attr in zip(mesh.polygons,attributes):")
ctx=dict(bpy=bpy,math=math,random=random,cube=cube,export=export_glass,glass=glass);exec(compile(text,'reception_glazing','exec'),ctx)
widths=sorted(set(round(p['width_m'],5) for p in CFG['glass']))
for i,w in enumerate(widths):ctx['panes']('Office'+str(i),w,1.95,.008,12,11,61006+i)
for p in CFG['glass']:p['glass_kind']='Office'+str(widths.index(round(p['width_m'],5)))
(ROOT/'Config/layout.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
for im in bpy.data.images:
    if im.source=='FILE' and im.has_data:im.pack()
bpy.context.scene['tests_run']=False;bpy.context.scene['rendered']=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FacilityReceptionHall.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,tests_run=False,rendered=False),indent=2),encoding='utf8')
print('RECEPTION_SOURCE_COMPLETE',len(records),flush=True)
