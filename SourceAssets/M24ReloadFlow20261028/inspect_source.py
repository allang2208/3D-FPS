from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
out={'objects':[{'name':o.name,'parent':o.parent.name if o.parent else None,'hidden':o.hide_render,'location':list(o.location)} for o in s.objects if o.type=='MESH'],'poses':{}}
for role in ('reload','reload_mag10'):
 out['poses'][role]={str(f):{n:[round(v,3) for v in C@clips[role][f][n].translation] for n in ('upperarm_l','lowerarm_l','hand_l','WPN_Magazine')} for f in (18,20,21,22,23,24,26,28,30,31,32,34,36,38,40,42,44,48,54)}
(O/'source_layout.json').write_text(json.dumps(out,indent=2))
setup_render();s.render.resolution_x=800;s.render.resolution_y=450
set_pose(clips['reload'][25]);morphs();r.matrix_world=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))@C
cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
s.render.filepath=str(O/'before_release.png');bpy.ops.render.render(write_still=True)
print('M24_FLOW_SOURCE_READ',flush=True)
