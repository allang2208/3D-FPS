import bpy,json,math,itertools
from pathlib import Path
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();root=r.pose.bones['WPN_root'].matrix.copy();b=r.pose.bones['clavicle_l'];b.matrix=inv.inverted()@Matrix.Translation((.001,0,0))@inv@b.matrix;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};faces=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];use=sorted({i for f in faces for i in f});lookup={v:i for i,v in enumerate(use)};fs=[[lookup[i] for i in f] for f in faces];bones=[r.pose.bones['thumb_02_l'],r.pose.bones['thumb_03_l']];base=[b.rotation_quaternion.to_euler() for b in bones];direction=inv.to_3x3()@root.to_3x3()@Vector((0,0,-1));best=(1e30,None)
for params in itertools.product([-10,-5,0,5,10,15],[0,5,10,15,20,25]):
 for b,e,d in zip(bones,base,params):q=e.copy();q.z+=math.radians(d);b.rotation_quaternion=q.to_quaternion()
 bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@m.vertices[i].co for i in use];ev.to_mesh_clear();t=BVHTree.FromPolygons(vs,fs);mag=len(t.overlap(trees[0]));bp=[]
 for k in range(36):
  vv=[v+direction*(k*.002) for v in vs];t=BVHTree.FromPolygons(vv,fs);bp.append(len(t.overlap(trees[1])))
 score=(mag+sum(bp))*10000+sum(abs(x) for x in params)
 if score<best[0]:best=(score,dict(params=params,mag=mag,body=max(bp),body_sweep=bp));print(best,flush=True)
for b,e,d in zip(bones,base,best[1]['params']):q=e.copy();q.z+=math.radians(d);b.rotation_quaternion=q.to_quaternion()
bpy.context.view_layer.update();fit=json.loads((O/'wrap_fit.json').read_text());fit['thumb_insertion_sweep']=best[1];fit['hand_magazine_matrix']=[list(row) for row in inv@r.pose.bones['hand_l'].matrix];fit['bone_local_rotations']={b.name:list(b.rotation_quaternion) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))};(O/'wrap_fit.json').write_text(json.dumps(fit,indent=2));a=bpy.data.actions.new('M4_NATURAL_clear_thumb');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'grip_fitted.blend'));print('THUMB_SWEEP_DONE')
