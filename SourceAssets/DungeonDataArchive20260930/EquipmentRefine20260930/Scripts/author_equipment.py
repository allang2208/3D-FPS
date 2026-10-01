"""Dimensioned archive props rebuilt from the four saved design sheets."""
import json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Euler
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(Path(__file__).parent))
import mesh_helpers as g
from mesh_helpers import box,face,lathe,rod,tube,plaque,basis
PARTS=[];CURRENT=None
def part(name):
 global CURRENT
 if CURRENT:CURRENT['last_vertex']=len(g.V)
 CURRENT={'name':name,'first_vertex':len(g.V)};PARTS.append(CURRENT)
def transform(start,c=(0,0,0),rot=(0,0,0)):
 R=Euler(rot).to_matrix();C=Vector(c)
 for i in range(start,len(g.V)):g.V[i]=tuple(C+R@Vector(g.V[i]))
def screw(c,axis=(0,-1,0),r=.0045):
 n,u,v=basis(axis);c=Vector(c)
 lathe(c,n,[(0,r*1.23),(.0008,r*1.23),(.0012,r),(.0022,r*.87)],'steel',16)
 # A recessed black slot, with geometric head surrounding it.
 p=c+n*.00223
 face([p-u*r*.62-v*r*.13,p+u*r*.62-v*r*.13,p+u*r*.62+v*r*.13,p-u*r*.62+v*r*.13],'rubber')
def screws_rect(x,y,z,w,h,r=.0045):
 for dx in (-w/2,w/2):
  for dz in (-h/2,h/2):screw((x+dx,y,z+dz),r=r)
def torus(c,axis,R,r,surface='steel',major=48,minor=8):
 c=Vector(c);n,u,v=basis(axis)
 for i in range(major):
  for j in range(minor):
   pts=[]
   for a,b in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
    q=a*math.tau/major;t=b*math.tau/minor;pts.append(c+(u*math.cos(q)+v*math.sin(q))*(R+r*math.cos(t))+n*r*math.sin(t))
   face(pts,surface,[(i/major,j/minor),((i+1)/major,j/minor),((i+1)/major,(j+1)/minor),(i/major,(j+1)/minor)],True)
def handle(c,width=.16,depth=.035,r=.008,vertical=False):
 c=Vector(c);n,u,v=basis((0,-1,0));a=v if vertical else u
 # Rounded shoulders connect the pull bar to its two mounted bosses.
 points=[]
 for side in (-1,1):
  p=c+a*side*width/2;lathe(p,n,[(0,r*1.7),(.006,r*1.7),(.009,r*1.35)],'steel',24)
 for i in range(9):
  t=i*math.pi/16;points.append(c-a*(width/2-depth)+a*(-depth*math.cos(t))+n*(.01+depth*math.sin(t)))
 points.append(c+a*(width/2-depth)+n*(.01+depth))
 for i in range(1,9):
  t=i*math.pi/16;points.append(c+a*(width/2-depth+depth*math.sin(t))+n*(.01+depth*math.cos(t)))
 tube(points,r,'steel',12)
def label(c,w,h,key='index_0'):
 x,y,z=c;box((x,y+.002,z),(w+.009,.006,h+.009),'steel',.001)
 plaque((x,y-.0017,z),w,h,key,(0,-1,0),.001,'ivory')
def lock(c):
 x,y,z=c;lathe(c,(0,-1,0),[(0,.012),(.003,.012),(.004,.009)],'steel',24)
 box((x,y-.0043,z),(.0028,.0008,.010),'rubber',.0002)
def vent(c,w,h,count=12,vertical=False,surface='ivory'):
 x,y,z=c
 box((x,y+.023,z),(w,.014,h),'rubber',.001)
 # The front opening has actual separated blades, perimeter folds and recessed backing.
 for xx in (x-w/2,x+w/2):box((xx,y+.005,z),(.009,.034,h+.018),surface,.001)
 for zz in (z-h/2,z+h/2):box((x,y+.005,zz),(w,.034,.009),surface,.001)
 for i in range(count):
  t=(i+.5)/count-.5
  if vertical:box((x+t*w,y,z),(w/count*.36,.014,h-.015),surface,.0007)
  else:box((x,y,z+t*h),(w-.015,.017,h/count*.38),surface,.0007,rotation=(math.radians(-12),0,0))
