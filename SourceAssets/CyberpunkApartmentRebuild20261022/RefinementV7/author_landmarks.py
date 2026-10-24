"""Five original harbor landmarks on the retained footprints, no scene render."""
import bpy,ast,json,math,random,sys
from mathutils import Vector
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
old=PROJECT/'SourceAssets/CyberpunkBayBuildings20261022';out=ROOT/'Meshes';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(old/'DetailedBay_Source.blend'))
original=bpy.data.objects.get('Landmarks')
if original:bpy.data.objects.remove(original,do_unlink=True)
groups={};ATLAS_METRES=(76.8,121.6);FLOOR=3.8;mats={m.name:m for m in bpy.data.materials}
for name in ['Corporate','Financial','Housing','Terraces','Data','Harbor']:
 m=bpy.data.materials.new(name);m.diffuse_color=(.035,.05,.07,1);m.use_nodes=True;mats[name]=m
 nodes=m.node_tree.nodes;links=m.node_tree.links;principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 for suffix,pin in [('BC','Base Color'),('E','Emission Color')]:
  t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'Textures'/f'T_AP7_{name}_{suffix}.png'));t.image.pack();links.new(t.outputs['Color'],principled.inputs[pin])
 t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'Textures'/f'T_AP7_{name}_N.png'));t.image.colorspace_settings.name='Non-Color';t.image.pack()
 split=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],split.inputs[0]);green=nodes.new('ShaderNodeMath');green.operation='SUBTRACT';green.inputs[0].default_value=1;links.new(split.outputs['Green'],green.inputs[1])
 combined=nodes.new('ShaderNodeCombineColor');links.new(split.outputs['Red'],combined.inputs['Red']);links.new(green.outputs[0],combined.inputs['Green']);links.new(split.outputs['Blue'],combined.inputs['Blue'])
 normal=nodes.new('ShaderNodeNormalMap');links.new(combined.outputs[0],normal.inputs['Color']);links.new(normal.outputs[0],principled.inputs['Normal'])
 t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'Textures'/f'T_AP7_{name}_ORM.png'));t.image.colorspace_settings.name='Non-Color';t.image.pack()
 split=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],principled.inputs['Roughness']);links.new(split.outputs['Blue'],principled.inputs['Metallic']);principled.inputs['Emission Strength'].default_value=1.15
tree=ast.parse((old/'author_scene.py').read_text('utf8'))
names={'face','box','outline','shell','ring','beam','tier','equipment','signage'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'retained_architecture_helpers','exec'),globals())
_face=face
def face(g,vs,mat='Frame',uv=None):
 if uv is None:
  # Roofs, side returns and beam caps need a two-dimensional projection.
  # The retained facade helper supplies its own architectural UVs unchanged.
  origin=Vector(vs[0]);normal=Vector((0,0,0))
  for i in range(1,len(vs)-1):normal+=(Vector(vs[i])-origin).cross(Vector(vs[i+1])-origin)
  dominant=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=dominant]
  uv=[(v[axes[0]]/ATLAS_METRES[0],v[axes[1]]/ATLAS_METRES[1]) for v in vs]
 _face(g,vs,mat,uv)
_shell=shell
def shell(g,x,y,z,w,d,h,mat,roundness=0,taper=1,offset=0):
 first=len(groups.get(g,{}).get('f',[]));_shell(g,x,y,z,w,d,h,mat,roundness,taper,offset)
 if mat in ['Corporate','Financial','Housing','Terraces','Data','Harbor']:
  data=groups[g]
  for i in range(first,len(data['f'])):
   if data['m'][i]==mat:data['uv'][i]=[(a,b-(z-5)/ATLAS_METRES[1]) for a,b in data['uv'][i]]
records=[];designs=[]
def podium(g,x,y,w,d,family):
 shell(g,x,y,5,w*1.1,d*1.1,11.4,family)
 ring(g,x,y,16.4,w*1.13,d*1.13,.8,1.8,'Stone')
 # Recessed entrance canopy with real supporting columns.
 box(g,(x,y-d*.59,12),(w*.62,8,1.1),'Frame')
 for xx in [x-w*.26,x+w*.26]:beam(g,(xx,y-d*.59,5),(xx,y-d*.59,12),1.2,1.2)
 for xx in [x-w*.4,x+w*.4]:box(g,(xx,y-d*.551,9.5),(2,.8,7),'WarmLight')
def ribs(g,x,y,z,w,d,h,count=7):
 for i in range(count):
  xx=x-w/2+(i+.5)*w/count
  box(g,(xx,y-d/2-.65,z+h/2),(.9,1.3,h),'Frame')
def crown(g,x,y,z,w,d,neon='Neon0'):
 ring(g,x,y,z,w,d,5,1.5,'Frame');ring(g,x,y,z+4.6,w+.25,d+.25,.45,.45,neon)
 equipment(g,(x,y,z,w,d,0),39)

# Asymmetric towers connected by occupied sky bridges and a suspended crown.
g='Landmark_0';x=-680;y=1430;podium(g,x,y,88,86,'Financial')
for xx,w,h in [(x-25,33,342),(x+26,29,274)]:
 tier(g,xx,y,17.2,w,69,h,'Financial','Neon0',501,taper=.9)
 ribs(g,xx,y,17.2,w,69,h,5);crown(g,xx,y,17.2+h,w*.9,62)
for z in [146,244]:
 shell(g,x,y,z,46,28,11.4,'Corporate');box(g,(x,y-14.5,z+.6),(45,1,1),'WarmLight')
 for side in [-1,1]:beam(g,(x-19,y+side*14,z),(x+19,y+side*14,z+11.4),1.2,1.2)
