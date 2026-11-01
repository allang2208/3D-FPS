from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'preview.py').read_text().split('for name,role,f,view in')[0],'preview_setup','exec'))
folder=O/'CameraFrames';folder.mkdir(exist_ok=True)
for role,frames in [('aim',[0]),('fire',[12,16,25,40,48]),('reload_empty',[30,60,68,77,94]),('sprint_enter',[6,10]),('sprint_loop',[15])]:
 for f in frames:
  pose(role,f);r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
  s.render.resolution_x=640;s.render.resolution_y=360;s.render.filepath=str(folder/(role+'_'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
