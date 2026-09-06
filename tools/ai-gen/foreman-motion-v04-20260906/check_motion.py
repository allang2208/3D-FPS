import bpy,json,math
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=80
bpy.ops.import_scene.gltf(filepath=str(R/'foreman-motion-v04.glb'))
a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');s=bpy.context.scene
body=next(o for o in s.objects if o.type=='MESH' and 'Body' in o.name)
for track in a.animation_data.nla_tracks:track.mute=True
report={}
for name,duration in [('Idle',1),('Walk',1.5),('Attack',1.5),('Death',1.4)]:
 act=next(act for act in bpy.data.actions if act.name.startswith(name));a.animation_data.action=act
 if act.slots:a.animation_data.action_slot=act.slots[0]
 start,end=act.frame_range;assert abs((end-start)/80-duration)<1e-5
 poses=[];lows=[];roots=[];feet=[]
 for i in range(round(duration*160)+1):
  f=start+i/160*80;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
  poses.append([b.matrix.copy() for b in a.pose.bones]);roots.append(a.pose.bones['pelvis'].matrix.translation.copy());feet.append([a.pose.bones['foot.'+side].matrix.translation.copy() for side in ['L','R']])
  ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();lows.append(min((ev.matrix_world@v.co).z for v in me.vertices));ev.to_mesh_clear()
 gap=max(abs(x[r][c]-y[r][c]) for x,y in zip(poses[0],poses[-1]) for r in range(4) for c in range(4))
 seam=max(abs((poses[1][j][r][c]-poses[0][j][r][c])-(poses[-1][j][r][c]-poses[-2][j][r][c]))*160 for j in range(len(poses[0])) for r in range(4) for c in range(4))
 report[name]={'seconds':duration,'loop_pose_error':gap,'loop_derivative_error':seam,'mesh_low_z':[min(lows),max(lows)],'max_pelvis_step':max((x-y).length for x,y in zip(roots,roots[1:]))}
 assert min(lows)>-.006,(name,min(lows))
 if name in ['Idle','Walk']:assert gap<.0001,(name,gap)
 if name=='Walk':
  slip=[]
  for i in range(1,len(feet)):
   for k in range(2):
    ph=(i/160/1.5+k*.5)%1
    if .06<ph<.56:
     # Imported Blender -Y forward; world travel compensates stance backmotion.
     slip.append(abs((feet[i][k].y-feet[i-1][k].y)*160-.40/(1.5*.62)))
  report[name]['max_stance_speed_error_mps']=max(slip)
(R/'review-report.json').write_text(json.dumps(report,indent=2));print('FOREMAN_V04_REVIEW',json.dumps(report))
