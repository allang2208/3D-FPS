import bpy
from mathutils import Vector
def setup(size=720):
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=size;scene.render.resolution_y=size;scene.render.resolution_percentage=100
    world=bpy.data.worlds.new('Studio');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.13,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.4
    for loc,power,size in [((3,-4,5),450,4),((-3,-1,3),250,3),((1,4,4),350,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size
        o.rotation_euler=(Vector((.25,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object;floor.name='PreviewFloor'
    mat=bpy.data.materials.new('StudioGrey');mat.diffuse_color=(.12,.14,.13,1);floor.data.materials.append(mat)
    bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=3.1
    scene.camera=camera;scene.view_settings.view_transform='AgX'
    return camera
def aim(camera,loc,target=(.3,0,1)):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
