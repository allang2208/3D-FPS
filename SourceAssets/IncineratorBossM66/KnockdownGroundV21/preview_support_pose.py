"""Single diagnostic source view of the intended full-body resting support."""
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'KnockdownGroundV21'
exec((ROOT/'find_support_pose.py').read_text('utf-8').split('rows=[]')[0])
DOWN_PITCH=1.55;DOWN_ROLL=-.35
rig.animation_data.action=None;make_pose('Landing',.9,.9);bpy.context.view_layer.update()
scene=bpy.context.scene
if mesh.data.shape_keys:
 for k in mesh.data.shape_keys.key_blocks:k.value=0.
material=bpy.data.materials.new('Diagnostic neutral surface');material.diffuse_color=(.34,.38,.40,1);mesh.data.materials.clear();mesh.data.materials.append(material)
for p in mesh.data.polygons:p.material_index=0
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,floor_z-.005));ground=bpy.context.object
floor_mat=bpy.data.materials.new('Diagnostic floor');floor_mat.diffuse_color=(.18,.19,.21,1);ground.data.materials.append(floor_mat)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
world=bpy.data.worlds.new('Diagnostic world');scene.world=world;world.use_nodes=True;world.node_tree.nodes.clear()
bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],out.inputs[0])
bg.inputs[0].default_value=(.30,.34,.40,1);bg.inputs[1].default_value=.5
light=bpy.data.lights.new('Diagnostic key','AREA');light.energy=1500;light.shape='DISK';light.size=5
o=bpy.data.objects.new('Diagnostic key',light);scene.collection.objects.link(o);o.location=(2,-3,7)
o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Diagnostic camera');camdata.type='ORTHO';camdata.ortho_scale=6
cam=bpy.data.objects.new('Diagnostic camera',camdata);scene.collection.objects.link(cam);cam.location=(6,-8,4.8)
cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.render.filepath=str(ROOT/'Records/down-support-prototype.png');bpy.ops.render.render(write_still=True)