def frame(x,y,z,w,h,bar=.019,surface='green',depth=.032):
 for xx in (x-w/2,x+w/2):box((xx,y,z),(bar,depth,h+bar),surface,.002)
 for zz in (z-h/2,z+h/2):box((x,y,zz),(w-bar,depth,bar),surface,.002)
def shell(w,d,h,bottom=.08,plinth_floor=0):
 part('Folded cabinet shell and plinth')
 box((0,0,(bottom+plinth_floor)/2),(w,d,bottom-plinth_floor),'graphite',.005)
 for x in (-w/2+.012,w/2-.012):box((x,0,(h+bottom)/2),(.024,d,h-bottom),'green',.0028)
 box((0,d/2-.009,(h+bottom)/2),(w-.04,.018,h-bottom),'green',.0025)
 box((0,0,h-.018),(w,d,.036),'green',.004)
 box((0,0,bottom+.010),(w-.022,d-.016,.02),'green',.002)
 for x in (-w/2+.035,w/2-.035):box((x,-d/2+.008,(h+bottom)/2),(.026,.045,h-bottom-.05),'green',.002)
 # Raised service access skins preserve a narrow shadow seam on both sides.
 for sign in (-1,1):
  xx=sign*(w/2+.001)
  box((xx,.012,h*.52),(.007,d-.075,h-.19),'green',.0015)
  for yy in (-d/2+.062,d/2-.055):
   for zz in (.14,h-.10):screw((xx+sign*.004,yy,zz),(sign,0,0),.0045)
def dial(c,r=.078,key='dial_volts',square=False):
 x,y,z=c
 if square:
  box((x,y,z),(r*2.25,.028,r*2.10),'graphite',.006)
  plaque((x,y-.016,z),r*1.95,r*1.82,key,(0,-1,0),.001,'ivory')
 else:
  lathe((x,y+.01,z),(0,-1,0),[(0,r*1.07),(.026,r*1.07),(.032,r),(.032,r*.89),(.027,r*.89)],'graphite',64)
  center=Vector((x,y-.018,z))
  for i in range(64):
   a=i*math.tau/64;b=(i+1)*math.tau/64
   face([center,center+Vector((math.cos(a)*r*.89,0,math.sin(a)*r*.89)),center+Vector((math.cos(b)*r*.89,0,math.sin(b)*r*.89))],key,[(.5,.5),(.5+.48*math.cos(a),.5-.48*math.sin(a)),(.5+.48*math.cos(b),.5-.48*math.sin(b))])
 # Needle, boss and its physical shadow sit above the printed dial.
 p=Vector((x,y-.033,z-r*.11));tip=p+Vector((-r*.66,-.001,r*.36))
 face([p+Vector((-.002,0,-.003)),tip,p+Vector((.003,0,.003))],'rubber',[(.2,.2),(.8,.2),(.5,.8)])
 lathe(p,(0,-1,0),[(0,r*.065),(.002,r*.065)],'steel',20)
def knob(c,r=.017):
 x,y,z=c;lathe((x,y+.003,z),(0,-1,0),[(0,r*1.12),(.005,r*1.12),(.007,r),(.025,r),(.029,r*.86)],'plastic',32)
 for i in range(16):
  a=i*math.tau/16;rod((x+math.cos(a)*r,y-.003,z+math.sin(a)*r),(x+math.cos(a)*r,y-.021,z+math.sin(a)*r),.0013,'rubber',6)
 box((x,y-.027,z+r*.33),(.002,.001,r*.85),'ivory',.0002)
