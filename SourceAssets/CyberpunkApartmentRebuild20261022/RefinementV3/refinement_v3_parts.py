"""Larger shell, an actual gym extension, wall storage and manufactured equipment."""
import math

def apply_v3(e,revision):
 g=e['g'];B=e['B'];rb=e['roundbox'];pipe=e['pipe'];ring=e['ring'];text=e['text'];place=e['place'];world=e['world']
 wall=e['wall'];retire=e['retire_mesh'];cubby=e['cubby'];instance=e['container_instance']
 placements=e['placements'];containers=revision['containers'];height=e['HEIGHT'];changed=set()
 e['v3_changed']=changed
 for name in ('OfficeUI','WorkoutUI'):
  e['MATERIALS'][name]=e['BASE']+'/Materials/M_AP_'+name
 def drop(key):retire(key);changed.add(key)
 def move(label,p,yaw=None):
  for item in placements:
   if item['label']==label:
    item['p']=list(p)
    if yaw is not None:item['yaw']=yaw
 def screen(k,c,w,h,role='OfficeUI'):
  x,y,z=c
  g.poly(k,[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)],
         [(0,1,2,3)],role,uv=[[(0,0),(1,0),(1,1),(0,1)]])
 def local(p,q,yaw):
  a=math.radians(yaw);co,si=math.cos(a),math.sin(a)
  return (p[0]+q[0]*co-q[1]*si,p[1]+q[0]*si+q[1]*co,p[2]+q[2])

 # Gym floor area: 3.25*3.35 -> 6.50*5.025, exactly three times before 1.2 scale.
 gym=(-3.10,10.25,3.40,15.275);e['ROOMS']['Bath2']=gym
 drop('Wall_West');wall('Wall_West','Y',0,0,10.10,.30)
 drop('Wall_Back');wall('Wall_Back','X',13.75,3.55,20,.30,[(11.75,13.05,2.725)])
 wall('Gym_OuterWest','Y',-3.25,10.10,15.425,.30)
 wall('Gym_OuterNorth','X',15.425,-3.25,3.55,.30)
 wall('Gym_OuterSouth','X',10.10,-3.25,-.15,.30)
 wall('Gym_OuterEast','Y',3.55,13.90,15.425,.30)
 k='Gym_CornerReturns';world(k)
 B(k,(3.475,13.825,height/2),(.15,.15,height),'Wall',True)
 B(k,(-.075,10.175,height/2),(.15,.15,height),'Wall',True)
 # Original bathroom dividing wall remains in place; the extension begins beyond it.
 k='Gym_ExtensionSlab';world(k)
 B(k,(-1.70,12.7625,-.18),(3.40,5.625,.30),'Grout',True)
 B(k,(1.70,14.5875,-.18),(3.40,1.675,.30),'Grout',True)
 k='Gym_ExtensionFloorCollision';world(k)
 B(k,(-1.625,12.7625,-.015),(3.25,5.325,.03),'Grout',True)
 B(k,(1.70,14.5875,-.015),(3.40,1.675,.03),'Grout',True)
 e['no_collision'].discard(k)
 for key in ('Floor_Bath2','Ceiling_Bath2','CeilingTrim_Bath2','GymDetails'):drop(key)
 k='Gym_Ceiling';world(k)
 B(k,(.15,12.7625,height+.09),(6.68,5.205,.18),'Ceiling',True)
 k='Gym_Floor';world(k,False)
 for ix in range(13):
  for iy in range(10):
   B(k,(-3.10+(ix+.5)*.5,10.25+(iy+.5)*.5025,.024),(.497,.4995,.024),'Rubber')
 for x in (-3.03,3.33):B(k,(x,12.7625,.039),(.012,4.87,.005),'Cyan')
 for y in (10.32,15.205):B(k,(.15,y,.039),(6.36,.012,.005),'Cyan')
 # The visible rubber surface has an independent continuous collider.
 k='Gym_MatCollision';world(k)
 B(k,(.15,12.7625,.018),(6.50,5.025,.036),'Grout',True)
 e['v3_hidden']={'Gym_ExtensionFloorCollision','Gym_MatCollision'}
 k='Gym_Fixtures';world(k,False)
 for x,y in [(-1.8,11.55),(-1.8,14.15),(1.65,14.25)]:
  rb(k,(x,y,height-.07),(1.52,.22,.10),'Dark',.012)
  B(k,(x,y,height-.125),(1.43,.16,.01),'Warm')
  e['light']('Gym_'+str(x)+'_'+str(y),[x,y,height-.135],143,16,1100,radius=420,shadow=False)
 for x in (-2.9,3.1):
  B(k,(x,15.25,1.7),(.06,.035,2.65),'Dark');B(k,(x,15.222,1.7),(.018,.012,2.5),'Cyan')
 rb(k,(1.85,15.245,1.8),(1.18,.06,.69),'Dark',.016)
 screen(k,(1.85,15.208,1.8),1.12,.63,'WorkoutUI')
 text(k,'PULSE / TRAINING LAB',(-2.5,15.245,2.60),.14,'Paper')
 for j in range(12):B(k,(-2.65+j*.14,15.245,.55),(.07,.045,.65),'Teal')
 move('Gym_Treadmill',(2.30,13.60,.036))
 move('Gym_Bench',(-.75,11.75,.036))
 move('Gym_Weights',(-.72,14.98,.036))
 for c in containers:
  if c['label']=='Gym_Locker':c.update(p=[-2.85,11.0,.036],yaw=90)
 # Treadmill / bench / weight rack retain their working proportions and gain detail.
 changed.update(('Treadmill','TrainingBench','DumbbellRack'))
 k='Treadmill';screen(k,(0,.386,1.20),.39,.12,'WorkoutUI')
 for y in (-.82,.81):
  for x in (-.39,.39):
   g.cylinder(k,(x,y,.30),(x,y,.307),.012,'Steel',20)
   B(k,(x,y,.309),(.013,.003,.003),'Dark')
 for j in range(22):B(k,(0,-.76+j*.067,.283),(.60,.0018,.0018),'CabinetInside')
 for x in (-.31,.31):ring(k,(x,.51,1.275),(0,0,1),.048,.039,.012,'Steel')
 pipe(k,[(-.39,.77,.14),(-.45,.89,.08),(-.46,1.04,.025),(-.28,1.05,.025)],.006,'Rubber',12)
 k='TrainingBench'
 for y in (-.53,.53):
  for x in (-.20,.20):g.cylinder(k,(x,y,.073),(x,y,.082),.012,'Steel',16)
 for y in (-.49,.49):pipe(k,[(-.18,y,.48),(-.18,y+.08,.49),(.18,y+.08,.49),(.18,y,.48)],.002,'Linen',8)
 text(k,'PULSE  /  320 KG',(-.16,-.60,.31),.026,'Paper')
 k='DumbbellRack'
 for z in (.32,.66):
  for x in (-.33,0,.33):
   for y in [-.06+i*.012 for i in range(11)]:ring(k,(x,y,z+.088),(0,1,0),.015,.014,.003,'Dark')
   text(k,'08' if z<.4 else '12',(x-.022,-.166,z+.066),.030,'Paper')

 # Cable trainer: twin rails, actual weight stack, pulley wheels and continuous cable.
 k='CableTrainer'
 for x in (-.54,.54):
  rb(k,(x,0,.04),(.16,1.02,.08),'Dark',.014,col=True)
  B(k,(x,.32,1.13),(.07,.08,2.18),'Teal',True)
  for z in (.22,1.07,1.96):g.cylinder(k,(x,-.16,z),(x,.37,z),.014,'Steel',20)
 B(k,(0,.32,2.20),(1.16,.10,.10),'Teal',True)
 for x in (-.18,.18):g.cylinder(k,(x,.28,.12),(x,.28,2.08),.012,'Steel',24)
 for i in range(15):
  rb(k,(0,.28,.15+i*.045),(.52,.29,.040),'Dark',.006,col=i in (0,14))
  B(k,(.245,.125,.15+i*.045),(.035,.010,.012),'Paper')
 pipe(k,[(.0,.125,.48),(.0,-.015,.48),(.06,-.015,.48)],.010,'Amber',16)
 for x in (-.54,.54):
  for z in (.24,1.72,2.12):
   ring(k,(x,.20,z),(1,0,0),.068,.052,.028,'Dark')
   g.cylinder(k,(x-.025,.20,z),(x+.025,.20,z),.014,'Steel',20)
  pipe(k,[(x,.20,.27),(x,.20,2.17),(x,.11,2.18),(x,.10,1.73),(x,-.19,1.73),(x,-.34,1.44)],.004,'Rubber',12)
  pipe(k,[(x,-.34,1.44),(x-.11,-.35,1.30),(x+.11,-.35,1.30),(x,-.34,1.44)],.012,'Steel',16)
  pipe(k,[(x-.085,-.35,1.30),(x+.085,-.35,1.30)],.017,'Rubber',20)
  for z in [.45+i*.10 for i in range(13)]:g.cylinder(k,(x,-.046,z),(x,-.050,z),.006,'Dark',16)
 pipe(k,[(-.52,.24,2.24),(-.39,.04,2.30),(.39,.04,2.30),(.52,.24,2.24)],.024,'Steel',24)
 for side in (-1,1):pipe(k,[(side*.21,.04,2.30),(side*.39,.04,2.30)],.030,'Rubber',24)
 text(k,'NEXUS / CABLE',(-.34,.25,2.18),.045,'Paper')
 place('Gym_CableTrainer',k,(-2.42,13.70,.036),90,room='Gym')
 # Rowing machine: supported rail, sliding seat, fan housing, foot straps and console.
 k='RowingMachine'
 for y in (-1.0,.73):
  B(k,(0,y,.055),(.58,.13,.11),'Dark',True)
  for x in (-.25,.25):rb(k,(x,y,.05),(.10,.16,.10),'Rubber',.012)
 B(k,(0,-.20,.22),(.095,1.95,.10),'Steel',True)
 B(k,(0,-.20,.276),(.065,1.86,.008),'Dark')
 rb(k,(0,-.40,.37),(.36,.29,.10),'Fabric',.035,col=True)
 for x in (-.11,.11):
  for y in (-.49,-.31):g.cylinder(k,(x-.022,y,.30),(x+.022,y,.30),.035,'Dark',24)
 g.lathe(k,(-.19,.67,.45),(1,0,0),[(0,.20),(.025,.24),(.355,.24),(.38,.20)],'Teal',64)
 for side in (-1,1):
  x=side*.196
  for j in range(12):
   a=j*math.tau/12
   pipe(k,[(x,.67+.04*math.cos(a),.45+.04*math.sin(a)),(x,.67+.21*math.cos(a+.2),.45+.21*math.sin(a+.2))],.004,'Steel',8)
  ring(k,(x,.67,.45),(1,0,0),.215,.209,.006,'Steel')
 for x in (-.22,.22):
  rb(k,(x,.20,.22),(.17,.33,.035),'Dark',.01,col=True)
  pipe(k,[(x-.08,.18,.24),(x-.07,.18,.32),(x+.07,.18,.32),(x+.08,.18,.24)],.012,'Rubber',12)
 pipe(k,[(0,.49,.53),(0,.25,.66),(0,.05,.66)],.025,'Steel',24)
 rb(k,(0,.07,.74),(.26,.06,.18),'Dark',.012);screen(k,(0,.034,.74),.225,.145,'WorkoutUI')
 pipe(k,[(0,.49,.52),(0,.05,.51)],.003,'Steel',10)
 pipe(k,[(-.19,.05,.51),(.19,.05,.51)],.014,'Rubber',24)
 place('Gym_Rower',k,(.35,13.72,.036),room='Gym')

 # Move the passage-blocking service cabinet onto the west wall; preserve IDs.
 service=[c for c in containers if c['label'].startswith('Service_Storage')]
 b,f,hinge=cubby('ServiceWall',.48,.25,.72,1,wall_mount=True)
 for c,(x,y,yaw) in zip(service,[(3.70,8.96,90),(3.70,9.49,90),(5.70,8.96,-90)]):
  c.update(body=b,front=f,hinge=list(hinge),p=[x,y,1.28],yaw=yaw,caption='卫生间墙面储物柜')
 # A new hanging vanity replaces the pedestal sink, with two functional doors.
 placements[:]=[p for p in placements if p['label']!='Bath1_Basin']
 b,f,hinge=cubby('VanityBay',.435,.44,.48,1,wall_mount=True)
 for i,x in enumerate((3.85,4.31)):instance('Vanity_'+str(i),b,f,(x,13.28,.30),hinge=hinge,caption='洗手台储物柜',room='Bath1')
 k='VanityTop';n=64;vs=[];fs=[]
 # Solid counter ring: rectangle outside, elliptical basin opening inside.
 for kind,z in [('outer',.81),('outer',.845),('inner',.845),('inner',.81)]:
  for i in range(n):
   a=i*math.tau/n;c,s=math.cos(a),math.sin(a)
   if kind=='outer':factor=max(abs(c),abs(s));x=.46*c/factor;y=.265*s/factor
   else:x=.295*c;y=.185*s-.025
   vs.append((x,y,z))
 for ringidx in range(4):
  nxt=(ringidx+1)%4
  for i in range(n):j=(i+1)%n;fs.append((ringidx*n+i,ringidx*n+j,nxt*n+j,nxt*n+i))
 g.poly(k,vs,fs,'Stone')
 # Basin: an actual inset bowl, rim, drain and inner slope.
 vs=[];fs=[]
 for rx,ry,z in [(.302,.192,.850),(.280,.170,.851),(.258,.150,.81),(.08,.05,.715),(.020,.020,.710)]:
  for i in range(n):a=i*math.tau/n;vs.append((rx*math.cos(a),ry*math.sin(a)-.025,z))
 for j in range(4):
  for i in range(n):q=(i+1)%n;fs.append((j*n+i,j*n+q,(j+1)*n+q,(j+1)*n+i))
 g.poly(k,vs,fs,'Ceramic',smooth=True)
 g.cylinder(k,(0,-.025,.707),(0,-.025,.712),.020,'Steel',40)
 pipe(k,[(0,.22,.845),(0,.22,1.02),(0,.18,1.07),(0,.04,1.07),(0,.015,1.04)],.012,'Steel',24)
 g.cylinder(k,(.08,.22,.847),(.08,.22,.91),.015,'Steel',24)
 for x in (-.42,.42):B(k,(x,0,.798),(.035,.46,.026),'Dark',True)
 for y in (-.24,.24):B(k,(0,y,.80),(.88,.03,.020),'Dark',True)
 rb(k,(.375,.07,.89),(.065,.08,.09),'Dark',.008)
 pipe(k,[(.375,.07,.94),(.375,.07,.98),(.34,.07,.98)],.008,'Steel',16)
 place('Bath1_VanityTop',k,(4.08,13.28,0),room='Bath1')

 # Headboards sit against rear walls; wardrobes and drawers have their own open zones.
 move('Bed2_Bed',(16.72,5.47,0));move('Bed3_Bed',(17.85,12.32,0))
 for c in containers:
  if c['label'].startswith('Bed2_Nightstand'):
   side=-1 if '_-1_' in c['label'] else 1;c['p']=[16.72+side*1.1,6.24,0]
  if c['label'].startswith('Bed3_Nightstand'):
   side=-1 if '_-1_' in c['label'] else 1;c['p']=[17.85+side*1.1,13.09,0]
  if c['label'].startswith('Bed2_Wardrobe'):c['p'][1]-=1.85

 # Manufactured desks with actual input devices, monitor supports and service hardware.
 for key in ('WritingDesk','CyberWorkstation'):drop(key)
 def workstation(key,w,three=False):
  rb(key,(0,0,.77),(w,.80 if three else .68,.045),'Teal',.013,col=True)
  depth=.80 if three else .68
  for x in (-w/2+.12,w/2-.12):
   for y in (-depth/2+.10,depth/2-.10):
    rb(key,(x,y,.375),(.045,.055,.75),'Dark',.006,col=True)
    g.cylinder(key,(x,y,.007),(x,y,.03),.028,'Rubber',24)
   B(key,(x,0,.16),(.045,depth-.18,.045),'Steel')
  B(key,(0,depth/2-.11,.59),(w-.24,.04,.055),'Steel')
  xs=(-.62,0,.62) if three else (-.15,)
  for x in xs:
   rb(key,(x,.21,.801),(.26,.20,.02),'Dark',.009)
   pipe(key,[(x,.25,.81),(x,.25,1.07),(x,.23,1.19)],.020,'Steel',24)
   ring(key,(x,.22,1.19),(1,0,0),.027,.012,.035,'Steel')
   rb(key,(x,.20,1.24),(.59,.048,.37),'Dark',.012)
   screen(key,(x,.171,1.24),.552,.326)
   for j in range(16):B(key,(x-.24+j*.032,.228,1.24),(.012,.008,.16),'CabinetInside')
   g.cylinder(key,(x+.258,.169,1.06),(x+.258,.166,1.06),.004,'Cyan',16)
   pipe(key,[(x,.26,1.12),(x,.31,.81),(.50,.31,.805),(.52,.27,.70)],.004,'Rubber',12)
  rb(key,(-.07,-.17,.797),(.78,.34,.008),'Rubber',.014)
  rb(key,(-.14,-.18,.816),(.48,.17,.024),'Dark',.009)
  for row in range(4):
   for col in range(14):
    rb(key,(-.355+col*.033,-.232+row*.033,.833),(.027,.026,.010),'Teal',.0025,3)
  rb(key,(-.14,-.252,.835),(.19,.015,.01),'Steel',.003)
  rb(key,(.32,-.18,.825),(.067,.108,.04),'Dark',.017)
  B(key,(.32,-.211,.848),(.004,.038,.004),'Steel')
  g.cylinder(key,(.32,-.19,.849),(.32,-.176,.849),.005,'Rubber',20)
  # Small speakers with circular drivers and inset grilles.
  for x in (-w/2+.13,w/2-.13):
   rb(key,(x,.15,.90),(.13,.12,.21),'Dark',.012)
   for z,rr in ((.88,.039),(.96,.018)):
    ring(key,(x,.085,z),(0,1,0),rr,rr*.76,.006,'Steel')
    g.cylinder(key,(x,.083,z),(x,.081,z),rr*.7,'CabinetInside',32)
  for x in (-w/2+.08,w/2-.08):
   for y in (-depth/2+.07,depth/2-.07):g.cylinder(key,(x,y,.792),(x,y,.796),.007,'Steel',16)
  B(key,(0,-depth/2-.005,.76),(w-.18,.008,.010),'Cyan')
  text(key,'NEXUS / STUDIO',(-w/2+.12,-depth/2-.011,.724),.026,'Paper')
 workstation('WritingDesk',1.65)
 workstation('CyberWorkstation',2.30,True)
 # Desktop drawer bodies and moving trays remain separate native containers.
 b,f,hi=cubby('DeskDrawer',.43,.48,.20,0,drawer=True,wall_mount=True)
 for p in [p for p in placements if p['key']=='WritingDesk']:
  instance(p['label']+'_Drawer',b,f,local(p['p'],(.51,.02,.53),p['yaw']),p['yaw'],hi,'Drawer',.29,'书桌抽屉',p['room'])

 # Standalone computer chassis: open internal frame, boards, fans, GPU and glazing.
 k='ComputerTower';w=.29;d=.46;h=.53
 for z in (.02,h-.015):rb(k,(0,0,z),(w,d,.025),'Teal',.007,col=True)
 for x in (-w/2+.012,w/2-.012):
  for y in (-d/2+.012,d/2-.012):B(k,(x,y,h/2),(.020,.020,h-.04),'Steel')
 B(k,(-w/2+.012,0,h/2),(.012,d-.04,h-.04),'Dark',True)
 B(k,(0,d/2-.012,h/2),(w-.04,.014,h-.04),'Dark',True)
 for x in (-.10,.10):
  for y in (-.17,.17):g.cylinder(k,(x,y,-.012),(x,y,.012),.018,'Rubber',24)
 # Motherboard lies inside the left side panel; components stand off toward the glass.
 B(k,(-.112,.02,.31),(.007,.32,.31),'CabinetInside')
 B(k,(-.09,.015,.35),(.034,.08,.08),'Steel')
 for y in (.095,.12):B(k,(-.088,y,.36),(.038,.016,.17),'Dark')
 B(k,(0,.04,.215),(.22,.31,.035),'Teal')
 for y in (-.055,.105):
  ring(k,(0,y,.236),(0,0,1),.062,.054,.007,'Steel')
  for i in range(9):
   a=i*math.tau/9;g.beam(k,(.018*math.cos(a),y+.018*math.sin(a),.24),(.05*math.cos(a+.3),y+.05*math.sin(a+.3),.24),.008,.004,'Dark')
 rb(k,(0,.07,.09),(.23,.27,.11),'Dark',.007)
 for z in (.19,.39):
  ring(k,(0,-.221,z),(0,1,0),.100,.088,.014,'Steel')
  ring(k,(0,-.227,z),(0,1,0),.086,.081,.006,'Cyan')
  g.cylinder(k,(0,-.22,z),(0,-.234,z),.022,'Dark',32)
  for i in range(11):
   a=i*math.tau/11;g.beam(k,(.027*math.cos(a),-.224,z+.027*math.sin(a)),(.075*math.cos(a+.4),-.224,z+.075*math.sin(a+.4)),.014,.006,'CabinetInside')
 for x in (-.12,.12):
  for z in (.05,.48):g.cylinder(k,(x,-.23,z),(x,-.235,z),.005,'Steel',16)
 for i in range(6):pipe(k,[(.06+i*.008,.15,.12),(.10+i*.002,.12,.17),(.08+i*.004,.11,.23)],.002,'Rubber',8)
 for x in (-.06,0,.06):B(k,(x,.231,.40),(.027,.006,.014),'Steel')
 B(k,(0,-.231,.49),(.022,.006,.008),'Cyan')
 glass='ComputerGlass';e['glass_groups'].add(glass)
 B(glass,(.143,0,.278),(.006,.411,.453),'Glass')
 for p in [p for p in placements if p['key'] in ('CyberWorkstation','WritingDesk')]:
  # Separate PC pedestal at floor height keeps the desk surface and monitors clear.
  offset=(.83,.05,.012) if p['key']=='CyberWorkstation' else (-.50,.15,.012)
  pos=local(p['p'],offset,p['yaw'])
  place(p['label']+'_PC',k,pos,p['yaw'],room=p['room'])
  place(p['label']+'_PCGlass',glass,pos,p['yaw'],collision=False,room=p['room'])
 for c in containers:c['opened_yaw']=90.
 revision.update(revision='20261022_RefinementV3',scene_scale=1.2,
  gym=dict(before_area_m2=3.25*3.35,authored_area_m2=6.5*5.025,final_area_m2=6.5*5.025*1.2**2,
           expansion_factor=3,bounds_before_global_scale=gym),
  reusable_container_tag='ColdSteel.SceneContainer.Reclosable')
