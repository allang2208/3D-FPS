"""Doctor-office wing: dimensioned shell, retained hospital surface art, new signs.
Blender background production only; no rendering or gameplay execution.
"""
import bpy,bmesh,json,math,sys,os
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
BASE='/Game/Dungeons/MedicalOfficeWing20261010'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonRoomShells20260922/Scripts'))
from corridor_surfaces import CorridorSurfaces,clip
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
MAP={
 'Concrete':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete',
 'Paint':'/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_White',
 'Blue':'/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_Blue',
 'Steel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PaintedSteel',
 'Rubber':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber',
 'Text':'/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_White',
 'Floor':json.loads((PROJECT/'SourceAssets/DungeonReceptionHall20261006/Config/materials.json').read_text('utf8'))['Floor']['existing_ue_path'],
}
MATS={k:bpy.data.materials.new('MO_'+k) for k in MAP}
SURF=CorridorSurfaces(ROOT,MAP,MATS)
# One real rail owns this horizontal band. Fit its front to the retained relief,
# then cut that band out of the local tile copy rather than overlaying coplanar faces.
RAIL_BOTTOM,RAIL_TOP=.91,.98
RAIL_TILE_FRONT_CM=.4+100*max(p[1] for _,records,_,_ in SURF.panels
 for face,_,_ in records if min(p[2] for p in face)<RAIL_TOP and max(p[2] for p in face)>RAIL_BOTTOM for p in face)
# CorridorSurfaces adds retained source slots with RS_ names; keep actual names in the manifest.
g.ROOM='DoctorsOffice'
def pt(p):return (p[0]/100,-p[1]/100,p[2]/100)
def box(kind,c,s,mat='Concrete',yaw=0,col=False):
 g.box(kind,pt(c),[v/100 for v in s],mat,-math.radians(yaw),col)
def wall(a,b,holes=(),height=440,tiles=False,framed=True):
 dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);d=(dx/length,dy/length);ang=math.degrees(math.atan2(dy,dx))
 finished=[dict(lo=h[0]-h[1]/2,hi=h[0]+h[1]/2,bot=h[2],top=h[3]) for h in holes]
 # The continuous steel reveal owns the finished aperture. Bury the concrete
 # and facing end caps 5 mm inside it, instead of sharing the visible jamb plane.
 cuts=[dict(h,lo=h['lo']-.5,hi=h['hi']+.5,top=h['top']+.5) if framed else h for h in finished]
 xs=sorted({0,length,*[v for h in cuts for v in (h['lo'],h['hi'])]})
 def segment(lo,hi,z0,z1,kind='Walls',mat='Concrete',thick=24,offset=0):
  if hi<=lo or z1<=z0:return
  box(kind,[a[0]+d[0]*(lo+hi)/2-d[1]*offset,a[1]+d[1]*(lo+hi)/2+d[0]*offset,(z0+z1)/2],[hi-lo,thick,z1-z0],mat,ang,kind=='Walls')
 for lo,hi in zip(xs,xs[1:]):
  cut=next((h for h in cuts if h['lo']<(lo+hi)/2<h['hi']),None)
  spans=[(0,cut['bot']),(cut['top'],height)] if cut else [(0,height)]
  for z0,z1 in spans:
   segment(lo,hi,z0,z1)
   # Thin painted facing wraps the wall, with reused tiled surfaces on the public hall.
   segment(lo,hi,max(z0,152),z1,'WallFinish','Paint',24.4)
   segment(lo,hi,z0,min(z1,150),'WallFinish','Blue',24.3)
 # Rails stop outside the entire jamb, including the metal face; they must not
 # meet the 29 cm deep frame on the same front plane.
 solid=[(0,length)]
 for h in finished:
  if h['bot']>105:continue
  margin=6.8 if framed else 0
  solid=[p for lo,hi in solid for p in ((lo,min(hi,h['lo']-margin)),(max(lo,h['hi']+margin),hi)) if p[1]>p[0]]
 for lo,hi in solid:
  segment(lo,hi,12,20,'Trim','Steel',26)
  front=RAIL_TILE_FRONT_CM if tiles else 14.5
  segment(lo,hi,91,98,'Trim','Rubber',front+14.5,(front-14.5)/2)
 for h in finished if framed else ():
  if h['bot']==0:
   lo,hi,top=h['lo'],h['hi'],h['top']
   # External portal collars remain inside the declared 14 cm room envelope.
   depth=29 if tiles else 28
   outline=((lo-6,0),(lo,0),(lo,top),(hi,top),(hi,0),(hi+6,0),(hi+6,top+6),(lo-6,top+6))
   vs=[pt((a[0]+d[0]*t-d[1]*n,a[1]+d[1]*t+d[0]*n,z)) for n in (-depth/2,depth/2) for t,z in outline]
   faces=[tuple(range(7,-1,-1)),tuple(range(8,16))]
   faces.extend((i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8))
   g.poly('Frames',vs,faces,'Steel')
   # Separate convex collision members, with no internal render caps.
   for t in (lo-3,hi+3):
    g.box(None,pt((a[0]+d[0]*t,a[1]+d[1]*t,top/2)),(.06,depth/100,top/100),'Steel',-math.radians(ang),'Frames')
   g.box(None,pt((a[0]+d[0]*(lo+hi)/2,a[1]+d[1]*(lo+hi)/2,top+3)),((hi-lo+12)/100,depth/100,.06),'Steel',-math.radians(ang),'Frames')
 if tiles:
  start=Vector((b[0]/100,-b[1]/100));direction=Vector((-d[0],d[1]));normal=Vector((-direction.y,direction.x))
  openings=[dict(center=(length-h[0])/100,width=(h[1]+14)/100,bottom=h[2]/100,height=(h[3]+8)/100) for h in holes]
  host={'ROOM':{'id':'MedicalOfficeWing','height_m':height/100},'group':g.group}
  data=g.group('Tiles');first=len(data['f'])
  SURF.wall(host,start,direction,normal,length/100,openings,None,.24)
  tail=list(zip(data['f'][first:],data['m'][first:],data['uv'][first:],data['smooth'][first:]))
  for key in ('f','m','uv','smooth'):del data[key][first:]
  for indices,material,uv,smooth in tail:
   points=[(*data['v'][vi],*tex) for vi,tex in zip(indices,uv)]
   if max(p[2] for p in points)<=RAIL_BOTTOM or min(p[2] for p in points)>=RAIL_TOP:
    data['f'].append(indices);data['m'].append(material);data['uv'].append(uv);data['smooth'].append(smooth);continue
   for piece in (clip(points,2,RAIL_BOTTOM,False),clip(points,2,RAIL_TOP,True)):
    if len(piece)<3:continue
    base=len(data['v']);data['v'].extend(p[:3] for p in piece)
    data['f'].append(tuple(range(base,base+len(piece))));data['m'].append(material)
    data['uv'].append([p[3:] for p in piece]);data['smooth'].append(smooth)

