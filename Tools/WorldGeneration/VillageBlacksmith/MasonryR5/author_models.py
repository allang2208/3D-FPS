"""Build a broad, bonded chimney from the house's own UV-mapped stone geometry."""
import bpy,math,json,random
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/MasonryR5';AUTH=OUT/'Authored';AUTH.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HouseStoneBank.blend'))
bpy.context.preferences.filepaths.save_version=0
bank=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.location.y>.02 and o.dimensions.x>.25 and o.dimensions.z>.16]
if not bank:raise RuntimeError('House stone bank has no usable outer-face blocks')
for o in bpy.context.scene.objects:o.hide_set(True)
rng=random.Random(1711175)
mats={n:bpy.data.materials.new(n) for n in ('HouseStone','HouseMortar','Iron','Stone')}
parts=[];collision=[];assets=[]
def vec(p):return Vector((p[0]/100,-p[1]/100,p[2]/100))
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def collider(c,s):collision.append(dict(center=list(c),size=list(s),rotation=[0,0,0]))
def box(name,c,s,mat='HouseMortar',solid=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=vec(c));o=bpy.context.object;o.name=name;o.dimensions=Vector(s)/100
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(mats[mat]);parts.append(o)
 if mat!='HouseMortar':
  b=o.modifiers.new('Worn edges','BEVEL');b.width=.003;b.segments=2;apply(o,b)
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='SurfaceMetres')
 for f in o.data.polygons:
  axes=[a for a in range(3) if a!=max(range(3),key=lambda j:abs(f.normal[j]))]
  for i in f.loop_indices:
   p=o.data.vertices[o.data.loops[i].vertex_index].co;uv.data[i].uv=(p[axes[0]],p[axes[1]])
 if solid:collider(c,s)
 return o
def stone(c,s,yaw):
 donor=rng.choice(bank);o=donor.copy();o.data=donor.data.copy();bpy.context.collection.objects.link(o);o.hide_set(False)
 o.name='Bonded house fieldstone';o.location=vec(c);o.rotation_euler=(0,0,0);o.scale=(1,1,1);o.dimensions=Vector(s)/100
 active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.rotation_euler.z=math.radians(-yaw+rng.uniform(-1.8,1.8))
 o.data.materials.clear();o.data.materials.append(mats['HouseStone'])
 for f in o.data.polygons:f.material_index=0
 parts.append(o)
def face(side,lo,hi,z0,z1,outer,depth,course):
 if hi-lo<6 or z1-z0<4:return
 count=max(1,round((hi-lo)/rng.uniform(47,61)))
 weights=[rng.uniform(.85,1.15) for _ in range(count)];span=(hi-lo)/sum(weights);cursor=lo
 for w in weights:
  width=w*span;mid=cursor+width/2;cursor+=width
  d=depth+rng.uniform(-2,2);c=(outer-d)/2+rng.uniform(-.7,.7)
  z=(z0+z1)/2
  if side=='front':p=(mid,-c,z);yaw=0
  elif side=='back':p=(mid,c,z);yaw=180
  elif side=='right':p=(c,mid,z);yaw=90
  else:p=(-c,mid,z);yaw=-90
  stone(p,(width-1.1,d,z1-z0-1.),yaw)
def course(z0,z1,outer,index,port=False):
 inner=54.;depth=(outer-inner)/2+2
 core=outer-15
 # Continuous recessed mortar core seals the bedding joints, leaving the flue hollow.
 for sign in (-1,1):
  box('Recessed side mortar',(sign*(core+inner)/4,0,(z0+z1)/2),((core-inner)/2,core,z1-z0))
  collider((sign*(outer+inner-1)/4,0,(z0+z1)/2),((outer-inner-1)/2,outer-1,z1-z0))
 for sign in (-1,1):
  cy=sign*(core+inner)/4;thick=(core-inner)/2
  if sign==-1 and port and z0<258 and z1>196:
   if z0<196:
    box('Port sill core',(0,cy,(z0+196)/2),(inner,thick,196-z0))
    collider((0,sign*(outer+inner-1)/4,(z0+196)/2),(inner,(outer-inner-1)/2,196-z0))
   if z1>258:
    box('Port lintel core',(0,cy,(258+z1)/2),(inner,thick,z1-258))
    collider((0,sign*(outer+inner-1)/4,(258+z1)/2),(inner,(outer-inner-1)/2,z1-258))
  else:
   box('Recessed face mortar',(0,cy,(z0+z1)/2),(inner,thick,z1-z0))
   collider((0,sign*(outer+inner-1)/4,(z0+z1)/2),(inner,(outer-inner-1)/2,z1-z0))
 for side in ('front','back','left','right'):
  long=(side in ('front','back'))==(index%2==0)
  half=outer/2 if long else (outer-2*depth)/2+8
  if side=='front' and port and z0<258 and z1>196:
   face(side,-half,-31,z0,z1,outer,depth,index);face(side,31,half,z0,z1,outer,depth,index)
   if z0<196:face(side,-31,31,z0,196,outer,depth,index)
   if z1>258:face(side,-31,31,258,z1,outer,depth,index)
  else:face(side,-half,half,z0,z1,outer,depth,index)
