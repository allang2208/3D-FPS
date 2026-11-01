"""Scoped source playback review, including every joint key and keyframe sheets."""
from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'inspect_source.py').read_text().replace("O.parent/'M24MotionPolish20261027/M24_MotionPolish_Editable.blend'","O/'M24_ArmRebuild_Editable.blend'").replace("O/'source_before.json'","O/'source_after.json'")
exec(compile(code,'source_after','exec'))
for role,data in out['clips'].items():
 rows=[{n:Matrix(m) for n,m in row.items()} for row in data['poses']]
 delta={n:max(math.degrees(min(t,2*math.pi-t)) for a,b in zip(rows,rows[1:]) for t in [a[n].to_quaternion().rotation_difference(b[n].to_quaternion()).angle]) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r')}
 print('STEP',role,delta,flush=True)
exec(compile((O/'preview.py').read_text().split('for name,role,f,view in')[0],'preview_setup','exec'))
for role,frames in [('fire',[0,8,12,16,20,25,30,35,40,44,48,55]),('reload_empty',[0,13,21,30,38,48,60,68,77,87,94,110]),('sprint_enter',[0,3,6,9,12,15])]:
 folder=O/'ReviewFrames'/role;folder.mkdir(parents=True,exist_ok=True)
 s.render.resolution_x=640;s.render.resolution_y=360
 for f in frames:
  pose(role,f);r.matrix_world=Matrix.Identity(4)
  target=r.pose.bones['WPN_BoltHandle'].matrix.translation
  cam.location=target+Vector((.4,-.20,.15));cam.rotation_euler=(target+Vector((0,-.02,-.03))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.65
  s.render.filepath=str(folder/(str(f)+'.png'));bpy.ops.render.render(write_still=True)
