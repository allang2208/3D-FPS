import bpy,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'hunyuan_v01'));import studio
bpy.ops.wm.open_mainfile(filepath=str(R/'delivery/HandBrain_SingleFace.blend'))
s=bpy.context.scene;rig=bpy.data.objects['SK_HandBrain'];a=bpy.data.actions['Attack_Howl'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
cam=studio.setup(640);s.cycles.samples=16;cam.data.ortho_scale=2.65
studio.aim(cam,(5,-5,1.9),(.15,0,1.02))
folder=R/'preview_frames';folder.mkdir(exist_ok=True)
for i in range(36):
 frame=1+i*2.5;s.frame_set(int(frame),subframe=frame%1)
 s.render.filepath=str(folder/f'{i:03}.png');bpy.ops.render.render(write_still=True)
studio.aim(cam,(6,0,1),(.28,0,.84));cam.data.ortho_scale=1.35
for f in [1,13,26,40,67,91]:
 s.frame_set(f);s.render.filepath=str(R/'delivery'/f'Face_{f:02}.png');bpy.ops.render.render(write_still=True)
print('SINGLE_FACE_PREVIEW_COMPLETE')
