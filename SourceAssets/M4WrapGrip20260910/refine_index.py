import bpy,json,math,itertools,random
from pathlib import Path
from mathutils import Vector,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 o=bpy.data.objects[name];ev=o.evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
report={}
for digit in ['index']:
 ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(digit))>.6};padids=[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==digit+'_03_l' and g.weight>.8 for g in v.groups)];fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)]
 bones=[r.pose.bones['index_metacarpal_l']] if digit=='index' else [r.pose.bones[f'thumb_{i:02}_l'] for i in [1,2,3]];base=[b.rotation_quaternion.to_euler() for b in bones]
 def evaluate(params):
  for b,e in zip(bones,base):b.rotation_quaternion=e.to_quaternion()
  if digit=='index':e=base[0].copy();e.x+=math.radians(params[0]);e.y+=math.radians(params[1]);bones[0].rotation_quaternion=e.to_quaternion()
  else:
   e=base[0].copy();e.x+=math.radians(params[0]);e.y+=math.radians(params[1]);e.z+=math.radians(params[2]);bones[0].rotation_quaternion=e.to_quaternion()
   for i in [1,2]:e=base[i].copy();e.z=math.radians(params[i+2]);bones[i].rotation_quaternion=e.to_quaternion()
  bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();tree=BVHTree.FromPolygons(vs,fs);pairs=[len(tree.overlap(t)) for t in trees];dist=min(trees[0].find_nearest(vs[i])[3] for i in padids)*1000;mean=sum((vs[i] for i in padids),Vector())/len(padids);score=sum(pairs)*1000+abs(dist-.5)*2
  if digit=='thumb':score+=(mean-Vector((.023,-.020,.047))).length*1000
  return score,{'params':list(params),'pairs':pairs,'pad_distance_mm':dist,'pad_mean':list(mean)}
 rng=random.Random(73)
 samples=list(itertools.product(range(-8,9,2),range(-8,9,2))) if digit=='index' else [[rng.uniform(-70,70),rng.uniform(-70,70),rng.uniform(-70,70),rng.uniform(-15,70),rng.uniform(-15,70)] for _ in range(1400)]
 best=(1e30,None)
 for params in samples:
  result=evaluate(params)
  if result[0]<best[0]:best=result
 for step in ([1,.4] if digit=='index' else [12,6,3,1]):
  for _ in range(2):
   for axis in range(len(best[1]['params'])):
    for sign in [-1,1]:
     p=best[1]['params'].copy();p[axis]+=sign*step;result=evaluate(p)
     if result[0]<best[0]:best=result
 evaluate(best[1]['params']);report[digit]=best[1];print(digit,best,flush=True)
fit=json.loads((O/'wrap_fit.json').read_text());fit['contact_refinement'].update(report);fit['bone_local_rotations']={b.name:list(b.rotation_quaternion) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))};(O/'wrap_fit.json').write_text(json.dumps(fit,indent=2));a=bpy.data.actions.new('M4_WRAP_contact');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'grip_fitted.blend'));print('CONTACT_REFINED')
