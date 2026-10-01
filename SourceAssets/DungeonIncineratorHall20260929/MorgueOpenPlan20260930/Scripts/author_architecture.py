"""Open-plan basement matching the hall footprint, open slab stairs and recessed jambs."""
import json,runpy,math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
C=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'))
ns=runpy.run_path(str(HALL/'Scripts/author_hall.py'),init_globals={'SKIP_HALL_EXPORT':True},run_name='open_b1')
old=ns['G']['Stairs'];keep=[i for i,f in enumerate(old['f']) if all(old['v'][j][1]>5 for j in f)]
stairs={k:([old[k][i] for i in keep] if k!='v' else old[k]) for k in ('v','f','m','uv','smooth')}
ns['G'].clear();ns['G']['Stairs']=stairs
box=ns['box'];beam=ns['beam'];poly=ns['poly'];prism=ns['prism'];clip=ns['clip_xy']
z=C['floor_z'];ceiling=C['ceiling_z'];outline=C['outline_m']
for key,color in [('ClinicalTile',(.46,.49,.45,1)),('ClinicalPlaster',(.54,.55,.50,1)),('ClinicalFloor',(.29,.32,.30,1))]:
    ns['MAPPING'][key]=C['ue_base']+'/Materials/M_'+key
    mat=bpy.data.materials.new('RS_'+key);mat.diffuse_color=color;ns['MATS'][key]=mat
prism('B1Floor',outline,z-.30,z-.025,'Mortar')
for ix in range(47):
    for iy in range(35):
        a=-14+ix*28/47+.0025;b=-14+(ix+1)*28/47-.0025
        lo=-10.5+iy*.6+.0025;hi=lo+.595;q=outline
        for axis,value,greater in ((0,a,True),(0,b,False),(1,lo,True),(1,hi,False)):q=clip(q,axis,value,greater)
        if len(q)>=3:prism('B1Floor',q,z-.025,z,'ClinicalFloor')

def extrude_profile(kind,points,point,depth,mat):
    # Triangulate concave caps once; no overlapping boxes at U-frame corners.
    if sum(a*d-c*b for (a,b),(c,d) in zip(points,points[1:]+points[:1]))<0:points=list(reversed(points))
    coords=[Vector((a,b,0)) for a,b in points];lookup={tuple(v):i for i,v in enumerate(coords)};n=len(coords)
    caps=[[v if isinstance(v,int) else lookup[tuple(v)] for v in tri] for tri in tessellate_polygon([coords])]
    vertices=[point(a,b,d) for d in (-depth/2,depth/2) for a,b in points]
    faces=[tuple(reversed(t)) for t in caps]+[tuple(n+i for i in t) for t in caps]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    origin=Vector(point(0,0,0));axis_a=Vector(point(1,0,0))-origin;axis_b=Vector(point(0,1,0))-origin;axis_d=Vector(point(0,0,1))-origin
    if axis_a.cross(axis_b).dot(axis_d)<0:faces=[tuple(reversed(face)) for face in faces]
    poly(kind,vertices,faces,mat)

def wall(start,end,doors=(),thickness=.20,sides=(-1,1)):
    start=Vector(start);end=Vector(end);v=(end-start).normalized();normal=Vector((-v.y,v.x));length=(end-start).length;yaw=math.atan2(v.y,v.x)
    def block(a,b,bottom,top):
        if b-a<.0001 or top-bottom<.0001:return
        p=start+v*(a+b)/2
        box('B1Walls',(p.x,p.y,(bottom+top)/2),(b-a,thickness,top-bottom),'ClinicalPlaster',yaw)
        end_z=min(top,z+1.65)
        if end_z<=bottom:return
        count=math.ceil((b-a)/.3);rows=math.ceil((end_z-bottom)/.3)
        for side in sides:
            for i in range(count):
                p=start+v*(a+(i+.5)*(b-a)/count)+normal*side*(thickness/2+.008)
                for j in range(rows):
                    zz=bottom+(j+.5)*(end_z-bottom)/rows
                    box('B1Wainscot',(p.x,p.y,zz),((b-a)/count-.004,.016,(end_z-bottom)/rows-.004),'ClinicalTile',yaw)
    cursor=0;recess=C['door_frame_wall_recess_m'];frame_width=.075
    for a,b,h in doors:
        # Concrete/tiles terminate 6 mm behind the visible frame opening.
        block(cursor,a-recess,z,ceiling);block(a-recess,b+recess,z+h+recess,ceiling);cursor=b+recess
        points=[(a-frame_width,z),(a,z),(a,z+h),(b,z+h),(b,z),(b+frame_width,z),(b+frame_width,z+h+frame_width),(a-frame_width,z+h+frame_width)]
        def point(t,zz,d):
            p=start+v*t+normal*d;return (p.x,p.y,zz)
        extrude_profile('B1DoorFrames',points,point,C['door_frame_depth_m'],'PaintedSteel')
    block(cursor,length,z,ceiling)

