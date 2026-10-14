import bpy,pathlib
from mathutils import Vector
R=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(R/'output/Incinerator_Game.blend'))
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.002));m=bpy.data.materials.new('Backdrop');m.diffuse_color=(.037,.049,.061,1);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.037,.049,.061,1);bs.inputs['Roughness'].default_value=.85;bpy.context.object.data.materials.append(m)
for name,loc,power,size in [('Key',(-3,-4,5),950,3),('Fill',(4,-2,3),750,3),('Rim',(1,3,4),1100,2.5)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-5,2.0));c=bpy.context.object;c.rotation_euler=(Vector((0,0,1.03))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=2.8
s=bpy.context.scene;s.camera=c;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.world=bpy.data.worlds.new('Studio');s.world.color=(.2,.2,.2);s.view_settings.view_transform='AgX';s.render.resolution_x=1400;s.render.resolution_y=1500;s.render.resolution_percentage=100;s.render.filepath=str(R/'output/Incinerator_Front.png');bpy.ops.render.render(write_still=True)
