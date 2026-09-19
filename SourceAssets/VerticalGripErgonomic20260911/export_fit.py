import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
for variant in ['vertical','prism']:
 d=O/variant;bpy.ops.wm.open_mainfile(filepath=str(d/'Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];hand=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.view_layer.update();names=[b.name for b in r.data.bones];parents=[names.index(b.parent.name) if b.parent else -1 for b in r.data.bones];rest=np.array([list(map(list,b.matrix_local)) for b in r.data.bones]);pose=np.array([list(map(list,r.pose.bones[n].matrix)) for n in names]);weights=np.zeros((len(hand.data.vertices),len(names)))
 for v in hand.data.vertices:
  for g in v.groups:
   n=hand.vertex_groups[g.group].name
   if n in names:weights[v.index,names.index(n)]=g.weight
 weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-10)
 vertices=np.array([list(r.matrix_world.inverted()@hand.matrix_world@v.co)+[1] for v in hand.data.vertices]);calc=np.einsum('nb,bij,nj->ni',weights,pose@np.linalg.inv(rest),vertices)
 ev=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();actual=np.array([list(r.matrix_world.inverted()@ev.matrix_world@v.co)+[1] for v in mesh.vertices]);error=float(np.abs(calc-actual).max());assert error<1e-5,error;ev.to_mesh_clear()
 np.savez(d/'lbs.npz',vertices=vertices,weights=weights,rest=rest,pose=pose,parents=parents);(d/'lbs.json').write_text(json.dumps({'names':names,'error':error}))
 G=r.pose.bones['WPN_root'].matrix@Matrix(json.loads((d/'fit_final.json').read_text())['grip_in_root']);vv=[];ff=[]
 for ob in bpy.context.scene.objects:
  if not ob.name.startswith('VG_' if variant=='vertical' else 'PH_'):continue
  e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();offset=len(vv);vv.extend([list(G.inverted()@e.matrix_world@v.co) for v in m.vertices]);ff.extend([tuple(i+offset for i in t.vertices) for t in m.loop_triangles]);e.to_mesh_clear()
 np.savez(d/'grip.npz',vertices=vv,faces=ff,G=np.array(list(map(list,G))))
 print('EXPORTED',variant,error,flush=True)
