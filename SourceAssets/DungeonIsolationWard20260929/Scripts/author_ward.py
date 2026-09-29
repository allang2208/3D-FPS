"""Precision architecture for one isolation ward. No rendering or game execution."""
import json,math,sys,os
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix

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
 'Yellow':'/Game/Dungeons/SeamMetal20260923/Materials/MI_Room_YellowPaint',
 'Rubber':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber',
 'Glass':'/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassV2',
}
MATS={k:bpy.data.materials.new('RS_'+k) for k in MAPPING}
SURFACES=CorridorSurfaces(ROOT,MAPPING,MATS)
for batch in ('DungeonSeamMetal20260923','DungeonWallDamage20260923'):
 remap=json.loads((PROJECT/'SourceAssets'/batch/'Config/material-remap.json').read_text(encoding='utf-8'))
 MAPPING={k:remap.get(v,v) for k,v in MAPPING.items()}
G={};GLASS_COLLISION=[];ROOM={'id':CFG['id'],'height_m':4.5,'origin_m':[0,0,0]}
EXPORT_KINDS=set(filter(None,os.environ.get('WARD_EXPORT_KINDS','').split(',')))
def group(kind):return G.setdefault(kind,dict(v=[],f=[],m=[],uv=[],smooth=[]))
def poly(kind,vs,fs,mat,uv=None,smooth=False):
 g=group(kind);off=len(g['v']);g['v'].extend(tuple(p) for p in vs)
 g['f'].extend(tuple(off+i for i in f) for f in fs);g['m'].extend([mat]*len(fs))
 g['uv'].extend(uv if uv is not None else [None]*len(fs))
 g['smooth'].extend(smooth if isinstance(smooth,list) else [smooth]*len(fs))
def box(kind,c,size,mat='Concrete',yaw=0):
 co,si=math.cos(yaw),math.sin(yaw);a,b,h=[x/2 for x in size]
 vs=[(c[0]+x*co-y*si,c[1]+x*si+y*co,c[2]+z) for x,y,z in
     [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]]
 poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
detail.setup(globals())

