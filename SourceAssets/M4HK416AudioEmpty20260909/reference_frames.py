import bpy, json
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HK416_reference.blend'))
scene=bpy.context.scene
a=bpy.data.actions['reload_empty']
rigs=[o for o in scene.objects if o.type=='ARMATURE']
print('SLOTS',[(s.identifier,s.target_id_type) for s in a.slots])
for o in rigs:
    o.animation_data_create();o.animation_data.action=a
    slot=next(s for s in a.slots if s.identifier[2:]==o.name)
    o.animation_data.action_slot=slot
camera_data=bpy.data.cameras.new('Reference');camera=bpy.data.objects.new('Reference',camera_data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=(0,0,0);camera.rotation_euler=Vector((0,-1,0)).to_track_quat('-Z','Y').to_euler();camera_data.lens=22;camera_data.clip_start=.001
scene.world=bpy.data.worlds.new('RefWorld');scene.world.color=(.17,.19,.22)
for loc in [(1,0,2),(-1,-1,1)]:
    d=bpy.data.lights.new('RefLight','AREA');d.energy=100;d.size=2;o=bpy.data.objects.new('RefLight',d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,-.3,0))-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=800;scene.render.resolution_y=500;scene.render.resolution_percentage=100
report=[]
for t in [1.333333,1.7,2.0,2.166667,2.3,2.55]:
    f=t/2.7*167.2;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
    gun=next(o for o in rigs if 'ARMA' in o.pose.bones);arm=next(o for o in rigs if 'mixamorig2:LeftHand' in o.pose.bones)
    root=gun.matrix_world@gun.pose.bones['ARMA'].matrix
    hand=arm.matrix_world@arm.pose.bones['mixamorig2:LeftHand'].matrix
    report.append({'runtime':t,'source_frame_24hz':f,'left_hand_in_gun':[list(r) for r in root.inverted()@hand],
                   'bolt':list(gun.pose.bones['CAMARA'].location),'release':list(gun.pose.bones['PALANCA'].rotation_quaternion)})
    scene.render.filepath=str(OUT/f'hk_reference_{round(t*1000)}.png');bpy.ops.render.render(write_still=True)
(OUT/'hk_motion.json').write_text(json.dumps(report,indent=2))
print('HK_REFERENCE_COMPLETE')
