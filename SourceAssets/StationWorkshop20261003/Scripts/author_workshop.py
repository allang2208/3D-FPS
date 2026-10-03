"""Precise station workshop geometry. UE centimetres in the author recipe; no renders."""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
refine_root=Path(__file__).resolve().parents[1]/'RefineV2'
refine_receipt=refine_root/'Receipts/install.json'
if __name__=='__main__' and refine_receipt.exists() and json.loads(refine_receipt.read_text('utf8')).get('stage')=='maps_saved':
    import runpy
    runpy.run_path(str(refine_root/'Scripts/author_refine.py'),run_name='__main__')
    runpy.run_path(str(refine_root/'Scripts/repair_warehouse_labels.py'),run_name='__main__')
    raise SystemExit(0)
sys.path.insert(0,str(Path(__file__).resolve().parent))
import geometry as g
ROOT=g.ROOT;OUT=g.OUT;BASE=g.BASE
for argument in sys.argv:
    if argument.startswith('--only='):g.EXPORT_NAMES={'SM_SW_'+key for key in argument[7:].split(',')}
REGIONS={'Board':[16,16,1150,780],'Door':[16,824,1200,240],
 'Monitor':[1240,16,784,441],'Map':[1240,500,784,441],
 'Paper':[16,1100,640,460],'Label':[16,1620,760,152],
 'Tools':[820,1620,760,152],'Safety':[1240,990,700,560]}

def b(p):return (p[0]/100,-p[1]/100,p[2]/100)
def box(c,s,mat='Paint',edge=.25):return g.box(b(c),tuple(v/100 for v in s),mat,edge/100)
def cyl(c,r,h,mat='Steel',axis=(0,0,1),sides=32):return g.cylinder(b(c),r/100,h/100,mat,(axis[0],-axis[1],axis[2]),sides)
def tube(points,r=.35,mat='Rubber'):return g.tube([b(p) for p in points],r/100,mat)
def rotated(o,p,yaw):
    origin=Vector(b(p))
    o.location=origin+(__import__('mathutils').Matrix.Rotation(math.radians(-yaw),3,'Z') @ (o.location-origin))
    o.rotation_euler.z+=math.radians(-yaw);return o
def bolt(c,axis=(0,-1,0),r=.55):return cyl(c,r,.4,'Steel',axis,sides=12)
def ring(c,r,t,mat='Steel',axis=(1,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=12,major_radius=r/100,minor_radius=t/100,location=b(c))
    o=bpy.context.object;o.rotation_euler=Vector((axis[0],-axis[1],axis[2])).to_track_quat('Z','Y').to_euler()
    for f in o.data.polygons:f.use_smooth=True
    return g.finish(o,mat,0)
def printed(c,w,h,key,normal=(0,-1,0),mat='Labels',horizontal=False):
    if horizontal:u=Vector((1,0,0));v=Vector((0,-1,0))
    else:u=Vector((normal[1],-normal[0],0)).normalized();v=Vector((0,0,1))
    center=Vector(c);vertices=[b(center+u*x*w/2+v*y*h/2) for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))]
    mesh=bpy.data.meshes.new('Native aspect printed face');mesh.from_pydata(vertices,[],[(0,1,2,3)]);mesh.update()
    o=bpy.data.objects.new('Printed '+key,mesh);bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(g.MATS[mat]);uv=mesh.uv_layers.new(name='UVMap');x,y,pw,ph=REGIONS[key]
    coords=[(x/2048,1-(y+ph)/2048),((x+pw)/2048,1-(y+ph)/2048),((x+pw)/2048,1-y/2048),(x/2048,1-y/2048)]
    for li in mesh.polygons[0].loop_indices:uv.data[li].uv=coords[mesh.loops[li].vertex_index]
    g.parts.append(o)
