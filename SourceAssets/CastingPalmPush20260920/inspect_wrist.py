"""Render and measure the requested cast wrist/forearm comparison only."""
import bpy, json, math, sys, argparse
from pathlib import Path
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--output',required=True)
p.add_argument('--motion',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=a.blend)
rig=bpy.data.objects['SK_FireballCasting_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export']
# A linked source collection contains a studio wall that occludes the side view.
# A temporary scene isolates the actual skinned arm without changing the blend.
scene=bpy.data.scenes.new('WristReviewOnly');bpy.context.window.scene=scene
scene.collection.objects.link(rig);scene.collection.objects.link(arms)
camera=bpy.data.objects.new('WristReviewCamera',bpy.data.cameras.new('WristReviewCamera'))
scene.collection.objects.link(camera);scene.camera=camera
rig.animation_data.action=bpy.data.actions['A_Fireball_CastDetached']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
records=[]
duration=rig.animation_data.action.frame_range[1]/300
def angle(x,y):return math.degrees(x.angle(y))
for seconds in sorted(set([min(i/60,duration) for i in range(math.ceil(duration*60)+1)]+[.13,.26,.34,.46,.60,.75,.90,1.12,duration])):
    scene.frame_set(round(seconds*300));bpy.context.view_layer.update()
    pose=rig.pose.bones;A=pose['upperarm_l'].head;E=pose['lowerarm_l'].head;H=pose['hand_l'].head
    F=pose['middle_01_l'].head-H
    R=rig.data.bones
    RH=R['hand_l'].head_local
    rf=(R['middle_01_l'].head_local-RH).normalized()
    rn=(R['pinky_01_l'].head_local-RH).cross(R['index_01_l'].head_local-RH).normalized()
    across=rf.cross(rn).normalized();ld=(H-E).normalized()
    lower_side=(pose['lowerarm_l'].matrix.to_quaternion()@R['lowerarm_l'].matrix_local.to_quaternion().inverted())@across
    hand_side=(pose['hand_l'].matrix.to_quaternion()@R['hand_l'].matrix_local.to_quaternion().inverted())@across
    records.append({'t':seconds,'shoulder':list(A),'elbow':list(E),'wrist':list(H),
        'wrist_bend_deg':angle(H-E,F),
        'wrist_twist_deg':angle(lower_side-ld*lower_side.dot(ld),hand_side-ld*hand_side.dot(ld)),
        'upper_length_ratio':(E-A).length/(R['lowerarm_l'].head_local-R['upperarm_l'].head_local).length,
        'lower_length_ratio':(H-E).length/(R['hand_l'].head_local-R['lowerarm_l'].head_local).length,
        'lower_scale':list(pose['lowerarm_l'].matrix.to_scale()),'hand_scale':list(pose['hand_l'].matrix.to_scale())})
(out/'pose-measurements.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
scene.frame_set(225);bpy.context.view_layer.update()
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
world=bpy.data.worlds.new('WristReviewWorld');scene.world=world;world.use_nodes=True
world.node_tree.nodes.clear();background=world.node_tree.nodes.new('ShaderNodeBackground');output=world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs[0],output.inputs[0]);background.inputs[0].default_value=(.15,.18,.22,1);background.inputs[1].default_value=.7
clay=bpy.data.materials.new('WristReviewClay');clay.use_nodes=True
clay.node_tree.nodes.clear();shader=clay.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=clay.node_tree.nodes.new('ShaderNodeOutputMaterial')
clay.node_tree.links.new(shader.outputs[0],output.inputs[0]);shader.inputs['Base Color'].default_value=(.34,.39,.45,1);shader.inputs['Roughness'].default_value=.7
scene.view_layers[0].material_override=clay
for ob in list(bpy.data.objects):
    if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
for pos,power,size in [((.3,-.3,.7),180,1.0),((-.7,.6,.3),100,1.2)]:
    data=bpy.data.lights.new('WristReviewLight','AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector((-.22,.35,-.2))-ob.location).to_track_quat('-Z','Y').to_euler()
camera=scene.camera;camera.data.type='PERSP';camera.data.lens=26
for name,position,target in [('player',(0,0,0),(-.17,.48,-.15)),('side',(-.9,.38,-.06),(-.22,.32,-.25))]:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
hold=min(records,key=lambda r:abs(r['t']-.75))
summary={'output':str(out),'hold_metrics':hold,'max_wrist_bend':max(r['wrist_bend_deg'] for r in records),
    'max_wrist_twist':max(r['wrist_twist_deg'] for r in records),
    'max_length_error':max(abs(r[k]-1) for r in records for k in ['upper_length_ratio','lower_length_ratio'])}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
if a.motion:
    scene.render.resolution_x=720;scene.render.resolution_y=556;scene.cycles.samples=6
    camera.location=(0,0,0);camera.rotation_euler=(Vector((-.17,.48,-.15))-camera.location).to_track_quat('-Z','Y').to_euler()
    frames=out/'Motion';frames.mkdir(exist_ok=True)
    # Pause briefly on the initial grip at each loop. Source motion remains at
    # real speed (20 fps) and includes the entire fixed 0.30-second push hold.
    for index in range(round(duration*20)+1):
        scene.frame_set(round(min(index/20,duration)*300));bpy.context.view_layer.update()
        scene.render.filepath=str(frames/f'{index:03d}.png');bpy.ops.render.render(write_still=True)
