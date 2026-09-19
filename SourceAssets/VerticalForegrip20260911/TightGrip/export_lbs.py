import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Integration/M4_Vertical_Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];hand=bpy.data.objects['SK_Manny_Arms_Export'];s=bpy.context.scene;bpy.context.view_layer.update()
names=[b.name for b in r.data.bones];parents=[names.index(b.parent.name) if b.parent else -1 for b in r.data.bones];rest=np.array([list(map(list,b.matrix_local)) for b in r.data.bones]);pose=np.array([list(map(list,r.pose.bones[n].matrix)) for n in names]);weights=np.zeros((len(hand.data.vertices),len(names)))
for v in hand.data.vertices:
 for g in v.groups:
  n=hand.vertex_groups[g.group].name
  if n in names:weights[v.index,names.index(n)]=g.weight
weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-10)
vertices=np.array([list(r.matrix_world.inverted()@hand.matrix_world@v.co)+[1] for v in hand.data.vertices]);calc=np.einsum('nb,bij,nj->ni',weights,pose@np.linalg.inv(rest),vertices)
e=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();actual=np.array([list(r.matrix_world.inverted()@e.matrix_world@v.co)+[1] for v in m.vertices]);print('LBS error',np.abs(calc-actual).max());e.to_mesh_clear()
np.savez(O/'hand_lbs.npz',vertices=vertices,weights=weights,rest=rest,pose=pose,parents=parents)
(O/'hand_lbs.json').write_text(json.dumps({'names':names,'modifiers':[(m.name,m.type) for m in hand.modifiers]},indent=2))

G=np.array(json.loads((O.parent/'Integration/fit_final.json').read_text())['grip_matrix']);grip=next(o for o in s.objects if o.name.startswith('VG_')) if False else next(o for o in bpy.context.scene.objects if o.name.startswith('VG_'))
gv=np.array([list(grip.matrix_world@v.co)+[1] for v in grip.data.vertices])@np.linalg.inv(G).T
z=np.unique(np.round(gv[:,2],6));profile=[(float(t),float(np.max(np.linalg.norm(gv[np.abs(gv[:,2]-t)<.000002,:2],axis=1)))) for t in z]
(O/'grip_profile.json').write_text(json.dumps(profile))
