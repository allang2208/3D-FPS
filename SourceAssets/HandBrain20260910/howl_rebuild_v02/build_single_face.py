"""Rebuild an actual oral opening in the original mesh; no imported replacement face."""
import bpy,bmesh,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'hunyuan_v01'))
import studio
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'hunyuan_v01/delivery/HandBrain_Animated.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_HandBrain'];body=bpy.data.objects['HandBrain_Body']
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis.identity()
for ob in list(scene.objects):
 if ob.type not in {'MESH','ARMATURE'} or ob.name=='PreviewFloor':bpy.data.objects.remove(ob,do_unlink=True)
original_names=[b.name for b in rig.data.bones]
original_vertices=len(body.data.vertices)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def material(name,color,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
 return m
oral=material('Oral mucosa - authored local interior',(.022,.0025,.004),.85)
body.data.materials.append(oral);oral_index=len(body.data.materials)-1
zm=.758;wy=.245;hz=.12
body.data.calc_loop_triangles()
source_coords=[v.co.copy() for v in body.data.vertices]
source_tris=[tuple(t.vertices) for t in body.data.loop_triangles]
source_uvs=[[body.data.uv_layers.active.data[j].uv.copy() for j in t.loops] for t in body.data.loop_triangles]
bvh=BVHTree.FromPolygons(source_coords,source_tris,all_triangles=True)
def surface(y,z):
 hit,normal,idx,dist=bvh.ray_cast(Vector((2,y,z)),Vector((-1,0,0)))
 assert hit is not None
 uv=barycentric_transform(hit,*[source_coords[j] for j in source_tris[idx]],*[Vector((u.x,u.y,0)) for u in source_uvs[idx]])
 return hit,uv.xy
# Reproject original skin color into one local UV chart. Sampling across the old atlas
# through per-corner UV interpolation alone would cross islands and produce streaks.
skin=bpy.data.materials.new('Original skin - reprojected mouth UV');skin.use_nodes=True
bs=skin.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.78
oldbs=body.data.materials[0].node_tree.nodes.get('Principled BSDF')
source_image=oldbs.inputs['Base Color'].links[0].from_node.image
sw,sh=source_image.size;pixels=np.empty(sw*sh*4,dtype=np.float32);source_image.pixels.foreach_get(pixels);pixels=pixels.reshape(sh,sw,4)
size=512;patch=np.zeros((size,size,4),dtype=np.float32);patch[:,:,3]=1
for iz in range(size):
 for iy in range(size):
  y=-.32+.64*(iy+.5)/size;z=.60+.32*(iz+.5)/size
  co,uv=surface(y,z);px=max(0,min(sw-1,int(uv.x*sw)));py=max(0,min(sh-1,int(uv.y*sh)))
  patch[iz,iy]=pixels[py,px]
im=bpy.data.images.new('MouthSkin_Reprojected',width=size,height=size);im.pixels.foreach_set(patch.ravel());im.pack()
node=skin.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;skin.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
body.data.materials.append(skin);skin_index=len(body.data.materials)-1
bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
old_layer=bm.verts.layers.int.new('source_vertex')
oral_layer=bm.verts.layers.int.new('oral_vertex')
lip_t_layer=bm.verts.layers.float.new('lip_band_t')
lip_split_layer=bm.verts.layers.float.new('lip_band_split')
for v in bm.verts:v[old_layer]=v.index+1
cut=[f for f in bm.faces if (lambda c:c.x>.43 and (c.y/.29)**2+((c.z-zm)/hz)**2<1)(f.calc_center_median())]
cutset=set(cut);rim_edges=[e for e in bm.edges if sum(f in cutset for f in e.link_faces)==1 and len(e.link_faces)==2]
adj={}
for e in rim_edges:
 a,b=e.verts;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert adj and all(len(n)==2 for n in adj.values()),'Mouth boundary is not one simple closed loop'
start=next(iter(adj));loop=[start];prev=None;cur=start
while True:
 nxt=next(v for v in adj[cur] if v!=prev)
 if nxt==start:break
 loop.append(nxt);prev,cur=cur,nxt
 assert len(loop)<=len(adj)
assert len(loop)==len(adj),'Multiple mouth holes would be invalid'
bmesh.ops.delete(bm,geom=cut,context='FACES')
# Project this small cut boundary to a clean lip ellipse, preserving original X depth and UVs.
angles=[]
startangle=math.atan2((loop[0].co.z-zm)/hz,loop[0].co.y/.29)
orientation=sum(a.co.y*b.co.z-b.co.y*a.co.z for a,b in zip(loop,loop[1:]+loop[:1]))
for i,v in enumerate(loop):
 a=startangle+(1 if orientation>0 else -1)*math.tau*i/len(loop);angles.append(a)
# Retopologize the surrounding lip band with radial quad loops and sampled original UV.
deform=bm.verts.layers.deform.verify();uvlayer=bm.loops.layers.uv.active
outer=loop
for t in [.12,.25,.4,.55,.7,.82,.92,1.]:
 ring=[]
 for orig,a in zip(outer,angles):
  y=(1-t)*orig.co.y+t*wy*math.cos(a);z=(1-t)*orig.co.z+t*(zm+.004*math.sin(a))
  co,uv=surface(y,z);co.x+=.016*math.sin(math.pi*t)**2
  v=bm.verts.new(co);v[old_layer]=0;v[lip_t_layer]=t;v[lip_split_layer]=.5+.5*math.sin(a)
  for g,w in orig[deform].items():v[deform][g]=w
  ring.append(v)
 for i in range(len(loop)):
  j=(i+1)%len(loop);f=bm.faces.new((loop[i],loop[j],ring[j],ring[i]));f.material_index=skin_index
  for l in f.loops:l[uvlayer].uv=((l.vert.co.y+.32)/.64,(l.vert.co.z-.60)/.32)
 loop=ring
# Attached quad rings form the mouth lining. They share the original lip boundary.
deform=bm.verts.layers.deform.verify();rings=[loop]
for depth,scale in [(.012,.99),(.035,.98),(.075,.94),(.13,.86),(.20,.74),(.28,.58),(.35,.38),(.40,.16)]:
 ring=[]
 for orig,a in zip(loop,angles):
  v=bm.verts.new((orig.co.x-depth,wy*math.cos(a)*scale,zm+.004*math.sin(a)*scale));v[old_layer]=0;v[oral_layer]=1
  for g,w in orig[deform].items():v[deform][g]=w
  ring.append(v)
 old=rings[-1]
 for i in range(len(loop)):
  j=(i+1)%len(loop);f=bm.faces.new((old[i],old[j],ring[j],ring[i]));f.material_index=oral_index
 rings.append(ring)
center=bm.verts.new((.18,0,zm));center[old_layer]=0;center[oral_layer]=1
g=body.vertex_groups.get('neck');center[deform][g.index]=1
for i in range(len(loop)):
 f=bm.faces.new((rings[-1][i],rings[-1][(i+1)%len(loop)],center));f.material_index=oral_index
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
body.data.normals_split_custom_set([(0,0,0)]*len(body.data.loops))
for p in body.data.polygons:p.use_smooth=True
# Child deform bones reproduce each old influence at rest. Original actions stay untouched.
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for part in ['jaw','upper','cheek_L','cheek_R']:
 for name in ['base','neck','cranium']:
  parent=rig.data.edit_bones[name];b=rig.data.edit_bones.new('mouth_'+part+'_'+name)
  b.head=parent.head;b.tail=parent.tail;b.roll=parent.roll;b.parent=parent
bpy.ops.object.mode_set(mode='OBJECT')
groups={}
for b in rig.data.bones:
 groups[b.name]=body.vertex_groups.get(b.name) or body.vertex_groups.new(name=b.name)
source_map=[]
attr=body.data.attributes.get('source_vertex')
for v in body.data.vertices:
 x,y,z=v.co;inside=bool(body.data.attributes['oral_vertex'].data[v.index].value)
 source_map.append(attr.data[v.index].value-1 if attr else -1)
 front=smooth(.26,.51,x);side=1-smooth(.26,.47,abs(y))
 if inside:front=1;side=1
 split=max(0,min(1,.5+(z-zm)/.008))
 band_t=body.data.attributes['lip_band_t'].data[v.index].value
 if band_t>0:
  target=body.data.attributes['lip_band_split'].data[v.index].value
  blend=smooth(0,1,band_t);split=split*(1-blend)+target*blend
 lower=(1-split)*smooth(.29,.61,z)*front*side
 upper=split*(1-smooth(.9,1.22,z))*front*side
 if inside:
  lower=1-split;upper=split
 cheek=front*smooth(.23,.34,abs(y))*(1-smooth(.43,.59,abs(y)))*smooth(.50,.7,z)*(1-smooth(1.08,1.35,z))*.65
 # Keep influence sums normalized while preserving old parent weights.
 amounts={'jaw':lower,'upper':upper,'cheek_L' if y>=0 else 'cheek_R':cheek}
 total=sum(amounts.values())
 if total>1:amounts={k:w/total for k,w in amounts.items()};total=1
 old=[(body.vertex_groups[g.group].name,g.weight) for g in v.groups]
 for name,w in old:
  if name not in ['base','neck','cranium']:continue
  groups[name].remove([v.index])
  if 1-total>1e-6:groups[name].add([v.index],w*(1-total),'REPLACE')
  for part,amount in amounts.items():
   if amount*w>1e-6:groups['mouth_'+part+'_'+name].add([v.index],w*amount,'REPLACE')
# Oral teeth: small local geometry, not another source head. Fully behind original lips at rest.
teethmat=material('Aged teeth',(.48,.43,.28),.56)
teeth=[]
for row in ['upper','jaw']:
 for i in range(11):
  y=(i-5)*.035;frac=y/.245
  x=surface(y,zm)[0].x-.045;z=zm+(.018 if row=='upper' else -.018)
  bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,location=(x,y,z))
  o=bpy.context.object;o.name='Oral_tooth';o.scale=(.021,.018,.033 if row=='upper' else .026)
  bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  o.data.materials.append(teethmat)
  for p in o.data.polygons:p.use_smooth=True
  top=.5+.5*math.sqrt(1-frac*frac)
  if row=='jaw':top=1-top
  ids=list(range(len(o.data.vertices)))
  o.vertex_groups.new(name='mouth_upper_neck').add(ids,top,'REPLACE')
  o.vertex_groups.new(name='mouth_jaw_neck').add(ids,1-top,'REPLACE');teeth.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in teeth:o.select_set(True)
