from pathlib import Path
O=Path(__file__).parent
exec((O/'solve_release_path.py').read_text().split('p0,v0=')[0])
u=.5;bas=basis.copy();t=smooth(u*1.5)
for n,q in qs.items():bas[index[n],:3,:3]=np.array(q.slerp(Quaternion(opened[n]),t).to_matrix())
p=base.copy();p[index['hand_l'],:3,3]+=G[:3,:3]@np.array((0,.0848528,.0848528))*smooth((u-.25)/.75)
for i in left:p[i]=p[par[i]]@lr[i]@bas[i]
pred={n:np.linalg.inv(G)@p[index[n]] for n in ['hand_l','index_01_l','index_02_l','index_03_l']}
bpy.ops.wm.open_mainfile(filepath=str(O/'m4/canted/A_M4_Canted_reload.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(4,subframe=.5);bpy.context.view_layer.update();gg=np.array(r.pose.bones['WPN_root'].matrix)@np.array(fit['grip_in_root'])
for n,m in pred.items():print('PREDICTION',n,'pred',m[:3,3].tolist(),'actual',(np.linalg.inv(gg)@np.array(r.pose.bones[n].matrix))[:3,3].tolist(),'matrix_error',np.max(np.abs(m-np.linalg.inv(gg)@np.array(r.pose.bones[n].matrix))),flush=True)
