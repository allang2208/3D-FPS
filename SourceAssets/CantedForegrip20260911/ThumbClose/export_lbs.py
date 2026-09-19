import bpy,json,numpy as np,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Integration/A_M4_Canted_idle.blend'));s=bpy.context.scene;s.frame_set(0);r=bpy.data.objects['SK_M4_Infima'];hand=bpy.data.objects['SK_Manny_Arms_Export'];bpy.context.view_layer.update();names=[b.name for b in r.data.bones];parents=[names.index(b.parent.name) if b.parent else -1 for b in r.data.bones];rest=np.array([list(map(list,b.matrix_local)) for b in r.data.bones]);pose=np.array([list(map(list,r.pose.bones[n].matrix)) for n in names]);weights=np.zeros((len(hand.data.vertices),len(names)))
for v in hand.data.vertices:
 for g in v.groups:
  n=hand.vertex_groups[g.group].name
  if n in names:weights[v.index,names.index(n)]=g.weight
weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-10);vertices=np.array([list(r.matrix_world.inverted()@hand.matrix_world@v.co)+[1] for v in hand.data.vertices]);np.savez(O/'hand_lbs.npz',vertices=vertices,weights=weights,rest=rest,pose=pose,parents=parents);(O/'hand_lbs.json').write_text(json.dumps({'names':names}))
hand.data.calc_loop_triangles();np.save(O/'triangles.npy',np.array([list(t.vertices) for t in hand.data.loop_triangles]))
f=json.loads((O/'fit_baseline.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);pivot=Vector((0,0,-.014));T=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(45),4,'X')@Matrix.Translation(-pivot);B=G@T;(O/'body_frame.json').write_text(json.dumps([list(row) for row in B]));grip=next(o for o in s.objects if o.name.startswith('CG_'));gv=np.array([list(B.inverted()@r.matrix_world.inverted()@grip.matrix_world@v.co) for v in grip.data.vertices]);z=np.unique(np.round(gv[:,2],6));profile=[(float(t),float(np.max(np.linalg.norm(gv[np.abs(gv[:,2]-t)<.000002,:2],axis=1)))) for t in z if t<-.023];(O/'grip_profile.json').write_text(json.dumps(profile));print('LBS_DATA_READY',len(vertices))
