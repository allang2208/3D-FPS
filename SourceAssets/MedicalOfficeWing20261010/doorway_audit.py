"""Scoped, user-requested surface/swing audit of saved doorway geometry."""
import json,math,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'Receipts/doorways-before.json'
data=json.loads(source.read_text('utf8'));meshes=data['meshes'];modules={m['id']:m for m in data['modules']}

def pose(v,p,yaw):
 c,s=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
 return [v[0]*c-v[1]*s+p[0],v[0]*s+v[1]*c+p[1],v[2]+p[2]]

def surfaces(module,at=(0,0,0),yaw=0):
 result=[]
 for i,part in enumerate(module['parts']):
  path=part['mesh']
  if path not in meshes:continue
  label=module['id']+'/'+path.rsplit('/',1)[-1]+':'+str(i)
  scale=part.get('scale',[1,1,1])
  for tri in meshes[path]['triangles']:
   result.append((label,[pose(pose([v[k]*scale[k] for k in range(3)],part['position'],part.get('yaw',0)),at,yaw) for v in tri]))
 return result

def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def area(p):return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))*.5 if len(p)>2 else 0
def clip(poly,edgea,edgeb):
 if not poly:return []
 out=[];a=poly[-1];da=cross(edgea,edgeb,a)
 for b in poly:
  db=cross(edgea,edgeb,b)
  if (da>=0)!=(db>=0):
   t=da/(da-db);out.append([a[k]+t*(b[k]-a[k]) for k in range(2)])
  if db>=0:out.append(b)
  a,da=b,db
 return out
def overlap(a,b):
 if sum(b[i][0]*b[(i+1)%len(b)][1]-b[(i+1)%len(b)][0]*b[i][1] for i in range(len(b)))<0:b=list(reversed(b))
 for i in range(len(b)):
  a=clip(a,b[i],b[(i+1)%len(b)])
  if len(a)<3:return 0
 return area(a)

def contains(poly,point):
 signs=[cross(poly[i],poly[(i+1)%len(poly)],point) for i in range(len(poly))]
 return min(signs)>=-.0001 or max(signs)<=.0001

def scan(name,geometry,center,yaw,width,height,depth=30):
 planes=defaultdict(list);limits=[(-width/2-9,width/2+9),(-depth,depth),(.8,height+8)]
 co,si=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
 for label,tri in geometry:
  points=[]
  for x,y,z in tri:
   x-=center[0];y-=center[1]
   points.append([-si*x+co*y,co*x+si*y,z-center[2]])
  if any(max(p[k] for p in points)<limits[k][0] or min(p[k] for p in points)>limits[k][1] for k in range(3)):continue
  axis=next((k for k in range(3) if max(p[k] for p in points)-min(p[k] for p in points)<.002),None)
  if axis is None:continue
  axes=[k for k in range(3) if k!=axis];poly=[[p[k] for k in axes] for p in points]
  sign=1 if cross(*poly)>0 else -1
  if area(poly)<.001:continue
  # A CCW clipping rectangle in the projected plane.
  x0,x1=limits[axes[0]];y0,y1=limits[axes[1]]
  rect=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
  for j in range(4):poly=clip(poly,rect[j],rect[(j+1)%4])
  if area(poly)<.001:continue
  planes[(axis,round(points[0][axis],2),sign)].append((label,poly))
 hits=defaultdict(float)
 for key,faces in planes.items():
  for i,(a,ap) in enumerate(faces):
   for b,bp in faces[i+1:]:
    if 'Frame' not in a and 'Frame' not in b:continue
    amount=overlap(ap,bp)
    if amount>.02:hits[(a,b,str(key))]+=amount
 # Recover the real jamb/header planes from the saved triangles, independently
 # of the nominal aperture dimensions used to bound the overlap search.
 jambs=[];headers=[]
 for (axis,at,sign),faces in planes.items():
  point=[0,150] if axis==0 else [0,0]
  if axis not in (0,2):continue
  if any('Frame' in label and contains(poly,point) for label,poly in faces):
   if axis==0:jambs.append(at)
   elif at>150:headers.append(at)
 left=max((x for x in jambs if x<0),default=None);right=min((x for x in jambs if x>0),default=None)
 return dict(id=name,coincident_faces=[dict(a=a,b=b,plane=p,area_cm2=round(v,3)) for (a,b,p),v in hits.items()],
             overlap_area_cm2=round(sum(hits.values()),3),measured_jambs_cm=[left,right],
             measured_clear_width_cm=right-left if left is not None and right is not None else None,
             measured_header_height_cm=min(headers,default=None))

