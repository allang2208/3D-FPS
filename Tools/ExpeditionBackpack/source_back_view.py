"""DCC construction view needed to locate the supplied mesh's harness anchors."""
import bpy
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ExpeditionBackpack20261022')
bpy.ops.wm.open_mainfile(filepath=str(R/'ExpeditionBackpack_source.blend'))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('AuthorWorld');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[1].default_value=.5
for name,loc,energy in [('Key',(-1,2,2),180),('Fill',(2,1,1),130)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.size=2
    ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('SourceBack');ob=bpy.data.objects.new('SourceBack',cam);scene.collection.objects.link(ob);ob.location=(.7,2.5,.4);ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=.74;scene.camera=ob
scene.render.filepath=str(R/'Icon/source_back_authoring.png');bpy.ops.render.render(write_still=True)
