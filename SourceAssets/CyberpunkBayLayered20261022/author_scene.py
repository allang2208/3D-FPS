"""Build a spatially consistent bay, export grouped midground and bake the far city.
Only production textures are rendered. No game or acceptance capture is performed.
"""
import bpy,math,json,random,sys
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
r=random.Random(SEED)
EXPORT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
groups={};materials={};buildings=[]

def material(key,color,emission=0,rough=.55):
 m=bpy.data.materials.new(key);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
 p.inputs['Roughness'].default_value=rough
 p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
 materials[key]=m;return m
material('Concrete',(.035,.044,.060));material('Metal',(.009,.013,.021),rough=.3)
for k,c in enumerate(PALETTE):material('Neon'+str(k),c,1.4)
material('Navigation',(.8,.08,.025),2)
fac=material('Facade',(.03,.04,.055));p=fac.node_tree.nodes.get('Principled BSDF')
for file,pin in [('T_BayFacade_BC.png','Base Color'),('T_BayFacade_E.png','Emission Color')]:
 t=fac.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(FACADES/file));t.image.pack()
 fac.node_tree.links.new(t.outputs['Color'],p.inputs[pin])
p.inputs['Emission Strength'].default_value=1.3;p.inputs['Roughness'].default_value=.38
sg=material('Signs',(.01,.01,.02));p=sg.node_tree.nodes.get('Principled BSDF')
t=sg.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(FACADES/'T_BaySigns_E.png'));t.image.pack()
sg.node_tree.links.new(t.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=2

def face(group,verts,mat='Concrete',uv=None):
 g=groups.setdefault(group,dict(v=[],f=[],m=[],uv=[]));s=len(g['v']);g['v'].extend(verts)
 g['f'].append(tuple(range(s,s+len(verts))));g['m'].append(mat)
 if uv is None:
  n=(Vector(verts[1])-Vector(verts[0])).cross(Vector(verts[2])-Vector(verts[0]))
  axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=axis]
  uv=[(p[axes[0]]/102.4,p[axes[1]]/182.4) for p in verts]
 g['uv'].append(uv)

