"""Read source action data for candidate selection. No game or render."""
import bpy,json,math
from pathlib import Path
OUT=Path(__file__).resolve().parent
report={}
for stem in ['Free3D_Cross_Attack','Free3D_Heavy_Attack']:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/(stem+'.blend')))
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    first,last=arm.animation_data.action.frame_range
    fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    names=['RightArm','RightForeArm','RightHand','LeftArm','LeftForeArm','LeftHand',
           'RightUpLeg','RightLeg','LeftUpLeg','LeftLeg','Spine','Spine1','Spine2']
    bones={n:next(b for b in arm.pose.bones if b.name.split(':')[-1]==n) for n in names}
    samples={n:[] for n in names}
    positions={n:[] for n in ['LeftHand','RightHand']}
    for frame in range(int(first),int(last)+1):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        for n,b in bones.items():samples[n].append(b.matrix_basis.to_quaternion().copy())
        for n in positions:positions[n].append(list(arm.matrix_world@bones[n].head))
    row={'duration_seconds':(last-first)/fps,'samples':int(last-first+1),'fps':fps,
         'max_local_rotation_change_deg':{},'hands_world':positions}
    for n,values in samples.items():
        row['max_local_rotation_change_deg'][n]=round(max(min(a:=values[0].rotation_difference(q).angle,2*math.pi-a) for q in values)*180/math.pi,2)
    report[stem]=row
    print(stem,row['duration_seconds'],row['samples'],row['max_local_rotation_change_deg'])
(OUT/'free3d-motion-evidence.json').write_text(json.dumps(report,indent=2))
