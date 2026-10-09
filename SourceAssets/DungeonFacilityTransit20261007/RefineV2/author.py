"""Replace coarse portal equipment with fabricated assemblies and near-view surfaces."""
import bpy,bmesh,math,json,sys,hashlib,random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
# Execute original dimensioned construction in an isolated namespace, without its export/main.
src=(PARENT/'author.py').read_text('utf8');ctx={'__file__':str(PARENT/'author.py'),'__name__':'portal_base_recipe'}
exec(compile(src[:src.index('records=[]')],'portal_base_recipe','exec'),ctx)
g=ctx['g'];B=ctx['B'];CFG=ctx['CFG'];ATLAS=ctx['ATLAS'];TECH=json.loads((ROOT/'atlas.json').read_text('utf8'))
ROLES=json.loads((ROOT/'materials.json').read_text('utf8'));BASE='/Game/Dungeons/FacilityTransit20261007/RefineV2';OUT=ROOT/'Authored'
keep={'Signs','ThroatFloor','SampleCap','SampleSign'}
for key in list(g.G):
 if key[0]=='Hall' or key[1] not in keep:g.G.pop(key,None);g.C.pop(key,None)
def tech(key,c,w,kind='EquipmentLabels'):
 rect=TECH['rects'][key];h=w*(rect[3]-rect[1])/(rect[2]-rect[0]);group=g.group(kind);start=len(group['m']);g.printed_plate(kind,c,w,h,key,(0,-1,0),TECH,.008)
 for i in range(start,len(group['m'])):
  if group['m'][i]=='Labels':group['m'][i]='TechLabels'
def dial(key,c,r):
 x,y,z=c;rect=TECH['rects'][key];W,H=TECH['size'];points=[];uv=[]
 for i in range(96):
  a=i*math.tau/96;px=.5+.5*math.cos(a);py=.5+.5*math.sin(a);points.append((x+r*math.cos(a),y,z+r*math.sin(a)));uv.append(((rect[0]+px*(rect[2]-rect[0]))/W,1-(rect[3]-py*(rect[3]-rect[1]))/H))
 g.poly('InstrumentFaces',points,[tuple(range(96))],'TechLabels',[uv])
def plate_frame(k,c,w,h,mat='Brushed',depth=.045,rail=.032):
 x,y,z=c
 for s in (-1,1):B(k,(x+s*(w/2-rail/2),y,z),(rail,depth,h),mat)
 for s in (-1,1):B(k,(x,y,z+s*(h/2-rail/2)),(w-rail*2,depth,rail),mat)
def screws(c,w,h,r=.009):
 x,y,z=c
 for a in (-1,1):
  for b in (-1,1):g.bolt('Fasteners',(x+a*(w/2-.035),y,z+b*(h/2-.035)),(0,-1,0),r)
def case(k,c,size,paint):
 x,y,z=c;w,d,h=size
 B(k,c,size,paint,True);B(k,(x,y-d/2-.012,z),(w-.032,.024,h-.032),'Gasket')
 B(k,(x,y-d/2-.033,z),(w-.07,.025,h-.07),paint);plate_frame('CaseRims',(x,y-d/2-.044,z),w-.03,h-.03,'Brushed',.020,.010)
 for zz in (z-h*.30,z+h*.30):
  B('HingeMounts',(x-w/2+.045,y-d/2-.060,zz),(.09,.055,.13),'Brushed');g.cylinder('HingePins',(x-w/2+.056,y-d/2-.077,zz-.065),(x-w/2+.056,y-d/2-.077,zz+.065),.018,'Brushed',32)
 for zz in (z-h*.27,z+h*.27):
  g.cylinder('QuarterTurns',(x+w/2-.076,y-d/2-.070,zz),(x+w/2-.076,y-d/2-.08,zz),.018,'Brushed',24);B('QuarterTurnSlots',(x+w/2-.076,y-d/2-.085,zz),(.02,.008,.004),'Graphite')
def clamp(c,axis,r):
 g.ring('PipeClamps',c,axis,r+.027,r+.005,.055,'Brushed',48)
 x,y,z=c;B('PipeAnchors',(x,-.106,z),(.18,.06,.20),'Graphite');g.cylinder('PipeAnchors',(x,-.13,z),(x,y+.02,z),.027,'Brushed',24);screws((x,-.142,z),.18,.20,.007)
