"""Seeded cabinet contents and close-range console / record-desk construction."""
import random
VARIANT='Closed';DETAIL_SEED=930527
FILE_OPENINGS={
 'Closed':{},
 'UpperOpen':{(0,4):(.26,8),(1,1):(.09,0)},
 'LowerOpen':{(1,0):(.30,0),(0,2):(.16,5)},
}
def folder(x,y,z,w=.435,h=.255,tab=0):
 box((x,y,z),(w,.008,h),'paper',.0008)
 box((x+tab,y,z+h/2+.01),(.095,.008,.028),'paper',.0008)
 box((x,y+.008,z-.006),(w-.016,.010,h-.035),'ivory',.0005)

def drawer_body(x,front,z,w,h,depth=.46):
 box((x,front,z),(w,.022,h),'pale',.003)
 for dx in (-w/2+.006,w/2-.006):box((x+dx,front+depth/2,z-.018),(.011,depth,h-.07),'green',.0015)
 box((x,front+depth/2,z-h/2+.016),(w-.015,depth,.012),'green',.001)
 box((x,front+depth-.007,z-.018),(w-.013,.012,h-.07),'green',.001)

def files():
 shell(1.10,.60,1.95,.07);openings=FILE_OPENINGS[VARIANT]
 part('Central divider and recessed empty drawer sockets')
 box((0,-.025,1.),(.025,.56,1.80),'green',.002)
 for z in (.087,.453,.819,1.185,1.551,1.917):box((0,-.278,z),(1.044,.041,.013),'graphite',.001)
 for col,x in enumerate((-.267,.267)):
  for row in range(5):
   extension,contents=openings.get((col,row),(0,0));z=.270+row*.366;front=-.303-extension
   part(f'Drawer {col+1}-{row+1} extension {extension:.2f} contents {contents}')
   drawer_body(x,front,z,.506,.348)
   label((x,front-.014,z+.084),.097,.046,'index_'+str((col*5+row+(3 if VARIANT=='UpperOpen' else 6 if VARIANT=='LowerOpen' else 0))%10))
   handle((x,front-.016,z-.013),.176,.024,.0075);lock((x,front-.015,z-.082))
   if extension:
    for dx in (-.255,.255):
     box((x+dx,-.07,z-.09),(.013,.43,.035),'graphite',.001)
     box((x+dx,front+.16,z-.085),(.013,.30,.028),'steel',.001)
     for yy in (front+.035,front+.14):screw((x+dx,yy,z-.084),(1 if dx>0 else -1,0,0),.0028)
    for i in range(contents):folder(x,front+.042+i*.043,z+.033,.434,.255,(-.115,.09,0)[i%3])

