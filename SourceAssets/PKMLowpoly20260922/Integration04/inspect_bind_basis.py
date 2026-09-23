import bpy,json,pathlib
from mathutils import Matrix
O=pathlib.Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Mechanics02/PKM_Mechanics_Editable.blend'))
mr={b.name:b.matrix_local.copy() for b in bpy.data.objects['PKM_MechanicalRig'].data.bones}
bpy.ops.wm.open_mainfile(filepath=str(R/'Animation03/PKM_Manny_Reload_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];a=bpy.data.actions['PKM_Idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);rw=r.data.bones['WPN_root'].matrix_local;pw=r.pose.bones['WPN_root'].matrix
out={}
for n in ['PKM_Cover','PKM_Box','PKM_BoxLid','PKM_Belt_00']:
 b=r.data.bones[n];p=r.pose.bones[n]
 out[n]={'rest_error':max(abs(x-y) for row1,row2 in zip(b.matrix_local,rw@fit@mr[n]) for x,y in zip(row1,row2)),'pose_error':max(abs(x-y) for row1,row2 in zip(p.matrix,pw@fit@mr[n]) for x,y in zip(row1,row2)),'rest':[list(v) for v in b.matrix_local],'expected_rest':[list(v) for v in rw@fit@mr[n]],'inherit':b.use_inherit_rotation,'parent':b.parent.name}
print(json.dumps(out));(O/'bind_basis_inspection.json').write_text(json.dumps(out,indent=2))
