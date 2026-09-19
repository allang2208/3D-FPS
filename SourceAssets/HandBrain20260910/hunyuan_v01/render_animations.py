import bpy,sys
from pathlib import Path
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from studio import setup,aim
bpy.ops.wm.open_mainfile(filepath=str(root/'delivery/HandBrain_Animated.blend'))
rig=bpy.data.objects['SK_HandBrain'];scene=bpy.context.scene;cam=setup(640);scene.cycles.samples=8
aim(cam,(3,-7,2.6));cam.data.ortho_scale=3.25
for name,duration in [('Idle',2),('Move',1),('Attack_Slam',2)]:
    action=bpy.data.actions[name];rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    out=root/'preview_frames'/name;out.mkdir(parents=True,exist_ok=True)
    for k in range(duration*12):
        frame=1+k*30/12;scene.frame_set(int(frame),subframe=frame-int(frame))
        scene.render.filepath=str(out/f'{k:03}.png');bpy.ops.render.render(write_still=True)
    print('CLIP_RENDERED',name,flush=True)