def gland(c,axis,r):
 g.lathe('CableGlands',c,axis,[(0,r*1.24),(.018,r*1.24),(.022,r*1.06),(.05,r*1.06),(.061,r*.80),(.10,r*.78)],'Brushed',48)
 g.lathe('GlandBoot',Vector(c)+Vector(axis)*.09,axis,[(0,r*.8),(.04,r*.73),(.09,r*.55)],'Gasket',48)
def gauge(c,r=.19):
 x,y,z=c;g.lathe('GaugeHousing',(x,y+.11,z),(0,-1,0),[(0,r*.88),(.08,r),(.14,r),(.154,r*.96)],'Brushed',96)
 g.ring('GaugeSeal',(x,y-.047,z),(0,-1,0),r*.955,r*.86,.012,'Gasket',96);dial('gauge',(x,y-.056,z),r*.858)
 g.beam('GaugeNeedle',(x+.07*r,y-.062,z-.07*r),(x-r*.42,y-.062,z+r*.48),.010,.008,'Graphite');g.cylinder('GaugePivot',(x,y-.062,z),(x,y-.076,z),.017,'Brushed',32)
def bent_handle(c,width=.20,height=.30):
 x,y,z=c;g.rounded_pipe('Handles',[(x-width/2,y+.05,z-height/2),(x-width/2,y-.08,z-height/2),(x+width/2,y-.08,z+height/2),(x+width/2,y+.05,z+height/2)],.018,'Brushed',24)

