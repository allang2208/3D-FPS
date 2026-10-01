"""Precise structural modelling; existing project surfaces and props remain shared."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent;PROJECT=SCRIPT.parents[2]
# Reuse stable industrial modelling functions without executing the station layout.
src=(PROJECT/'SourceAssets/DungeonFlueGasStation20261001/Scripts/author_station.py').read_text('utf-8').split('# Concrete shell, real construction joints')[0]
src=src.replace("CFG['ue_base']+'/RefineV2/Materials/M_FlueGas_Labels_V2'","CFG['ue_base']+'/Materials/M_CargoWarehouse_Labels'")
exec(compile(src,'warehouse_shared_geometry','exec'))
ROOM['height_m']=8.5
exec(compile((SCRIPT/'refined_details.py').read_text('utf-8'),'warehouse_refined_details','exec'))

# Main shell and opposing, offset entrance/exit necks. Only two exterior openings.
paving(-15,-14,15,14)
wall_segment((-15,-14),(15,-14),8.5,tiles=False)
wall_segment((15,-14),(15,14),8.5,[dict(center=19,width=3,height=2.8)],tiles=False)
wall_segment((15,14),(-15,14),8.5,tiles=False)
wall_segment((-15,14),(-15,-14),8.5,[dict(center=23,width=4.2,height=4.5)],tiles=False)
box('Roof',(0,0,8.68),(30.28,28.28,.36),'Concrete')
for side,y,width in [(-1,-9,4.4),(1,5,4.0)]:
    a,b=sorted((side*15,side*17));paving(a,y-width/2,b,y+width/2)
    for yy in (y-width/2,y+width/2):wall_segment((a,yy),(b,yy),4.85,tiles=False)
    wall_segment((side*17,y-width/2),(side*17,y+width/2),4.85,[dict(center=width/2,width=3,height=2.8)],tiles=False)
    box('Roof',((a+b)/2,y,5.0),(2.28,width+.28,.3),'Concrete')
    if CFG.get('phase')=='subject':box('SamplePortCaps',(side*17,y,1.4),(.15,3,2.8),'PaintedSteel')
# Structural steel bents, wide flange sections and real column feet.
for y in (-12.7,-6,1,8,13):
    for x in (-14.55,14.55):
        box('Columns',(x,y,4.0),(.18,.23,8.0),'PaintedSteel')
        for xx in (-.17,.17):box('Columns',(x+xx,y,4.0),(.045,.48,8.0),'PaintedSteel')
        box('Columns',(x,y,.04),(.63,.76,.08),'BareSteel')
        for dx in (-.23,.23):
            for dy in (-.29,.29):detail.fastener((x+dx,y+dy,.086),(0,0,1),.026,'Hardware')
    for z in (7.55,8.12):box('RoofRibs',(0,y,z),(29.1,.42,.06),'PaintedSteel')
    box('RoofRibs',(0,y,7.84),(29.1,.045,.52),'PaintedSteel')
    for x in (-14.55,14.55):beam('RoofRibs',(x,y,6.2),(x+(-1 if x>0 else 1)*1.8,y,7.55),.1,.12,'PaintedSteel')
# Dock is raised 1.2 m; a side stair at each end and a central roller transfer lip.
box('Dock',(0,11.35,.6),(29.0,4.7,1.2),'Concrete')
box('DockEdge',(0,8.985,1.12),(29,.055,.16),'BareSteel')
for x in (-5.5,0,5.5):box('DockBumpers',(x,8.89,.65),(.5,.18,.65),'Rubber')
for x in (-10,10):
    start=6.28
    for i in range(8):
        top=(i+1)*.15;y=start+(i+.5)*.34
        box('StairTreads',(x,y,top/2),(1.9,.34,top),'Concrete')
        box('Nosing',(x,y-.155,top+.004),(1.86,.025,.008),'Yellow')
    for side in (-1,1):railings((x+side*.98,start+.17,.15),(x+side*.98,8.83,1.2),'StairRails')
for a,b in [(-14.5,-11.03),(-8.97,-1.3),(1.3,8.97),(11.03,14.5)]:railings((a,9.04,1.2),(b,9.04,1.2))
# Heavy shelving hugs side walls; triangulated end bracing and replaceable deck tiers.
for rack in CFG['racks']:
    starts={k:len(v['v']) for k,v in G.items()}
    x,y,z=rack['position'];w=rack['width'];dep=rack['depth'];h=rack['height']
    for dx in (-dep/2,dep/2):
        for dy in (-w/2,w/2):
            xx=x+dx;yy=y+dy
            box('Racks',(xx,yy,h/2),(.065,.08,h),'PaintedSteel')
            box('Racks',(xx,yy,.015),(.2,.22,.03),'BareSteel')
            for zz in (.3,1.3,2.3,3.3,4.3):
                detail.fastener((xx+(.04 if x<0 else -.04),yy,zz),(1 if x<0 else -1,0,0),.011,'RackHardware')
    for dy in (-w/2,w/2):
        for zi in (0,1,2):
            beam('RackBraces',(x-dep/2,y+dy,.2+zi*1.45),(x+dep/2,y+dy,1.65+zi*1.45),.025,.045,'BareSteel')
    for zz in (.20,1.83,3.46):
        box('RackDecks',(x,y,zz-.025),(dep-.10,w-.08,.05),'BareSteel')
        for dx in (-dep/2,dep/2):box('Racks',(x+dx,y,zz-.08),(.08,w,.14),'Yellow')
    # Impact protection separated from the upright, firmly attached to the slab.
    front=x+(dep/2+.15)*(1 if x<0 else -1)
    for dy in (-w/2,w/2):
        box('RackGuards',(front,y+dy,.28),(.15,.18,.56),'Yellow')
        box('RackGuards',(front,y+dy,.018),(.28,.3,.036),'BareSteel')
    angle=math.radians(rack.get('yaw_blender',0));co,si=math.cos(angle),math.sin(angle)
    if angle:
        for k,g in G.items():
            for vi in range(starts.get(k,0),len(g['v'])):
                px,py,pz=g['v'][vi];dx,dy=px-x,py-y
                g['v'][vi]=(x+dx*co-dy*si,y+dx*si+dy*co,pz)
# Connected bridge, sheave block, swivel and forged safety hook.
build_hoist()
# Transfer roller table terminates at the central dock opening, no unsupported floating parts.
for x in (-.74,.74):box('RollerFrame',(x,9.25,1.43),(.09,3.35,.16),'PaintedSteel')
for y in (7.7,8.5,9.3,10.1,10.85):
    base=1.2 if y>=9 else 0
    for x in (-.69,.69):box('RollerFrame',(x,y,(base+1.44)/2),(.07,.07,1.44-base),'PaintedSteel')
for i in range(21):
    y=7.72+i*.15;lathe('Rollers',(-.69,y,1.50),(1,0,0),[(0,.056),(1.38,.056)],'BareSteel',20)
build_floor_markings()
# Fixed signage belongs on solid wall faces, outside the entrance/exit apertures.
plate('Signs',(0,-13.83,3.6),3.5,1.1,'Main',(0,1,0))
plate('Signs',(-14.82,-9,5.1),2.3,.72,'Entry',(1,0,0))
plate('Signs',(14.82,5,3.5),1.9,.60,'Exit',(-1,0,0))
plate('Signs',(-3.0,9.0,2.95),1.5,.47,'Dock',(0,-1,0))
for x in (-3.55,-2.45):box('SignSupports',(x,9.05,2.2),(.045,.045,2.0),'BareSteel')
for side in (-1,1):plate('Signs',(side*14.81,0,5.4),1.8,.56,'RackW' if side<0 else 'RackE',(-side,0,0))
plate('Signs',(2,10.50,7.23),1.05,.28,'Hoist',(0,-1,0))
# Tray and conduit live below the ceiling, clear of beams; end plates seal pipe sections.
for x in (-10,10):
    for yy in range(-12,14,2):beam('CableTrays',(x-.25,yy,7.25),(x+.25,yy,7.25),.035,.035,'BareSteel')
    for dx in (-.25,.25):box('CableTrays',(x+dx,0,7.25),(.035,26,.08),'BareSteel')
    for dx in (-.12,0,.12):detail.tube('CableTrays',[(x+dx,-13,7.29),(x+dx,13,7.29)],.025,'Rubber',12)
for light in CFG['lights']:
    x,y,z=light['position'];ceiling=4.85 if abs(x)>15 else 8.5
    for dx in (-.28,.28):detail.tube('LampHangers',[(x+dx,y,z+.08),(x+dx,y,ceiling-.03)],.011,'BareSteel',12)
exec(compile((SCRIPT/'export_geometry.py').read_text('utf-8'),str(SCRIPT/'export_geometry.py'),'exec'))