def tapes():
 rng=random.Random(DETAIL_SEED+{'Full':1,'Sparse':2,'Empty':3}[VARIANT]);shell(1.10,.62,2.05,.075)
 part('Five rows of adjustable shelves with visible empty interiors')
 for z in (.635,.901,1.167,1.433,1.699,1.965):
  box((0,.002,z),(1.052,.584,.014),'pale',.0018)
  box((0,-.294,z-.014),(1.044,.013,.023),'green',.001)
 for x in (-.174,.174):box((x,.012,1.30),(.012,.55,1.32),'green',.0015)
 for x in (-.502,-.184,-.164,.164,.184,.502):
  box((x,.20,1.31),(.012,.012,1.25),'graphite',.0008)
  for j in range(20):screw((x,-.277,.69+j*.062),r=.0018)
 part('Storage drawers with rails and real inner pans')
 for i,z in enumerate((.212,.492)):
  extension=.22 if VARIANT=='Empty' and i==1 else .12 if VARIANT=='Sparse' and i==0 else 0
  front=-.316-extension;drawer_body(0,front,z,1.028,.272,.48)
  for x in (-.322,.322):handle((x,front-.016,z),.143,.023,.007)
  label((0,front-.017,z),.109,.048,'index_'+str(8+i));screws_rect(0,front-.018,z,.988,.228,.0035)
  if extension:
   for x in (-.509,.509):box((x,front+.15,z-.065),(.012,.30,.025),'steel',.001)
   if VARIANT!='Empty':
    for j in range(3):box((-.23+j*.17,front+.12,z-.03),(.135,.19,.14),'plastic',.002)
 part('Header with lock and archive plaque')
 box((0,-.310,2.005),(1.05,.035,.065),'pale',.002)
 plaque((-.07,-.329,2.005),.82,.028,'tape_plate',(0,-1,0));lock((.465,-.330,2.005))
 part('Seeded archive contents '+VARIANT)
 for row in range(5):
  for col,xc in enumerate((-.351,0,.351)):
   bottom=.643+row*.266
   if VARIANT=='Empty':continue
   if VARIANT=='Sparse' and (row,col) not in ((0,0),(1,2),(2,1),(3,0),(4,2)):continue
   if (VARIANT=='Full' and (row,col) in ((1,0),(2,2),(3,1))) or (VARIANT=='Sparse' and (row,col)==(3,0)):
    reel((xc-.026,-.225,bottom+.111),.107,0)
    if VARIANT=='Full':reel((xc+.113,.035,bottom+.111),.105,math.pi/2)
    continue
   count=rng.randint(5,7) if VARIANT=='Full' else rng.randint(1,3)
   shift=rng.uniform(-.025,.025) if count<5 else 0
   for i in range(count):
    start=len(g.V);xx=xc-.130+i*.039+shift;yy=-.126+rng.uniform(-.014,.020)
    box((xx,yy,bottom+.106),(.034,.285,.208),'plastic' if rng.random()<.7 else 'ivory',.0025)
    box((xx,yy-.145,bottom+.106),(.032,.009,.203),'graphite',.001)
    plaque((xx,yy-.150,bottom+.106),.024,.190,'tape_'+str(rng.randrange(12)),(0,-1,0),.0006,'ivory')
    # Small manufacturing/placement yaw variations; positions remain within the cubby.
    R=Euler((0,0,rng.uniform(-.023,.023))).to_matrix();C=Vector((xx,yy,bottom))
    for k in range(start,len(g.V)):g.V[k]=tuple(C+R@(Vector(g.V[k])-C))

def hinge(c):
 x,y,z=c
 for dz in (-.028,0,.028):lathe((x,y,z+dz-.012),(0,0,1),[(0,.009),(.023,.009)],'steel',20)
 for xx in (-.020,.020):box((x+xx,y+.005,z),(.027,.006,.078),'steel',.0015)

def writing_pad(c,angle=0,opened=False):
 """Horizontal paper with real edges, printed top, clip and a turned corner."""
 start=len(g.V);x,y,z=c
 box((0,0,0),(.255,.335,.007),'graphite',.002)
 for j in range(5):box((.001*(j%2),-.003,.004+j*.0011),(.232,.302,.001),'ivory',.00015)
 plaque((0,-.003,.0099),.229,.298,'logsheet',(0,0,1),.0004,'paper')
 box((0,.139,.015),(.075,.030,.005),'steel',.002)
 tube([(-.027,.14,.018),(-.027,.114,.023),(.027,.114,.023),(.027,.14,.018)],.0019,'steel',10)
 if opened:face([(.06,-.15,.010),(.115,-.15,.010),(.115,-.097,.014),(.098,-.112,.027)],'paper')
 transform(start,c,(0,0,angle))

def closed_binder(c,angle=0,color='green'):
 start=len(g.V)
 for z in (-.023,.023):box((0,0,z),(.24,.315,.004),color,.0015)
 box((-.118,0,0),(.006,.313,.046),color,.001)
 box((.003,0,0),(.225,.296,.040),'paper',.001)
 for z in (-.014,-.007,0,.007,.014):box((.116,0,z),(.0008,.285,.0007),'ivory',.0001)
 plaque((0,-.02,.026),.17,.115,'index_4',(0,0,1),.0005,'paper')
 transform(start,c,(0,0,angle))

