"""Incinerator architecture geometry helpers, adapted from the accepted station author; reuse the approved ceramic/pipe authors.
No game run, preview render or visual acceptance. Dimensions are in metres.
"""
import json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
CFG=json.loads((ROOT/'Config/room.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonRoomShells20260922/Scripts'))
from corridor_surfaces import CorridorSurfaces
import room_detail_geometry as detail

MAPPING={
 'Concrete':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete',
 'Mortar':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_ExposedMortar',
 'BareSteel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel',
 'PaintedSteel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PaintedSteel',
 'ServicePaint':'/Game/Dungeons/SeamMetal20260923/Materials/MI_Service_Paint',
 'ServiceHardware':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PipeCutSteel',
 'PipeEnamel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PipeEnamel',
 'PipeInner':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PipeInner',
 'PipeCutSteel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PipeCutSteel',
 'RailSteel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_FreightTrack',
 'BridgeDeck':'/Game/Dungeons/SeamMetal20260923/Materials/MI_BridgeDeck',
 'Yellow':'/Game/Dungeons/SeamMetal20260923/Materials/MI_Room_YellowPaint',
 'Rubber':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber'
}
MATS={key:bpy.data.materials.new('RS_'+key) for key in MAPPING}
SURFACES=CorridorSurfaces(ROOT,MAPPING,MATS)
for batch in ('DungeonSeamMetal20260923','DungeonWallDamage20260923'):
 remap=json.loads((PROJECT/'SourceAssets'/batch/'Config/material-remap.json').read_text(encoding='utf-8'))
 MAPPING={key:remap.get(path,path) for key,path in MAPPING.items()}
G={};ROOM={'id':CFG['id'],'height_m':5.72,'origin_m':[0,0,0]}

def group(kind):return G.setdefault(kind,dict(v=[],f=[],m=[],uv=[],smooth=[]))
def poly(kind,vs,fs,mat,uv=None,smooth=False):
 g=group(kind);offset=len(g['v']);g['v'].extend(tuple(v) for v in vs)
 g['f'].extend(tuple(offset+i for i in f) for f in fs);g['m'].extend([mat]*len(fs))
 g['uv'].extend(uv if uv is not None else [None]*len(fs))
 g['smooth'].extend(smooth if isinstance(smooth,list) else [smooth]*len(fs))
def box(kind,c,size,mat='Concrete',yaw=0):
 co,si=math.cos(yaw),math.sin(yaw);a,b,h=[x/2 for x in size]
 vs=[(c[0]+dx*co-dy*si,c[1]+dx*si+dy*co,c[2]+dz) for dx,dy,dz in
     [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]]
 poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
def beam(kind,a,b,width,height,mat='BareSteel'):
 a,b=Vector(a),Vector(b);z=(b-a).normalized();x=z.cross(Vector((0,0,1)) if abs(z.z)<.9 else Vector((0,1,0))).normalized();y=z.cross(x)
 vs=[tuple(p+x*dx*width/2+y*dy*height/2) for p in (a,b) for dx,dy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
def extrude_x(kind,profile,x0,x1,mat='Concrete'):
 # Closed profile on the Y/Z plane, with explicit triangulated concave caps.
 points=[Vector((y,z,0)) for y,z in profile];n=len(points)
 caps=[tuple(tri) for tri in tessellate_polygon([points])]
 vs=[(x,y,z) for x in (x0,x1) for y,z in profile]
 fs=[tuple(reversed(f)) for f in caps]+[tuple(n+i for i in f) for f in caps]
 fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
 poly(kind,vs,fs,mat)
def vault(kind,x0,x1,cy,spring,rx,rise,thickness,mat='Concrete',steps=64):
 vs=[]
 for x in (x0,x1):
  for add in (0,thickness):
   for i in range(steps+1):
    t=math.pi*i/steps;vs.append((x,cy+(rx+add)*math.cos(t),spring+(rise+add)*math.sin(t)))
 n=steps+1;fs=[];uvs=[];sm=[]
 for i in range(steps):
  for face in [(i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i),
               (i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1)]:
   fs.append(face);uvs.append([(vs[v][0]/2,(v%n)/steps*math.pi*(rx+rise)/4) for v in face]);sm.append(len(fs)%4 in (1,2))
 fs.extend([(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)]);uvs.extend([None,None]);sm.extend([False,False])
 poly(kind,vs,fs,mat,uvs,sm)
def wall_segment(start,end,height,openings=(),tiles=True):
 start,end=Vector(start),Vector(end);direction=(end-start).normalized();normal=Vector((-direction.y,direction.x));length=(end-start).length
 cuts=sorted((o['center']-o['width']/2-.07,o['center']+o['width']/2+.07,o['height']+.08) for o in openings)
 def fill(a,b,z0,z1):
  if b-a<.001:return
  p=start+direction*(a+b)/2;box('Walls',(p.x,p.y,(z0+z1)/2),(b-a,.28,z1-z0),'Concrete',math.atan2(direction.y,direction.x))
 cursor=0
 for a,b,z in cuts:fill(cursor,a,0,height);fill(a,b,z,height);cursor=b
 fill(cursor,length,0,height)
 if tiles:SURFACES.wall(globals(),start,direction,normal,length,openings,None,.28)
 for o in openings:
  for t in (o['center']-o['width']/2-.035,o['center']+o['width']/2+.035):
   p=start+direction*t;box('Frames',(p.x,p.y,o['height']/2),(.07,.34,o['height']),'BareSteel',math.atan2(direction.y,direction.x))
  p=start+direction*o['center'];box('Frames',(p.x,p.y,o['height']+.04),(o['width']+.14,.34,.08),'BareSteel',math.atan2(direction.y,direction.x))
def paving(x0,y0,x1,y1):
 # Recessed mortar and small real joints, not black stripes laid on the same plane.
 box('Floors',((x0+x1)/2,(y0+y1)/2,-.14),(x1-x0,y1-y0,.24),'Concrete')
 nx=math.ceil((x1-x0)/1.2);ny=math.ceil((y1-y0)/.9);dx=(x1-x0)/nx;dy=(y1-y0)/ny
 for ix in range(nx):
  for iy in range(ny):box('Paving',(x0+(ix+.5)*dx,y0+(iy+.5)*dy,-.016),(dx-.009,dy-.009,.036),'Concrete')
def railings(a,b,kind='Railings',height=1.1):
 a,b=Vector(a),Vector(b);count=max(1,math.ceil((b-a).length/1.25))
 for z in (.52,height):detail.tube(kind,[a+Vector((0,0,z)),b+Vector((0,0,z))],.026,'PaintedSteel',12)
 for i in range(count+1):
  p=a+(b-a)*i/count;detail.tube(kind,[p,p+Vector((0,0,height))],.03,'PaintedSteel',12)
  box(kind,p+Vector((0,0,.009)),(.115,.115,.018),'BareSteel')
