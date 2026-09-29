"""Build the distinct station subject in Blender; reuse the approved ceramic/pipe authors.
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
detail.setup(globals())
H,T,B,S=CFG['hall'],CFG['track'],CFG['bridge'],CFG['stairs']
hx0,hx1=H['x'];hy0,hy1=H['y'];tx0,tx1=T['x'];ty0,ty1=T['y'];floor=T['floor']
spring,rise,rx=H['spring'],H['rise'],H['vault_rx']
bx0,bx1=B['x'];by0,by1=B['y'];bt=B['top'];sx0,sx1=S['x'];sw=S['width']
west,north=CFG['ports'];nx,ny,_=north['position'];wx,wy,_=west['position']
roof_at=lambda y:spring+rise*math.sqrt(1-(y/rx)**2)

# Rebuild to physical dimensions instead of scaling tiles, rails or human steps.
paving(hx0,hy0,tx0,hy1);paving(tx0,hy0,hx1,ty0);paving(tx0,ty1,hx1,hy1)
box('TrackBed',((tx0+tx1)/2,0,floor-.14),(tx1-tx0,ty1-ty0,.28),'Mortar')
for y in (ty0-.08,ty1+.08):box('Floors',((tx0+hx1)/2,y,floor/2),(hx1-tx0,.16,-floor),'Concrete')
rw=T['recovery_width'];rg=T['recovery_going'];rn=T['recovery_steps'];rend=tx0+rn*rg
for lo,hi in ((ty0,-rw/2),(rw/2,ty1)):
 box('Floors',(tx0-.08,(lo+hi)/2,floor/2),(.16,hi-lo,-floor),'Concrete')
for i in range(rn):
 top=(i+1)*floor/rn
 box('RecoverySteps',(tx0+(i+.5)*rg,0,(floor-.12+top)/2),(rg,rw,top-floor+.12),'Concrete')
for y in (-rw/2-.10,rw/2+.10):railings((tx0,y,0),(rend,y,floor),height=.98)
for y0,y1 in ((ty0,-rw/2-.10),(rw/2+.10,ty1)):railings((tx0,y0,0),(tx0,y1,0))

# Access openings and arch piers use the same configured doorway positions.
wall_segment((hx0,hy0),(hx1,hy0),spring+.02)
wall_segment((hx1,hy1),(hx0,hy1),spring+.02,[{'center':hx1-nx,'width':north['width'],'height':north['height']}])
wall_segment((hx0,hy1),(hx0,hy0),spring+.02,[{'center':hy1-wy,'width':west['width'],'height':west['height']}])
vault('Vault',hx0-.14,hx1+.14,0,spring,rx,rise,.30)
st=CFG['structure']
for x in st['rib_positions_x']:
 vault('Ribs',x-st['pier_width']/2,x+st['pier_width']/2,0,spring,rx-.29,rise-.28,.31,steps=56)
 for y in (hy0+.11,hy1-.11):
  box('Ribs',(x,y,spring/2),(st['pier_width'],.42,spring),'Concrete')
  box('Ribs',(x,y,.16),(st['pier_base_width'],.55,.32),'Concrete')
  box('Ribs',(x,y,spring-.12),(st['pier_base_width'],.58,.22),'Concrete')
top=[(rx*math.cos(math.pi*i/64),spring+rise*math.sin(math.pi*i/64)) for i in range(65)]
for a,b in ((hx0-.14,hx0+.14),(hx1-.14,hx1+.14)):extrude_x('Walls',top,a,b)

# Wider track spacing is carried into both mouths and their sealed extensions.
tr,ts,th=T['tunnel_radius'],T['tunnel_spring'],T['tunnel_rise'];c0,c1=T['centres_y']
for lo,hi in ((hy0,c0-tr),(c0+tr,c1-tr),(c1+tr,hy1)):
 box('Walls',(hx1,(lo+hi)/2,(floor+spring+.02)/2),(.28,hi-lo,spring+.02-floor),'Concrete')
for cy in T['centres_y']:
 arc=[(cy+tr*math.cos(math.pi*i/32),ts+th*math.sin(math.pi*i/32)) for i in range(33)]
 extrude_x('Walls',arc+[(cy-tr,spring+.02),(cy+tr,spring+.02)],hx1-.14,hx1+.14)
 vault('TunnelShell',hx1,tx1+.16,cy,ts,tr,th,.26,steps=32)
 for y in (cy-tr-.13,cy+tr+.13):box('TunnelShell',((hx1+tx1)/2,y,(floor+ts)/2),(tx1-hx1+.2,.26,ts-floor),'Concrete')
 for x in (hx1+.04,(hx1+tx1)/2):vault('Frames',x-.07,x+.07,cy,ts,tr-.08,th-.08,.10,'BareSteel',32)
 extrude_x('TunnelSeals',[(cy-tr,floor),(cy+tr,floor)]+arc,tx1-.07,tx1+.15,'Concrete')
 for z in (floor+.65,floor+1.55,floor+2.45):box('TunnelSeals',(tx1-.17,cy,z),(.10,tr*2-.14,.11),'PaintedSteel')
 beam('TunnelSeals',(tx1-.24,cy-tr+.21,floor+.4),(tx1-.24,cy+tr-.21,ts+.35),.11,.10,'PaintedSteel')

count=math.ceil(hx1-tx0);span=(hx1-tx0)/count
for sign in (-1,1):
 for i in range(count):
  x=tx0+(i+.5)*span;edge=ty1+.08;band=ty1+.38
  box('Coping',(x,sign*edge,-.025),(span-.012,.38,.14),'Concrete')
  box('Coping',(x,sign*band,.006),(span-.012,.22,.018),'Yellow')
  for j in range(8):box('Coping',(x-span*.42+j*span*.12,sign*band,.017),(.046,.18,.013),'Yellow')

# Keep standard 1435 mm rail gauge, sleeper size and buffer mechanics.
rail_profile=[(-.075,0),(.075,0),(.075,.018),(.013,.033),(.009,.126),(.034,.142),
              (.036,.170),(.026,.184),(-.026,.184),(-.036,.170),(-.034,.142),(-.009,.126),(-.013,.033),(-.075,.018)]
rs=T['rail_start'];half_gauge=T['gauge']/2
for cy in T['centres_y']:
 for yy in (cy-half_gauge,cy+half_gauge):extrude_x('Rails',[(yy+y,floor+.19+z) for y,z in rail_profile],rs,tx1-.10,'RailSteel')
 for i in range(math.floor((tx1-.25-(rs+.15))/.60)+1):
  x=rs+.15+i*.60;box('Sleepers',(x,cy,floor+.085),(.24,2.45,.15),'Concrete')
  for yy in (cy-half_gauge,cy+half_gauge):
   box('Rails',(x,yy,floor+.171),(.19,.20,.035),'BareSteel')
   for sy in (-.068,.068):box('Rails',(x,yy+sy,floor+.20),(.09,.028,.036),'RailSteel')
 for yy in (cy-.85,cy+.85):
  beam('BufferStops',(rs+.15,yy,floor+.12),(rs+1.15,yy,floor+1.1),.15,.15,'PaintedSteel')
  beam('BufferStops',(rs+2.1,yy,floor+.12),(rs+1.15,yy,floor+1.1),.15,.15,'PaintedSteel')
 box('BufferStops',(rs+1.18,cy,floor+1.095),(.25,2.20,.25),'PaintedSteel')
 for yy in (cy-.54,cy+.54):box('BufferStops',(rs+.99,yy,floor+1.095),(.16,.30,.30),'Rubber')

# Widened bridge and 30 ordinary 16 cm risers reach the new 4.8 m upper route.
box('Bridge',((bx0+bx1)/2,0,bt-B['thickness']/2),(bx1-bx0,by1-by0,B['thickness']),'BridgeDeck')
for x in (bx0+.08,bx1-.08):box('Bridge',(x,0,bt-.23),(.16,by1-by0,.22),'PaintedSteel')
for y in (-S['centres_y'][1]+.35,ty0-.45,ty1+.45,S['centres_y'][1]-.35):
 for x in (bx0+.08,bx1-.08):
  top=roof_at(y);detail.tube('BridgeHangers',[(x,y,bt-.14),(x,y,top-.01)],.028,'BareSteel',12)
  box('BridgeHangers',(x,y,top-.035),(.22,.19,.07),'BareSteel')
railings((bx1-.07,by0+.10,bt),(bx1-.07,by1-.10,bt))
inner=S['centres_y'][1]-sw/2-.10
railings((bx0+.07,-inner,bt),(bx0+.07,inner,bt))
for cy in S['centres_y']:
 for i in range(S['steps']):
  top=(i+1)*S['rise'];x=sx0+i*S['going']
  box('Stairs',(x+S['going']/2,cy,top-.065),(S['going'],sw,.13),'BridgeDeck')
  box('Stairs',(x+.01,cy,top-.15),(.022,sw,.30),'PaintedSteel')
  box('Stairs',(x+.01,cy,top+.001),(.025,sw-.05,.006),'Yellow')
 for yy in (cy-sw/2+.12,cy+sw/2-.12):
  beam('Stairs',(sx0,yy,-.10),(sx1,yy,bt-.10),.15,.25,'PaintedSteel')
  railings((sx0,yy,S['rise']),(sx1,yy,bt))
 for yy in (cy-sw/2+.08,cy+sw/2-.08):railings((bx0,yy,bt),(bx1,yy,bt))

# Standard-size vestibules preserve future room interfaces and the sample return.
paving(wx,wy-2.3,hx0,wy+2.3)
wall_segment((wx,wy-2.3),(hx0,wy-2.3),3.4);wall_segment((hx0,wy+2.3),(wx,wy+2.3),3.4)
wall_segment((wx,wy+2.3),(wx,wy-2.3),3.4,[{'center':2.3,'width':west['width'],'height':west['height']}])
box('Vault',((wx+hx0)/2,wy,3.54),(hx0-wx+.2,4.88,.28),'Concrete')
paving(nx-2.3,hy1,nx+2.3,ny)
wall_segment((nx+2.3,hy1),(nx+2.3,ny),3.4);wall_segment((nx-2.3,ny),(nx-2.3,hy1),3.4)
wall_segment((nx+2.3,ny),(nx-2.3,ny),3.4,[{'center':2.3,'width':north['width'],'height':north['height']}])
box('Vault',(nx,(hy1+ny)/2,3.54),(4.88,ny-hy1+.2,.28),'Concrete')
if CFG.get('phase')=='standalone_architecture':
 box('SamplePortCaps',(wx-.06,wy,west['height']/2),(.12,west['width'],west['height']),'PaintedSteel')
 box('SamplePortCaps',(nx,ny+.06,north['height']/2),(north['width'],.12,north['height']),'PaintedSteel')

ROOM['height_m']=8.265
for sign in (-1,1):
 y=sign*(hy1-.65)
 box('Frames',(-1,y,8.30),(24.8,.14,.07),'BareSteel')
 detail.smooth_pipe([(-13,y,2.0),(-13,y,6.675),(11,y,6.675)],.105)
 for x in (-13,-7,-1,5,11):
  detail.tube('Frames',[(x,y,8.335),(x,y,roof_at(y)-.01)],.016,'BareSteel',12)
for lamp in CFG['lights']:
 x,y,z=lamp['position'];roof=roof_at(y)
 for dx in (-.46,.46):
  detail.tube('Frames',[(x+dx,y,z+.21),(x+dx,y,roof-.01)],.014,'BareSteel',12)
  box('Frames',(x+dx,y,roof-.018),(.10,.12,.036),'BareSteel')

records=[]
for kind,g in G.items():
 if not g['f']:continue
 name='SM_Station_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
 names=list(dict.fromkeys(g['m']))
 for key in names:mesh.materials.append(MATS[key])
 uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
 for face,mat,coords,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
  face.material_index=names.index(mat);face.use_smooth=smooth
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
  scale=.8 if mat=='ServicePaint' else .075 if mat=='V2_CeramicFractureCore' else 1.28 if 'WallRelief' in mat else 2
  for ci,li in enumerate(face.loop_indices):
   p=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=coords[ci] if coords is not None else (p[dims[0]]/scale,p[dims[1]]/scale)
   age.data[li].color=(.13+.13*max(0,math.sin(p.x*1.2+p.y*.8+p.z*3)),0,0,1)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 if kind!='Tiles':
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 if kind in ('Walls','Floors','Paving','Coping','Bridge','Stairs','Sleepers','BufferStops','SamplePortCaps'):
  bevel=obj.modifiers.new('Manufactured arris','BEVEL');bevel.width=.003 if kind in ('Stairs','Coping') else .005;bevel.segments=2;bevel.limit_method='ANGLE'
  bpy.ops.object.modifier_apply(modifier=bevel.name)
 tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 mesh=obj.data;uv=mesh.uv_layers.active.data
 for face in mesh.polygons:
  ids=list(face.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-12:continue
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
  for li in ids:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv[li].uv=(p[dims[0]]/2,p[dims[1]]/2)
 fbx=OUT/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
 records.append({'name':name,'kind':kind,'fbx':str(fbx),'materials':{'RS_'+key:MAPPING[key] for key in names},
                 'triangles':len(mesh.polygons),'collision':kind not in ('Tiles','Frames','BridgeHangers','Services'),
                 'sample_only':kind=='SamplePortCaps'})
 print('STATION_AUTHORED',kind,len(mesh.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'AbandonedTransitStation_Subject.blend'))
(OUT/'manifest.json').write_text(json.dumps({'objects':records,'tests_run':False,'rendered':False,'revision':CFG['revision'],
 'ceramic_source':'DungeonTileFracture20260922 through CorridorSurfaces','source_units':'metres; UE centimetres'},indent=2),encoding='utf-8')
print('STATION_SUBJECT_AUTHORED',len(records),flush=True)