def finish(role):
 global parts,collision
 active(parts[0])
 for o in parts:o.hide_set(False);o.select_set(True)
 bpy.ops.object.join();o=parts[0];o.name='SM_SmithLoft_'+role+'_R5'
 o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
 tri=o.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;apply(o,tri)
 lods=[]
 for level,ratio in ((0,1),(1,.52),(2,.25)):
  q=o
  if level:
   q=o.copy();q.data=o.data.copy();bpy.context.collection.objects.link(q)
   dec=q.modifiers.new('Distance geometry','DECIMATE');dec.ratio=ratio;dec.delimit={'MATERIAL','UV'};apply(q,dec)
  active(q);file=AUTH/(o.name+(f'_LOD{level}' if level else '')+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
  q.data.calc_loop_triangles();lods.append(dict(level=level,file=str(file),triangles=len(q.data.loop_triangles)))
  if level:bpy.data.objects.remove(q,do_unlink=True)
 assets.append(dict(role=role,name=o.name,lods=lods,materials=[m.name for m in o.data.materials],collision_boxes=collision,preserve_source_uv=True))
 o.location.x=len(assets)*15;parts=[];collision=[]

course(0,24,182,0)
levels=[24,60,96,132]+list(range(168,1100,36))+[1100]
for i,(z0,z1) in enumerate(zip(levels,levels[1:])):course(z0,z1,162 if z0<132 else 146,i+1,True)
course(1100,1124,176,0);course(1124,1150,108,1)
for z in (285,590,870):
 for x in (-56,56):box('Chimney wall anchor',(x,-90,z),(5,52,5),'Iron')
finish('Chimney')

# Extend the accepted duct to the new shaft centre at house Y=500 cm.
for x in (-25,25):box('Duct side',(x,104,223.6),(1,172,45.2),'Iron')
for z in (201,246.2):box('Duct top bottom',(0,104,z),(50,172,1),'Iron')
for y in (20,103,184):
 for x in (-27,27):box('Collar side',(x,y,225),(4,4,54),'Iron')
 for z in (198,252):box('Collar crosspiece',(0,y,z),(58,4,4),'Iron')
finish('SmokeDuct')

# Preserve the approved front paving; widen only the buried chimney foundation.
old=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3/Authored/VillageBlacksmith_LoftR3.blend'
with bpy.data.libraries.load(str(old),link=False) as (src,dst):dst.objects=['SM_SmithLoft_Apron']
o=dst.objects[0];bpy.context.collection.objects.link(o);o.matrix_world=Matrix.Identity(4)
o.data.materials.clear();o.data.materials.append(mats['Stone']);o.data.materials.append(mats['HouseMortar'])
for v in o.data.vertices:
 if v.co.y<-3:
  v.co.x=2+(v.co.x-2)*200/152
  v.co.y=-5+(v.co.y+4.8)*196/148
for f in o.data.polygons:f.material_index=1 if sum(o.data.vertices[i].co.y for i in f.vertices)/len(f.vertices)<-3 else 0
parts.append(o)
for x in (-270,-90,90,270):collider((x,-427,3),(179.4,72,6))
collider((200,500,2),(200,196,4));finish('Apron')
for o in list(bpy.context.scene.objects):
 if o.name.startswith('HouseStone_'):bpy.data.objects.remove(o,do_unlink=True)
(OUT/'model-manifest.json').write_text(json.dumps(dict(assets=assets,source='HouseStoneBank.blend',shaft_width_cm=146,previous_shaft_width_cm=92,chimney_house_location=[200,500,0],gameplay_started=False,rendered=False),indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'VillageBlacksmith_MasonryR5.blend'))
print('SMITH_MASONRY_R5_AUTHORED',[(a['role'],a['lods'][0]['triangles']) for a in assets])