def push(c,w=.032,h=.032,color='ivory',key=None):
 x,y,z=c;box((x,y+.002,z),(w+.013,.019,h+.013),'graphite',.003)
 box((x,y-.010,z),(w,.011,h),color,.003)
 if key:plaque((x,y-.016,z),w*.77,h*.77,key,(0,-1,0),.0005,color)
def server():
 shell(.72,1.05,2.15,.10,.075)
 part('Adjustable feet and bottom intake')
 for x in (-.29,.29):
  for y in (-.44,.44):
   lathe((x,y,0),(0,0,1),[(0,.038),(.013,.038),(.018,.03),(.018,.014),(.096,.014)],'steel',24)
   for z in (.045,.058,.071):torus((x,y,z),(0,0,1),.014,.0015,'steel',20,6)
 # Recessed plinth was raised from the foot datum; bottom at zero after final author shift.
 vent((0,-.525,.205),.59,.12,9,False,'graphite')
 part('19 inch rack rails with open mounting slots')
 for x in (-.315,.315):
  for dx in (-.010,.010):box((x+dx,-.515,1.19),(.009,.025,1.82),'graphite',.001)
  for j in range(42):box((x,-.515,.29+j*.044),(.024,.025,.025),'graphite',.0008)
 part('Two disk cartridge modules with six pull-out bays')
 for row,z in enumerate((1.11,1.58)):
  box((0,-.19,z),(.588,.61,.431),'graphite',.002)
  # Separate fascia pieces leave an unobstructed louver opening on the right.
  box((-.081,-.527,z),(.416,.018,.427),'ivory',.004)
  for zz in (z-.157,z+.157):box((.211,-.527,zz),(.166,.018,.113),'ivory',.002)
  vent((.205,-.540,z),.129,.178,13,False,'ivory')
  for col,x in enumerate((-.209,-.097,.015)):
   box((x,-.542,z),(.105,.035,.352),'steel',.002)
   box((x,-.568,z),(.087,.025,.328),'plastic',.004)
   box((x,-.584,z+.108),(.064,.012,.052),'graphite',.002)
   push((x,-.593,z+.047),.009,.010,'amber')
   handle((x,-.586,z-.067),.15,.022,.006,True)
   screw((x,-.578,z+.156),r=.0026);lock((x,-.59,z-.14))
  for x in (-.278,.278):handle((x,-.547,z),.19,.026,.007,True)
  screws_rect(0,-.542,z,.55,.385,.004)
 part('Two power supply ventilation trays')
 for z in (.445,.711):
  box((0,-.225,z),(.587,.55,.230),'graphite',.003)
  for x in (-.259,.259):box((x,-.529,z),(.065,.022,.232),'ivory',.003)
  vent((0,-.537,z),.437,.198,48,True,'ivory')
  for x in (-.277,.277):handle((x,-.547,z),.151,.022,.006,True)
  push((.257,-.545,z+.003),.012,.043,'plastic');push((.257,-.560,z-.011),.004,.006,'amber')
  screws_rect(0,-.545,z,.546,.196,.0035)
 part('Meters status strip and top service header')
 box((0,-.525,1.918),(.585,.041,.20),'ivory',.004)
 dial((-.205,-.548,1.929),.062,'dial_volts',True);dial((-.063,-.548,1.929),.062,'dial_amps',True)
 for i in range(8):
  x=.039+i*.029;lathe((x,-.55,1.94),(0,-1,0),[(0,.009),(.004,.009)],'graphite',16)
  lathe((x,-.555,1.94),(0,-1,0),[(0,.0065),(.004,.0065),(.006,.004)],['red','amber','amber','jade','jade','red','jade','red'][i],20)
 label((.139,-.55,1.875),.20,.022,'server_plate');screws_rect(0,-.552,1.918,.546,.164,.0033)
 vent((-.191,-.535,2.078),.161,.074,7,False,'green');vent((.191,-.535,2.078),.161,.074,7,False,'green')
 box((0,-.527,2.078),(.18,.028,.104),'green',.002);label((0,-.545,2.078),.14,.044,'server_plate')
 part('Side service cover and rear cable glands')
 for sign in (-1,1):
  start=len(g.V);vent((0,0,.28),.22,.11,9,False,'green');transform(start,(sign*.370,.24,0),(0,0,sign*math.pi/2))
  box((sign*.372,.06,1.48),(.009,.47,.60),'green',.002)
  for y in (-.15,.27):
   for z in (1.215,1.745):screw((sign*.378,y,z),(sign,0,0),.004)
 for x in (-.18,0,.18):lathe((x,.537,.22),(0,1,0),[(0,.022),(.02,.022),(.027,.015)],'rubber',24)