for i,a in enumerate(outline):wall(a,outline[(i+1)%len(outline)],thickness=.28,sides=(1,))
# Only the two retained functional rooms enclose space. The transfer foyer is open.
wall((-4.8,5.2),(8.8,5.2),[(2.1,4.5,2.45),(9.0,11.4,2.45)])
for x in (-4.8,2,8.8):wall((x,5.2),(x,10.36))

# Thin closed stair slabs leave the space below and between flights open.
st=C['stairs'];front=-2.65;turn=-5.95
for side,(a,b),start,sign,top in [('West',st['west_flight_x'],front,-1,0),('East',st['east_flight_x'],turn,1,-1.8)]:
    points=[(start,top)]
    for i in range(12):
        level=top-(i+1)*.15;yy=start+sign*i*.275
        points.extend([(yy,level),(yy+sign*.275,level)])
        nose=yy+sign*.023
        box('B1Nosing',((a+b)/2,nose,level+.004),(b-a-.05,.035,.008),'Yellow')
    finish=start+sign*3.3
    points.extend([(finish,top-1.8-.35),(start,top-.35)])
    extrude_profile('Stairs',points,lambda yy,zz,d:((a+b)/2+d,yy,zz),b-a,'Concrete')
    for x in (a+.06,b-.06):beam('B1Structure',(x,start,top-.24),(x,finish,top-1.8-.24),.08,.14,'PaintedSteel')
box('Stairs',(-10.8,-6.8,-1.92),(4.1,1.7,.24),'Concrete')
for x in (-12.65,-8.95):
    box('B1Structure',(x,-7.3,-2.82),(.14,.14,1.56),'PaintedSteel')
    box('B1Structure',(x,-7.3,z+.015),(.28,.28,.03),'BareSteel')
# No shaft spine, front shaft wall or side enclosure is generated.
for x in (-5,1.5,7.8):box('B1Structure',(x,0,-.43),(.28,20.4,.36),'Concrete')
for x in (-5,7.8):
    for y in (-6.8,3.8):box('B1Structure',(x,y,(z+ceiling)/2),(.32,.32,ceiling-z),'Concrete')
for y in (-6.8,3.8):box('B1Structure',(1.4,y,-.47),(13.1,.24,.44),'Concrete')
box('B1Services',(1.4,1.8,-.65),(24.0,.38,.28),'PipeEnamel')
box('B1Services',(5.4,5.65,-.65),(.38,7.8,.28),'PipeEnamel')
for x in (-9,-5,-1,3,7,11):
    for y in (1.57,2.03):beam('B1Services',(x,y,ceiling),(x,y,-.82),.018,.018,'BareSteel')
# Physically support new basement fixtures and the two stair inspection lamps.
for light in C['lights']:
    x,y,h=light['position']
    if h<0:
        for dx in (-.46,.46):rod_start=(x+dx,y,ceiling);beam('B1Services',rod_start,(x+dx,y,h+.16),.016,.016,'BareSteel')
    elif light['id']=='StairUpper':
        beam('B1Services',(-13.08,y,1.08),(-13.08,y,h+.18),.045,.045,'PaintedSteel')
        beam('B1Services',(-13.08,y,h+.18),(x,y,h+.18),.045,.045,'PaintedSteel')
    else:
        for dx in (-.46,.46):beam('B1Services',(x+dx,-7.73,h+.18),(x+dx,y,h+.18),.04,.04,'PaintedSteel')
ns['OUT']=ROOT/'Authored/Architecture';ns['OUT'].mkdir(parents=True,exist_ok=True)
ns['EXPORT_SUFFIX']='_OpenB1V2';ns['EXPORT_BLEND_NAME']='Morgue_OpenPlan_B1_ArchitectureV2.blend';ns['CFG']=dict(ns['CFG'],revision=C['revision'])
script=HALL/'Scripts/export_geometry.py';exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