def box(g,p,d,mat='Concrete'):
 x,y,z=p;a,b,c=[v/2 for v in d]
 v=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
    (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
 for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(g,[v[i] for i in ids],mat)

def prism(g,x,y,z,w,d,h,mat='Facade',corners=8,taper=1):
 # Chamfered corners carry silhouette highlights without thousands of bevel polygons.
 pts=[(-.38,-.5),(.38,-.5),(.5,-.38),(.5,.38),(.38,.5),(-.38,.5),(-.5,.38),(-.5,-.38)]
 if corners!=8:pts=[(math.sin(i*math.tau/corners)*.5,math.cos(i*math.tau/corners)*.5) for i in range(corners)][::-1]
 low=[(x+a*w,y+b*d,z) for a,b in pts];high=[(x+a*w*taper,y+b*d*taper,z+h) for a,b in pts]
 face(g,low[::-1],'Metal');face(g,high,'Metal')
 offset=r.random()
 for i in range(len(pts)):
  j=(i+1)%len(pts);ww=(Vector(low[j])-Vector(low[i])).length
  face(g,[low[i],low[j],high[j],high[i]],mat,[(offset,0),(offset+ww/102.4,0),(offset+ww/102.4,h/182.4),(offset,h/182.4)])

def sign(g,x,y,z,w,h,k):
 box(g,(x,y+.5,z),(w+1,1,h+1),'Metal')
 col=k%4;row=k//4
 u0=(col+.065)/4;u1=(col+.935)/4;v0=1-(row+.935)/4;v1=1-(row+.065)/4
 face(g,[(x-w/2,y-.06,z-h/2),(x+w/2,y-.06,z-h/2),(x+w/2,y-.06,z+h/2),(x-w/2,y-.06,z+h/2)],
      'Signs',[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])

def tower(g,x,y,w,d,h,style,k):
 base=5;z=base
 box(g,(x,y,base/2),(w*1.22,d*1.18,base),'Concrete')
 neon='Neon'+str(k%4)
 if style==0: # stepped residential tower with a recessed service spine
  for frac,ww,dd,ox in [(.46,1,1,0),(.34,.82,.87,w*.06),(.20,.62,.72,-w*.04)]:
   prism(g,x+ox,y,z,w*ww,d*dd,h*frac);z+=h*frac
   box(g,(x+ox,y-d*dd/2-.08,z-.8),(w*ww*.78,.55,1.2),neon)
 elif style==1: # faceted round tower, broad crown
  prism(g,x,y,z,w,d,h,corners=16,taper=.88)
  prism(g,x,y,z+h-8,w*1.05,d*1.05,7,'Metal',16)
  prism(g,x,y,z+h-2,w*1.07,d*1.07,1.8,neon,16)
 elif style==2: # split towers and a real high skybridge opening
  for ox in [-w*.30,w*.30]:prism(g,x+ox,y,z,w*.36,d,h*(1 if ox<0 else .85))
  box(g,(x,y,z+h*.66),(w*.85,d*.42,6),'Facade')
  box(g,(x,y-d*.22,z+h*.66-3.2),(w*.85,.8,1),neon)
 elif style==3: # cantilevered data tower with dark vertical fins
  prism(g,x,y,z,w*.70,d*.78,h*.45)
  prism(g,x-w*.08,y,z+h*.45,w,d,h*.55,taper=.92)
  for a in [-.4,-.20,0,.20,.4]:box(g,(x+a*w,y-d*.51,z+h*.73),(.9,1.8,h*.50),'Metal')
  box(g,(x-w*.4,y-d*.52,z+h*.73),(1.6,.9,h*.48),neon)
 else: # lower terraced blocks, roof equipment and planted deck parapets
  for i in range(3):
   prism(g,x,y+i*d*.07,z+i*h/3,w*(1-i*.14),d*(1-i*.18),h/3)
  box(g,(x,y-d*.51,z+5),(w*.92,.8,1.2),neon)
 top=z+h
 box(g,(x,y,top+2),(w*.35,d*.32,4),'Metal')
 if h>150:
  box(g,(x,y,top+10),(1.2,1.2,14),'Metal');box(g,(x,y,top+17),(1.6,1.6,1.5),'Navigation')
 if not g.startswith('Far'):
  for side in [-1,1]:
   box(g,(x+side*w*.38,y-d*.50-.3,base+7),(1.8,1.1,13),neon)
  if k%3!=1:sign(g,x-w*.08,y-d*.56,base+h*.46,min(w*.48,25),min(h*.24,40),k%16)
 buildings.append(dict(group=g,x=x,y=y,width=w,depth=d,height=h,style=style))

# A continuous opposite shore occupies the central/left view. Its right end turns
# away into the estuary, leaving open sea rather than a second wall of buildings.
shore=[(-3600,1850),(-2600,1430),(-1800,1160),(-900,1090),(0,1230),(650,1490),(1120,1900),(1400,2500),(1470,3400)]
for i in range(len(shore)-1):
 a=Vector((*shore[i],0));b=Vector((*shore[i+1],0));g='Quay_'+str(i//2)
 tangent=(b-a).normalized();inland=Vector((-tangent.y,tangent.x,0));depth=600
 pts=[a,b,b+inland*depth,a+inland*depth]
 face(g,[(p.x,p.y,5) for p in pts]);face(g,[(a.x,a.y,-8),(b.x,b.y,-8),(b.x,b.y,5),(a.x,a.y,5)],'Metal')
 face(g,[(a.x,a.y,3.2),(b.x,b.y,3.2),(b.x,b.y,4.1),(a.x,a.y,4.1)],'Neon0')
 n=max(1,int((b-a).length/100))
 for j in range(n):
  p=a+(b-a)*(j+.5)/n+inland*85
  h=r.uniform(45,150);w=r.uniform(38,69);d=r.uniform(40,65)
  tower('City_'+str(i//2),p.x,p.y,w,d,h,j%5,j+i*11)
  if j%2==0:
   p+=inland*150;tower('City_'+str(i//2),p.x,p.y,w*1.2,d*1.2,h*r.uniform(1.1,1.8),(j+2)%5,j+i*5)

# Deliberate landmarks: skyline hierarchy instead of uniform random boxes.
for p in [(-680,1430,88,86,345,2,0),(-360,1490,77,77,292,1,2),(-1480,1450,92,72,260,3,1),
          (390,1680,78,88,230,0,3),(1120,2420,110,90,205,2,4)]:tower('Landmarks',*p)
# Lower ferry landing, terminals and cranes have a legible shoreline scale.
for x,y in [(-760,1080),(-270,1160),(200,1280)]:
 box('Harbor',(x,y-38,3),(92,95,6),'Concrete');box('Harbor',(x,y-30,11),(56,40,16),'Facade')
 box('Harbor',(x,y-30,20),(67,46,3),'Metal');sign('Harbor',x,y-51,12,24,9,7)
for x,y in [(1080,2020),(1220,2210)]:
 for a in [-15,15]:box('Harbor',(x+a,y,32),(3,8,64),'Metal')
 box('Harbor',(x,y-25,65),(41,105,4),'Neon2');box('Harbor',(x,y-65,43),(1.3,1.3,40),'Metal')

# Near-bank promenade below the apartment. It anchors the observation point to a shore.
near=[(-2200,-180),(-1100,-80),(-400,28),(0,36),(500,72),(1400,10),(2500,-240)]
for i in range(len(near)-1):
 a=Vector((*near[i],0));b=Vector((*near[i+1],0));land=Vector((0,-550,0));g='NearBank'
 face(g,[(p.x,p.y,3) for p in [a,a+land,b+land,b]])
 face(g,[(a.x,a.y,-10),(a.x,a.y,3),(b.x,b.y,3),(b.x,b.y,-10)],'Concrete')
 face(g,[(a.x,a.y,2.0),(b.x,b.y,2.0),(b.x,b.y,2.5),(a.x,a.y,2.5)],'Neon0')
 for j in range(max(1,int((b-a).length/45))):
  p=a+(b-a)*(j+.5)/max(1,int((b-a).length/45))
  box(g,(p.x,p.y-3,3.8),(.8,.8,1.6),'Metal')
  box(g,(p.x,p.y-3,4.45),(.82,.82,.18),'Neon2')

# Far source city: only its production capture is shipped, not its geometry.
for row in range(3):
 for i in range(54):
  x=-6500+i*150+r.uniform(-20,20);y=3100+row*240+max(0,x-200)*.65+r.uniform(0,60)
  if x>1350 and x<3500:continue # open river mouth, aligned with the midground shore
  tower('FarCity',x,y,r.uniform(58,110),r.uniform(65,95),r.uniform(90,300)*(1 if row==0 else .85),(i+row)%5,i+row*31)
for i in range(14):
 x=3800+i*190;y=4700+i*80
 tower('FarHeadland',x,y,r.uniform(70,120),80,r.uniform(50,155),i%5,i)

# Far land belongs to the production capture only; keep the mouth open between
# the two headlands and support every baked building with a shoreline silhouette.
face('FarTerrain',[(-7500,2880,4),(1320,2880,4),(1320,9000,4),(-7500,9000,4)],'Metal')
face('FarTerrain',[(3650,4350,4),(8000,4350,4),(8000,10000,4),(3650,10000,4)],'Metal')
for x1,x2,y in [(-7500,1320,2880),(3650,8000,4350)]:
 face('FarTerrain',[(x1,y,-15),(x2,y,-15),(x2,y,4),(x1,y,4)],'Metal')

objects={}
for name,data in groups.items():
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);objects[name]=obj
 order=list(dict.fromkeys(data['m']))
 for k in order:mesh.materials.append(materials[k])
 uv=mesh.uv_layers.new(name='FacadeUV')
 for poly,mat,coords in zip(mesh.polygons,data['m'],data['uv']):
  poly.material_index=order.index(mat)
  for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co

# Regular water near region transitions to large far quads; no per-frame capture.
sea=material('Water',(.006,.017,.024),rough=.13)
g='Water';xs=[-16000,-8000,-3000]+list(range(-1800,1801,40))+[3000,8000,16000]
ys=[-700]+list(range(-200,2201,40))+[3200,5000,10000,22000]
for a,b in zip(xs,xs[1:]):
 for c,d in zip(ys,ys[1:]):face(g,[(a,c,0),(b,c,0),(b,d,0),(a,d,0)],'Water')
data=groups[g];mesh=bpy.data.meshes.new(g);mesh.from_pydata(data['v'],[],data['f']);mesh.update();mesh.materials.append(sea)
uv=mesh.uv_layers.new(name='WaterUV')
for poly in mesh.polygons:
 for li in poly.loop_indices:
  p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p.x/100,p.y/100)
obj=bpy.data.objects.new(g,mesh);scene.collection.objects.link(obj);objects[g]=obj

records=[]
for key,ob in objects.items():
 if key.startswith('Far'):continue
 # Export a transformed copy: Blender-to-UE Y flip yields the declared world basis.
 copy=ob.copy();copy.data=ob.data.copy();scene.collection.objects.link(copy)
 copy.name='SM_Bay_'+key
 for v in copy.data.vertices:v.co=(-v.co.x+10,-v.co.y,v.co.z-90)
 bpy.ops.object.select_all(action='DESELECT');copy.select_set(True);bpy.context.view_layer.objects.active=copy
 tri=copy.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 fbx=EXPORT/(copy.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
  bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_tspace=True)
 records.append(dict(key=key,name=copy.name,fbx=str(fbx),asset=DEST+'/Meshes/'+copy.name,
  triangles=len(copy.data.polygons),materials=[m.name for m in copy.data.materials],nanite=key!='Water',collision=False))
 bpy.data.objects.remove(copy,do_unlink=True)

# Soft night sky, with broad atmospheric cloud variation and a subdued horizon.
world=bpy.data.worlds.new('BayNightSky');world.use_nodes=True;scene.world=world
n=world.node_tree.nodes;l=world.node_tree.links;n.clear();out=n.new('ShaderNodeOutputWorld');bg=n.new('ShaderNodeBackground')
tc=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(tc.outputs['Normal'],sep.inputs[0])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=0;ramp.color_ramp.elements[0].color=(.017,.012,.032,1)
ramp.color_ramp.elements[1].position=.7;ramp.color_ramp.elements[1].color=(.0015,.003,.011,1)
l.new(sep.outputs['Z'],ramp.inputs[0]);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4.2;noise.inputs['Detail'].default_value=3
l.new(tc.outputs['Normal'],noise.inputs['Vector']);mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.26
l.new(ramp.outputs[0],mix.inputs[1]);l.new(noise.outputs['Fac'],mix.inputs[2]);l.new(mix.outputs[0],bg.inputs['Color']);l.new(bg.outputs[0],out.inputs[0])
sun_data=bpy.data.lights.new('ProductionMoon','SUN');sun_data.energy=.55;sun_data.color=(.35,.49,1);sun_data.angle=.2
sun=bpy.data.objects.new('ProductionMoon',sun_data);scene.collection.objects.link(sun);sun.rotation_euler=(.55,-.35,-.7)
camera=bpy.data.cameras.new('ProductionCubemap');camera.lens=18;camera.sensor_width=36;camera.clip_end=80000
cam=bpy.data.objects.new('ProductionCubemap',camera);scene.collection.objects.link(cam);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.cycles.max_bounces=1
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
 prefs.compute_device_type='OPTIX';prefs.get_devices()
 available=[d for d in prefs.devices if d.type=='OPTIX']
 if available:
  for d in prefs.devices:d.use=d.type=='OPTIX'
  scene.cycles.device='GPU'
except Exception:pass
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.film_transparent=False
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'CyberpunkBay_Source.blend'))
manifest=dict(stage='meshes_authored',revision=OWNER,meshes=records,buildings=buildings,shore=shore,near_shore=near,
 observer=EYE,sea_level_ue_cm=-9000,far_face_size=FAR_FACE_SIZE,reflection_face_size=REFLECTION_FACE_SIZE,
 water_parent=WATER_PARENT,former_background_used=False,production_texture_bake=True,tests_run=False,acceptance_rendered=False)
(ROOT/'assembly.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
views=[('PX',(1,0,0),(0,0,1)),('NX',(-1,0,0),(0,0,1)),('PY',(0,0,1),(0,-1,0)),
       ('NY',(0,0,-1),(0,1,0)),('PZ',(0,1,0),(0,0,1)),('NZ',(0,-1,0),(0,0,1))]
report=dict(stage='baking',captures={})
for capture,res,pos in [('Far',FAR_FACE_SIZE,EYE),('Reflection',REFLECTION_FACE_SIZE,(0,200,1))]:
 folder=ROOT/'CubeFaces'/capture;folder.mkdir(parents=True,exist_ok=True)
 for key,ob in objects.items():ob.hide_render=(not key.startswith('Far')) if capture=='Far' else key=='Water'
 scene.render.resolution_x=res;scene.render.resolution_y=res;cam.location=pos
 report['captures'][capture]=dict(size=res,origin=pos,faces=[])
 for name,forward,up in views:
  f=Vector(forward);up=Vector(up);right=f.cross(up);cam.rotation_euler=Matrix((right,up,-f)).transposed().to_euler()
  scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
  report['captures'][capture]['faces'].append(name)
  (ROOT/'bake-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('BAY_PRODUCTION_FACE_SAVED',capture,name,flush=True)
report['stage']='production_cubes_baked';(ROOT/'bake-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BAY_SOURCE_AUTHORING_COMPLETE',flush=True)