def files():
 shell(1.10,.60,1.95,.07)
 part('Central divider and drawer guides')
 box((0,-.025,1.0),(.025,.56,1.80),'green',.002)
 for z in (.087,.453,.819,1.185,1.551,1.917):box((0,-.278,z),(1.044,.041,.013),'graphite',.001)
 for col,x in enumerate((-.267,.267)):
  for row in range(5):
   part(f'Drawer {col+1}-{row+1} with index handle and lock')
   z=.270+row*.366;opened=col==0 and row==2;front=-.303-(.12 if opened else 0)
   box((x,front,z),(.506,.022,.358),'pale',.003)
   for dx in (-.255,.255):box((x+dx,front+.245,z-.018),(.009,.48,.282),'green',.0012)
   box((x,front+.245,z-.157),(.508,.48,.009),'green',.001)
   box((x,front+.481,z-.018),(.507,.009,.282),'green',.001)
   label((x,front-.014,z+.085),.097,.046,'index_'+str(col*5+row))
   handle((x,front-.016,z-.013),.176,.024,.0075);lock((x,front-.015,z-.082))
   if opened:
    part('Visible telescopic runners and stored folders')
    for dx in (-.252,.252):
     box((x+dx,front+.18,z-.09),(.014,.34,.027),'steel',.001)
     box((x+dx,front+.29,z-.074),(.012,.31,.012),'steel',.001)
    for i in range(6):
     yy=front+.033+i*.025;zz=z+.086+(.012 if i%2 else 0)
     box((x,yy,zz-.09),(.441,.007,.25),'paper',.001)
     box((x+(-.11 if i%2 else .08),yy,zz+.045),(.105,.007,.035),'paper',.001)
     box((x,yy+.005,zz-.103),(.422,.011,.21),'ivory',.0005)
def reel(c,r=.108,angle=0):
 start=len(g.V);x,y,z=c
 lathe((x,y+.016,z),(0,-1,0),[(0,r*.90),(.018,r*.90)],'plastic',64)
 for yy in (y+.021,y-.014):
  torus((x,yy,z),(0,-1,0),r,.004,'steel',64,8)
  torus((x,yy,z),(0,-1,0),r*.84,.0025,'steel',48,6)
  lathe((x,yy+.002,z),(0,-1,0),[(0,r*.245),(.005,r*.245),(.006,r*.12)],'steel',32)
  for j in range(3):
   a=j*math.tau/3+.16;p=Vector((x,yy,z));u=Vector((math.cos(a),0,math.sin(a)));v=Vector((-math.sin(a),0,math.cos(a)))
   for offset in (-.003,.003):
    q=p+Vector((0,offset,0));face([q+u*r*.19-v*r*.12,q+u*r*.89-v*r*.095,q+u*r*.89+v*r*.095,q+u*r*.19+v*r*.12],'steel')
  lathe((x,yy-.006,z),(0,-1,0),[(0,r*.067),(.002,r*.067)],'rubber',24)
 if angle:
  C=Vector(c);R=Euler((0,0,angle)).to_matrix()
  for i in range(start,len(g.V)):g.V[i]=tuple(C+R@(Vector(g.V[i])-C))
