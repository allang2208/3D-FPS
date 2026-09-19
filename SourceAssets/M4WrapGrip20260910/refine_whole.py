import bpy,json,math,random
from pathlib import Path
from mathutils import Matrix,Vector,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();b=r.pose.bones['clavicle_l'];b.matrix=inv.inverted()@Matrix.Translation((.007,-.007,0))@inv@b.matrix;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];rng=random.Random(91);report={}
for digit in ['thumb','index','ring','pinky','middle']:
 bones=[r.pose.bones[digit+'_metacarpal_l']] if digit!='thumb' else []
 bones += [r.pose.bones[f'{digit}_{j:02}_l'] for j in [1,2,3]];base=[b.rotation_quaternion.to_euler() for b in bones];padids=[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==digit+'_03_l' and g.weight>.8 for g in v.groups)]
 def evaluate(params):
  for b,e,delta in zip(bones,base,params):
   q=e.copy()
   for axis in range(3):q[axis]+=math.radians(delta[axis])
   b.rotation_quaternion=q.to_quaternion()
  bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();tree=BVHTree.FromPolygons(vs,fs);pairs=sum(len(tree.overlap(t)) for t in trees);dist=min(trees[0].find_nearest(vs[i])[3] for i in padids)*1000;score=pairs*10000+abs(dist-.7)*10+sum(abs(x) for p in params for x in p)*.008
  return score,{'params':[list(p) for p in params],'pairs':pairs,'pad_distance_mm':dist}
 zero=[[0,0,0] for b in bones];best=evaluate(zero)
 for step in [12,6,3,1]:
  for it in range(5):
   improved=False
   for j in range(len(bones)):
    for axis in ([0,1,2] if j==0 else [2]):
     for sign in [-1,1]:
      pp=[p.copy() for p in best[1]['params']];pp[j][axis]+=step*sign;v=evaluate(pp)
      if v[0]<best[0]:best=v;improved=True
   if not improved:break
 evaluate(best[1]['params']);report[digit]=best[1];print(digit,best,flush=True)
fit=json.loads((O/'wrap_fit.json').read_text());fit['whole_hand_refinement']=report;fit['hand_magazine_matrix']=[list(row) for row in (inv@r.pose.bones['hand_l'].matrix)];fit['bone_local_rotations']={b.name:list(b.rotation_quaternion) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))};(O/'wrap_fit.json').write_text(json.dumps(fit,indent=2));a=bpy.data.actions.new('M4_WRAP_whole_contact');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'grip_fitted.blend'));print('WHOLE_GRIP_DONE')