def wall(a,b,height=4.5,holes=(),both=False,tiles=True):
 """Door/window openings are actual missing masonry, with distinct jamb and glazing meshes."""
 a,b=Vector(a),Vector(b);d=(b-a).normalized();n=Vector((-d.y,d.x));length=(b-a).length;angle=math.atan2(d.y,d.x)
 cuts=[dict(lo=h['center']-h['width']/2,hi=h['center']+h['width']/2,bottom=h.get('bottom',0),top=h['height'],glass=h.get('glass',False),interactive=h.get('interactive',False)) for h in holes]
 # All fixed frames (windows AND doors) need clearance from the concrete
 # reveal on every edge. V7 excluded glass windows and left all four inner
 # planes coplanar. Bury masonry 5 mm inside the continuous metal frame;
 # finished openings and the separate interactive door assemblies stay put.
 masonry_cuts=[dict(h,lo=h['lo']-.005,hi=h['hi']+.005,
                    bottom=max(0,h['bottom']-.005),top=h['top']+.005)
               if not h['interactive'] else h for h in cuts]
 xs=sorted(set([0,length]+[v for h in masonry_cuts for v in (h['lo'],h['hi'])]))
 def fill(lo,hi,z0,z1,kind='Walls',mat='Concrete',depth=.28,offset=0):
  if hi-lo<.001 or z1-z0<.001:return
  p=a+d*(lo+hi)/2+n*offset;box(kind,(p.x,p.y,(z0+z1)/2),(hi-lo,depth,z1-z0),mat,angle)
  if kind=='ObservationGlass':GLASS_COLLISION.append(dict(center=[p.x,p.y,(z0+z1)/2],size=[hi-lo,.08,z1-z0],yaw=angle))
 for lo,hi in zip(xs,xs[1:]):
  h=next((c for c in masonry_cuts if c['lo']<=(lo+hi)/2<=c['hi']),None)
  if h:fill(lo,hi,0,h['bottom']);fill(lo,hi,h['top'],height)
  else:fill(lo,hi,0,height)
 if tiles:
  # Remove ceramic behind the cover frame, including its thickness and header.
  doorcuts=[dict(h,width=h['width']+.17,height=h['height']+.09,bottom=max(0,h.get('bottom',0)-.08)) for h in holes]
  SURFACES.wall(globals(),a,d,n,length,doorcuts,None,.28)
  if both:
   reversed_holes=[dict(h,center=length-h['center']) for h in doorcuts]
   SURFACES.wall(globals(),b,-d,-n,length,reversed_holes,None,.28)
 for h in cuts:
  lo,hi,z0,z1=h['lo'],h['hi'],h['bottom'],h['top']
  if h['interactive']:continue  # The movable door actor owns its reveal frame.
  if h['glass']:
   # One closed reveal ring: no overlapping jamb/sill boxes or coplanar cover strips.
   def ring(kind,outer,inner,depth,mat):
    def corners(rect):
     l,r,b,t=rect;return ((l,b),(r,b),(r,t),(l,t))
    vs=[]
    for offset in (-depth/2,depth/2):
     for rect in (outer,inner):
      for t,z in corners(rect):
       p=a+d*t+n*offset;vs.append((p.x,p.y,z))
    faces=[]
    for i in range(4):
     j=(i+1)%4
     faces.extend(((i,j,j+4,i+4),(i+8,i+12,j+12,j+8),
                   (i,i+8,j+8,j),(i+4,j+4,j+12,i+12)))
    poly(kind,vs,faces,mat)
   ring('Frames',(lo-.076,hi+.076,z0-.07,z1+.08),(lo,hi,z0,z1),.48,'BareSteel')
   # Hide mating caps 3 mm inside the frame seat, without changing the
   # visible rubber lip or the clearance reserved for breakable glass.
   ring('WindowGaskets',(lo-.003,hi+.003,z0-.003,z1+.003),(lo+.020,hi-.020,z0+.020,z1-.020),.04,'Rubber')
   fill(lo+.025,hi-.025,z0+.025,z1-.025,'ObservationGlass','Glass',.016)
   # Fine safety mullion makes the transparent opening legible from either room.
   fill((lo+hi)/2-.02,(lo+hi)/2+.02,z0+.017,z1-.017,'Frames','PaintedSteel',.05)
  else:
   # One continuous U-section also removes coincident post/header end caps.
   outline=((lo-.076,z0),(lo,z0),(lo,z1),(hi,z1),(hi,z0),
            (hi+.076,z0),(hi+.076,z1+.08),(lo-.076,z1+.08))
   vs=[]
   for offset in (-.24,.24):
    for t,z in outline:
     p=a+d*t+n*offset;vs.append((p.x,p.y,z))
   faces=[tuple(range(7,-1,-1)),tuple(range(8,16))]
   faces.extend((i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8))
   poly('Frames',vs,faces,'BareSteel')
 # Wall protection bumper follows solid wall portions and stops at each door jamb.
 solid=[(0,length)]
 for h in cuts:
  if h['bottom']>1:continue
  solid=[p for lo,hi in solid for p in ((lo,min(hi,h['lo']-.12)),(max(lo,h['hi']+.12),hi)) if p[1]-p[0]>.12]
 for side in ((1,-1) if both else (1,)):
  for lo,hi in solid:
   fill(lo+.02,hi-.02,.88,.99,'WallRails','PaintedSteel',.042,side*.20)
   fill(lo+.02,hi-.02,.92,.96,'WallRails','Rubber',.012,side*.229)

def door(center,width=3.2,interactive=False):return dict(center=center,width=width,height=3.0,interactive=interactive)
def window(center,width=3.4):return dict(center=center,width=width,bottom=1.55,height=2.88,glass=True)
def horizontal_front(room):
 x0,x1=room['x'];y=4.5 if room['id'][0]=='N' else -4.5
 # Start/end reversed on the north wall so ceramic front faces the hall.
 sign=-1 if y>0 else 1;a=(x1,y) if sign<0 else (x0,y);b=(x0,y) if sign<0 else (x1,y)
 holes=[door(sign*(room['door_x']-a[0]),interactive=True),window(sign*(room['window_x']-a[0]))]
 wall(a,b,5.8,holes,True)

# Nonrectangular footprint: south suites and the separate decon wing leave an exterior notch.
for i,(x0,y0,x1,y1) in enumerate(CFG['floor_rectangles_m']):
 box('FloorSlabs',((x0+x1)/2,(y0+y1)/2,-.13),(x1-x0,y1-y0,.29))
 nx=math.ceil((x1-x0)/1.2);ny=math.ceil((y1-y0)/1.2);dx=(x1-x0)/nx;dy=(y1-y0)/ny
 for ix in range(nx):
  for iy in range(ny):box('FloorFinish',(x0+(ix+.5)*dx,y0+(iy+.5)*dy,.030),(dx-.007,dy-.007,.024))
 height=5.8 if i==0 else 3.4 if i>=4 else 4.5
 box('RoofSlabs',((x0+x1)/2,(y0+y1)/2,height+.13),(x1-x0+.28,y1-y0+.28,.26))

