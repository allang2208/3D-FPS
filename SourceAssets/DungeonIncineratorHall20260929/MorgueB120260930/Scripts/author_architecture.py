"""Full B1 mortuary shell and return stair in the existing floor aperture."""
import json,runpy,math
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
C=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'))
ns=runpy.run_path(str(HALL/'Scripts/author_hall.py'),init_globals={'SKIP_HALL_EXPORT':True},run_name='b1_architecture')
# Preserve only the existing observation stairs; remove the eight shallow pit steps.
old=ns['G']['Stairs'];keep=[i for i,f in enumerate(old['f']) if all(old['v'][j][1]>5 for j in f)]
stairs={'v':old['v'],'f':[old['f'][i] for i in keep],'m':[old['m'][i] for i in keep],
        'uv':[old['uv'][i] for i in keep],'smooth':[old['smooth'][i] for i in keep]}
ns['G'].clear();ns['G']['Stairs']=stairs
box=ns['box'];beam=ns['beam'];z=C['floor_z'];ceiling=C['ceiling_z'];x0,y0,x1,y1=C['rect_m']
for key,color in [('ClinicalTile',(.46,.49,.45,1)),('ClinicalPlaster',(.54,.55,.50,1)),('ClinicalFloor',(.29,.32,.30,1))]:
    ns['MAPPING'][key]=C['ue_base']+'/Materials/M_'+key
    mat=bpy.data.materials.new('RS_'+key);mat.diffuse_color=color;ns['MATS'][key]=mat

box('B1Floor',((x0+x1)/2,(y0+y1)/2,z-.16),(x1-x0,y1-y0,.27),'Mortar')
nx=math.ceil((x1-x0)/.6);ny=math.ceil((y1-y0)/.6);dx=(x1-x0)/nx;dy=(y1-y0)/ny
for i in range(nx):
    for j in range(ny):
        x=x0+(i+.5)*dx;y=y0+(j+.5)*dy
        if x<-8.6 and y<-2.65:continue
        box('B1Floor',(x,y,z-.0125),(dx-.005,dy-.005,.025),'ClinicalFloor')

def wall(axis,at,lo,hi,doors=(),tiled=True):
    # Real doorway voids, with jambs and lintels. No door-shaped texture on a wall.
    def segment(a,b,bottom,top):
        if b-a<.001:return
        center=(at,(a+b)/2,(bottom+top)/2) if axis=='x' else ((a+b)/2,at,(bottom+top)/2)
        size=(.18,b-a,top-bottom) if axis=='x' else (b-a,.18,top-bottom)
        box('B1Walls',center,size,'ClinicalPlaster')
        if not tiled:return
        end=min(top,z+1.65)
        if end<=bottom:return
        count=math.ceil((b-a)/.3);rows=math.ceil((end-bottom)/.3)
        for side in (-1,1):
            for i in range(count):
                for j in range(rows):
                    along=a+(i+.5)*(b-a)/count;zz=bottom+(j+.5)*(end-bottom)/rows
                    cc=(at+side*.099,along,zz) if axis=='x' else (along,at+side*.099,zz)
                    ss=(.016,(b-a)/count-.004,(end-bottom)/rows-.004) if axis=='x' else ((b-a)/count-.004,.016,(end-bottom)/rows-.004)
                    box('B1Wainscot',cc,ss,'ClinicalTile')
    cursor=lo
    for a,b,h in sorted(doors):
        segment(cursor,a,z,ceiling);segment(a,b,z+h,ceiling);cursor=b
        for p in (a-.035,b+.035):
            cc=(at,p,z+h/2) if axis=='x' else (p,at,z+h/2)
            ss=(.23,.07,h) if axis=='x' else (.07,.23,h)
            box('B1DoorFrames',cc,ss,'PaintedSteel')
        cc=(at,(a+b)/2,z+h+.035) if axis=='x' else ((a+b)/2,at,z+h+.035)
        ss=(.23,b-a+.14,.07) if axis=='x' else (b-a+.14,.23,.07)
        box('B1DoorFrames',cc,ss,'PaintedSteel')
    segment(cursor,hi,z,ceiling)

wall('x',x0-.09,y0,y1);wall('x',x1+.09,y0,y1)
wall('y',y0-.09,x0,x1);wall('y',y1+.09,x0,x1)
wall('x',-6,y0,y1,[(-1.2,1.2,2.5)])
wall('y',2.3,-6,x1,[(-3.6,-1.4,2.35),(3.6,5.4,2.35)])
wall('x',1.8,2.3,y1)
# Stair shaft walls end at the underside of the retained hall floor.
wall('x',-8.51,y0,-2.65,tiled=False)
wall('y',-2.65,-13,-8.6,[(-10.62,-8.78,2.45)],False)
# The two stair flights have 24 risers and a full-depth turning landing.
st=C['stairs'];front=-2.65;turn=-5.95
for i in range(st['risers_per_flight']):
    top=-(i+1)*st['rise_m'];a,b=st['west_flight_x'];yy=front-(i+.5)*st['going_m']
    box('Stairs',((a+b)/2,yy,(z-.12+top)/2),(b-a,st['going_m'],top-z+.12),'Concrete')
    box('B1Nosing',((a+b)/2,yy+st['going_m']/2-.022,top+.004),(b-a-.05,.035,.008),'Yellow')
    top=-1.8-(i+1)*st['rise_m'];a,b=st['east_flight_x'];yy=turn+(i+.5)*st['going_m']
    box('Stairs',((a+b)/2,yy,(z-.12+top)/2),(b-a,st['going_m'],top-z+.12),'Concrete')
    box('B1Nosing',((a+b)/2,yy-st['going_m']/2+.022,top+.004),(b-a-.05,.035,.008),'Yellow')
box('Stairs',(-10.8,-6.8,-1.92),(4.1,1.7,.24),'Concrete')
# A small dividing spine gives the parallel handrails an actual support.
box('B1ShaftSpine',(-10.825,-4.3,-1.85),(.18,3.3,3.5),'Concrete')
# Service ceiling beams support the furnace floor above; clear height stays >2.8m.
for x in (-5.7,.8,7.45):
    box('B1Structure',(x,-1.4,-.43),(.27,12.25,.36),'Concrete')
for x,y in ((-.2,-6.8),(-5.7,4.5),(7.4,4.5)):
    box('B1Structure',(x,y,(z+ceiling)/2),(.30,.30,ceiling-z),'Concrete')
# Ceiling extraction duct and branches, with suspended collars.
box('B1Services',(0,-.1,-.65),(12.0,.38,.28),'PipeEnamel')
box('B1Services',(4.3,1.8,-.65),(.38,4.0,.28),'PipeEnamel')
for x in (-4,-1,2,5):
    for yy in (-.33,.13):beam('B1Services',(x,yy,-.25),(x,yy,-.82),.018,.018,'BareSteel')
ns['OUT']=ROOT/'Authored/Architecture';ns['OUT'].mkdir(parents=True,exist_ok=True)
ns['EXPORT_SUFFIX']='_MorgueB1';ns['EXPORT_BLEND_NAME']='Incinerator_B1_Mortuary_Architecture.blend'
ns['CFG']=dict(ns['CFG'],revision=C['revision'])
script=HALL/'Scripts/export_geometry.py';exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
