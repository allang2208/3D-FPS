exec(compile(open(__file__.replace('fit_support.py','check_contact.py')).read().split('for clip,end in')[0],__file__,'exec'))
a=bpy.data.actions['M4_HK416_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update();base={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
for d in [.012,.022,.032,.042,.052]:
 for n,m in base.items():r.pose.bones[n].matrix_basis=m
 bpy.context.view_layer.update();b=r.pose.bones['clavicle_l'];m=b.matrix.copy();m.translation+=r.pose.bones['WPN_root'].matrix.to_3x3()@Vector((0,-d,0));b.matrix=m;bpy.context.view_layer.update()
 D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center);ev=hm.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();coords=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',coords);p=(np.array(D.inverted()@ev.matrix_world)@np.column_stack((coords.reshape(-1,3)[ids],np.ones(len(ids)))).T).T[:,:3];ev.to_mesh_clear()
 q=np.stack((np.sqrt(p[:,0]**2+(p[:,2]+.085)**2)-.070,np.abs(p[:,1])-.0355),axis=1);distance=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.maximum(q[:,0],q[:,1]),0);print('SUPPORT',d,float(distance.min()*1000))
