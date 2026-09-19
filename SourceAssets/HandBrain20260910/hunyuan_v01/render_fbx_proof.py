import bpy,sys
from pathlib import Path
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from studio import setup,aim
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
bpy.ops.import_scene.fbx(filepath=str(root/'delivery/SK_HandBrain_Animated.fbx'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
action=next(a for a in bpy.data.actions if 'Attack_Slam' in a.name)
rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
bpy.context.scene.frame_set(31)
cam=setup(640);aim(cam,(3,-7,2.6));cam.data.ortho_scale=3.25
bpy.context.scene.render.filepath=str(root/'delivery/FBX_impact_proof.png');bpy.ops.render.render(write_still=True)
