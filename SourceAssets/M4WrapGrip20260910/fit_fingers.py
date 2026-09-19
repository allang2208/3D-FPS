import bpy,json,math,itertools
from pathlib import Path
from mathutils import Vector,Euler,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_candidate.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];mag=bpy.data.objects['M4_Magazine Light.003_Export'];body=bpy.data.objects['M4_M4 Body_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None
inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();delta=inv.inverted()@Matrix.Translation((.010,-.010,0))@inv;ps={b.name:b.matrix.copy() for b in r.pose.bones}
r.pose.bones['clavicle_l'].matrix=delta@ps['clavicle_l']
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for o in [mag,body]:
 ev=o.evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
report={}
for digit in ['index','middle','ring','pinky','thumb']:
 ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(digit))>.6};padids=[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==digit+'_03_l' and g.weight>.8 for g in v.groups)];fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];bones=[r.pose.bones[f'{digit}_{j:02}_l'] for j in [1,2,3]];original=[b.rotation_quaternion.to_euler() for b in bones]
 def evaluate(angles):
  for b,e,z in zip(bones,original,angles):q=e.copy();q.z=math.radians(z);b.rotation_quaternion=q.to_quaternion()
  bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();tree=BVHTree.FromPolygons(vs,fs);pairs=sum(len(tree.overlap(t)) for t in trees);dist=min(trees[0].find_nearest(vs[i])[3] for i in padids)*1000;meanx=sum(vs[i].x for i in padids)/len(padids);score=pairs*100+dist*2+max(0,meanx+.006)*4000
  return score,{'angles':angles,'pairs':pairs,'pad_distance_mm':dist,'pad_mean_x_mm':meanx*1000}
 anglesets=[[-55,-40,-25,-10,5,20,35],[5,25,45,65,85,105],[0,20,40,60,80]] if digit!='thumb' else [[math.degrees(e.z)+d for d in [-20,-10,0,10,20]] for e in original]
 best=(1e20,None)
 for angles in itertools.product(*anglesets):
  result=evaluate(angles)
  if result[0]<best[0]:best=result
 for step in [7,3]:
  for angles in itertools.product(*[[a-step,a,a+step] for a in best[1]['angles']]):
   result=evaluate(angles)
   if result[0]<best[0]:best=result
 evaluate(best[1]['angles']);report[digit]=best[1];print(digit,best,flush=True)
# Save exact local controls and the magazine-space wrist transform.
fit={'hand_magazine_matrix':[list(row) for row in (inv@r.pose.bones['hand_l'].matrix)],'bone_local_rotations':{b.name:list(b.rotation_quaternion) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))},'contact_report':report}
(O/'wrap_fit.json').write_text(json.dumps(fit,indent=2));a=bpy.data.actions.new('M4_WRAP_fitted');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'grip_fitted.blend'));print('WRAP_FIT_DONE')
