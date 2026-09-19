import bpy,json,math,itertools
from pathlib import Path
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'natural_grip.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];pads=[[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==d+'_03_l' and g.weight>.8 for g in v.groups)] for d in ['thumb','index','middle','ring','pinky']];best=(1e20,None)
for params in itertools.product([-20,0,20],[25,45,60],[15,30]):
 for d in ['index','middle','ring','pinky']:
  for j,z in enumerate(params,1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Euler((0,0,math.radians(z))).to_quaternion()
 bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear()
 for shift in itertools.product([-.04,-.02,0,.02,.04,.06],[-.06,-.04,-.02,0,.02,.04,.06],[-.02,0,.02]):
  vv=[v+Vector(shift) for v in vs];t=BVHTree.FromPolygons(vv,fs);pairs=sum(len(t.overlap(x)) for x in trees);ds=[min(trees[0].find_nearest(vv[i])[3] for i in pp)*1000 for pp in pads];score=pairs*10000+sum(ds)*3+max(ds)*3+Vector(shift).length*100
  if score<best[0]:best=(score,dict(angles=params,shift=shift,pairs=pairs,distances=ds));print(best,flush=True)
(O/'natural_search_full.json').write_text(json.dumps(best,indent=2));params=best[1]['angles']
for d in ['index','middle','ring','pinky']:
 for j,z in enumerate(params,1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Euler((0,0,math.radians(z))).to_quaternion()
b=r.pose.bones['clavicle_l'];b.matrix=inv.inverted()@Matrix.Translation(best[1]['shift'])@inv@b.matrix;bpy.context.view_layer.update();a=bpy.data.actions.new('M4_NATURAL_fit');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'natural_fit.blend'));print('NATURAL_FIT_DONE')