def emit(key,hulls=(),pivot=(0,0,0),nanite=True):
    o=g.emit('SM_SW_'+key,pivot=b(pivot),hulls=[(b(c),tuple(v/100 for v in s)) for c,s in hulls])
    g.records[-1].update(kind=key,nanite=nanite);return o

# Workshop fits inside the existing platform. Doors are real openings in the wall and collision.
walls=[]
def wall(c,s):box(c,s,'Wall',.4);walls.append((c,s))
for x in (0,1000):wall((x,350,160),(14,700,320))
wall((500,700,160),(1000,14,320))
# Front: personnel door 60..180; glazed wall 265..735; service opening 760..980.
for lo,hi in ((0,60),(180,265),(735,760),(980,1000)):
    wall(((lo+hi)/2,0,160),(hi-lo,14,320))
wall((120,0,283),(120,14,74));wall((870,0,298),(220,14,44))
wall((500,0,52.5),(470,14,105));wall((500,0,288),(470,14,64))
emit('Walls',walls)
box((500,350,328),(1020,720,16),'Concrete',.5)
emit('Roof',[((500,350,328),(1020,720,16))])
for x in (9,991):box((x,350,6),(3,690,12),'Paint',.15)
box((500,690,6),(985,3,12),'Paint',.15)
for lo,hi in ((0,60),(180,760),(980,1000)):box(((lo+hi)/2,9,6),(hi-lo,3,12),'Paint',.15)
for x in (60,180,760,980):box((x,0,123 if x<200 else 138),(7,23,246 if x<200 else 276),'Paint',.2)
box((120,0,246),(127,23,7),'Paint');box((870,0,276),(227,23,7),'Paint')
for x in (265,421.67,578.33,735):box((x,0,181),(5,17,154),'Paint')
for z in (107,255):box((500,0,z),(470,17,5),'Paint')
box((500,-4.5,110),(472,4,3),'Steel',.1)
emit('Frames')
glass=[]
for lo,hi in ((267.5,419.17),(424.17,575.83),(580.83,732.5)):
    box(((lo+hi)/2,0,181),(hi-lo,.65,143),'Glass',.02)
    glass.append((((lo+hi)/2,0,181),(hi-lo,.8,143)))
emit('ObservationGlass',glass,nanite=False)

# Door leaves are saved at an open angle, with hinge plates, handles and inspection panels.
doors=[]
for hinge,width,height,angle in [((60,0,0),118,243,76),((760,0,0),108,272,87),((980,0,0),-108,272,-87)]:
    x,y,z=hinge;sign=1 if width>0 else -1;w=abs(width)
    pieces_start=len(g.parts)
    box((x+width/2,y,height/2),(w,4,height),'Paint',.45)
    box((x+width/2,y-2.15,height*.67),(w-24,.8,54),'Plastic',.1)
    for hh in (24,height/2,height-24):cyl((x,y,hh),1.05,11,'Steel')
    tube([(x+sign*(w-13),-3,height*.43),(x+sign*(w-13),-7,height*.43),(x+sign*(w-13),-7,height*.43+13)],.75,'Steel')
    for p in g.parts[pieces_start:]:rotated(p,hinge,angle)
    a=math.radians(angle)
    doors.append(((x+width*.5*math.cos(a),y+width*.5*math.sin(a),height*.5),
        (abs(width*math.cos(a))+abs(4*math.sin(a)),abs(width*math.sin(a))+abs(4*math.cos(a)),height)))
emit('OpenedDoors',doors)

# Power is physically connected to the interior wall and the reused workbench socket adapter.
for p,q in [((38,686,305),(955,686,305)),((647,10,305),(647,10,91)),((230,686,305),(230,686,132))]:
    tube([p,q],.7,'Steel')
    for t in (.14,.43,.76):
        c=tuple(p[i]+(q[i]-p[i])*t for i in range(3));box(c,(3.5,2,2),'Paint',.1)
