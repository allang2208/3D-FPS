import bpy
from pathlib import Path
from mathutils import Vector
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima');bpy.ops.wm.open_mainfile(filepath=str(out/'SK_M4_Infima_Export.blend'))
s=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima']
for o in s.objects:
 if o.type=='MESH':o.hide_render=o.parent!=rig
rig.animation_data_create();a=bpy.data.actions['M4_idle'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];s.frame_set(0)
d=bpy.data.cameras.new('ExportCamera');c=bpy.data.objects.new('ExportCamera',d);s.collection.objects.link(c);c.location=(0,0,0);c.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();d.lens=25;d.clip_start=.001;s.camera=c
for o in list(s.objects):
 if o.type=='LIGHT':o.hide_render=True
for co in [(1,-1,2),(-1,0,1)]:
 d=bpy.data.lights.new('Check','AREA');d.energy=100;d.size=2;o=bpy.data.objects.new('Check',d);s.collection.objects.link(o);o.location=co;o.rotation_euler=(Vector((0,.3,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(out/'export_idle_check.png');bpy.ops.render.render(write_still=True)