for theme in CFG['themes']:
 key=theme['id'];m=theme['code'];g.ROOM=key
 g.G.pop((key,'Signs'),None)
 ctx['sign'](key,(0,-.15,3.58),3.0)
 ctx['sign'](key+'_notice',(2.65,-.37,2.2),1.76)
 if key=='staff_living':ctx['sign']('rules',(-2.65,-.27,2.15),1.75)
 # Recessed structural body; new lining restores the exact three-metre clearance.
 for s in (-1,1):
  # Structure is behind the visible 3 m opening; it never shares a lining face.
  B('StructuralBody',(s*2.675,.18,2.7),(2.25,.36,5.4),'Concrete',True)
  B('StructuralBody',(s*1.70,2.035,1.4),(.30,3.93,2.8),'Concrete',True)
  # Fabricated hollow-section frame, step/reveal and rolled seal.
  B('FramePosts',(s*1.595,-.17,1.4),(.19,.48,2.8),m,True)
  B('FrameReveals',(s*1.602,-.427,1.42),(.164,.034,2.68),'Graphite')
  B('FrameFaces',(s*1.608,-.452,1.42),(.146,.026,2.65),m)
  g.cylinder('FrameSeals',(s*1.511,-.407,.05),(s*1.511,-.407,2.755),.009,'Gasket',24)
  B('FrameFeet',(s*1.64,-.17,.032),(.27,.56,.064),'Brushed',True)
  for zz in (.24,1.40,2.58):g.bolt('Fasteners',(s*1.625,-.470,zz),(0,-1,0),.012)
  # Four folded panels sit over a continuous shadow recess, separated by real joints.
  B('PanelBacking',(s*2.73,-.045,2.25),(2.12,.07,4.27),'Graphite')
  for z0,z1 in ((.54,1.38),(1.394,2.40),(2.414,3.30),(3.314,4.37)):
   B('FacadePanels',(s*2.73,-.102,(z0+z1)/2),(2.09,.046,z1-z0),m)
   for xx in (s*1.73,s*3.72):
    for zz in (z0+.065,z1-.065):g.bolt('Fasteners',(xx,-.132,zz),(0,-1,0),.007)
  B('Kickplates',(s*2.73,-.139,.277),(2.09,.024,.49),'Brushed');screws((s*2.73,-.158,.277),2.09,.49,.007)
  for y in (.579,1.553,2.527,3.501):
   B('PassagePanels',(s*1.51,y,1.66),(.02,.958,2.08),'Ivory' if key in ('medical','staff_living','ecology') else 'Graphite')
   B('PassageKickplate',(s*1.51,y,.28),(.02,.958,.5),'Brushed')
  for z in (.60,2.74):B('PassageReveals',(s*1.495,2.04,z),(.016,3.88,.028),m)
  B('LiningBacker',(s*1.535,2.035,1.4),(.012,3.93,2.8),'Gasket')
  B('EntryReturns',(s*1.515,.084,1.4),(.03,.028,2.8),'Brushed')
 B('StructuralBody',(0,.18,4.23),(3.1,.36,2.34),'Concrete',True)
 # Front frame ends at y=.07. Throat ceiling starts at this boundary, not y=0.
 B('Throat',(0,2.035,2.93),(3.56,3.93,.26),'Concrete',True)
 B('Throat',(0,2,-.17),(3.56,4,.3),'Concrete',True)
 B('FrameHeader',(0,-.17,2.873),(3.38,.48,.146),m,True);B('FrameHeader',(0,-.448,2.89),(3.37,.036,.11),'Graphite')
 B('CanopyCassette',(0,-.38,4.54),(7.6,.90,.28),m);B('CanopySeams',(0,-.837,4.54),(7.50,.017,.016),'Gasket')
 B('CanopyUnderside',(0,-.40,4.390),(7.48,.79,.022),'Graphite')
 B('LampHousing',(0,-.52,4.361),(3.62,.27,.056),'Brushed');B('Diffusers',(0,-.52,4.322),(3.45,.205,.021),'Glow')
 for x in (-3.65,3.65):screws((x,-.845,4.54),.19,.22,.008)
 for y in (1,3):
  B('TunnelFixtures',(0,y,2.718),(1.35,.28,.11),'Brushed');B('TunnelFixtures',(0,y,2.654),(1.29,.235,.018),'Gasket');B('Diffusers',(0,y,2.640),(1.24,.20,.018),'Glow')
  for x in (-.63,.63):g.bolt('Fasteners',(x,y,2.647),(0,0,-1),.007)
 # Remount main signs just proud of the facade; preserve their original aspect and artwork.
 for x in (1.90,3.40):B('NoticeMounts',(x,-.235,2.2),(.05,.22,.48),'Brushed')
 tech('serial',(-2.72,-.142,.38),.55)
 if key=='freight':
  for s in (-1,1):
   for x in (s*1.98,s*3.49):
    B('BumperMount',(x,-.20,.77),(.27,.13,1.32),'Brushed',True)
    # Extruded D-profile rubber buffer, rounded front silhouette.
    outline=[(x-.105,-.275),(x+.105,-.275)]+[(x+math.cos(a)*.105,-.285-math.sin(a)*.14) for a in [i*math.pi/24 for i in range(25)]]
    g.prism('DockBuffers',outline,.18,1.38,'Gasket',True)
    for z in (.38,.86,1.23):
     g.cylinder('BufferFixings',(x,-.415,z),(x,-.446,z),.027,'Brushed',24);g.bolt('BufferFixings',(x,-.45,z),(0,-1,0),.014)
   for z in (1.64,3.28,4.16):
    B('DockReinforcement',(s*2.73,-.181,z),(2.05,.09,.085),'Brushed');screws((s*2.73,-.231,z),1.97,.17,.012)
  case('ShutterDrive',(-2.75,-.37,2.5),(.65,.45,.86),m)
  g.cylinder('DriveCover',(-2.75,-.642,2.50),(-2.75,-.666,2.50),.19,'Graphite',64);g.ring('DriveCover',(-2.75,-.671,2.50),(0,-1,0),.198,.174,.015,'Brushed',64)
  for x in (-1.25,0,1.25):
   g.cylinder('ShutterAxle',(x-.25,.54,3.17),(x+.25,.54,3.17),.18,'Brushed',48)
  B('ShutterCassette',(0,.60,3.19),(3.32,.52,.50),'Graphite')
  for i in range(7):B('ShutterSlats',(0,.329,2.98+i*.061),(3.20,.032,.048),'Brushed')
  g.rounded_pipe('DriveConduit',[(-2.75,-.26,2.92),(-2.75,-.26,4.13),(0,-.26,4.13),(0,.60,3.47)],.025,'Gasket',24)
  tech('load',(-2.75,-.151,1.78),.76)
 elif key=='medical':
  for s in (-1,1):
   for i in range(7):
    for j in range(8):B('GlazedTiles',(s*(1.715+(i+.5)*.288),-.151,.61+(j+.5)*.303),(.282,.023,.297),'Porcelain')
  case('HEPAHousing',(-2.73,-.34,3.67),(1.63,.39,.82),'Ivory');plate_frame('FilterFrame',(-2.73,-.587,3.70),1.40,.47,'Brushed',.03,.045)
  B('FilterRecess',(-2.73,-.570,3.70),(1.35,.02,.42),'Graphite')
  for i in range(24):B('FilterFins',(-3.37+i*.055,-.612,3.70),(.025,.054,.37),'Brushed')
  for z in (3.59,3.70,3.81):B('FilterGuard',(-2.73,-.645,z),(1.32,.015,.012),'Brushed')
  tech('filter',(-2.73,-.586,3.38),.80)
  case('HygieneDispenser',(-2.73,-.29,1.76),(.40,.25,.53),'Ivory')
  B('DispenserLevel',(-2.73,-.467,1.82),(.047,.014,.19),'Graphite')
  g.rounded_pipe('DispenserSpout',[(-2.73,-.31,1.50),(-2.73,-.53,1.50),(-2.73,-.53,1.44)],.014,'Brushed',24)
  B('DispenserPump',(-2.73,-.48,1.58),(.22,.04,.06),'Brushed')
  B('DripTray',(-2.73,-.38,1.30),(.47,.43,.04),'Brushed');plate_frame('TrayLips',(-2.73,-.606,1.34),.47,.10,'Brushed',.018,.018)
  for i in range(8):B('DripGrid',(-2.93+i*.055,-.40,1.326),(.02,.33,.012),'Graphite')
  tech('wash',(-2.73,-.181,2.28),1.16)
 elif key=='treatment':
  for s in (-1,1):
   # Each heat shield has a real frame and open diagonal ventilation blades.
   for x in (s*2.03,s*2.70,s*3.37):
    plate_frame('HeatShieldFrames',(x,-.21,1.84),.59,2.10,'Graphite',.12,.045)
    for i in range(16):B('HeatShieldLouvres',(x,-.23,.88+i*.123),(.48,.12,.068),'Brushed')
   g.lathe('Bollards',(s*1.95,-.70,0),(0,0,1),[(.01,.18),(.08,.18),(.10,.118),(.95,.118),(1.05,.108),(1.095,.065),(1.105,0)],'SafetyYellow',64,True)
   for z in (.32,.69):g.ring('BollardBands',(s*1.95,-.70,z),(0,0,1),.119,.113,.13,'Graphite',64)
  g.rounded_pipe('ExtractElbow',[(-2.73,-.50,3.15),(-2.73,-.50,4.92),(-2.73,3.65,4.92)],.24,'Brushed',64)
  for z in (3.33,4.03,4.66):
   g.flange('DuctFlanges',(-2.73,-.50,z),(0,0,1),.24,12)
   B('DuctBracket',(-2.73,-.13,z),(.66,.06,.16),'Graphite');screws((-2.73,-.167,z),.66,.16,.01)
  g.lathe('ExtractInlet',(-2.73,-.50,3.18),(0,0,-1),[(0,.24),(.10,.24),(.22,.34),(.25,.34)],'Brushed',64)
  for i in range(9):B('InletGrille',(-3.0+i*.067,-.50,2.919),(.021,.50,.012),'Graphite')
  tech('hot',(-2.73,-.76,3.85),.84);tech('ppe',(-2.73,-.311,2.41),.90)
 elif key=='staff_living':
  for s in (-1,1):
   for i in range(14):B('TimberPanels',(s*(1.785+i*.144),-.179,1.30),(.136,.07,1.82),'Wood')
   for z in (.38,2.23):B('TimberMouldings',(s*2.73,-.226,z),(2.04,.08,.065),'Wood')
   B('SconcePlate',(s*2.73,-.172,3.15),(.22,.08,.74),'Brushed')
   for z in (2.95,3.38):g.cylinder('SconceArms',(s*2.73,-.21,z),(s*2.73,-.37,z),.018,'Brushed',32)
   g.lathe('SconceShade',(s*2.73,-.37,2.89),(0,0,1),[(0,.09),(.035,.11),(.46,.11),(.49,.09)],'Glow',64)
   for z in (2.89,3.38):g.lathe('SconceCaps',(s*2.73,-.37,z),(0,0,1),[(0,.113),(.026,.113),(.036,.088)],'Brushed',64)
  # Existing rules plate remains readable; trim surrounds it without a duplicate print face.
  plate_frame('NoticeFrame',(-2.65,-.260,2.15),1.83,.865,'Wood',.07,.045)
  for x in (-3.32,-2.72,-2.12):
   case('MailSlots',(x,-.28,.91),(.51,.22,.43),'Graphite');B('MailSlotRecess',(x,-.45,1.01),(.36,.022,.033),'Gasket');B('MailSlotBrow',(x,-.466,1.04),(.40,.054,.032),'Brushed');g.cylinder('MailLock',(x+.12,-.455,.83),(x+.12,-.466,.83),.018,'Brushed',24)
  tech('keys',(-2.72,-.258,1.37),1.25)
  B('KeyRail',(-2.72,-.26,1.55),(1.7,.075,.055),'Brushed')
  for i in range(6):
   x=-3.42+i*.28;g.rounded_pipe('KeyHooks',[(x,-.30,1.55),(x,-.43,1.55),(x,-.45,1.61)],.007,'Brushed',16)
   if i%2==0:g.torus('KeyRings',(x,-.436,1.515),(0,1,0),.034,.004,'Brushed',32,8);B('KeyTags',(x,-.436,1.455),(.045,.009,.058),'Ivory')
 elif key=='ecology':
  for x,r in [(-3.39,.085),(-2.98,.052)]:
   g.rounded_pipe('WaterRisers',[(x,3.7,.55),(x,-.36,.55),(x,-.36,4.98),(x,3.7,4.98)],r,'EC',48)
   for z in (.90,3.55,4.60):g.flange('WaterFlanges',(x,-.36,z),(0,0,1),r,8)
   for z in (.30,2.7,4.35):clamp((x,-.36,z),(0,0,1),r)
  g.lathe('ValveBody',(-3.39,-.36,1.18),(0,0,1),[(0,.088),(.05,.118),(.13,.14),(.25,.14),(.32,.118),(.38,.088)],'Brushed',64)
  g.lathe('ValveGland',(-3.39,-.39,1.38),(0,-1,0),[(0,.09),(.12,.09),(.17,.058),(.26,.05)],'Brushed',48)
  g.torus('ValveWheel',(-3.39,-.72,1.38),(0,1,0),.215,.023,'SafetyRed',64,16)
  for i in range(5):
   a=i*math.tau/5;g.beam('ValveSpokes',(-3.39,-.72,1.38),(-3.39+.203*math.cos(a),-.72,1.38+.203*math.sin(a)),.026,.022,'SafetyRed')
  g.bolt('ValveNut',(-3.39,-.75,1.38),(0,-1,0),.024)
  # Gauge has a connected pressure takeoff, graduated dial and raised physical needle.
  g.rounded_pipe('GaugeTakeoff',[(-2.98,-.36,2.18),(-2.38,-.36,2.18),(-2.38,-.36,2.43)],.014,'Brushed',24)
  gauge((-2.38,-.35,2.64),.20)
  case('Flowmeter',(-2.30,-.255,1.60),(.49,.21,.87),'Ivory');tech('flow',(-2.30,-.42,1.64),.36)
  for z in (1.165,2.04):gland((-2.30,-.255,z),(0,0,-1 if z<1.5 else 1),.03)
  g.rounded_pipe('MeterReturn',[(-2.30,-.255,1.01),(-2.30,-.255,.79),(-2.98,-.36,.79)],.019,'Gasket',24)
  tech('supply',(-3.39,-.478,3.18),.37);tech('return',(-2.98,-.435,3.18),.37);tech('valve',(-3.28,-.17,1.96),.60)
 elif key=='power':
  B('CabinetBacking',(-2.73,-.17,2.17),(1.99,.08,3.06),'Graphite');screws((-2.73,-.220,2.17),1.94,3.00,.016)
  case('IsolatorCabinet',(-2.73,-.39,1.79),(1.56,.40,1.72),'PW')
  tech('switch',(-2.73,-.646,2.35),1.05);tech('danger',(-2.73,-.646,1.13),.98)
  g.cylinder('HandleBezel',(-2.73,-.66,1.73),(-2.73,-.705,1.73),.225,'Graphite',96);dial('switchdial',(-2.73,-.71,1.73),.206)
  g.lathe('HandleHub',(-2.73,-.718,1.73),(0,-1,0),[(0,.10),(.025,.10),(.045,.079),(.064,.079)],'SafetyRed',64)
  B('MouldedGrip',(-2.73,-.829,1.80),(.085,.078,.31),'SafetyRed');B('GripInset',(-2.73,-.873,1.82),(.049,.018,.18),'Gasket')
  for x in (-3.21,-2.73,-2.25):
   # Insulators are bolted onto the enclosure, with smooth curved sheds and terminal collars.
   B('BushingFoot',(x,-.36,2.678),(.23,.23,.052),'Brushed');gland((x,-.36,2.697),(0,0,1),.067)
   profile=[(0,.057),(.03,.06)]
   for j in range(5):
    for k in range(13):
     t=k/12;profile.append((.032+j*.079+t*.079,.055+.043*math.sin(math.pi*t)**1.5))
   profile.extend([(.437,.057),(.458,.052)])
   g.lathe('PorcelainBushings',(x,-.36,2.79),(0,0,1),profile,'Porcelain',80)
   gland((x,-.36,3.248),(0,0,1),.055)
   B('TerminalClamp',(x,-.36,3.36),(.115,.095,.035),'Brushed')
   for dx in (-.04,.04):g.bolt('TerminalBolts',(x+dx,-.36,3.38),(0,0,1),.009)
   g.rounded_pipe('PowerCables',[(x,-.36,3.42),(x,-.36,4.97),(x,3.8,4.97)],.029,'Gasket',32)
   for z in (3.73,4.10,4.54):g.ring('CableFerrules',(x,-.36,z),(0,0,1),.033,.029,.054,'Brushed',32)
  g.tray((-3.45,-.36),(-2.01,-.36),4.86,.48)
  for x in (-3.28,-2.20):
   B('TraySupports',(x,-.125,4.79),(.16,.05,.24),'Brushed');g.cylinder('TraySupports',(x,-.16,4.78),(x,-.36,4.78),.018,'Brushed',24)
  for j,z in enumerate((1.02,.98)):g.rounded_pipe('CabinetConduit',[(-3.14+j*.80,-.38,z),(-3.14+j*.80,-.38,.71),(-3.50+j*1.0,-.38,.71)],.021,'Gasket',24)

