"""Upgrade the existing building placements; keep shore, water and view composition.
Only the six building clusters are exported. Far geometry becomes production cubes.
"""
import bpy,sys,json,math,random
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
bpy.ops.wm.open_mainfile(filepath=str(OLD/'CyberpunkBay_Source.blend'))
scene=bpy.context.scene
old_manifest=json.loads((OLD/'assembly.json').read_text())
replace={'City_0','City_1','City_2','City_3','Landmarks','Harbor','FarCity','FarHeadland'}
for ob in list(bpy.data.objects):
 if ob.name in replace:bpy.data.objects.remove(ob,do_unlink=True)
groups={};buildings=[];mats={m.name:m for m in bpy.data.materials}
EXPORT.mkdir(parents=True,exist_ok=True)
def flat(name,color,metal=0,rough=.55,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for pin,val in [('Base Color',(*color,1)),('Metallic',metal),('Roughness',rough),('Emission Color',(*color,1)),('Emission Strength',emission)]:p.inputs[pin].default_value=val
 mats[name]=m;return m
flat('Frame',(.055,.070,.092),.65,.36)
flat('Stone',(.10,.125,.15),.15,.72)
flat('Roof',(.027,.038,.05),.3,.65)
flat('WarmLight',(.72,.38,.14),0,.5,1.2)
for family in ['Office','Residential','Tech']:
 m=flat(family,(.03,.04,.06));p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n=m.node_tree.nodes;l=m.node_tree.links
 for suffix,pin in [('BC','Base Color'),('E','Emission Color')]:
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(FACADES/f'T_{family}_{suffix}.png'));t.image.pack();l.new(t.outputs['Color'],p.inputs[pin])
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(FACADES/f'T_{family}_N_GL.png'));t.image.colorspace_settings.name='Non-Color';t.image.pack()
 norm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],norm.inputs['Color']);l.new(norm.outputs[0],p.inputs['Normal'])
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(FACADES/f'T_{family}_ORM.png'));t.image.colorspace_settings.name='Non-Color';t.image.pack()
 sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],p.inputs['Roughness']);l.new(sep.outputs['Blue'],p.inputs['Metallic'])
 p.inputs['Emission Strength'].default_value=1.1
def face(g,vs,mat='Frame',uv=None):
 data=groups.setdefault(g,dict(v=[],f=[],m=[],uv=[]));s=len(data['v']);data['v'].extend(vs)
 data['f'].append(tuple(range(s,s+len(vs))));data['m'].append(mat)
 if uv is None:uv=[(v[0]/ATLAS_METRES[0],v[2]/ATLAS_METRES[1]) for v in vs]
 data['uv'].append(uv)
def box(g,p,d,mat='Frame'):
 x,y,z=p;a,b,c=[v/2 for v in d]
 vs=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
 for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(g,[vs[i] for i in ids],mat)