box((230,688.7,131),(9.2,9.1,5.2),'Paint',.15)
for x in (643.5,650.5):bolt((x,7.6,90),axis=(0,1,0),r=.35)
box((647,8.6,90),(10,3.2,8),'Plastic',.35)
box((647,11,90),(3.8,4,4.6),'Rubber',.35)
tube([(647,13,90),(647,18,86),(643,25,77),(627,40,77),(615,58.1,87),(615,58.1,102)],.24)
box((955,688,258),(15,7,21),'Paint',.4)
printed((955,683.9,258),12,2.4,'Label')
emit('Electrical')

# Dispatch furniture: actual supports, trim, keyboard keys, handset and loose paper surface.
box((610,72,75),(210,80,5),'Wood',.55)
for x in (517,703):
    for y in (39,105):box((x,y,36),(4,4,72),'Paint',.2);box((x,y,1.1),(5,5,2.2),'Rubber',.1)
box((610,45,62),(186,3,4),'Steel');box((610,109,62),(186,3,4),'Steel')
emit('DispatchDesk',[((610,72,75),(210,80,5)),*((((x,y,36),(4,4,72)) for x in (517,703) for y in (39,105)))])
box((595,61,111),(49,5.5,30),'Plastic',.65)
box((595,61,90.5),(6,5,24),'Steel',.3);box((595,62,78.5),(28,18,2),'Steel',.5)
printed((595,64.05,111),44.8,25.2,'Monitor',normal=(0,1,0),mat='Screen')
for x in (573,577,581):cyl((x,64.2,98),.35,.2,'Steel',axis=(0,1,0),sides=12)
box((593,94,78.3),(45,15,1.6),'Plastic',.4)
for row in range(4):
    for col in range(13):box((574+col*2.9,89+row*2.7,79.4),(2.2,2,1),'Rubber',.12)
box((595,105.5,79.4),(19,2,1),'Rubber',.1)
box((629,94,78.7),(6,10,2.4),'Rubber',.6)
tube([(629,89,79),(631,83,79),(619,78,79),(605,69,79)],.14)
box((537,68,79.5),(14,17,4),'Plastic',.4)
for x in (533,537,541):
    for y in (69,73,77):box((x,y,82),(2,2,.8),'Rubber',.15)
tube([(530,62,84),(530,61,89),(542,61,89),(546,64,84)],1.4,'Rubber')
for x in (530,546):box((x,63,82.1),(4,4,1.2),'Plastic',.2)
tube([(545,65,84),(549,66,84),(550,74,82),(550,82,79),(550,91,79)],.18)
box((690,53,89.5),(7,5,24),'Plastic',.3)
for z in (81,84,87):box((690,55.65,z),(4,.6,.5),'Rubber',.1)
cyl((690,53,108.5),.28,15,'Rubber',sides=12)
printed((691,55.8,98),5,1,'Label',normal=(0,1,0))
emit('DispatchElectronics')

# Detailed notice board and clear signage; UV rectangles match physical aspect.
box((580,689,196),(121,5,84),'Wood',.5)
printed((580,686.35,196),115,78,'Board')
for x in (525,635):bolt((x,685.9,234),r=.45)
box((300,-12,283),(124,3,28),'Paint',.2);printed((300,-13.6,283),120,24,'Door')
box((420,688,220),(82.4,4,48.2),'Paint',.25);printed((420,685.85,220),78.4,44.1,'Map')
box((919,689,202),(54,3,44),'Paint',.3);printed((919,687.35,202),50,40,'Safety')
emit('NoticeSigns')

# Parts rack: one metre of opening clearance above the lower tote shelf.
rack=[]
for x in (665,865):
    for y in (613,681):
        box((x,y,99),(4,4,198),'Paint',.2);rack.append(((x,y,99),(4,4,198)))
        box((x,y,1),(9,9,2),'Steel',.15)
for z in (30,130,180):
    box((765,647,z),(207,72,3),'Paint',.2);rack.append(((765,647,z),(207,72,3)))
    for x in (665,865):box((x,647,z-3),(4,66,6),'Steel',.2)
