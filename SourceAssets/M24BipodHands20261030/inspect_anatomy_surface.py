from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
row=sample_pose(.30);root=row['WPN_root']@rest['WPN_root'].inverted()
target=(row['lowerarm_l'].translation+row['upperarm_l'].translation)*.5
cam.location=target+root.to_3x3()@Vector((-.5,-.14,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.42
s.render.resolution_x=720;s.render.resolution_y=480
for mode in ('all','native_only','no_shapes'):
    set_pose(row,.30)
    for key in skin.data.shape_keys.key_blocks:
        if mode=='no_shapes' or (mode=='native_only' and key.name.startswith('M24_BipodElbow')):key.value=0
    bpy.context.view_layer.update();s.render.filepath=str(folder/('elbow_'+mode+'.png'));bpy.ops.render.render(write_still=True)
print('SURFACE_COMPONENTS_RENDERED',flush=True)