# Broad T-shaped circulation, two consultation rooms, records, shared office, chief office and clinical support.
rects=[(-900,-2300,1700,0),(1700,-1320,2000,-880)]
for x0,y0,x1,y1 in rects:
 box('FloorSlabs',[(x0+x1)/2,(y0+y1)/2,-12],[x1-x0,y1-y0,24],col=True)
 box('Roof',[(x0+x1)/2,(y0+y1)/2,452],[x1-x0,y1-y0,24],col=True)
 nx,ny=math.ceil((x1-x0)/90),math.ceil((y1-y0)/90)
 for i in range(nx):
  for j in range(ny):
   sx,sy=(x1-x0)/nx,(y1-y0)/ny
   box('FloorFinish',[x0+(i+.5)*sx,y0+(j+.5)*sy,.3],[sx-.5,sy-.5,.6],'Floor')
wall((-900,0),(1700,0),[(900,300,0,280)])
wall((-900,-2300),(-900,0))
wall((1700,-2300),(-900,-2300))
wall((1700,0),(1700,-2300),[(1100,440,0,440)],framed=False)
wall((1700,-880),(2000,-880));wall((2000,-1320),(1700,-1320))
wall((2000,-880),(2000,-1320),[(220,300,0,280)])
# 320 cm combined leaf width plus 3 cm each side for the 5 cm leaf thickness
# rotating about its outer centreline hinge. These are interior openings only.
wall((-210,0),(-210,-2300),[(500,326,0,300),(1330,326,0,300),(1990,326,0,300)],tiles=True)
wall((210,-880),(210,0),[(430,326,0,300)],tiles=True)
wall((1700,-880),(210,-880),[(730,326,0,300)],tiles=True)
wall((210,-1320),(1700,-1320),[(370,326,0,300),(1140,326,0,300)],tiles=True)
wall((-900,-900),(-210,-900));wall((-900,-1700),(-210,-1700))
wall((960,-2300),(960,-1320))
# The records suite can also be reached from the rear of the main spine.
wall((210,-2300),(210,-1320))
# Ceiling coffers and narrow services support a hospital corridor without low obstacles.
for y in range(-2200,0,400):box('CeilingGrid',[0,y,429],[390,8,18],'Steel')
for x in range(300,1700,400):box('CeilingGrid',[x,-1100,429],[8,390,18],'Steel')
for y in (-180,-820,-1430,-2190):
 box('CeilingGrid',[960,y,427],[1430,9,20],'Steel')