office=surfaces(modules['MedicalDoctorOffice']);ward=surfaces(modules['AbandonedIsolationWard']);theatre=surfaces(modules['AbandonedAnatomyTheatre'])
doors=[('Consult01',-210,-500,0),('Consult02',-210,-1330,0),('Records',-210,-1990,0),('TeamHall',210,-450,0),
       ('TeamWaiting',970,-880,90),('Chief',580,-1320,90),('Support',1350,-1320,90)]
results=[scan('Office.'+n,office,[x,y,0],yaw,326,300) for n,x,y,yaw in doors]
results += [scan('Office.Entry',office,[0,0,0],90,300,280),scan('Office.Exit',office,[2000,-1100,0],0,300,280),scan('Office.SleeveJunction',office,[1700,-1100,0],0,440,440)]
for part in modules['AbandonedIsolationWard']['parts']:
 if part['mesh'].endswith('SM_Ward_GlassDoorFrame'):
  pos=part['position'];results.append(scan('Ward.'+part['ward_frame'],ward,[pos[0],pos[1],0],part['yaw'],326,301))
for ident,geo in [('AbandonedIsolationWard',ward),('AbandonedAnatomyTheatre',theatre)]:
 for p in modules[ident]['ports']:
  yaw=math.degrees(math.atan2(p['normal'][1],p['normal'][0]))
  results.append(scan(ident+'.'+p.get('id','Port'),geo,p['position'],yaw,p['width'],p['height']))
# Both ends of each retained medical route connector, at its exact saved pose.
line=json.loads((ROOT.parent/'DungeonHospitalLine20261003/Config/line.json').read_text('utf8'))
placed=[(p,surfaces(modules[p['id']],p['position'],p['yaw'])) for p in line['placements']]
for i in range(len(placed)-1):
 p,geo=placed[i];q,other=placed[i+1]
 port=modules[p['id']]['ports'][1];center=pose(port['position'],p['position'],p['yaw'])
 n=port['normal'];yaw=p['yaw']+math.degrees(math.atan2(n[1],n[0]))
 results.append(scan('MedicalJoin.'+str(i),geo+other,center,yaw,300,280))
leaf=next(v for k,v in meshes.items() if k.endswith('SM_Ward_GlassDoorMetalV5'))
vertices={tuple(v) for tri in leaf['triangles'] for v in tri};sweeps={}
for opening in (320,322,326):
 worst=999
 for side in (-1,1):
  for angle in range(-85,86):
   c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
   for x,y,z in vertices:
    if side>0:x,y=-x,-y
    y-=side*79.75;depth=x*c-y*s;across=side*160+x*s+y*c
    if abs(depth)<=24:worst=min(worst,opening/2-abs(across))
 sweeps[str(opening)]=round(worst,4)
report=dict(source=str(source),doorway_count=len(results),doorways=results,swing_minimum_clearance_cm=sweeps,
    interpretation='same-facing coplanar triangle overlaps near doorways; mesh-space sweep only; no rendering or live physics',gameplay_tested=False,rendered=False)
dest=source.with_name(source.stem+'-audit.json');dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(doorway_count=len(results),overlaps=[(r['id'],r['overlap_area_cm2']) for r in results],swing=sweeps),ensure_ascii=False))