_console_original=console
def console():
 _console_original()
 part('Hinged pedestal doors and service fittings')
 for x in (-.945,.945):
  for z in (.25,.61):hinge((x-.350,-.488,z))
  lock((x+.20,-.510,.51))
  label((x-.12,-.489,.652),.21,.073,'service_plate')
  vent((x,-.488,.18),.42,.065,5,False,'green')
  for yy in (-.36,.36):
   for dx in (-.32,.32):lathe((x+dx,yy,.001),(0,0,1),[(0,.027),(.012,.027),(.018,.020)],'rubber',20)
 part('Instrument surround seams legends and captive fasteners')
 slope=math.atan2(.18,.53);start=len(g.V)
 for x in (-.458,.458):
  box((x,-.014,0),(.016,.028,.55),'graphite',.001)
  for z in (-.245,.245):screw((x,-.031,z),r=.0035)
 label((-.905,-.021,-.082),.42,.034,'meter_label')
 label((.905,-.021,-.266),.46,.025,'console_plate')
 # Small engraved name strips under the button rows; distinct numbered printed tiles.
 for row in range(4):
  for col in range(4):
   xx=.640+col*.176;zz=.204-row*.087
   plaque((xx,-.019,zz-.036),.080,.012,'index_'+str((row*4+col)%10),(0,-1,0),.0004,'ivory')
 # CRT lower edge with analogue brightness control and pilot lamp.
 knob((.375,-.024,-.213),.014)
 push((-.375,-.026,-.213),.012,.012,'jade')
 transform(start,(0,.05,1.175),(-slope,0,0))
 part('Rear service lid cable tray and strain reliefs')
 box((0,.514,1.16),(1.72,.016,.36),'green',.004)
 for x in (-.82,.82):
  for z in (1.015,1.305):screw((x,.524,z),(0,1,0),.004)
 for x in (-.46,.46):box((x,.485,.38),(.07,.085,.39),'graphite',.002)
 box((0,.50,.53),(1.14,.14,.018),'green',.003)
 for x in (-.32,-.12,.12,.32):
  lathe((x,.518,1.10),(0,1,0),[(0,.020),(.012,.020),(.018,.013)],'steel',24)
  tube([(x,.535,1.10),(x,.58,1.05),(x,.58,.71),(x+.04,.56,.55)],.006,'rubber',12)
 part('Removable desktop edge trim and operators footrest')
 for x in (-1.30,1.30):
  rod((x,-.47,.792),(x,.055,.916),.006,'steel',12)
  for y in (-.47,.055):screw((x,y,.798+(y+.47)*.236),(0,0,1),.0035)
 rod((-.47,.07,.15),(.47,.07,.15),.025,'graphite',24)
 for x in (-.45,.45):rod((x,.30,.02),(x,.07,.15),.017,'steel',20)
 # Fitted slim pen rail along the front, so it does not cover the existing keyboard.
 box((0,-.478,.775),(1.03,.028,.012),'graphite',.003)
 rod((-.34,-.479,.791),(-.16,-.479,.791),.0037,'ivory',12)
 lathe((-.16,-.479,.791),(1,0,0),[(0,.0037),(.014,.0007)],'steel',12)

