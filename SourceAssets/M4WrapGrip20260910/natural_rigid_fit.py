import bpy,json,math,random
from pathlib import Path
from mathutils import Vector,Matrix,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'natural_fit.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();pivot=inv@r.pose.bones['hand_l'].matrix.translation;dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};faces=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];use=sorted({i for f in faces for i in f});lookup={v:i for i,v in enumerate(use)};fs=[[lookup[i] for i in f] for f in faces];ev=h.evaluated_get(dg);m=ev.to_mesh();vs=[inv@ev.matrix_world@m.vertices[i].co-pivot for i in use];ev.to_mesh_clear();pads=[[lookup[v.index] for v in h.data.vertices if v.index in lookup and any(h.vertex_groups[g.group].name==d+'_03_l' and g.weight>.8 for g in v.groups)] for d in ['thumb','index','middle','ring','pinky']]
def evaluate(p):
 rot=Euler(tuple(math.radians(x) for x in p[3:])).to_matrix();shift=Vector(p[:3]);vv=[rot@v+pivot+shift for v in vs];t=BVHTree.FromPolygons(vv,fs);pairs=sum(len(t.overlap(x)) for x in trees);ds=[min(trees[0].find_nearest(vv[i])[3] for i in pp)*1000 for pp in pads];score=pairs*10000+sum(abs(d-.7) for d in ds)*3+max(ds)*3+sum(abs(x) for x in p[3:])*.03
 return score,dict(params=p,pairs=pairs,distances=ds)
rng=random.Random(226);best=evaluate([0]*6)
for i in range(2200):
 p=[rng.uniform(-.03,.015),rng.uniform(-.025,.020),rng.uniform(-.010,.045)]+[rng.uniform(-25,25) for _ in range(3)];v=evaluate(p)
 if v[0]<best[0]:best=v;print(best,flush=True)
for step in [.006,.003,.001,.0003]:
 for _ in range(7):
  improved=False
  for axis in range(6):
   for sign in [-1,1]:
    p=best[1]['params'].copy();p[axis]+=step*sign*(500 if axis>=3 else 1);v=evaluate(p)
    if v[0]<best[0]:best=v;improved=True
  if not improved:break
print('FINAL',best,flush=True);(O/'natural_rigid_fit.json').write_text(json.dumps(best,indent=2));p=best[1]['params'];delta=Matrix.Translation(pivot+Vector(p[:3]))@Euler(tuple(math.radians(x) for x in p[3:])).to_matrix().to_4x4()@Matrix.Translation(-pivot);b=r.pose.bones['clavicle_l'];b.matrix=inv.inverted()@delta@inv@b.matrix;bpy.context.view_layer.update();a=bpy.data.actions.new('M4_NATURAL_final');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'natural_final.blend'))
exec((O/'render_fit.py').read_text(encoding='utf-8').replace("O/'grip_fitted.blend'","O/'natural_final.blend'").replace("f'grip_fitted_{i}.png'","f'natural_final_{i}.png'"))