# Clockwise/inward facing boundary segments, with one 3m interface per end vestibule.
wall((-30,17),(-30,4.5));wall((-30,4.5),(-30,-4.5),5.8,[dict(center=4.5,width=3,height=2.8)]);wall((-30,-4.5),(-30,-12.5))
wall((-30,-12.5),(10,-12.5));wall((10,-12.5),(10,-4.5))
wall((10,-4.5),(17,-4.5),5.8)
wall((17,-4.5),(17,-10.5));wall((17,-10.5),(30,-10.5),4.5)
wall((30,-10.5),(30,-4.5));wall((30,-4.5),(30,4.5),5.8,[dict(center=4.5,width=3,height=2.8)])
wall((30,4.5),(30,17));wall((30,17),(-30,17))

for r in CFG['rooms']:horizontal_front(r)
# An open 4.7m west passage connects the main hall and rear gallery without a door bottleneck.
box('Lintels',(-25,4.5,5.17),(10,.28,1.26))
for x in (-20,-4,12):wall((x,4.5),(x,12.5),4.5,both=True)
wall((-10,-12.5),(-10,-4.5),4.5,both=True)
wall((30,12.5),(-20,12.5),4.5,[door(9),door(42)],True)
wall((17,-4.5),(30,-4.5),5.8,[door(6.5,interactive=True)],True)

# Equal hall-end connectors. No sample caps or return portal geometry.
wall((-33,-2.3),(-30,-2.3),3.4);wall((-30,2.3),(-33,2.3),3.4)
wall((-33,2.3),(-33,-2.3),3.4,[dict(center=2.3,width=3,height=2.8)],tiles=False)
wall((30,-2.3),(33,-2.3),3.4);wall((33,2.3),(30,2.3),3.4)
wall((33,-2.3),(33,2.3),3.4,[dict(center=2.3,width=3,height=2.8)],tiles=False)

# Attached piers are aligned to partition ends, outside the door and observation apertures.
for x in (-20,-4,12):
 box('Structure',(x,4.39,2.9),(.32,.42,5.8))
 box('Structure',(x,4.32,.13),(.43,.48,.26))
for x in (-30,-10,10,30):
 box('Structure',(x,-4.42,2.9),(.32,.36,5.8))
for x in (-20,-4,12):box('Structure',(x,0,5.54),(.32,9,.52))

# Layered ceiling bays and service slot grills, built as bounded static meshes.
for r in CFG['rooms']:
 x0,x1=r['x'];y0,y1=r['y'];cx=(x0+x1)/2;cy=(y0+y1)/2
 box('CeilingPanels',(cx,cy,4.465),(x1-x0-.48,y1-y0-.48,.065),'PaintedSteel')
 for x in (x0+.3,x1-.3):box('CeilingFrames',(x,cy,4.39),(.07,y1-y0-.5,.10),'BareSteel')
 for y in (y0+.3,y1-.3):box('CeilingFrames',(cx,y,4.39),(x1-x0-.5,.07,.10),'BareSteel')
 # A fixed headwall utility trunk reserves usable patient equipment space, no placeholder beds.
 if 'rear_door_x' not in r:
  back=y1-.25 if y0>0 else y0+.25
  box('HeadwallServices',(cx,back,1.24),(3.1,.13,.22),'PaintedSteel')
  box('HeadwallServices',(cx,back+( -.075 if y0>0 else .075),1.24),(3.0,.012,.07),'BareSteel')
  for x in (cx-.85,cx+.85):box('HeadwallServices',(x,back,1.47),(.16,.14,.14),'Rubber')
 for k in range(24):box('VentGrilles',(cx-1.15+k*.10,cy+1.8,4.34),(.04,.55,.065),'BareSteel')
 for yy in (cy+1.50,cy+2.10):box('VentGrilles',(cx,yy,4.36),(2.55,.05,.10),'PaintedSteel')

# Hall ducts stay overhead and clear of all piers/door headers.
for y in (-3.5,3.5):
 box('VentDucts',(0,y,5.02),(59,.56,.45),'PaintedSteel')
 for x in range(-29,30,2):
  box('VentDucts',(x,y,5.02),(.055,.63,.51),'BareSteel')
  for yy in (y-.35,y+.35):detail.tube('CeilingFrames',[(x,yy,5.25),(x,yy,5.8)],.011,'BareSteel',12)