tube([(665,681,33),(865,681,177)],.75,'Steel');tube([(865,681,33),(665,681,177)],.75,'Steel')
emit('PartsRack',rack)
for x,y in ((700,641),(744,643),(796,650)):
    for k in range(3):ring((x+k*2,y,132.7+k*2.4),5.2,1.2,axis=(0,0,1))
for x in (815,833):
    cyl((x,641,139),4,15,'Steel');cyl((x,641,147),4.7,1.3,'Steel')
box((723,650,190),(53,45,17),'Plastic',.45)
printed((723,626.8,190),38,7.6,'Tools')
for i in range(6):cyl((781+i*6,655,182.9),1.4,11,'Copper',axis=(1,0,0))
emit('RackSpares')

# A dismantled motor on a dedicated stand avoids the accepted workbench's tools and cloth.
stand=[]
box((463,547,75),(96,65,5),'Steel',.45);stand.append(((463,547,75),(96,65,5)))
for x in (425,501):
    for y in (523,571):box((x,y,36),(4,4,72),'Paint');stand.append(((x,y,36),(4,4,72)))
box((463,547,18),(84,54,3),'Paint');stand.append(((463,547,18),(84,54,3)))
emit('MotorStand',stand)
cyl((449,546,94),13.4,48,'Paint',axis=(1,0,0),sides=64)
for x in range(427,473,4):ring((x,546,94),13.6,.6,'Steel')
for x in (426,471):
    cyl((x,546,94),15.2,2.4,'Steel',axis=(1,0,0),sides=48)
    for t in range(8):
        a=t*math.tau/8;bolt((x+1.5,546+12*math.cos(a),94+12*math.sin(a)),axis=(1,0,0))
for y in (536,556):box((449,y,79),(35,7,6),'Paint',.2)
box((449,546,111),(15,15,7),'Paint',.4)
box((478,567,81),(15,15,1.5),'Paint',.3)
ring((485,546,94),12.5,2.5,'Copper')
ring((485,546,94),15,1.2,'Steel')
cyl((502,546,94),4,28,'Steel',axis=(1,0,0),sides=48)
cyl((502,546,94),9.5,17,'Steel',axis=(1,0,0),sides=48)
for t in range(12):
    a=t*math.tau/12;y=546+8.8*math.cos(a);z=94+8.8*math.sin(a)
    tube([(493,y,z),(493,y+1,z+1),(510,y+1,z+1),(511,y,z)],.65,'Copper')
box((502,546,81),(23,27,7),'Wood',.3)
tube([(449,546,114),(461,546,114),(467,559,100),(479,562,81)],.32)
printed((449,531.9,94),12,2.4,'Label')
emit('MotorService')

# Two ceiling fixtures, suspended from the exact workshop ceiling underside.
for x,y in ((290,335),(780,355)):
    for xx in (x-25,x+25):cyl((xx,y,313),.6,14,'Steel')
    box((x,y,304),(76,19,8),'Paint',.4);box((x,y,299.7),(68,13,.8),'Lamp',.15)
emit('LightFixtures')

# The exterior repair cart links the workroom to the station platform.
cart=[]
box((1118,240,49),(98,62,4),'Paint',.3);cart.append(((1118,240,49),(98,62,4)))
box((1118,240,13),(98,62,3),'Paint',.3);cart.append(((1118,240,13),(98,62,3)))
for x in (1077,1159):
    for y in (216,264):
        box((x,y,31),(3,3,40),'Steel',.2)
        cyl((x,y,6.8),6.8,4,'Rubber',axis=(1,0,0));cyl((x,y,6.8),2.8,4.6,'Steel',axis=(1,0,0))
        box((x,y,12),(4,6,8),'Steel',.2)
tube([(1070,213,48),(1070,213,73),(1070,267,73),(1070,267,48)],1.2,'Steel')
for z in (51,15):
    for y in (210,270):box((1118,y,z),(96,1.5,7),'Paint',.2)
