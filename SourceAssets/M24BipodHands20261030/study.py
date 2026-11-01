from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
t=.24;row=sample_pose(t);set_pose(row,t);active={k.name:k.value for k in skin.data.shape_keys.key_blocks if k.value>.01}
print('ACTIVE_SHAPES',len(skin.data.shape_keys.key_blocks),active,flush=True)
target=row['lowerarm_l'].translation
cam.location=target+Vector((-.25,-.12,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.27
for mode in ('all','no_shapes'):
    if mode=='no_shapes':
        for k in skin.data.shape_keys.key_blocks:k.value=0.
        bpy.context.view_layer.update()
    s.render.filepath=str(folder/('elbow_'+mode+'.png'));bpy.ops.render.render(write_still=True)
    print('ELBOW_VARIANT',mode,flush=True)
print('HELPERS',[(n,list((rest['upperarm_l'].inverted()@rest[n]).to_quaternion()),list((row['upperarm_l'].inverted()@row[n]).to_quaternion())) for n in ('upperarm_twist_01_l','upperarm_twist_02_l')],flush=True)
