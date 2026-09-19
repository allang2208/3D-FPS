import bpy,json,itertools
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'natural_grip.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();trees=[]
for name in ['M4_Magazine Light.003_Export','M4_M4 Body_Export']:
 ev=bpy.data.objects[name].evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>.7};fs=[list(p.vertices) for p in h.data.polygons if any(i in ids for i in p.vertices)];ev=h.evaluated_get(dg);m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();pads=[[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==d+'_03_l' and g.weight>.8 for g in v.groups)] for d in ['thumb','index','middle','ring','pinky']]
best=(1e20,None)
for shift in itertools.product([-.030,-.020,-.010,0,.010,.020,.030],repeat=3):
 vv=[v+Vector(shift) for v in vs];t=BVHTree.FromPolygons(vv,fs);pairs=sum(len(t.overlap(x)) for x in trees);ds=[min(trees[0].find_nearest(vv[i])[3] for i in pp)*1000 for pp in pads];score=pairs*10000+sum(ds)+Vector(shift).length*500
 if score<best[0]:best=(score,dict(shift=shift,pairs=pairs,distances=ds));print(best,flush=True)
(O/'natural_search.json').write_text(json.dumps(best,indent=2))