def desk():
 """Purpose-built archive worktable; both layouts share the same manufactured desk."""
 part('Rolled edge desktop layered panel and rear upstand')
 box((0,0,.752),(1.50,.78,.046),'green',.008)
 box((0,0,.779),(1.466,.745,.009),'graphite',.003)
 for x in (-.742,.742):box((x,0,.751),(.015,.772,.038),'steel',.003)
 box((0,.368,.810),(1.49,.018,.070),'green',.003)
 part('Tubular legs welded aprons feet and stretcher')
 for x in (-.665,.665):
  for y in (-.305,.305):
   box((x,y,.368),(.035,.035,.70),'steel',.004)
   box((x,y,.014),(.054,.054,.028),'rubber',.004)
   for zz in (.68,.71):screw((x,y-.020,zz),r=.004)
  box((x,0,.17),(.026,.61,.028),'green',.003)
  box((x,0,.715),(.030,.65,.051),'green',.003)
 box((0,.313,.19),(1.33,.027,.034),'green',.003)
 box((0,.320,.69),(1.35,.026,.078),'green',.003)
 for x in (-.635,.635):
  for y in (-.30,.30):box((x,y,.71),(.065,.069,.009),'steel',.001)
 part('Suspended stationery drawer and runners')
 box((-.32,-.01,.66),(.55,.66,.012),'graphite',.002)
 ext=.075 if VARIANT=='B' else 0;front=-.368-ext
 drawer_body(-.32,front,.671,.516,.102,.58);handle((-.32,front-.015,.668),.13,.020,.0055)
 for x in (-.577,-.063):box((x,-.025,.664),(.012,.61,.09),'green',.002)
 part('Cable grommet and mounted utility strip')
 lathe((.56,.245,.789),(0,0,1),[(0,.029),(.004,.029),(.004,.023),(.001,.023)],'rubber',32)
 tube([(.56,.245,.794),(.62,.27,.82),(.69,.39,.78),(.69,.41,.53)],.004,'rubber',12)
 box((.44,.352,.653),(.32,.044,.062),'ivory',.004)
 for x in (.34,.44,.54):
  box((x,.327,.65),(.045,.004,.041),'plastic',.003)
  for dx in (-.01,.01):box((x+dx,.324,.65),(.004,.001,.017),'rubber',.0002)
 part('In-tray folded lips and page stack')
 tx=-.44 if VARIANT=='A' else .44;ty=.135
 box((tx,ty,.795),(.32,.31,.012),'steel',.002)
 for x in (tx-.155,tx+.155):box((x,ty,.821),(.010,.305,.062),'green',.002)
 box((tx,ty+.15,.821),(.314,.010,.062),'green',.002)
 for i in range(8 if VARIANT=='A' else 2):
  box((tx+(i%3-.5)*.002,ty,.805+i*.0017),(.274,.258,.0015),'paper',.0002)
 plaque((tx,ty,.820 if VARIANT=='A' else .810),.264,.247,'logsheet',(0,0,1),.0005,'ivory')
 part('Different working paperwork arrangement '+VARIANT)
 if VARIANT=='A':
  writing_pad((.12,-.10,.793),-.10,True)
  closed_binder((.44,.16,.814),.13)
 else:
  writing_pad((-.10,-.085,.793),.15,False)
  for j in range(2):closed_binder((-.45,.14,.814+j*.053),-.08+j*.07,'green' if j==0 else 'graphite')
 # Loose pen, cap, clip and a metal stamp; all rest on the real desktop.
 rod((.32,-.23,.797),(.46,-.19,.797),.0038,'plastic',16)
 rod((.32,-.23,.797),(.304,-.235,.797),.0023,'steel',12)
 box((-.12,.235,.797),(.095,.055,.014),'steel',.003)
 lathe((-.12,.235,.804),(0,0,1),[(0,.012),(.029,.012),(.034,.026),(.050,.026)],'plastic',24)

def revision_specs():
 def produce(fn,v):
  def call():
   global VARIANT
   VARIANT=v;fn()
  return call
 specs=[]
 for v in ('Closed','UpperOpen','LowerOpen'):
  hulls=[((0,0,.975),(1.11,.64,1.95))]
  for (col,row),(extension,count) in FILE_OPENINGS[v].items():
   hulls.append((((-.267,.267)[col],-.303-extension/2,.270+row*.366),(.514,extension+.08,.348)))
  specs.append(('FileArchive_'+v,produce(files,v),hulls))
 for v in ('Full','Sparse','Empty'):
  hulls=[((0,0,1.025),(1.11,.66,2.05))]
  if v!='Full':hulls.append(((0,-.426,.492 if v=='Empty' else .212),(1.04,.26,.272)))
  specs.append(('TapeLibrary_'+v,produce(tapes,v),hulls))
 specs.append(('DispatchConsole',console,[((-.945,0,.395),(.83,.99,.79)),((.945,0,.395),(.83,.99,.79)),((0,0,.84),(2.71,1.08,.20)),((0,.25,1.18),(2.71,.58,.54))]))
 for v in ('A','B'):
  specs.append(('RecordsDesk_'+v,produce(desk,v),[((0,0,.765),(1.50,.79,.065)),((-.665,0,.37),(.055,.67,.74)),((.665,0,.37),(.055,.67,.74)),((-.32,-.03,.66),(.56,.72,.13))]))
 return specs
