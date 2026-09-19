import bpy
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'M4_EmptyReload_BoltRelease.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
for o in s.objects:
    if o.type=='MESH':o.hide_render=o.parent!=r
    if o.type=='LIGHT':o.hide_render=True
d=bpy.data.cameras.new('EmptyPreview');c=bpy.data.objects.new('EmptyPreview',d);s.collection.objects.link(c);s.camera=c
c.location=(-.07,-.10,.05);c.rotation_euler=Vector((0,1,-.04)).to_track_quat('-Z','Y').to_euler();d.lens=24;d.clip_start=.001
for loc in [(1,-1,2),(-1,0,1)]:
    d=bpy.data.lights.new('EmptyLight','AREA');d.energy=100;d.size=2;l=bpy.data.objects.new('EmptyLight',d);s.collection.objects.link(l);l.location=loc;l.rotation_euler=(Vector((0,.3,-.1))-l.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=960;s.render.resolution_y=600;s.render.resolution_percentage=100
for f in [114,138,156,174,184,208,228]:
    s.frame_set(f);bpy.context.view_layer.update();s.render.filepath=str(OUT/f'empty_{f}.png');bpy.ops.render.render(write_still=True)
print('M4_EMPTY_PREVIEW_COMPLETE')