# Use the established export path, with four-segment edge radii and physically scaled UVs.
materials={}
for k,r in ROLES.items():
 mtl=bpy.data.materials.new('FT2_'+k);mtl.use_nodes=True;p=mtl.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*r['basecolor_linear'],1);p.inputs['Roughness'].default_value=r.get('roughness',.5);p.inputs['Metallic'].default_value=r.get('metallic',0);materials[k]=mtl
out=src[src.index('records=[]'):src.index('# Accepted native breakable glass recipe')]
out=out.replace("name='SM_FT_'","name='SM_FT2_'").replace("'FT_'+r","'FT2_'+r")
out=out.replace("mod.width=.0025;mod.segments=2","mod.width=.004 if kind in ('IsolatorCabinet','HEPAHousing','FramePosts','CanopyCassette','HygieneDispenser','MouldedGrip','ShutterDrive') else .0015;mod.segments=4")
out=out.replace("coords[j] if coords else", "coords[j] if role in ('Labels','TechLabels') and coords else (coords[j][0]/s,coords[j][1]/s) if coords else")
out=out.replace("kind not in ('Signs','SampleSign','Diffusers')","kind not in ('Signs','SampleSign','Diffusers','EquipmentLabels','InstrumentFaces')")
exec(compile(out,'refined_portal_export','exec'),globals())
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SixPortal_DetailV2.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,tests_run=False,rendered=False),indent=2),encoding='utf8')
print('REFINED_SIX_PORTALS_EXPORTED',len(records),flush=True)