def tapes():
 shell(1.10,.62,2.05,.075)
 part('Five shelf rows and three deep columns')
 for z in (.635,.901,1.167,1.433,1.699,1.965):
  box((0,.002,z),(1.052,.584,.014),'pale',.0018)
  box((0,-.294,z-.014),(1.044,.013,.023),'green',.001)
 for x in (-.174,.174):box((x,.012,1.30),(.012,.55,1.32),'green',.0015)
 for x in (-.502,-.184,-.164,.164,.184,.502):
  box((x,.20,1.31),(.012,.012,1.25),'graphite',.0008)
  for j in range(20):screw((x,-.277,.69+j*.062),r=.0018)
 part('Two lower full width drawers')
 for i,z in enumerate((.212,.492)):
  box((0,-.316,z),(1.028,.026,.272),'pale',.003)
  for x in (-.322,.322):handle((x,-.332,z),.143,.023,.007)
  label((0,-.333,z),.109,.048,'index_'+str(8+i));screws_rect(0,-.334,z,.988,.228,.0035)
 part('Header and serial plaque')
 box((0,-.310,2.005),(1.05,.035,.065),'pale',.002)
 plaque((-.07,-.329,2.005),.82,.028,'tape_plate',(0,-1,0));lock((.465,-.330,2.005))
 part('Magnetic tape cases and spines')
 for row in range(5):
  if row==2:continue
  for col,xc in enumerate((-.351,0,.351)):
   if (row,col) in ((0,2),(1,1),(3,1)):continue
   count=5+((row+col)%3)
   for i in range(count):
    xx=xc-.137+i*.039;bottom=.643+row*.266;yy=-.131+(i%3)*.006
    box((xx,yy,bottom+.106),(.034,.285,.208),'plastic' if (i+row)%3 else 'ivory',.0025)
    box((xx,yy-.145,bottom+.106),(.032,.009,.203),'graphite',.001)
    plaque((xx,yy-.150,bottom+.106),.024,.190,'tape_'+str((i+row*3+col)%12),(0,-1,0),.0006,'ivory')
 part('Three-spoke magnetic reels')
 for col,xc in enumerate((-.351,0,.351)):
  reel((xc-.025,-.225,1.281),.107)
  for j in range(2):reel((xc+.12,-.002+j*.032,1.281),.105,math.pi/2)
