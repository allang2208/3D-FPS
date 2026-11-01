from pathlib import Path
exec(compile((Path(__file__).parent/'surface_scan.py').read_text().split('samples=[]')[0],'elbow_preview','exec'))
label='after' if 'candidate' in sys.argv else 'before'
row=runtime(.275,.275);set_pose(row);morphs_full();r.matrix_world=Matrix.Identity(4)
target=row['lowerarm_l'].translation
cam.location=target+Vector((-.28,-.15,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.20
s.render.resolution_x=720;s.render.resolution_y=540;s.render.filepath=str(O/('elbow_'+label+'.png'));bpy.ops.render.render(write_still=True)
