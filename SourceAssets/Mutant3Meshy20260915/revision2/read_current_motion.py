"""Read the two user-reported animation problems on the current editable skin."""
import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'Mutant3_Meshy_Animated.blend'))
scene=bpy.context.scene; rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=360; scene.render.resolution_y=360; scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='SINGLE'
scene.display.shading.single_color=(.37,.43,.33)
scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
if scene.world is None: scene.world=bpy.data.worlds.new('MotionReadWorld')
scene.world.color=(.65,.65,.65)
camera=bpy.data.cameras.new('MotionReadCamera'); ob=bpy.data.objects.new('MotionReadCamera',camera); scene.collection.objects.link(ob)
ob.location=(3,-5,2.1); ob.rotation_euler=(Vector((0,0,.85))-ob.location).to_track_quat('-Z','Y').to_euler()
camera.type='ORTHO'; camera.ortho_scale=2.7; scene.camera=ob
(ROOT/'read_current').mkdir(exist_ok=True)
for role,frames in {'RunFast':[0,13.5,27,40.5,54],'Stagger':[0,12,72,90,108]}.items():
    action=bpy.data.actions['A_Mutant3_'+role]; rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
    for i,frame in enumerate(frames):
        scene.frame_set(math.floor(frame),subframe=frame%1)
        scene.render.filepath=str(ROOT/'read_current'/f'{role}_{i}.png'); bpy.ops.render.render(write_still=True)
print('CURRENT_MOTION_REFERENCE_READ',flush=True)
