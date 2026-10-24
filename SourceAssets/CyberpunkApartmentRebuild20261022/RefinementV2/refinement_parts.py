"""Screenshot-driven apartment revision. All dimensions metres, Blender axes.
Carcasses have real separate panels, backs and shelves; moving parts are never
baked into a closed solid. Native scene containers own opening and inventory.
"""
import math,json
from pathlib import Path

def apply_refinement(e):
 g=e['g'];B=e['B'];rb=e['roundbox'];pipe=e['pipe'];ring=e['ring'];text=e['text']
 place=e['place'];world=e['world'];placements=e['placements'];ROOT=e['ROOT'];rooms=e['ROOMS']
 containers=[]
 def retire(key):
  g.G.pop(('Apartment',key),None);g.C.pop(('Apartment',key),None)
  e['world_meshes'].discard(key);e['no_collision'].discard(key);e['glass_groups'].discard(key)
 def remove(labels=(),keys=()):placements[:]=[p for p in placements if p['label'] not in labels and p['key'] not in keys]
 def instance(label,body,front,p,yaw=0,hinge=(0,0,0),motion='Swing',travel=.30,caption='储物柜',room=''):
  containers.append(dict(id='Apartment.'+label,label=label,body=body,front=front,p=list(p),yaw=yaw,
    hinge=list(hinge),motion=motion,travel=travel,caption=caption,room=room,opening_duration=.65,
    opened_yaw=102.,storage_pages=1,initial_open_fraction=0.))
 def transform(p,local,yaw):
  a=math.radians(yaw);co,si=math.cos(a),math.sin(a)
  return (p[0]+local[0]*co-local[1]*si,p[1]+local[0]*si+local[1]*co,p[2]+local[2])

 # Door audit: five open portals had wall/reveal faces at exactly equal planes.
 # A real U-section reveal replaces the old embedded box; its jambs meet its
 # header end-to-end, and its returns meet the throat without overlapping faces.
 retire('OpenPortalTrim');world('OpenPortalTrim',False)
 portals=[('Living',6.825,8.25,12.,3.025),('Kitchen',8.475,6.625,9.875,3.025),
          ('Foyer',8.475,11.75,13.05,3.025),('Laundry',8.475,1.375,2.75,3.025),
          ('Service',8.475,4.35,5.725,3.025)]
 for label,y,a,b,h in portals:
  k='OpenPortalTrim';t=.018;face=.024;lip=.050;depth=.15
  for x,s in ((a,1),(b,-1)):
   B(k,(x+s*t/2,y,(h-t)/2),(t,depth,h-t),'Dark')
   for sign in (-1,1):B(k,(x+s*(t-lip)/2,y+sign*(depth+face)/2,(h-t)/2),(lip+t,face,h-t),'Teal')
  B(k,((a+b)/2,y,h-t/2),(b-a,depth,t),'Dark')
  for sign in (-1,1):
   B(k,((a+b)/2,y+sign*(depth+face)/2,h+(lip-t)/2),(b-a+lip*2,face,lip+t),'Teal')
  B(k,((a+b)/2,y-.103,h+.013),(b-a-.06,.008,.012),'Cyan')
 retire('Thresholds');world('Thresholds',False)
 for d in e['DOORS']:
  size=(d['width']+.09,.55,.006) if d['yaw']==90 else (.55,d['width']+.09,.006)
  B('Thresholds',(d['p'][0],d['p'][1],.015),size,'Steel')
  k='Door_'+d['name']+'_Frame';retire(k);w,h=d['width'],d['height']
  for sign in (-1,1):
   rb(k,(0,sign*(w/2+.035),h/2),(.206,.07,h),'Dark',.006,col=True)
   B(k,(-.109,sign*(w/2+.035),h/2),(.008,.018,h-.04),'Steel')
  rb(k,(0,0,h+.045),(.226,w+.14,.09),'Dark',.006,col=True)
  B(k,(-.12,0,h+.045),(.008,w-.08,.016),'Cyan')
 for label,y,a,b,h in portals:B('Thresholds',((a+b)/2,y,.015),(b-a,.25,.006),'Steel')
 reveal_report=dict(open_portals=[dict(id=n,old_jamb_wall_clearance_mm=0,new_jamb_lining_mm=18,
     construction='U-section; throat/return/header meet at edges',clear_width_m=b-a-.036)
     for n,y,a,b,h in portals],sliding_doors=[dict(id=d['name'],post_header_joint='end-to-end',
     old_floor_threshold_offset_mm=0,new_floor_threshold_offset_mm=6) for d in e['DOORS']],
     runtime_tested=False,scope='five open portals and seven sliding-door thresholds/frames')
 (ROOT/'door_reveal_diagnosis.json').write_text(json.dumps(reveal_report,indent=2),encoding='utf8')

 # Remove the stock bookshelf, stray dining chair and doorway plant.
 remove(labels=('Living_ReadingShelf','Living_ReadingChair','Bed3_Bookcase'))
 for p in placements:
  if p['label'] in ('Planter1','Foliage1'):p['p'][:2]=[12.9,.85] # moved away from Bed2's entry and sliding pocket
  if p['label'] in ('Planter0','Foliage0'):p['p'][:2]=[6.13,.84]
  if p['label']=='Living_Sofa':p['p'][0]=7.50
  if p['label'] in ('Living_CoffeeTable','Living_Tray','Living_Magazines'):p['p'][0]=9.25
 # The former master is the room shown with the headboard in its entrance.
 placements[:]=[p for p in placements if not p['label'].startswith('Master_')]
 # The west/larger bathroom becomes the gym; the east bathroom stays functional.
 placements[:]=[p for p in placements if not p['label'].startswith('Bath2_')]
 for k in ('ShowerScreen_Bath2','ShowerTrim_Bath2','WetCladding_Bath2'):retire(k)
 for p in placements:
  if p['label']=='Laundry_Hamper':p.update(p=[.59,9.12,.867],yaw=90,scale=.72)
  # Apply neutral finishes to the original asset instances only; shared assets stay untouched.
  if p['key'] in e['REUSE'] and p['key'] not in ('Plant','Plant2','NearTower'):
   p['override'].update(dict(PaintedSteel='Teal',OlivePaint='Teal',Paint='Teal',Wood='Oak',
                             BareSteel='Steel',ServiceHardware='Steel'))
  if p['key']=='OfficeChair':p['override'].update(Fabric='Fabric',Leather='Fabric',Seam='Fabric')

 def cubby(name,w,d,h,shelves=1,drawer=False,hero=False,wall_mount=False):
  body=name+'Body';front=name+'Front';t=.024;bottom=0. if wall_mount else .09
  # Six independent construction surfaces. No opaque filler behind an opening.
  for x in (-w/2+t/2,w/2-t/2):rb(body,(x,0,(h+bottom)/2),(t,d,h-bottom),'Teal',.004,col=True)
  B(body,(0,d/2-t/2,(h+bottom)/2),(w-2*t,t,h-bottom),'CabinetInside',True)
  for z in (bottom+t/2,h-t/2):rb(body,(0,0,z),(w-2*t,d,t),'Teal',.004,col=True)
  for i in range(shelves):
   z=bottom+(h-bottom)*(i+1)/(shelves+1)
   B(body,(0,.015,z),(w-2*t-.004,d-.055,.018),'CabinetInside',True)
   B(body,(0,-d/2+.032,z),(w-2*t-.008,.012,.018),'Steel')
  if not wall_mount:
   for x in (-w/2+.055,w/2-.055):
    for y in (-d/2+.055,d/2-.055):g.cylinder(body,(x,y,0),(x,y,bottom),.020,'Dark',24)
  for x in (-w/2+.012,w/2-.012):
   B(body,(x,-d/2-.006,(h+bottom)/2),(.014,.012,h-bottom),'Steel')
  if drawer:
   # Complete tray, front, bottom, back and side boards move together.
   fw=w-.035;fh=h-bottom-.018;z=bottom+fh/2
   rb(front,(0,-d/2-.018,z),(fw,.035,fh),'Teal',.006)
   g.box(None,(0,-d/2-.018,z),(fw,.035,fh),collision=front)
   B(front,(0,0,bottom+.024),(w-.085,d-.075,.018),'CabinetInside')
   for x in (-w/2+.041,w/2-.041):B(front,(x,0,bottom+fh*.35),(.014,d-.07,fh*.6),'CabinetInside')
   B(front,(0,d/2-.044,bottom+fh*.35),(w-.095,.014,fh*.6),'CabinetInside')
   pipe(front,[(-w*.25,-d/2-.041,z+.025),(-w*.25,-d/2-.064,z+.025),
               (w*.25,-d/2-.064,z+.025),(w*.25,-d/2-.041,z+.025)],.006,'Steel')
   for x in (-w/2+.031,w/2-.031):B(body,(x,0,bottom+.05),(.012,d-.055,.025),'Steel')
   hinge=(0,0,0)
  else:
   fw=w-.035;fh=h-bottom-.016
   rb(front,(fw/2,0,bottom+fh/2),(fw,.030,fh),'Teal',.006)
   g.box(None,(fw/2,0,bottom+fh/2),(fw,.030,fh),collision=front)
   B(front,(fw/2,-.019,bottom+fh/2),(fw-.055,.008,fh-.10),'Dark')
   hx=fw-.065;hz=max(.32,min(1.15,h*.62))
   pipe(front,[(hx,-.025,hz-.09),(hx,-.048,hz-.075),(hx,-.048,hz+.075),(hx,-.025,hz+.09)],.007,'Steel')
   for z in (bottom+.085,h-.085):g.cylinder(front,(.009,.006,z-.026),(.009,.006,z+.026),.009,'Steel',32)
   hinge=(-fw/2,-d/2-.024,0)
   if hero:
    # Inset data panel, edge guard, segmented vent and two restrained status bars.
    B(front,(fw*.48,-.025,h*.72),(fw*.62,.008,.20),'Screen')
    text(front,'NODE / 09',(.06,-.032,h*.73),.030,'Cyan')
    for j in range(11):B(front,(.08+j*(fw-.17)/10,-.026,.29),(.018,.009,.095),'Steel')
    for x in (.035,fw-.035):B(front,(x,-.024,h*.52),(.009,.008,h*.50),'Cyan')
    for x in (.055,fw-.055):
     for z in (.16,h-.08):g.cylinder(front,(x,-.028,z),(x,-.032,z),.004,'Steel',12)
  return body,front,hinge
 # Replace the former solid cabinets with individually searchable bays.
 oldcab=[p for p in placements if p['key'] in ('MediaConsole','EntryCabinet','Nightstand','ServiceCabinet','Wardrobe')]
 remove(keys=('MediaConsole','EntryCabinet','Nightstand','ServiceCabinet','Wardrobe'))
 for k in ('MediaConsole','EntryCabinet','Nightstand','ServiceCabinet','Wardrobe'):retire(k)
 defs={'MediaConsole':(2.9,.45,.58,5,1,False),'EntryCabinet':(1.8,.38,.95,3,2,False),
       'Nightstand':(.48,.42,.48,1,0,True),'ServiceCabinet':(1.50,.46,1.05,3,2,False),
       'Wardrobe':(2.4,.62,2.65,4,3,False)}
 for key,(w,d,h,n,shelves,drawer) in defs.items():
  bw=w/n-.006;body,front,hinge=cubby(key+'Cell',bw,d,h,shelves,drawer)
  for p in [p for p in oldcab if p['key']==key]:
   for i in range(n):instance(p['label']+'_'+str(i+1),body,front,transform(p['p'],(-w/2+(i+.5)*w/n,0,0),p['yaw']),p['yaw'],hinge,
     'Drawer' if drawer else 'Swing',min(.33,d-.10),'床头抽屉' if drawer else '衣柜' if key=='Wardrobe' else '储物柜',p['room'])
 # Designed specifically for this apartment: two tall cybernetic archive modules.
 body,front,hinge=cubby('CyberArchive',.68,.43,1.95,3,False,True)
 for i,y in enumerate((4.08,4.80)):instance('Living_Archive_'+str(i),body,front,(5.20,y,0),90,hinge,caption='客厅智能档案柜',room='Living')
 for i,y in enumerate((2.86,3.58)):instance('Office_Archive_'+str(i),body,front,(4.53,y,0),-90,hinge,caption='办公室资料柜',room='Office')
 # Convert remaining refrigerator components to the same native container family.
 fridge=[p for p in placements if p['label'].startswith('Fridge_')];remove(labels=[p['label'] for p in fridge])
 for part in ('Lower','Upper'):
  p=next(p for p in fridge if p['label']=='Fridge_'+part+'Body')
  instance('Fridge_'+part,'Fridge'+part+'Body','Fridge'+part+'Door',p['p'],p['yaw'],(-.355,-.383,0),caption='冷藏储物格' if part=='Lower' else '冷冻储物格',room='Kitchen')

 # Rebuild kitchen storage as real carcasses. Keep the already modelled sink,
 # hob, oven, faucet and worktop, removing only their closed cabinet mass.
 retire('KitchenRun')
 k='KitchenRun';d=.65;h=.92
 for x,wid in [(-1.65,.30),(.55,2.50)]:rb(k,(x,0,h),(wid,.70,.04),'Stone',.008,col=True)
 for y in (-.30,.30):rb(k,(-1.1,y,h),(.80,.10,.04),'Stone',.006,col=True)
 B(k,(-1.1,0,.738),(.69,.47,.022),'Steel')
 for x in (-1.445,-.755):B(k,(x,0,.825),(.018,.49,.18),'Steel')
 for y in (-.245,.245):B(k,(-1.1,y,.825),(.71,.018,.18),'Steel')
 g.cylinder(k,(-1.1,0,.750),(-1.1,0,.754),.033,'Dark',48)
 for x in (-1.47,-.73):B(k,(x,0,.928),(.022,.53,.012),'Steel')
 for y in (-.265,.265):B(k,(-1.1,y,.928),(.762,.022,.012),'Steel')
 pipe(k,[(-1.1,.27,.94),(-1.1,.27,1.20),(-1.1,.24,1.26),(-1.1,.10,1.26),(-1.1,.055,1.22)],.013,'Steel',24)
 g.cylinder(k,(-.94,.27,.94),(-.94,.27,1.00),.023,'Steel',32)
 rb(k,(.9,-.02,.948),(.57,.52,.015),'Dark',.012)
 for x in (.76,1.04):
  for y in (-.15,.12):ring(k,(x,y,.956),(0,0,1),.093,.092,.001,'Steel')
 B(k,(0,.362,1.19),(3.60,.025,.51),'Stone')
 rb(k,(.9,0,.49),(.58,.64,.74),'Teal',.009,col=True)
 rb(k,(.9,-.335,.52),(.574,.045,.65),'Steel',.009)
 rb(k,(.9,-.363,.46),(.49,.012,.39),'Dark',.015)
 B(k,(.9,-.372,.46),(.43,.006,.31),'Screen')
 pipe(k,[(.69,-.38,.71),(.69,-.41,.71),(1.11,-.41,.71),(1.11,-.38,.71)],.010,'Steel')
 for x in (.73,1.07):g.cylinder(k,(x,-.374,.78),(x,-.395,.78),.025,'Dark',40)
 rb(k,(.9,.13,1.75),(.59,.44,.08),'Steel',.01)
 B(k,(.9,.23,2.18),(.29,.24,.82),'Dark')
 for j in range(11):B(k,(.68+j*.044,-.085,1.72),(.018,.26,.005),'Dark')
 for i in range(6):B(k,(-1.5+i*.6,.04,1.647),(.52,.022,.012),'Warm')
 for name,w,depth,height,shelves in [('Base',.59,.65,.88,1),('Sink',.59,.65,.70,0),('Upper',.59,.38,.94,1)]:
  b,f,hi=cubby('Kitchen'+name,w,depth,height,shelves,wall_mount=name=='Upper')
  for i in range(6):
   if i==4:continue
   if name=='Sink' and i not in (0,1):continue
   if name=='Base' and i in (0,1):continue
   pos=(8.9-1.5+i*.6,13.12+(.19 if name=='Upper' else 0),1.66 if name=='Upper' else 0)
   instance('Kitchen_'+name+'_'+str(i),b,f,pos,hinge=hi,caption='吊柜' if name=='Upper' else '厨房储物柜',room='Kitchen')

 # Clear glass panel replaces the opaque, weathered green mirror.
 remove(keys=('Mirror',))
 k='VanityClearGlass';e['glass_groups'].add(k)
 B(k,(0,0,.43),(.76,.008,.84),'Glass')
 for x in (-.392,.392):B(k,(x,.003,.43),(.020,.024,.88),'Dark')
 for z in (0.,.86):B(k,(0,.003,z),(.764,.024,.020),'Dark')
 for x in (-.32,.32):
  for z in (.06,.80):g.cylinder(k,(x,.01,z),(x,.035,z),.012,'Steel',28)
 place('Bath1_ClearGlass','VanityClearGlass',(4.08,13.53,1.20),collision=False,room='Bath1')

 # Office: proper worktop supports, monitor brackets, PC chassis and cable routing.
 k='CyberWorkstation';rb(k,(0,0,.77),(2.30,.80,.045),'Teal',.012,col=True)
 for x in (-1.02,1.02):
  for y in (-.29,.29):B(k,(x,y,.37),(.045,.055,.74),'Dark',True)
  B(k,(x,0,.055),(.075,.73,.035),'Steel')
 B(k,(0,.29,.53),(2.03,.045,.07),'Steel')
 for x in (-.59,0,.59):
  B(k,(x,.25,.97),(.035,.04,.37),'Steel')
  rb(k,(x,.21,1.28),(.56,.04,.37),'Dark',.012)
  B(k,(x,.186,1.28),(.535,.007,.342),'Screen')
  # Framed interface tracery is fine geometry, not a floating panel.
  for j in range(5):B(k,(x-.20,.181,1.18+j*.036),(.12+j*.022,.002,.004),'Cyan')
 rb(k,(0,-.18,.798),(.64,.18,.026),'Dark',.008)
 for i in range(18):
  for j in range(4):rb(k,(-.287+i*.033,-.238+j*.035,.817),(.026,.028,.008),'CabinetInside',.002,2)
 rb(k,(.48,-.18,.811),(.064,.105,.035),'Teal',.016)
 rb(k,(.85,.09,.26),(.28,.43,.48),'Dark',.014,col=True)
 B(k,(.85,-.134,.27),(.23,.012,.39),'Teal')
 for z in (.12,.28,.44):
  ring(k,(.85,-.145,z),(0,1,0),.054,.046,.008,'Steel')
  g.cylinder(k,(.85,-.15,z),(.85,-.153,z),.017,'Cyan',32)
  for j in range(8):
   a=j*math.tau/8;pipe(k,[(.85+.021*math.cos(a),-.151,z+.021*math.sin(a)),(.85+.041*math.cos(a+.35),-.151,z+.041*math.sin(a+.35))],.004,'CabinetInside',8)
 for x in (-.59,0,.59):pipe(k,[(x,.26,1.05),(x,.30,.81),(.65,.30,.805),(.78,.32,.48)],.004,'Rubber',10)
 B(k,(0,-.408,.762),(1.90,.010,.014),'Cyan')
 text(k,'NEXUS / WORKSTATION 09',(-.9,-.416,.728),.038,'Paper')
 place('Office_Workstation',k,(.80,3.05,0),90,room='Office')
 place('Office_Chair','OfficeChair',(1.92,3.05,0),-90,room='Office',override=dict(Paint='Teal',Fabric='Fabric',Leather='Fabric'))
 k='OfficeWallPanel';rb(k,(0,0,.85),(1.24,.05,1.70),'Dark',.012)
 for x in (-.52,.52):B(k,(x,-.032,.85),(.018,.009,1.5),'Cyan')
 text(k,'LOCAL NETWORK',(-.44,-.032,1.40),.08,'Paper')
 for j in range(8):
  B(k,(-.15,-.033,1.20-j*.115),(.58,.006,.008),'Steel')
  B(k,(.34,-.037,1.20-j*.115),(.04,.008,.02),'Cyan' if j%3 else 'Warm')
 place('Office_StatusWall',k,(2.52,6.71,.65),collision=False,room='Office')
 # Move the wall panel off the doorway; keep the entry axis completely empty.
 placements[-1].update(p=[.18,5.55,.65],yaw=90)

 # Compact gym: treadmill, adjustable bench and an independently supported rack.
 k='Treadmill';rb(k,(0,0,.15),(.92,1.92,.22),'Teal',.035,col=True)
 for x in (-.36,.36):
  for y in (-.72,.72):g.cylinder(k,(x,y,0),(x,y,.07),.035,'Rubber',32)
 rb(k,(0,-.03,.268),(.63,1.64,.024),'Rubber',.012)
 for x in (-.414,.414):
  rb(k,(x,-.02,.285),(.13,1.68,.035),'Dark',.010)
  for j in range(20):B(k,(x,-.78+j*.08,.305),(.095,.008,.004),'Steel')
  pipe(k,[(x,.66,.26),(x,.58,.75),(x,.47,1.12),(x,.08,1.13)],.027,'Steel',24)
  pipe(k,[(x,.40,1.13),(x,.07,1.13)],.031,'Rubber',24)
  rb(k,(x,.63,.22),(.12,.25,.09),'Dark',.016)
 rb(k,(0,.53,1.18),(.72,.23,.17),'Dark',.025)
 B(k,(0,.406,1.20),(.40,.008,.125),'Screen')
 text(k,'06.0 KM/H',(-.165,.397,1.18),.032,'Cyan')
 g.cylinder(k,(.27,.40,1.19),(.27,.39,1.19),.019,'Amber',40)
 pipe(k,[(.27,.387,1.16),(.25,.35,.95),(.18,.27,.96)],.002,'Rubber',8)
 for y in (-.77,.77):g.cylinder(k,(-.31,y,.226),(.31,y,.226),.050,'Steel',40)
 B(k,(0,-.972,.18),(.58,.006,.045),'Dark')
 text(k,'PULSE / RUN',(-.25,-.980,.16),.041,'Paper')
 place('Gym_Treadmill',k,(2.55,12.35,.036),room='Gym')
 k='TrainingBench'
 for y in (-.53,.53):
  B(k,(0,y,.035),(.60,.12,.07),'Dark',True)
  for x in (-.27,.27):rb(k,(x,y,.037),(.11,.145,.075),'Rubber',.012)
  g.beam(k,(0,y,.08),(0,y*.6,.39),.055,.07,'Steel',True)
 B(k,(0,0,.30),(.07,1.08,.09),'Teal',True)
 B(k,(0,.25,.395),(.08,.80,.10),'Teal',True)
 rb(k,(0,-.38,.475),(.40,.42,.10),'Fabric',.025,col=True)
 rb(k,(0,.25,.50),(.43,.80,.11),'Fabric',.030,col=True)
 for y in (-.52,.55):pipe(k,[(-.19,y,.50),(.19,y,.50)],.003,'Steel',8)
 for y in (.05,.18,.31,.44):B(k,(.055,y,.33),(.015,.025,.08),'Steel')
 g.cylinder(k,(-.08,.02,.36),(.12,.02,.36),.014,'Steel',32)
 pipe(k,[(.12,.02,.36),(.15,.02,.36),(.15,.02,.42)],.009,'Dark',16)
 place('Gym_Bench',k,(.75,12.12,.036),room='Gym')
 k='DumbbellRack'
 for x in (-.47,.47):
  B(k,(x,0,.32),(.04,.32,.64),'Teal',True);B(k,(x,0,.025),(.11,.43,.05),'Rubber')
 for z in (.32,.66):
  B(k,(0,0,z),(1.04,.32,.026),'Steel',True)
  for i in range(3):
   x=-.33+i*.33
   g.cylinder(k,(x,-.15,z+.088),(x,.15,z+.088),.014,'Steel',28)
   for y in (-.12,.12):
    g.lathe(k,(x,y-.035,z+.088),(0,1,0),[(0,.066),(.01,.075),(.065,.075),(.075,.066)],'Dark',12)
    g.cylinder(k,(x,y-.040,z+.088),(x,y-.042,z+.088),.028,'Steel',24)
 place('Gym_Weights',k,(.88,13.30,.036),room='Gym')
 body,front,hinge=cubby('GymLocker',.58,.39,1.32,2,False,True)
 instance('Gym_Locker',body,front,(.36,10.95,.036),90,hinge=hinge,caption='训练用品柜',room='Gym')
 k='GymDetails';world(k)
 rb(k,(1.775,12.12,.024),(3.20,2.90,.024),'Rubber',.012,col=True)
 for x in (.31,3.23):B(k,(x,12.12,.040),(.016,2.48,.006),'Cyan')
 B(k,(2.55,13.554,1.78),(.89,.035,.53),'Dark')
 B(k,(2.55,13.531,1.78),(.83,.008,.47),'Screen')
 text(k,'PULSE / TRAIN', (2.20,13.522,1.88),.064,'Cyan')
 for j in range(8):B(k,(2.22+j*.09,13.522,1.68),(.05,.008,.04+(j%4)*.028),'Steel')
 # White towel basket is now centred and supported by the washer's actual top.
 # Gray-black redesign also covers remaining bookcase in bedroom via replacement.
 body,front,hinge=cubby('BedArchive',.68,.40,1.85,3,False,True)
 instance('Bed3_Archive',body,front,(14.55,12.52,0),90,hinge,caption='卧室储物柜',room='Bed3')
 # Restore neutral overrides on all newly appended library instances.
 for p in placements:
  if p['key'] in ('OfficeChair','Chair','Sofa','CoffeeTable','DiningTable','LaundryBasket','Basin'):
   p['override'].update(dict(PaintedSteel='Teal',OlivePaint='Teal',Paint='Teal',Wood='Oak',BareSteel='Steel'))
 return dict(containers=containers,revision='20261022_RefinementV2',
   room_uses={'Master':'Office','Bath2':'Gym','Bath1':'Bathroom'},
   door_reveal_diagnosis=reveal_report,search_loot_policy='native searchable persistent storage; no dungeon-run loot binding')
