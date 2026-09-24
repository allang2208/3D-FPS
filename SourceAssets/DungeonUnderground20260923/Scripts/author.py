"""Produce the complete two-level industrial descent module; no Unreal/preview launch."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
for folder in ('Authored', 'Config', 'Receipts', 'Sources'):
    (ROOT/folder).mkdir(parents=True, exist_ok=True)
boss = ROOT.parent/'DungeonBossHall20260922/Scripts/author.py'
scope = {'__file__': str(boss), '__name__': 'descent_geometry_library'}
exec(compile(boss.read_text(encoding='utf-8').split('# Floor, high walls', 1)[0], str(boss), 'exec'), scope)
H = scope['H']
H['OUT'] = ROOT/'Authored'; H['RECORDS'] = []; H['LIGHTS'] = []; H['GROUPS'] = {}
H['ROOM'] = {'id': 'StairDrop1080', 'origin_m': [0, 0, 0], 'machines': []}
box, tube = H['box'], H['tube']
guards = scope['GUARDS']; ibeam = scope['ibeam']

def deck(rect, z):
    x0,y0,x1,y1 = rect
    box('Floors', ((x0+x1)/2,(y0+y1)/2,z-.06), (x1-x0,y1-y0,.12), 'BossStructuralSteel')
    # Worn solid tread plates give capsules and navigation a continuous surface.
    for x in (x0+.08,x1-.08):
        ibeam('Frames',(x,y0,z-.20),(x,y1,z-.20),.14,.24)

deck([-1.5,-1.8,1.5,1.8],0)
deck([-1.5,9.,4.8,10.8],-3.6)
deck([1.8,3.6,4.8,5.4],-5.4)
deck([-1.5,-1.8,4.8,0],-7.2)
deck([-1.5,7.2,1.5,10.8],-10.8)
# Opposed end doors let the upper rooms grow away from the lower confluence.
# The middle descent has a real L-1 pause, keeping all steps at 15 / 30 cm.
flights=[(0,1.8,9.,0,-3.6,24),(3.3,9.,5.4,-3.6,-5.4,12),
         (3.3,3.6,0,-5.4,-7.2,12),(0,0,7.2,-7.2,-10.8,24)]
walk=[[0,-1.8,0],[0,1.8,0],[0,9,-3.6],[0,9.9,-3.6],[3.3,9.9,-3.6],
      [3.3,9,-3.6],[3.3,5.4,-5.4],[3.3,3.6,-5.4],[3.3,0,-7.2],
      [3.3,-.9,-7.2],[0,-.9,-7.2],[0,0,-7.2],[0,7.2,-10.8],[0,10.8,-10.8]]
for flight,(xc,y0,y1,z0,z1,count) in enumerate(flights):
    for step in range(count):
        ya = y0+(y1-y0)*step/count
        yb = y0+(y1-y0)*(step+1)/count
        z = z0-(step+1)*.15
        box('StairWest',(xc,(ya+yb)/2,z-.045),(3,.30,.09),'BossGrating')
        box('StairWest',(xc,ya+(yb-ya)*.08,z+.002),(3,.045,.004),'YellowPaint')
        for x in (xc-1.43,xc+1.43):
            H['detail'].fastener((x,(ya+yb)/2,z+.005),(0,0,1),.012,kind='StairWest')
    for x in (xc-1.465,xc+1.465):
        ibeam('Frames',(x,y0,z0-.15),(x,y1,z1-.15),.10,.26)
        for height,radius,mat in ((1.10,.024,'YellowPaint'),(.54,.021,'BossStructuralSteel')):
            tube('GalleryRails',[(x,y0,z0+height),(x,y1,z1+height)],radius,mat,24)
        for step in sorted(set([*range(0,count,4),count-1])):
            t=(step+.5)/count; z=z0-(step+1)*.15; y=y0+(y1-y0)*t
            guards.post((x,y,z),(x,y,z0+(z1-z0)*t+1.10),'GalleryRails')
for y,z in ((9,-3.6),(0,-7.2)):guards.horizontal((1.465,y),(1.835,y),z)
guards.horizontal((1.465,-1.8),(1.465,1.8),0)
for x in (1.835,4.765):guards.horizontal((x,3.6),(x,5.4),-5.4)
guards.horizontal((1.465,7.2),(1.465,10.8),-10.8)

# Enclosed shaft, real 3 x 2.8 m doors at opposite ends and different elevations.
box('Shell',(1.65,4.5,3.10),(6.78,13.08,.20),'Concrete')
box('Shell',(1.65,4.5,-11.03),(6.78,13.08,.22),'Concrete')
for x in (-1.62,4.92):
    box('Shell',(x,4.5,-4.07),(.24,13.08,14.14),'Concrete')
xs=[-1.74,-1.5,1.5,1.8,4.8,5.04]; zs=[-11.14,-10.8,-8.,0.,2.8,3.2]
for y,lo,hi in ((-1.92,0,2.8),(10.92,-10.8,-8.)):
    for xa,xb in zip(xs,xs[1:]):
        for za,zb in zip(zs,zs[1:]):
            x,z=(xa+xb)/2,(za+zb)/2
            if not (-1.5<x<1.5 and lo<z<hi):box('Shell',(x,y,z),(xb-xa,.24,zb-za),'Concrete')
for y,z in ((-1.8,0),(10.8,-10.8)):
    for x in (-1.535,1.535):box('Frames',(x,y,z+1.4),(.07,.28,2.8),'BossStructuralSteel')
    box('Frames',(0,y,z+2.84),(3.14,.28,.08),'BossStructuralSteel')
    # The ivory wall band and actual ceramic joints retain the existing corridor vocabulary.
for z,ya,yb in ((0,-1.8,1.8),(-3.6,9.,10.8),(-5.4,3.6,5.4),(-7.2,-1.8,0),(-10.8,7.2,10.8)):
    for x,sgn in ((-1.496,1),(4.796,-1)):
        for row in range(8):
            for col in range(6):
                box('Tiles',(x,ya+(col+.5)*(yb-ya)/6,z+.14+(row+.5)*.158),(.018,(yb-ya)/6-.008,.150),'IvoryTile')

for x in (-1.40,4.70):
    tube('Services',[(x,10.60,2.75),(x,10.60,-10.65)],.055,'BossPipeCoat',24)
    for z in (1,-1.7,-4.4,-7.1,-9.8):
        tube('Services',[(x,10.60,z),(x,10.8,z)],.025,'BossPipeHardware',16)

lamps=[]
for flight,(xc,y0,y1,z0,z1,count) in enumerate(flights):
    z=(z0+z1)/2+2.30; y=(y0+y1)/2
    spec={'at':[xc,y,z],'warm':flight%2==0,'lumens':1600,'radius_cm':540,'role':'key'}
    H['lamp'](spec);lamps.append(spec)
    wall_x=-1.50 if xc==0 else 4.8
    tube('Fixtures',[(wall_x,y,z+.08),(xc,y,z+.08),(xc,y,z+.035)],.023,'BossStructuralSteel',16)
for x,y,z in ((0,-.8,2.4),(1.65,9.9,-1.2),(3.3,4.5,-3.),(1.65,-.9,-4.8),(0,9.9,-8.4)):
    spec={'at':[x,y,z],'warm':True,'lumens':1250,'radius_cm':480,'role':'key'}
    H['lamp'](spec);lamps.append(spec)
    wall_y=10.8 if y>5 else -1.8
    tube('Fixtures',[(x,wall_y,z+.08),(x,y,z+.08),(x,y,z+.035)],.023,'BossStructuralSteel',16)

from export_boss import export
H['PIPE_RUNS']=[]
export(H)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Dungeon_StairDrop1080.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps({'objects':H['RECORDS']},indent=2),encoding='utf-8')
def vec(p):return [round(p[0]*100,4),round(-p[1]*100,4),round(p[2]*100,4)]
minimum=[-174,-1104,-1114];maximum=[504,204,320]
module=dict(id='StairDrop1080',role='vertical_connector',min=minimum,max=maximum,cells=[dict(min=minimum,max=maximum)],
    ports=[dict(id='upper',position=[0,180,0],normal=[0,1,0],width=300,height=280),
           dict(id='lower',position=[0,-1080,-1080],normal=[0,-1,0],width=300,height=280)],
    parts=[dict(mesh='/Game/Dungeons/Underground20260923/Meshes/'+r['name'],position=[0,0,0],scale=[1,1,1],yaw=0,
                collision=r['kind']!='Fixtures',fluid=False,materials=[]) for r in H['RECORDS']],
    lights=[dict(position=vec([*l['at'][:2],l['at'][2]-.085]),intensity=l['lumens'],radius=l['radius_cm'],
                 color=[1,.64,.36] if l['warm'] else [.73,.84,1],role='key',cast_shadows=True) for l in lamps],
    anchors=[],walk_polyline=[vec(p) for p in walk],floor_delta=-2)
(ROOT/'Config/modules.json').write_text(json.dumps({'version':2,'room_ids':[],'modules':[module]},ensure_ascii=False,indent=2),encoding='utf-8')
print('UNDERGROUND_STAIR_AUTHORED',len(H['RECORDS']),'mesh groups',flush=True)
