import bpy,json,math,itertools
from pathlib import Path
from mathutils import Vector,Matrix,Euler,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();cl=r.pose.bones['clavicle_l'];cm=cl.matrix.copy();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];bones=[b for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky')) and '_metacarpal_' not in b.name];base={b.name:b.rotation_quaternion.copy() for b in bones}
best=(1e20,None)
for params in [(0,-20,0),(0,-30,-10),(0,-40,-10)]:
 rows=[];rot={}
 for b in bones:
  e=base[b.name].to_euler();e.z+=math.radians(params[int(b.name[-4:-2])-1]);rot[b.name]=e.to_quaternion()
 for k in range(1,21):
  u=k/20;w=max(0,min(1,(u-.2)/.6));travel=u*.085
  for b in bones:b.rotation_quaternion=base[b.name].slerp(rot[b.name],w)
  cl.matrix=inv.inverted()@Matrix.Translation((travel,0,0))@inv@cm;bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();t=BVHTree.FromPolygons(vs,fs);rows.append(sum(len(t.overlap(x)) for x in trees))
 score=sum(rows)*10000+sum(abs(x) for x in params)
 if score<best[0]:best=(score,dict(params=params,rows=rows,max_pairs=max(rows),rotations={n:list(q) for n,q in rot.items()}));print(best,flush=True)
(O/'open_grip_fit.json').write_text(json.dumps(best[1],indent=2))
