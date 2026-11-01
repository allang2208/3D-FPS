import bpy,json,math,os
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;phase=os.environ.get('THUNDER_REVIEW_PHASE','before');throw=os.environ.get('THUNDER_REVIEW_KIND')=='throw';O=P/(phase+('-throw' if throw else ''));O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/('ThunderThrowV1/ThunderHammer_Throw_Editable.blend' if throw else 'RecallCatchV2/ThunderHammer_RecallCatch_Editable.blend')))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];arms=bpy.data.objects['Warhammer_BareArmsV7']
for o in list(bpy.context.scene.objects):
    if o not in (rig,arms):bpy.data.objects.remove(o,do_unlink=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=[n for n in a.objects if n.startswith('SM_ThunderGodHammer_') and n.endswith('_factory')]
parts=[o for o in b.objects if o];mounts={o.name:Matrix.Translation(o.location.copy()) for o in parts}
for o in parts:bpy.context.collection.objects.link(o);o.parent=None;o.hide_render=False
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.world.color=(.22,.22,.22)
bpy.ops.object.camera_add(location=(0,0,0));cam=bpy.context.object;cam.data.clip_start=.008;cam.data.clip_end=100;cam.data.lens=18;scene.camera=cam
for loc,power,size in [((-.8,.2,1.3),90,1.4),((.8,.5,.4),65,1.1),((0,-.2,.1),25,1)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,.35,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
shots=[('ready',.32,'fp'),('catch',.06,'fp'),('catch',.18,'fp'),('catch',.36,'fp'),('catch',.595833333,'fp'),('catch',.60,'fp'),('ready',.32,'side'),('catch',.10,'side'),('catch',.36,'side')]
if throw:shots=[('charge',0.,'fp'),('charge',.3,'fp'),('charge',1.3,'fp'),('release',.1,'fp'),('release',.24,'fp'),('release',.36,'fp'),('release',.86,'fp'),('charge',1.3,'side'),('release',.24,'side')]
for j,(kind,t,view) in enumerate(shots):
    name=('A_ThunderHammer_ThrowCharge' if kind=='charge' else 'A_ThunderHammer_ThrowRelease') if throw else ('A_ThunderHammer_RecallReady_V2' if kind=='ready' else 'A_ThunderHammer_Catch_V2')
    a=bpy.data.actions[name];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    frame=t*240;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
    for o in parts:o.matrix_world=rig.matrix_world@rig.pose.bones['WPN_root'].matrix@mounts[o.name];o.hide_render=kind=='ready' or (kind=='release' and t>.24)
    if view=='fp':cam.location=(0,0,0);look=Vector((0,1,0));cam.data.lens=18
    else:cam.location=(.62,.53,.03);look=rig.pose.bones['hand_r'].matrix.translation-cam.location;cam.data.lens=28
    cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(O/f'{j:02d}_{kind}_{t:.3f}_{view}.png');bpy.ops.render.render(write_still=True)
print('RECALL_KEYFRAMES_RENDERED '+phase)