emit('RepairCart',cart)
cyl((1113,244,61),10,24,'Paint',axis=(1,0,0),sides=48)
for x in (1100,1126):cyl((x,244,61),10.8,1.5,'Steel',axis=(1,0,0))
for y in (223,257):box((1113,y,53),(24,4,4),'Steel')
tube([(1104,244,72),(1104,244,82),(1120,244,82),(1120,244,72)],.55,'Copper')
for i in range(3):ring((1141,240,52.1+i*2.2),6,1.1,axis=(0,0,1))
box((1090,243,16.5),(22,35,4),'Wood');printed((1090,224.9,16.5),18,3.6,'Label')
emit('CartEquipment')

# Searchable dispatch pedestal: body at local zero; upper drawer has a real tray and handle.
body=[]
for x in (-24,24):box((x,0,33),(2,58,64),'Paint');body.append(((x,0,33),(2,58,64)))
for z in (3,45,65):box((0,0,z),(48,58,2),'Paint');body.append(((0,0,z),(48,58,2)))
box((0,28,33),(48,2,64),'Paint');body.append(((0,28,33),(48,2,64)))
for z in (14,34):
    box((0,-29,z),(47,2,18),'Paint',.25)
    tube([(-7,-30,z),( -7,-34,z),(7,-34,z),(7,-30,z)],.5,'Steel')
for x in (-19,19):
    for y in (-22,22):box((x,y,1.25),(4,4,2.5),'Rubber',.15)
emit('DispatchFiles_Body',body)
box((0,-29,55),(47,2,18),'Paint',.25);box((0,-1,48),(44,55,1.3),'Steel',.15)
for x in (-22,22):box((x,-2,54),(1,54,11),'Steel',.15)
box((0,25,54),(44,1,11),'Steel',.15)
tube([(-7,-30,55),(-7,-34,55),(7,-34,55),(7,-30,55)],.5,'Steel')
box((0,-5,50),(29,41,2.3),'Wood',.1)
printed((0,-30.2,59),19,3.8,'Label')
emit('DispatchFiles_Drawer',pivot=(0,-29,47))

# Loose documents are separate from the desk so poses can vary without deforming the text.
box((0,0,.45),(32,23,.9),'Plastic',.12);printed((0,0,.95),32,23,'Paper',horizontal=True)
box((-13,0,1.25),(1,22,.6),'Steel',.1)
emit('DispatchPaper')
box((0,0,.6),(100,130,1.2),'Rubber',.25)
for x in range(-44,45,5):box((x,0,1.25),(1.2,122,.2),'Rubber',.05)
emit('OperatorMat')

# Standoffs span actual wall-to-fixture gaps rather than leaving floating clamps or boards.
for p,q in [((38,686,305),(955,686,305)),((647,10,305),(647,10,91)),((230,686,305),(230,686,132))]:
    for t in (.14,.43,.76):
        c=[p[i]+(q[i]-p[i])*t for i in range(3)]
        c[1]=690 if p[1]>600 else 8
        box(c,(3.5,6 if p[1]>600 else 2,2),'Steel',.1)
box((955,692.25,258),(15,1.5,21),'Paint',.1)
for x in (525,635):
    box((x,692.25,196),(4,1.5,54),'Steel',.1)
    cyl((x,686.25,234),.8,.5,'Steel',axis=(0,-1,0),sides=20)
for x in (385,455):box((x,691.5,220),(4,3,35),'Steel',.1)
for x in (895,943):box((x,691.75,202),(4,2.5,31),'Steel',.1)
for x in (245,355):box((x,-8.75,283),(4,3.5,18),'Steel',.1)
emit('AttachmentMounts')

for o in bpy.context.scene.objects:o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StationWorkshop_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=g.records,regions=REGIONS,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STATION_WORKSHOP_AUTHORED',len(g.records),flush=True)