def console():
 part('Two pedestal cabinets knee opening and recessed kickplates')
 for x in (-.945,.945):
  box((x,0,.047),(.81,.96,.094),'graphite',.005)
  for xx in (x-.397,x+.397):box((xx,0,.445),(.022,.94,.702),'green',.003)
  box((x,.461,.435),(.79,.018,.70),'green',.002)
  box((x,-.469,.429),(.757,.025,.667),'green',.004)
  screws_rect(x,-.484,.429,.70,.60,.005)
  box((x+.20,-.486,.42),(.061,.013,.14),'graphite',.004)
  box((x+.20,-.498,.42),(.022,.016,.105),'steel',.003)
  part('Pedestal ventilation and cable grommets')
  start=len(g.V);vent((0,0,.327),.30,.225,19,False,'green');transform(start,(x+(-.411 if x<0 else .411),.06,0),(0,0,-math.pi/2 if x<0 else math.pi/2))
 box((0,.417,.39),(1.10,.038,.60),'green',.003)
 part('Sloping desktop and shaped side returns')
 # Solid tapered desktop cross-section; top rises toward the instrument housing.
 pts=[(-.535,.755),(.12,.91),(.49,.91),(.49,.82),(-.535,.689)]
 for sign in (-1,1):
  vs=[(sign*1.35,y,z) for y,z in pts];face(vs if sign>0 else list(reversed(vs)),'green',[(.05,.95),(.7,.05),(.95,.05),(.95,.7),(.05,.95)])
 for i in range(len(pts)):
  a=pts[i];b=pts[(i+1)%len(pts)];face([(-1.35,*a),(1.35,*a),(1.35,*b),(-1.35,*b)],'green')
 box((0,-.536,.739),(2.71,.054,.099),'rubber',.012)
 for x in (-1.326,1.326):box((x,-.527,.738),(.034,.063,.111),'steel',.006)
 part('Raised sloped instrument housing')
 slope=math.atan2(.18,.53);height=math.hypot(.18,.53);panel_center=(0,.05,1.175)
 # Back, top and polygonal side panels follow the reference's angled face.
 box((0,.496,1.177),(2.70,.025,.548),'green',.005)
 box((0,.325,1.442),(2.70,.36,.025),'green',.005)
 for sign in (-1,1):
  coords=[(sign*1.35,-.04,.905),(sign*1.35,.14,1.44),(sign*1.35,.495,1.44),(sign*1.35,.495,.905)]
  face(coords if sign<0 else list(reversed(coords)),'green')
  start=len(g.V);vent((0,0,1.20),.22,.19,16,False,'green');transform(start,(sign*1.356,.33,0),(0,0,sign*math.pi/2))
 for x,w in [(-.905,.86),(0,.90),(.905,.86)]:
  start=len(g.V);box((x,0,0),(w,.03,height),'ivory',.008);screws_rect(x,-.018,0,w-.047,height-.046,.0045)
  if x<-.1:
   part('Two analog meters and three rotary selectors')
   for xx,key in [(-1.10,'dial_volts'),(-.714,'dial_amps')]:dial((xx,-.024,.098),.130,key)
   for j,xx in enumerate((-1.17,-.905,-.64)):
    plaque((xx,-.019,-.168),.178,.078,['system','channel','monitor'][j],(0,-1,0),.001,'ivory');knob((xx,-.025,-.177),.026)
  elif x>.1:
   part('Sixteen push buttons toggles and emergency stop')
   for row in range(4):
    for col in range(4):push((.640+col*.176,-.025,.204-row*.087),.062,.055,'amber','button_'+str(row*4+col+1))
   for xx in (.667,.840):
    lathe((xx,-.026,-.195),(0,-1,0),[(0,.020),(.008,.020),(.011,.012)],'steel',6,False)
    rod((xx,-.034,-.195),(xx,-.068,-.166),.005,'steel',16)
    lathe((xx,-.068,-.166),(0,-1,0),[(0,.008),(.012,.008)],'rubber',20)
   lathe((1.13,-.025,-.178),(0,-1,0),[(0,.041),(.006,.041)],'amber',48)
   lathe((1.13,-.032,-.178),(0,-1,0),[(0,.021),(.014,.021),(.014,.030),(.040,.030),(.046,.027)],'red',48)
  else:
   part('Recessed CRT bezel curved glass and lower adjustment keys')
   def contour(w,h,r):
    points=[]
    for cx,cz,start_a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
     for j in range(9):
      a=math.radians(start_a+j*90/8);points.append((cx+math.cos(a)*r,cz+math.sin(a)*r))
    return points
   rings=[]
   for w,h,r,yy in [(.660,.472,.055,.0),(.658,.470,.054,-.037),(.642,.454,.048,-.046),(.559,.423,.031,-.046),(.545,.410,.026,-.058),(.545,.410,.026,.0)]:
    rings.append([(xx,yy,.035+zz) for xx,zz in contour(w,h,r)])
   for k in range(len(rings)):
    a=rings[k];b=rings[(k+1)%len(rings)]
    for j in range(len(a)):face([a[j],a[(j+1)%len(a)],b[(j+1)%len(a)],b[j]],'ivory' if k<4 else 'graphite',smooth=True)
   box((0,.020,.035),(.556,.13,.418),'plastic',.013)
   # Uniform grid avoids long radial triangles producing diagonal reflection facets.
   nx,nz=40,30
   def glass_point(ix,iz):
    zz=(iz/nz-.5)*.402;r=.029;edge=max(0,abs(zz)-(.201-r));limit=.268-r+math.sqrt(max(0,r*r-edge*edge))
    xx=(ix/nx*2-1)*limit
    return (xx,-.059-.023*(1-(xx/.275)**2)*(1-(zz/.212)**2),.035+zz)
   for iz in range(nz):
    for ix in range(nx):
     ps=[glass_point(a,b) for a,b in [(ix,iz),(ix+1,iz),(ix+1,iz+1),(ix,iz+1)]]
     face(ps,'screen',[(p[0]/.536+.5,.5-(p[2]-.035)/.402) for p in ps],True)
   for j in range(6):push((-.215+j*.086,-.036,-.213),.038,.021,'ivory')
   plaque((0,-.02,-.257),.55,.019,'console_plate',(0,-1,0),.001,'ivory')
  transform(start,panel_center,(-slope,0,0))
 part('Recessed keyboard individual keycaps and desktop selectors')
 start=len(g.V)
 # The desktop lies in a distinct slope; details are attached to that plane.
 box((0,0,0),(1.10,.029,.246),'graphite',.006)
 rows=['1234567890','QWERTYUIOP','ASDFGHJKL','ZXCVBNM']
 for row,letters in enumerate(rows):
  for col,k in enumerate(letters):
   xx=-.482+col*.075+row*.007;zz=.091-row*.054
   push((xx,-.019,zz),.065,.042,'ivory','key_'+k)
 for row in range(4):
  for col in range(3):push((.282+col*.075,-.019,.091-row*.054),.061,.042,'ivory','key_'+str((row*3+col)%10))
 push((-.162,-.019,-.118),.37,.035,'ivory','key_SPACE')
 transform(start,(0,-.25,.827),(-math.radians(77),0,0))
 for x,keys in [(-.945,['tape_feed','volume']),(.945,[])]:
  start=len(g.V);box((x,0,0),(.60,.010,.255),'ivory',.004);screws_rect(x,-.007,0,.55,.205,.0035)
  if x<0:
   for j,k in enumerate(keys):
    xx=x-.145+j*.29;plaque((xx,-.007,0),.23,.21,k,(0,-1,0),.001,'ivory');knob((xx,-.012,.012),.024)
  else:
   for j,col in enumerate(['jade','amber','amber','red','ivory']):push((x-.23+j*.115,-.014,0),.064,.057,col)
  transform(start,(0,-.25,.827),(-math.radians(77),0,0))
 part('Rear power and data connections with supported cable')
 for x in (-1.06,-.84):
  lathe((x,.486,.27),(0,1,0),[(0,.033),(.013,.033),(.025,.023)],'rubber',32)
  tube([(x,.505,.27),(x,.58,.25),(x+.03,.61,.17),(x+.06,.61,.05),(x+.16,.58,.025)],.012,'rubber',16)