ROOM['height_m']=4.5
detail.smooth_pipe([(-29.2,16.35,1.5),(-29.2,16.35,3.8),(29.2,16.35,3.8)],.075)
for lamp in CFG['lights']:
 x,y,z=lamp['position'];ceiling=5.8 if lamp['id'].startswith('Hall') else 3.4 if lamp['id'] in ('Entry','Exit') else 4.5
 for dx in (-.46,.46):detail.tube('CeilingFrames',[(x+dx,y,z+.20),(x+dx,y,ceiling)],.012,'BareSteel',12)

# Compact architectural lettering is editable geometry, not a texture dependency.
def sign(text,center,facing,size=.24):
 d=Vector((1,0,0)) if facing<0 else Vector((-1,0,0));up=Vector((0,0,1));normal=d.cross(up)
 c=Vector(center);box('Wayfinding',c,(1.7,.06,.50),'PaintedSteel')
 curve=bpy.data.curves.new('Label_'+text,'FONT');curve.body=text;curve.align_x='CENTER';curve.align_y='CENTER';curve.size=size;curve.extrude=.0015;curve.resolution_u=4
 obj=bpy.data.objects.new('Label_'+text,curve);bpy.context.scene.collection.objects.link(obj)
 obj.matrix_world=Matrix(((d.x,up.x,normal.x,c.x+normal.x*.033),(d.y,up.y,normal.y,c.y+normal.y*.033),(d.z,up.z,normal.z,c.z),(0,0,0,1)))
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH')
 mesh=obj.data;poly('Wayfinding',[obj.matrix_world@v.co for v in mesh.vertices],[tuple(f.vertices) for f in mesh.polygons],'Yellow')
 bpy.data.objects.remove(obj,do_unlink=True)
for r in CFG['rooms']:sign('ISO '+r['id'],[r['door_x'],4.30 if r['id'][0]=='N' else -4.30,3.36],-1 if r['id'][0]=='N' else 1)
sign('DECON',[23.5,-4.29,3.36],1,.21)
sign('SERVICE',[-25,4.29,4.13],-1,.19)

records=[]
previous_records={i['kind']:i for i in json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['objects']} if EXPORT_KINDS else {}
for kind,g in G.items():
 if not g['f']:continue
 if EXPORT_KINDS and kind not in EXPORT_KINDS:
  records.append(previous_records[kind]);continue
 name='SM_Ward_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
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
   if mat=='Glass':
    points=[mesh.vertices[v].co for v in face.vertices]
    uv.data[li].uv=tuple((p[k]-min(v[k] for v in points))/max(.0001,max(v[k] for v in points)-min(v[k] for v in points)) for k in dims)
   age.data[li].color=(.12+.08*max(0,math.sin(p.x*1.2+p.y*.8+p.z*3)),0,0,1)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 if kind!='Tiles':
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 if kind in ('Walls','FloorFinish','FloorSlabs','Frames','Structure','HeadwallServices','Wayfinding'):
  mod=obj.modifiers.new('Manufactured edge','BEVEL');mod.width=.003;mod.segments=2;mod.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 mesh=obj.data;uv=mesh.uv_layers.active.data
 for face in mesh.polygons:
  ids=list(face.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-12:continue
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
  for li in ids:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv[li].uv=(p[dims[0]]/2,p[dims[1]]/2)
 fbx=OUT/(name+'.fbx')
 colliders=[]
 if kind=='ObservationGlass':
  for i,spec in enumerate(GLASS_COLLISION):
   bpy.ops.mesh.primitive_cube_add(size=1,location=spec['center']);c=bpy.context.object;c.name='UCX_'+name+'_'+str(i).zfill(2)
   c.dimensions=spec['size'];c.rotation_euler.z=spec['yaw'];bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);colliders.append(c)
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
  for c in colliders:c.select_set(True)
  bpy.context.view_layer.objects.active=obj
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
 for c in colliders:c.hide_set(True);c.hide_render=True;c.select_set(False)
 records.append(dict(name=name,kind=kind,fbx=str(fbx),materials={'RS_'+key:MAPPING[key] for key in names},triangles=len(mesh.polygons),
                     collision=kind in ('FloorSlabs','Walls','RoofSlabs','ObservationGlass','Structure','SamplePortCaps'),
                     nanite=kind!='ObservationGlass',collision_boxes=len(colliders),sample_only=kind=='SamplePortCaps'))
 print('WARD_AUTHORED',kind,len(mesh.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('WardWindowRevealFixV8.blend' if EXPORT_KINDS else 'AbandonedIsolationWard_Subject.blend')))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,revision=CFG['revision'],tests_run=False,rendered=False,
 ceramic_source='Approved DungeonTileFracture20260922 via CorridorSurfaces',units='metres; UE centimetres'),indent=2),encoding='utf-8')
print('WARD_SUBJECT_AUTHORED',len(records),flush=True)
