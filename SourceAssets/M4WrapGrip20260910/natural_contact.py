import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'natural_final.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];report={}
for d in ['index','middle','ring','pinky','thumb']:
 bones=[r.pose.bones[f'{d}_{j:02}_l'] for j in [1,2,3]];base=[b.rotation_quaternion.to_euler() for b in bones];padids=[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==d+'_03_l' and g.weight>.8 for g in v.groups)]
 def evaluate(params):
  for j,b in enumerate(bones):
   e=base[j].copy()
   if d=='thumb' and j==0:
    for ax in range(3):e[ax]+=math.radians(params[ax])
   else:e.z+=math.radians(params[j+2] if d=='thumb' else params[j])
   b.rotation_quaternion=e.to_quaternion()
  bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();tree=BVHTree.FromPolygons(vs,fs);pairs=sum(len(tree.overlap(t)) for t in trees);dist=min(trees[0].find_nearest(vs[i])[3] for i in padids)*1000;return pairs*10000+abs(dist-.7)*10+sum(abs(x) for x in params)*.02,dict(params=params.copy(),pairs=pairs,pad_distance_mm=dist)
 best=evaluate([0]*(5 if d=='thumb' else 3))
 for step in [5,2,1,.3]:
  for _ in range(5):
   improved=False
   for axis in range(len(best[1]['params'])):
    for sign in [-1,1]:
     pp=best[1]['params'].copy();pp[axis]+=step*sign
     if abs(pp[axis])>10:continue
     v=evaluate(pp)
     if v[0]<best[0]:best=v;improved=True
   if not improved:break
 evaluate(best[1]['params']);report[d]=best[1];print(d,best,flush=True)
fit={'hand_magazine_matrix':[list(row) for row in (inv@r.pose.bones['hand_l'].matrix)],'bone_local_rotations':{b.name:list(b.rotation_quaternion) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))},'natural_limits':'Unrotated metacarpals. Four-finger MCP -10..10, PIP 35..55, DIP 20..40 local Z; no independent axial twist. Native thumb plus at most 10 degrees per axis.','contact_report':report}
(O/'wrap_fit.json').write_text(json.dumps(fit,indent=2));a=bpy.data.actions.new('M4_NATURAL_accepted_shape');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'grip_fitted.blend'))
exec((O/'render_fit.py').read_text(encoding='utf-8'))