def material():
 m=bpy.data.materials.new(g.SLOT);m.use_nodes=True;n=m.node_tree.nodes;n.clear();links=m.node_tree.links
 out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');links.new(bs.outputs['BSDF'],out.inputs['Surface']);maps={}
 for suffix in ('BaseColor','NormalGL','ORM'):
  im=bpy.data.images.load(str(ROOT/'Authored/Textures'/('T_ArchiveEquipment_'+suffix+'.png')))
  if suffix!='BaseColor':im.colorspace_settings.name='Non-Color'
  im.pack();a=n.new('ShaderNodeTexImage');a.image=im;maps[suffix]=a
 links.new(maps['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
 sep=n.new('ShaderNodeSeparateColor');links.new(maps['ORM'].outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 norm=n.new('ShaderNodeNormalMap');links.new(maps['NormalGL'].outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bs.inputs['Normal']);return m
def build():
 global CURRENT
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC'
 mat=material();dest=ROOT/'Authored';records=[]
 source_col=bpy.data.collections.new('EDITABLE_COMPONENTS');scene.collection.children.link(source_col)
 game_col=bpy.data.collections.new('GAME_EXPORTS');scene.collection.children.link(game_col)
 specs=revision_specs()
 for idx,(key,author,colliders) in enumerate(specs):
  g.V.clear();g.F.clear();g.UV.clear();g.SMOOTH.clear();PARTS.clear();CURRENT=None;author();CURRENT['last_vertex']=len(g.V)
  # A single local floor datum for every visible part and support.
  bottom=min(v[2] for v in g.V)
  if bottom<0:
   for i,p in enumerate(g.V):g.V[i]=(p[0],p[1],p[2]-bottom)
  name='SM_Archive_'+key+'_V2';mesh=bpy.data.meshes.new(name);mesh.from_pydata(g.V,[],g.F);mesh.materials.append(mat);mesh.update();obj=bpy.data.objects.new(name,mesh);game_col.objects.link(obj)
  uv=mesh.uv_layers.new(name='UVMap')
  for p,coords,smooth in zip(mesh.polygons,g.UV,g.SMOOTH):
   p.use_smooth=smooth
   for li,coord in zip(p.loop_indices,coords):uv.data[li].uv=coord
  for p in PARTS:obj.vertex_groups.new(name=p['name']).add(list(range(p['first_vertex'],p['last_vertex'])),1,'REPLACE')
  source=obj.copy();source.data=obj.data.copy();source.name='EDIT_'+key;source_col.objects.link(source);source.location=(idx*4,5,0);source.hide_render=True
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  mod=obj.modifiers.new('Manufactured weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40;bpy.ops.object.modifier_apply(modifier=mod.name)
  mod=obj.modifiers.new('Game export triangulation','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
  mesh=obj.data;uv=mesh.uv_layers.active.data
  for p in mesh.polygons:
   ids=list(p.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
   if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1e-8:continue
   co=[mesh.vertices[mesh.loops[i].vertex_index].co for i in ids];axis=max(range(3),key=lambda k:abs(p.normal[k]));ds=[k for k in range(3) if k!=axis];center=sum(co,Vector())/3
   # Tiny bevel islands need a finite UV area after FBX conversion. Preserve the
   # original surface tile rather than mapping all small painted edges to steel.
   mean=(a+b+c)/3;px=mean.x*4096;py=(1-mean.y)*4096
   candidates=[(k,r) for k,r in g.ATLAS['rects'].items() if r[0]<=px<=r[2] and r[1]<=py<=r[3]]
   surface=min(candidates,key=lambda kv:(kv[1][2]-kv[1][0])*(kv[1][3]-kv[1][1]))[0] if candidates else 'steel'
   spans=[max(v[d] for v in co)-min(v[d] for v in co) for d in ds]
   for li,v in zip(ids,co):uv[li].uv=g.tex(surface,.5+(v[ds[0]]-center[ds[0]])/max(spans[0],1e-9)*.22,.5-(v[ds[1]]-center[ds[1]])/max(spans[1],1e-9)*.22)
  collision=[]
  for j,(center,size) in enumerate(colliders):
   bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=f'UCX_{name}_{j:02d}';ob.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.hide_render=True;collision.append(ob)
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
  for ob in collision:ob.select_set(True)
  bpy.context.view_layer.objects.active=obj;fbx=dest/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
  records.append(dict(kind=key,name=name,fbx=str(fbx),triangles=len(mesh.polygons),vertices=len(mesh.vertices),material=g.MATERIAL,slot=g.SLOT,collision_hulls=len(collision),bounds_min=[min(v.co[i] for v in mesh.vertices) for i in range(3)],bounds_max=[max(v.co[i] for v in mesh.vertices) for i in range(3)],semantic_parts=[p['name'] for p in PARTS]))
  for ob in collision:bpy.data.objects.remove(ob,do_unlink=True)
  obj.location=(idx*3.25,0,0);print('ARCHIVE_PROP_AUTHORED',key,len(mesh.polygons),flush=True)
 (dest/'manifest.json').write_text(json.dumps(dict(revision='archive_equipment_v2_20260930',objects=records,reference='../../Equipment20260930/References',material_slots_per_mesh=1,tests_run=False,variation_seed=DETAIL_SEED),indent=2),encoding='utf-8')
 bpy.ops.wm.save_as_mainfile(filepath=str(dest/'ArchiveEquipment_Editable.blend'))
exec(compile((ROOT/'Scripts/refined_parts.py').read_text(encoding='utf-8'),str(ROOT/'Scripts/refined_parts.py'),'exec'))
build()
