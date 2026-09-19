import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909/M4_EmptyReload_BoltRelease.blend')
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_equip']
r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
for o in s.objects:
    if o.type=='MESH':o.hide_render=o.parent!=r
    if o.type=='LIGHT':o.hide_render=True
d=bpy.data.cameras.new('EquipReference');c=bpy.data.objects.new('EquipReference',d);s.collection.objects.link(c);s.camera=c
c.location=(-.07,0,.07);c.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();d.lens=25;d.clip_start=.001
for loc in [(1,-1,2),(-1,0,1)]:
    d=bpy.data.lights.new('EquipLight','AREA');d.energy=100;d.size=2;l=bpy.data.objects.new('EquipLight',d);s.collection.objects.link(l);l.location=loc;l.rotation_euler=(Vector((0,.3,-.1))-l.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100
samples=[]
for f in [0,15,30,45,62]:
    s.frame_set(f);bpy.context.view_layer.update()
    samples.append({'frame':f,'time':f/60,'bones':{n:list(r.pose.bones[n].matrix.translation) for n in ['hand_l','hand_r','WPN_root','WPN_bolt']}})
    s.render.filepath=str(out/f'source_equip_{f:02}.png');bpy.ops.render.render(write_still=True)
(out/'source_equip.json').write_text(json.dumps({'action':'M4_equip','frames':list(a.frame_range),'fps':60,'samples':samples},indent=2))
print('EQUIP_REFERENCE_COMPLETE')
