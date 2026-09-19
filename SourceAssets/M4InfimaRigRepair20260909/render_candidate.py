import bpy,json
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'SK_M4_Infima_RigRepair.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima']
for o in scene.objects:
    if o.type=='MESH':o.hide_render=o.parent!=rig
    if o.type=='LIGHT':o.hide_render=True
camera_data=bpy.data.cameras.new('RepairPreview');camera=bpy.data.objects.new('RepairPreview',camera_data)
scene.collection.objects.link(camera);scene.camera=camera;camera.location=(0,0,0)
camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();camera_data.lens=25;camera_data.clip_start=.001
lights=[]
for point in [(1,-1,2),(-1,0,1)]:
    d=bpy.data.lights.new('RepairLight','AREA');d.energy=100;d.size=2;o=bpy.data.objects.new('RepairLight',d)
    scene.collection.objects.link(o);o.location=point;o.rotation_euler=(Vector((0,.3,-.1))-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=750;scene.render.resolution_percentage=100
def action(key):
    rig.animation_data_create();a=bpy.data.actions['M4_'+key];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
def render(name,f):
    scene.frame_set(f);bpy.context.view_layer.update();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
for key,frames in [('idle',[0]),('fire',[2]),('reload',[0,30,60,90,114,138,160,188])]:
    action(key)
    for frame in frames:render(key+'_'+str(frame),frame)
# Inspect the real repaired hinge from the same gun-local direction used in the failing evidence.
for o in scene.objects:
    if o.type=='MESH' and o.name.startswith('SK_Manny'):o.hide_render=True
for key in ['idle','fire']:
    action(key);scene.frame_set(0 if key=='idle' else 2);bpy.context.view_layer.update()
    root=rig.pose.bones['WPN_root'];world=root.matrix@root.bone.matrix_local.inverted()
    # In the export frame, use the hinge and a side-on vector derived from its bone axes.
    hinge=rig.pose.bones['WPN_Trigger'].matrix.translation
    camera_data.type='ORTHO';camera_data.ortho_scale=.13
    axis=rig.pose.bones['WPN_Trigger'].matrix.to_3x3()@Vector((1,0,0))
    target=hinge+rig.pose.bones['WPN_root'].matrix.to_3x3()@Vector((0,0,-.025))
    camera.location=target+axis*.25;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    render('trigger_repaired_'+key,0 if key=='idle' else 2)
print('M4_RIG_PREVIEW_COMPLETE')
