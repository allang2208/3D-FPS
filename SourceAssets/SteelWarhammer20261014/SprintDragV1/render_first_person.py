"""Requested first-person source-pose preview; real mesh, no concept generation."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Warhammer_SprintDrag_Editable.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
for obj in list(scene.objects):
    if obj not in (rig,bpy.data.objects['SM_SteelWarhammer'],bpy.data.objects['Warhammer_BareArmsV7']):bpy.data.objects.remove(obj,do_unlink=True)
world=bpy.data.worlds.new('WarhammerPreviewNeutral');world.use_nodes=True;world.node_tree.nodes.clear()
bg=world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(.18,.21,.26,1);bg.inputs['Strength'].default_value=.7
wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs['Surface']);scene.world=world
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG'
scene.view_settings.exposure=0
bpy.ops.object.camera_add(location=(0,0,0));camera=bpy.context.object;camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
camera.data.type='PERSP';camera.data.sensor_fit='HORIZONTAL';camera.data.angle=math.radians(112);camera.data.clip_start=.01;scene.camera=camera
for loc,power,size in [((-1,1,1.5),100,2),((1.2,.8,.5),90,1.6),((0,-1,.8),80,1.2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(Vector((0,.4,-.1))-lamp.location).to_track_quat('-Z','Y').to_euler()
for name,frame,file in [('A_Warhammer_SprintCarry',27,'carry_entry_first_person.png'),('A_Warhammer_SprintCarry',54,'sprint_first_person.png'),('A_Warhammer_SprintAttack',14,'attack_entry_first_person.png'),('A_Warhammer_SprintAttack',26,'attack_join_first_person.png')]:
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(frame)
    scene.render.filepath=str(P/file);bpy.ops.render.render(write_still=True)