bpy.context.view_layer.objects.active=teeth[0];bpy.ops.object.join();tooth=bpy.context.object;tooth.name='HandBrain_OralTeeth'
mod=tooth.modifiers.new('Original skeleton jaw','ARMATURE');mod.object=rig
tooth.parent=rig
def pose(amount):
 for p in rig.pose.bones:p.matrix_basis.identity()
 rig.pose.bones['arm_mount'].scale=(.055,)*3;rig.pose.bones['fan_mount'].scale=(.06,)*3
 for part,vec in {'jaw':(-.05,0,-.31),'upper':(.006,0,.11),'cheek_L':(0,.105,0),'cheek_R':(0,-.105,0)}.items():
  for parent in ['base','neck','cranium']:
   p=rig.pose.bones['mouth_'+part+'_'+parent];p.location=p.bone.matrix_local.to_quaternion().inverted()@(Vector(vec)*amount)
 bpy.context.view_layer.update()
pose(0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'SingleFace_Rig.blend'))
(R/'source_vertex_map.json').write_text(json.dumps(source_map))
(R/'build_report.json').write_text(json.dumps({'input':'hunyuan_v01/delivery/HandBrain_Animated.blend','replacement_face_imported':False,'removed_original_mouth_faces':len(cut),'lip_boundary_vertices':len(loop),'connected_oral_rings':8,'retopologized_skin_rings':8,'original_body_vertices':original_vertices,'body_vertices':len(body.data.vertices),'bone_count':len(rig.data.bones),'visual_accepted':False},indent=2))
cam=studio.setup(760);scene.cycles.samples=16
for name,loc in [('front',(6,0,1)),('side',(1,-6,1.25)),('hero',(4,-7,2.4))]:
 studio.aim(cam,loc,(.15,0,.98));cam.data.ortho_scale=2.5
 for state,amount in [('closed',0),('open',1)]:
  pose(amount);scene.render.filepath=str(R/(name+'_'+state+'.png'));bpy.ops.render.render(write_still=True)
print('SINGLE_FACE_BUILD_COMPLETE')
