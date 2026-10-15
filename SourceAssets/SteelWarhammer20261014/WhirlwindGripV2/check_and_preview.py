"""User-requested whole-clip contact/joint check and source-pose previews."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Warhammer_Whirlwind_IdleGrip_Editable.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
scene.frame_set(0);idle={b.name:b.matrix.copy() for b in rig.pose.bones}
grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
metric={'samples':1093,'source_sample_rate':600,'grip_position_error_mm':0.,'grip_rotation_error_degrees':0.,
        'bone_length_error_mm':0.,'bone_scale_error':0.,'max_hand_step_mm_at_600hz':0.,
        'min_hand_spacing_cm':1000.,'max_hand_spacing_cm':0.,'max_local_joint_step_degrees_at_600hz':0.,
        'endpoint_position_error_mm':0.,'endpoint_rotation_error_degrees':0.,'runtime_tested':False}
last=None;spine=[]
for i in range(1093):
    f=i*.5;scene.frame_set(int(f),subframe=f-int(f));pose={b.name:b.matrix.copy() for b in rig.pose.bones}
    wp=pose['WPN_root'];spacing=(pose['hand_l'].translation-pose['hand_r'].translation).length*100
    metric['min_hand_spacing_cm']=min(metric['min_hand_spacing_cm'],spacing)
    metric['max_hand_spacing_cm']=max(metric['max_hand_spacing_cm'],spacing)
    for side in ('l','r'):
        hand='hand_'+side;g=wp.inverted()@pose[hand]
        error=(g.translation-grips[side].translation).length*1000
        if error>metric['grip_position_error_mm']:metric['grip_position_error_mm']=error;metric['grip_error_time']=i/600
        metric['grip_rotation_error_degrees']=max(metric['grip_rotation_error_degrees'],math.degrees(g.to_quaternion().rotation_difference(grips[side].to_quaternion()).angle))
        for a,b in [('upperarm','lowerarm'),('lowerarm','hand')]:
            an,bn=a+'_'+side,b+'_'+side
            metric['bone_length_error_mm']=max(metric['bone_length_error_mm'],abs((pose[an].translation-pose[bn].translation).length-(idle[an].translation-idle[bn].translation).length)*1000)
        if last:
            step=(pose[hand].translation-last[hand].translation).length*1000
            if step>metric['max_hand_step_mm_at_600hz']:metric['max_hand_step_mm_at_600hz']=step;metric['hand_step_time']=i/600
    for bone in rig.pose.bones:
        name=bone.name
        metric['bone_scale_error']=max(metric['bone_scale_error'],max(abs(a-b) for a,b in zip(pose[name].to_scale(),idle[name].to_scale())))
        if last and name.startswith(('upperarm','lowerarm','hand_')):
            p=bone.parent.name;now=pose[p].inverted()@pose[name];before=last[p].inverted()@last[name]
            step=math.degrees(now.to_quaternion().rotation_difference(before.to_quaternion()).angle)
            if step>metric['max_local_joint_step_degrees_at_600hz']:metric['max_local_joint_step_degrees_at_600hz']=step;metric['joint_step_time']=i/600;metric['joint_step_bone']=name
    last=pose
for n,m in last.items():
    metric['endpoint_position_error_mm']=max(metric['endpoint_position_error_mm'],(m.translation-idle[n].translation).length*1000)
    metric['endpoint_rotation_error_degrees']=max(metric['endpoint_rotation_error_degrees'],math.degrees(m.to_quaternion().rotation_difference(idle[n].to_quaternion()).angle))
metric['contact_and_length_pass']=metric['grip_position_error_mm']<.15 and metric['grip_rotation_error_degrees']<.15 and metric['bone_length_error_mm']<.10 and metric['bone_scale_error']<.001
(P/'whole_clip_check.json').write_text(json.dumps(metric,indent=2),encoding='utf-8');print(json.dumps(metric),flush=True)
if not metric['contact_and_length_pass']:raise RuntimeError('Contact or segment-length check failed')
for obj in list(scene.objects):
    if obj not in (rig,bpy.data.objects.get('SM_SteelWarhammer'),bpy.data.objects.get('Warhammer_BareArmsV7')):bpy.data.objects.remove(obj,do_unlink=True)
world=bpy.data.worlds.new('WhirlwindInspection');world.use_nodes=True;world.node_tree.nodes.clear()
bg=world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(.18,.21,.26,1);bg.inputs['Strength'].default_value=.7
wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs['Surface']);scene.world=world
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.device='CPU'
scene.render.resolution_x=800;scene.render.resolution_y=450;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.view_settings.exposure=0
bpy.ops.object.camera_add(location=(0,0,0));camera=bpy.context.object
camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
camera.data.type='PERSP';camera.data.sensor_fit='HORIZONTAL';camera.data.angle=math.radians(112);camera.data.clip_start=.01;scene.camera=camera
for loc,power,size in [((-1,1,1.5),100,2),((1.2,.8,.5),90,1.6),((0,-1,.8),80,1.2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(Vector((0,.4,-.1))-lamp.location).to_track_quat('-Z','Y').to_euler()
for name,t in [('idle',0.),('ready',.5),('spin',1.05),('spin_end',1.3),('extended',1.48),('return',1.67)]:
    scene.frame_set(round(t*300));scene.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
camera.location=(1.35,-.55,.30);camera.data.angle=math.radians(62)
camera.rotation_euler=(Vector((0,.25,-.20))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.frame_set(444);scene.render.filepath=str(P/'extended_side.png');bpy.ops.render.render(write_still=True)
metric['source_previews_rendered']=True
(P/'whole_clip_check.json').write_text(json.dumps(metric,indent=2),encoding='utf-8')
