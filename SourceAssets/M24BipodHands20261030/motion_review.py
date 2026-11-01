from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
first=sample_pose(0);root=first['WPN_root']@rest['WPN_root'].inverted()
target=(first['hand_l'].translation+first['upperarm_l'].translation)*.5+root.to_3x3()@Vector((0,.04,0))
cam.location=target+root.to_3x3()@Vector((-.5,-.14,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.70
s.render.resolution_x=640;s.render.resolution_y=400
for i in range(30):
    t=min(.48,i/60);set_pose(sample_pose(t),t)
    s.render.filepath=str(folder/(f'motion_{i:02d}.png'));bpy.ops.render.render(write_still=True)
print('ANATOMY_MOTION_RENDERED',label,flush=True)