designs.append(dict(key=g,name='NEXUS EXCHANGE',shape='asymmetric occupied twin towers and structural sky bridges'))

# Staggered octagonal finance tower, a stepped spiral outline rather than a tube.
g='Landmark_1';x=-360;y=1490;podium(g,x,y,77,77,'Corporate')
for i in range(6):
 z=17.2+i*43;w=70-i*5;cx=x+math.sin(i*.9)*5;cy=y+math.cos(i*.9)*5
 tier(g,cx,cy,z,w,w,43,'Corporate','Neon3',510+i,8,.97)
 ring(g,cx,cy,z+42,w+2,w+2,2.2,2.3,'Stone',8)
 if i%2==0:box(g,(cx+w/2+.8,cy,z+22),(1.3,w*.6,34),'Neon3')
ring(g,x-5,y,276,36,36,13,2,'Frame',8);ring(g,x-5,y,288,37,37,.6,.5,'Neon3',8)
beam(g,(x-5,y,289),(x-5,y,316),1.5,1.5);box(g,(x-5,y,317),(2,2,1.6),'Navigation')
designs.append(dict(key=g,name='HELIX TRUST',shape='six offset octagonal setbacks and an open crown'))

# A heavy data exchange with a visibly supported cantilever and ventilation decks.
g='Landmark_2';x=-1480;y=1450;podium(g,x,y,92,72,'Data')
for i,(z,w,d,h,dx) in enumerate([(17.2,68,62,68,0),(85.2,92,72,76,8),(161.2,76,60,91,-5)]):
 tier(g,x+dx,y,z,w,d,h,'Data','Neon0',530+i)
 for sign in [-1,1]:
  yy=y+sign*(d/2+1)
  for j in range(3):beam(g,(x+dx-w*.45+j*w*.3,yy,z),(x+dx-w*.15+j*w*.3,yy,z+h),2.4,2.0)
 for side in [-1,1]:box(g,(x+dx+side*w*.35,y-d/2-1,z+h*.5),(2.1,2,h*.75),'Neon0')
crown(g,x-5,y,252.2,62,48)
designs.append(dict(key=g,name='ESTUARY DATA EXCHANGE',shape='three structural cantilevers, heavy braces and louvred plant floors'))

# Residential sky terraces, multiple silhouettes and warm recessed window banks.
g='Landmark_3';x=390;y=1680;podium(g,x,y,78,88,'Housing')
for i,(dx,dy,h) in enumerate([(-23,0,201),(21,15,225),(4,-24,161)]):
 tier(g,x+dx,y+dy,17.2,31,39,h,'Housing','Neon1',551+i)
 for z in range(40,int(h),38):
  ring(g,x+dx,y+dy,17.2+z,35,43,2.2,3.2,'Stone')
  box(g,(x+dx,y+dy-22,18+z),(29,1.8,.35),'WarmLight')
  for a in [-11,11]:box(g,(x+dx+a,y+dy-18,19+z),(4,5,2),'Roof')
 crown(g,x+dx,y+dy,17.2+h,28,36,'Neon1')
designs.append(dict(key=g,name='TIDELINE RESIDENCES',shape='warm three-wing housing, planted terrace basins and varied roof heights'))

# Port communications tower: tapered pylons carry a broad occupied observation ring.
g='Landmark_4';x=1120;y=2420;podium(g,x,y,110,90,'Harbor')
tier(g,x,y,17.2,36,40,132,'Harbor','Neon2',570,8,.75)
for dx,dy in [(-36,-23),(36,-23),(0,34)]:beam(g,(x+dx,y+dy,17.2),(x+dx*.35,y+dy*.35,158),4.3,5.2)
tier(g,x,y,149.2,96,80,22.8,'Corporate','Neon2',571,16,.90)
ring(g,x,y,170,101,85,4,3,'Frame',16);ring(g,x,y,174,102,86,.7,.7,'Neon2',16)
tier(g,x,y,175,30,30,27,'Harbor','Neon2',572,8,.70)
beam(g,(x,y,202),(x,y,232),1.4,1.4);box(g,(x,y,232),(2,2,1),'Navigation')
designs.append(dict(key=g,name='PORT SIGNAL AUTHORITY',shape='tapered pylons, occupied panoramic ring and communications mast'))

for name,data in groups.items():
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
 order=list(dict.fromkeys(data['m']))
 for mat in order:mesh.materials.append(mats[mat])
 uv=mesh.uv_layers.new(name='ArchitecturalUV')
 for p,key,coords in zip(mesh.polygons,data['m'],data['uv']):
  p.material_index=order.index(key)
  for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
 copy=ob.copy();copy.data=ob.data.copy();bpy.context.collection.objects.link(copy);copy.name='SM_AP7_'+name
 for v in copy.data.vertices:v.co=(-v.co.x+10,-v.co.y,v.co.z-90)
 bpy.ops.object.select_all(action='DESELECT');copy.select_set(True);bpy.context.view_layer.objects.active=copy
 mod=copy.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 fbx=out/(copy.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=name,name=copy.name,fbx=str(fbx),asset=BASE+'/Meshes/'+copy.name,triangles=len(copy.data.polygons),nanite=True,collision=False))
 bpy.data.objects.remove(copy,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'BayLandmarks_Source.blend'))
(ROOT/'city-assembly.json').write_text(json.dumps(dict(meshes=records,designs=designs,source_layout_preserved=True,rendered=False),indent=2),encoding='utf8')
print('AP7_LANDMARKS_AUTHORED',len(records),flush=True)