for x in (-120,120):box('Services',[x,-1150,420],[30,2210,20],'Steel')
# Corridor direction insets are physical trim, flush below the walking plane.
box('FloorWayfinding',[0,-660,.75],[10,1170,.04],'Blue')
box('FloorWayfinding',[1020,-1100,.75],[1870,10,.04],'Blue')
# Short fixture mounting straps close the actual 5.75 cm ceiling gap.
mounts=[(0,y) for y in (-210,-690,-1170,-1650,-2130)]
mounts += [(x,-1100) for x in (540,1050,1570,1850)]
mounts += [(-585,y) for y in (-300,-710,-1150,-1500,-1990)]
mounts += [(x,y) for x in (570,1250) for y in (-300,-690)]
mounts += [(580,-1640),(580,-2070),(1350,-1630),(1350,-2070)]
for x,y in mounts:
 for dx in (-45,45):box('CeilingGrid',[x+dx,y,437.1],[6,6,5.8],'Steel')

font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
def sign(text,c,normal,width=230,size=26):
 n=Vector((normal[0],-normal[1],0));up=Vector((0,0,1));right=up.cross(n);center=Vector(pt(c))
 yaw=math.degrees(math.atan2(normal[1],normal[0]))-90
 box('Signs',c,[width,5,60],'Blue',yaw)
 curve=bpy.data.curves.new(text,'FONT');curve.body=text;curve.font=font;curve.align_x='CENTER';curve.align_y='CENTER'
 curve.size=size/100;curve.extrude=.001;curve.resolution_u=3
 obj=bpy.data.objects.new(text,curve);bpy.context.collection.objects.link(obj)
 q=center+n*.027;obj.matrix_world=Matrix(((right.x,up.x,n.x,q.x),(right.y,up.y,n.y,q.y),(right.z,up.z,n.z,q.z),(0,0,0,1)))
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH')
 g.poly('Signs',[obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices) for f in obj.data.polygons],'Text')
 bpy.data.objects.remove(obj,do_unlink=True)
sign('医生办公室  /  CLINICAL OFFICES',[0,-14.8,334],[0,-1],650,35)
# The external entrance plate is inset into its header and remains within the room envelope.
sign('医疗办公区  /  DOCTORS',[0,11.2,334],[0,1],650,35)
sign('01  全科诊室',[-195.2,-500,340],[1,0],250)
sign('02  复诊室',[-195.2,-1330,340],[1,0],250)
sign('病历档案',[-195.2,-1990,340],[1,0],230)
sign('医生工作室',[195.2,-450,340],[-1,0],250)
sign('主任办公室',[580,-1305.2,340],[0,1],270)
sign('检查准备室',[1350,-1305.2,340],[0,1],270)
sign('候诊区   WAITING',[970,-894.8,345],[0,-1],420)
sign('隔离病房  →',[1640,-1305.2,347],[0,1],270,24)

records=[]
for (_,kind),data in g.G.items():
 if not data['f']:continue
 name='SM_MedicalOffice_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
 order=list(dict.fromkeys(data['m']))
 for role in order:mesh.materials.append(MATS[role])
 uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
 for f,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
  f.material_index=order.index(role);f.use_smooth=smooth
  axes=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(f.normal[a]))]
  for j,li in enumerate(f.loop_indices):
   p=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=coords[j] if coords else (p[axes[0]]/2,p[axes[1]]/2)
   age.data[li].color=(.14+.08*math.exp(-abs(p.z)/.25),0,0,1)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 if kind!='Tiles':
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 cols=[]
 for i,(vs,fs) in enumerate(g.C.get((g.ROOM,kind),[])):
  cm=bpy.data.meshes.new('UCX_'+name+'_%03d'%i);cm.from_pydata(vs,[],fs);cm.update();co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
 fbx=OUT/(name+'.fbx')
 if not os.environ.get('MEDICAL_OFFICE_EXPORT_KINDS') or kind in os.environ['MEDICAL_OFFICE_EXPORT_KINDS'].split(','):
  bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
 for co in cols:co.hide_set(True);co.hide_render=True
 records.append(dict(name=name,kind=kind,mesh=BASE+'/Meshes/'+name,fbx=str(fbx),materials={MATS[r].name:MAP[r] for r in order},
   collision=bool(cols),collision_boxes=len(cols),nanite=True,cast_shadow=kind not in ('Signs','FloorWayfinding'),triangles=len(obj.data.polygons)))
 print('MEDICAL_OFFICE_GEOMETRY_EXPORTED',kind,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MedicalOfficeWing.blend'))
(ROOT/'Config/geometry.json').write_text(json.dumps(dict(meshes=records,area_m2=611.2,source_surfaces='DungeonTileFracture20260922',
 mid_rail=dict(tile_band_removed_cm=[91,98],tiled_face_cm=RAIL_TILE_FRONT_CM,revision='waiting_finish_20261010')),ensure_ascii=False,indent=2),encoding='utf8')
