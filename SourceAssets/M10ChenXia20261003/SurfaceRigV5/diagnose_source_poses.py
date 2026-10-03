"""Requested, narrowly scoped source-pose inspection (no UE/game automation)."""
from pathlib import Path
import bpy,math,json,sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Diagnosis';OUT.mkdir(exist_ok=True)
def ramp(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for revision,file in [('before',ROOT.parent/'HowlV4/Delivery/M10_HowlV4_Editable.blend'),('after',ROOT/'Delivery/M10_SurfaceRigV5_Editable.blend')]:
    if '--howl-only' in sys.argv and revision=='before':continue
    if '--before-howl' in sys.argv and revision=='after':continue
    bpy.ops.wm.open_mainfile(filepath=str(file));scene=bpy.context.scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    obj=next(o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers))
    original=list(obj.data.materials)
    for other in scene.objects:
        if other.type=='MESH' and other!=obj and not other.name.startswith('M10_Oral'):other.hide_render=True
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=900;scene.render.resolution_y=650;scene.render.resolution_percentage=100
    if scene.world is None:scene.world=bpy.data.worlds.new('DiagnosisWorld')
    scene.world.use_nodes=True;tree=scene.world.node_tree;tree.nodes.clear()
    background=tree.nodes.new('ShaderNodeBackground');background.inputs[0].default_value=(.055,.065,.08,1);background.inputs[1].default_value=.4
    output=tree.nodes.new('ShaderNodeOutputWorld');tree.links.new(background.outputs[0],output.inputs['Surface'])
    scene.view_settings.view_transform='AgX'
    camdata=bpy.data.cameras.new('DiagnosisCamera');cam=bpy.data.objects.new('DiagnosisCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
    for name,pos,power,size in [('Key',(4,-3,5),700,3),('Fill',(3,3,2),450,3),('Rim',(-1,-1,4),600,3)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=pos;light.rotation_euler=(Vector((.8,0,.4))-light.location).to_track_quat('-Z','Y').to_euler()
    clay=bpy.data.materials.new('DiagnosisClay');clay.use_nodes=True;bsdf=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=(.38,.43,.47,1);bsdf.inputs['Roughness'].default_value=.65
    cases=[('face_clay','Idle',1,True,(4.0,-.95,1.0),(1.8,0,.36),1.40),('turn_roots','PivotLeft',10,True,(3.6,-4,2.5),(.0,-.35,.45),4.5)]
    if revision=='after':cases += [('face_texture','Idle',1,False,(4.0,-.95,1.0),(1.8,0,.36),1.4),('howl_texture','Howl',31,False,(4.0,-.95,1.0),(1.8,0,.38),1.5)]
    if '--howl-only' in sys.argv or '--before-howl' in sys.argv:cases=[('howl_texture','Howl',31,False,(4.0,-.95,1.0),(1.8,0,.38),1.5)]
    for label,role,frame,use_clay,eye,target,scale in cases:
        name='M10_'+role+'_V5' if revision=='after' else {'Idle':'M10_Idle','PivotLeft':'M10_PivotLeft_V2','Howl':'M10_Howl_V4'}[role]
        action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(frame)
        if obj.data.shape_keys:
            jaw=rig.pose.bones['jaw'];head=rig.pose.bones['head'];rest=rig.data.bones['head'].matrix_local.inverted()@rig.data.bones['jaw'].matrix_local
            neutral=head.matrix@rest;degrees=math.degrees(neutral.to_quaternion().rotation_difference(jaw.matrix.to_quaternion()).angle)
            obj.data.shape_keys.key_blocks['M10_MouthOpenTissue'].value=ramp(12,38,degrees)
            obj.data.shape_keys.key_blocks['M10_MouthWideTissue'].value=ramp(26,43,degrees)
        obj.data.materials.clear()
        for material in ([clay] if use_clay else original):obj.data.materials.append(material)
        cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=scale
        scene.render.filepath=str(OUT/f'{revision}_{label}.png');bpy.ops.render.render(write_still=True)
        print('M10_SCOPED_SOURCE_POSE',revision,label,flush=True)
print('M10_SOURCE_POSE_DIAGNOSIS_COMPLETE',flush=True)
