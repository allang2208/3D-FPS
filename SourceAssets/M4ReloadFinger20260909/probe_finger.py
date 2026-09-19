import bpy,json,math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4InfimaRigRepair20260909/SK_M4_Infima_RigRepair.blend')
scene=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima']
for o in scene.objects:
    if o.type=='MESH':o.hide_render=o.parent!=rig
    if o.type=='LIGHT':o.hide_render=True
camdata=bpy.data.cameras.new('FingerCamera');cam=bpy.data.objects.new('FingerCamera',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.20;camdata.clip_start=.001
for p in [(1,-1,2),(-1,0,1)]:
    d=bpy.data.lights.new('FingerLight','AREA');d.energy=120;d.size=2;o=bpy.data.objects.new('FingerLight',d)
    scene.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,.3,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
report={}
for action,frame in [('idle',0),('reload',60),('reload',114)]:
    a=bpy.data.actions['M4_'+action];rig.animation_data_create();rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_set(frame);bpy.context.view_layer.update()
    names=['hand_r','index_01_r','index_02_r','index_03_r','middle_01_r','middle_02_r','middle_03_r']
    report[action+str(frame)]={n:{'q':list(rig.pose.bones[n].rotation_quaternion),'p':list(rig.pose.bones[n].head),'tail':list(rig.pose.bones[n].tail),'basis':list(rig.pose.bones[n].rotation_quaternion.to_euler())} for n in names}
    target=(rig.pose.bones['index_01_r'].head+rig.pose.bones['index_03_r'].tail)/2
    cam.location=target+Vector((.18,-.20,.08));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(action+str(frame)+'_before.png'));bpy.ops.render.render(write_still=True)
(OUT/'probe.json').write_text(json.dumps(report,indent=2))
print('FINGER_PROBE_PASS')