def beam(g,a,b,width,depth=None,mat='Frame'):
 a=Vector(a);b=Vector(b);f=(b-a).normalized();ref=Vector((0,0,1)) if abs(f.z)<.95 else Vector((0,1,0))
 u=f.cross(ref).normalized()*width/2;v=f.cross(u).normalized()*(depth or width)/2
 pts=[tuple(p+du*u+dv*v) for p in [a,b] for du,dv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(g,[pts[i] for i in ids],mat)
def outline(x,y,w,d,roundness=0):
 pts=[(-.42,-.5),(.42,-.5),(.5,-.42),(.5,.42),(.42,.5),(-.42,.5),(-.5,.42),(-.5,-.42)]
 if roundness:pts=[(math.cos(i*math.tau/roundness)*.5,math.sin(i*math.tau/roundness)*.5) for i in range(roundness)]
 return [(x+a*w,y+b*d) for a,b in pts]
def shell(g,x,y,z,w,d,h,mat,roundness=0,taper=1,offset=0):
 low=outline(x,y,w,d,roundness);high=outline(x,y,w*taper,d*taper,roundness)
 face(g,[(a,b,z) for a,b in low][::-1],'Roof');face(g,[(a,b,z+h) for a,b in high],'Roof')
 distance=offset
 for i in range(len(low)):
  j=(i+1)%len(low);length=math.dist(low[i],low[j]);u0=distance/ATLAS_METRES[0];u1=(distance+length)/ATLAS_METRES[0]
  vs=[(*low[i],z),(*low[j],z),(*high[j],z+h),(*high[i],z+h)]
  face(g,vs,mat,[(u0,(z-5)/ATLAS_METRES[1]),(u1,(z-5)/ATLAS_METRES[1]),(u1,(z+h-5)/ATLAS_METRES[1]),(u0,(z+h-5)/ATLAS_METRES[1])]);distance+=length
def ring(g,x,y,z,w,d,h,thickness=.6,mat='Frame',roundness=0):
 outer=outline(x,y,w,d,roundness);inner=outline(x,y,w-2*thickness,d-2*thickness,roundness)
 for i in range(len(outer)):
  j=(i+1)%len(outer);a,b,c,dv=outer[i],outer[j],inner[j],inner[i]
  face(g,[(*a,z),(*b,z),(*b,z+h),(*a,z+h)],mat)
  face(g,[(*a,z+h),(*b,z+h),(*c,z+h),(*dv,z+h)],mat)
  face(g,[(*dv,z),(*c,z),(*b,z),(*a,z)],mat)
  face(g,[(*c,z),(*dv,z),(*dv,z+h),(*c,z+h)],mat)
def tier(g,x,y,z,w,d,h,family,neon,seed,roundness=0,taper=1):
 far=g.startswith('Far');rr=random.Random(seed)
 shell(g,x,y,z,w,d,h,family,roundness,taper,rr.randrange(24)*3.2)
 step=FLOOR*(2 if far else 1);count=int(h/step)
 for i in range(1,count+1):
  zz=min(h,i*step);s=1+(taper-1)*zz/h
  ring(g,x,y,z+zz-.32,w*s+.9,d*s+.9,.32,.85,'Frame',roundness)
 # Structural verticals are backed by the facade, with the same taper.
 low=outline(x,y,w+.65,d+.65,roundness);high=outline(x,y,w*taper+.65,d*taper+.65,roundness)
 for i in range(len(low)):
  j=(i+1)%len(low);segments=max(1,int(math.dist(low[i],low[j])/(12 if far else 8)))
  for k in range(segments):
   t=k/segments;a=Vector(low[i]).lerp(Vector(low[j]),t);b=Vector(high[i]).lerp(Vector(high[j]),t)
   beam(g,(*a,z),(*b,z+h),.58,.7)
 ring(g,x,y,z+h,w*taper+1.1,d*taper+1.1,1.5,.7,'Stone',roundness)
 # A few architectural crown light ribbons, not glowing outlines on every floor.
 if seed%3==0:ring(g,x,y,z+h+.3,w*taper+1.2,d*taper+1.2,.25,.25,neon,roundness)
 return (x,y,z+h,w*taper,d*taper,roundness)
def equipment(g,roof,seed):
 x,y,z,w,d,ro=roof;rr=random.Random(seed);far=g.startswith('Far')
 shell(g,x,y,z,w*.27,d*.28,4.2,'Roof')
 for i in range(2 if far else 3):
  xx=x+(i-1)*min(5,w*.13);yy=y+d*.23
  box(g,(xx,yy,z+1.6),(3.5,4.4,3.2),'Frame')
  if not far:
   for k in range(4):box(g,(xx,yy-1.6+k*.95,z+3.25),(3.1,.22,.12),'Roof')
 if seed%4==0:
  beam(g,(x,y,z+4),(x,y,z+14),.65)
  box(g,(x,y,z+14.4),(.9,.9,.6),'Navigation')
 if not far:
  for s in [-1,1]:
   beam(g,(x+s*w*.25,y+d*.2,z+.6),(x+s*w*.25,y-d*.24,z+.6),.5)
def signage(g,x,y,z,w,h,k):
 # Mounted on an actual flat wall; no detached billboard card.
 box(g,(x,y-.22,z),(w+.8,.65,h+.8),'Frame')
 u0=(k%4+.065)/4;u1=(k%4+.935)/4;v0=1-(k//4+.935)/4;v1=1-(k//4+.065)/4
 face(g,[(x-w/2,y-.56,z-h/2),(x+w/2,y-.56,z-h/2),(x+w/2,y-.56,z+h/2),(x-w/2,y-.56,z+h/2)],'Signs',[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
def tower(row,index):
 g=row['group'];x=row['x'];y=row['y'];w=row['width'];d=row['depth'];h=round(row['height']/FLOOR)*FLOOR
 style=row['style'];far=g.startswith('Far');seed=index*37+101;neon='Neon'+str(index%4)
 family=['Residential','Office','Office','Tech','Residential'][style];z=5;roofs=[]
 # Quays are at +5 m: podiums meet them without burying their ground floor.
 podium=FLOOR*2
 shell(g,x,y,z,w*1.16,d*1.12,podium,'Office');ring(g,x,y,z+podium,w*1.2,d*1.16,1.0,1.3,'Stone')
 if not far:
  for i in range(max(3,int(w/9))):
   xx=x-w*.48+(i+.5)*w*.96/max(3,int(w/9))
   box(g,(xx,y-d*.565,z+podium*.48),(.85,1.1,podium*.96),'Stone')
  box(g,(x,y-d*.59,z+podium-.8),(w*.85,3.2,.4),'Frame')
  box(g,(x,y-d*.61,z+podium-1.1),(w*.74,.4,.2),'WarmLight')
 z+=podium;main=max(FLOOR*5,h-podium)
 if style in (0,4):
  ratios=[.44,.34,.22] if style==0 else [1/3]*3
  running=0
  for i,f in enumerate(ratios):
   hh=main-running if i==2 else round(main*f/FLOOR)*FLOOR
   ox=(i%2)*w*.04 if style==0 else 0;oy=i*d*.065 if style==4 else 0
   roof=tier(g,x+ox,y+oy,z+running,w*(1-i*.16),d*(1-i*.17),hh,family,neon,seed+i)
   roofs.append(roof);running+=hh
 elif style==1:
  roofs.append(tier(g,x,y,z,w,d,main,family,neon,seed,32,.90))
  # Faceted crown shutters at real roof elevation, supported on the parapet.
  roof=roofs[-1]
  ring(g,x,y,roof[2]+1.5,roof[3]*.86,roof[4]*.86,6.5,1.2,'Frame',32)
  ring(g,x,y,roof[2]+7.8,roof[3]*.87,roof[4]*.87,.4,.5,neon,32)
 elif style==2:
  for sign in [-1,1]:roofs.append(tier(g,x+sign*w*.30,y,z,w*.37,d,main*(1 if sign<0 else .86),family,neon,seed+sign))
  bh=round(main*.66/FLOOR)*FLOOR
  shell(g,x,y,z+bh,w*.58,d*.38,FLOOR*2,'Office')
  box(g,(x,y-d*.19-.15,z+bh),(w*.58,.7,.5),neon)
  for side in [-1,1]:beam(g,(x-w*.24,y+side*d*.18,z+bh),(x+w*.24,y+side*d*.18,z+bh+FLOOR*2),.85)
 elif style==3:
  low=round(main*.44/FLOOR)*FLOOR
  tier(g,x,y,z,w*.72,d*.78,low,family,neon,seed)
  roofs.append(tier(g,x-w*.06,y,z+low,w,d,main-low,family,neon,seed+1))
  # Broad diagonal exoskeleton supports the cantilever on both visible sides.
  for side in [-1,1]:
   yy=y+side*d*.505
   for k in range(3):
    zz=z+low+k*(main-low)/3
    beam(g,(x-w*.45,yy,zz),(x+w*.33,yy,zz+(main-low)/3),1.4,1.8)
  box(g,(x-w*.48,y-d*.515,z+low+(main-low)/2),(1.1,.8,(main-low)*.90),neon)
 for i,roof in enumerate(roofs):
  if i==len(roofs)-1 or style==2:equipment(g,roof,seed+i)
 if not far and index%3!=1:
  # Signs belong to the podium so terraces/twin-tower openings remain unobstructed.
  signage(g,x,y-d*.56,z-podium*.48,min(w*.33,22),podium*.58,index%16)
 buildings.append(dict(**row,authored_height=h,facade=family,roof_equipment_supported=True))
for i,row in enumerate(old_manifest['buildings']):tower(row,i)
# Waterfront terminals: ribbed canopies, real trusses, recessed departure hall.
for idx,(x,y) in enumerate([(-760,1080),(-270,1160),(200,1280)]):
 g='Harbor';box(g,(x,y-38,3),(92,95,6),'Stone')
 shell(g,x,y-30,6,56,40,14,'Office')
 box(g,(x,y-30,20.5),(68,48,1),'Frame')
 for i in range(9):
  xx=x-30+i*7.5;beam(g,(xx,y-56,19.8),(xx,y-4,23.2),.6)
  if i%2==0:beam(g,(xx,y-52,6),(xx,y-52,20),.9)
 box(g,(x,y-54.2,19.5),(64,.45,.4),'Neon0');signage(g,x,y-50,14,20,6,7)
for idx,(x,y) in enumerate([(1080,2020),(1220,2210)]):
 g='Harbor'
 for side in [-1,1]:
  xx=x+side*15
  beam(g,(xx,y-10,5),(xx,y+3,64),2.0,2.6)
  beam(g,(xx,y+20,5),(xx,y+3,64),2.0,2.6)
  for k in range(4):beam(g,(xx,y-8+k*2,10+k*12),(xx,y+18-k*3,22+k*12),.7)
 for zz in [64,69]:
  for xx in [x-5,x+5]:beam(g,(xx,y-79,zz),(xx,y+28,zz),1)
 for k in range(10):
  yy=y-79+k*10.7
  for xx in [x-5,x+5]:beam(g,(xx,yy,64),(xx,yy+10.7,69),.55)
 beam(g,(x-16,y+3,64),(x+16,y+3,64),2)
 box(g,(x+7,y-15,62),(5,6,5),'Office');beam(g,(x,y-60,64),(x,y-60,30),.3)
 box(g,(x,y-60,29),(7,2,1),'Frame');box(g,(x,y+20,70),(1,1,.8),'Navigation')
objects={ob.name:ob for ob in scene.objects if ob.type=='MESH'}
records=[]
for name,data in groups.items():
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob);objects[name]=ob
 order=list(dict.fromkeys(data['m']))
 for key in order:mesh.materials.append(mats[key])
 uv=mesh.uv_layers.new(name='ArchitecturalUV')
 for poly,key,coords in zip(mesh.polygons,data['m'],data['uv']):
  poly.material_index=order.index(key)
  for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co
 if name.startswith('Far'):continue
 copy=ob.copy();copy.data=ob.data.copy();scene.collection.objects.link(copy);copy.name='SM_DetailedBay_'+name
 for v in copy.data.vertices:v.co=(-v.co.x+10,-v.co.y,v.co.z-90)
 bpy.ops.object.select_all(action='DESELECT');copy.select_set(True);bpy.context.view_layer.objects.active=copy
 mod=copy.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 fbx=EXPORT/(copy.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_tspace=True)
 records.append(dict(key=name,name=copy.name,fbx=str(fbx),asset=DEST+'/Meshes/'+copy.name,triangles=len(copy.data.polygons),materials=order,nanite=True))
 bpy.data.objects.remove(copy,do_unlink=True)
scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.cycles.max_bounces=2
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
 prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.film_transparent=True
scene.render.image_settings.color_mode='RGBA'
for ob in objects.values():ob.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'DetailedBay_Source.blend'))
(ROOT/'assembly.json').write_text(json.dumps(dict(stage='meshes_authored',revision=OWNER,meshes=records,buildings=buildings,
 retained_meshes=['Quay_0','Quay_1','Quay_2','Quay_3','NearBank','Water'],sky_source='MI_HDR_Night_Sky',
 production_texture_bake=True,tests_run=False,acceptance_rendered=False),indent=2),encoding='utf8')
views=[('PX',(1,0,0),(0,0,1)),('NX',(-1,0,0),(0,0,1)),('PY',(0,0,1),(0,-1,0)),('NY',(0,0,-1),(0,1,0)),('PZ',(0,1,0),(0,0,1)),('NZ',(0,-1,0),(0,0,1))]
report=dict(stage='baking',samples=32,captures={})
for capture,res,pos in [('Far',FAR_FACE_SIZE,EYE),('Reflection',REFLECTION_FACE_SIZE,(0,200,1))]:
 folder=ROOT/'CubeFaces'/capture;folder.mkdir(parents=True,exist_ok=True)
 for key,ob in objects.items():ob.hide_render=(not key.startswith('Far')) if capture=='Far' else key=='Water'
 scene.render.resolution_x=res;scene.render.resolution_y=res;scene.camera.location=pos
 report['captures'][capture]=dict(size=res,origin=pos,faces=[])
 for name,forward,up in views:
  f=Vector(forward);up=Vector(up);scene.camera.rotation_euler=Matrix((f.cross(up),up,-f)).transposed().to_euler()
  scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
  report['captures'][capture]['faces'].append(name)
  (ROOT/'bake-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('DETAILED_BAY_PRODUCTION_FACE',capture,name,flush=True)
report['stage']='production_cubes_baked';(ROOT/'bake-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('DETAILED_BAY_AUTHORED',flush=True)
