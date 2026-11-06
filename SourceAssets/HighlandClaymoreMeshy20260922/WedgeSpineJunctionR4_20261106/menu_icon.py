"""Production inventory icon using two asymmetrical strip reflections over the long faces."""
import math
import bpy
from mathutils import Matrix,Vector

def render_icon(scene,blade,path):
    path.parent.mkdir(exist_ok=True)
    for obj in scene.objects:
        if obj.type=='MESH':
            obj.hide_render=obj!=blade
    scene.render.engine='CYCLES'
    scene.cycles.samples=36
    scene.cycles.use_denoising=True
    scene.render.resolution_x=scene.render.resolution_y=1024
    scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.world=bpy.data.worlds.new('Blade finish studio')
    scene.world.use_nodes=True
    bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs[0].default_value=(.18,.18,.18,1)
    bg.inputs[1].default_value=.4
    center=Vector((0,0,.5545))
    spin=Matrix.Rotation(math.radians(8),3,'Z')
    camera=bpy.data.objects.new('Catalog camera',bpy.data.cameras.new('Catalog camera'))
    scene.collection.objects.link(camera)
    camera.data.type='ORTHO'
    camera.data.ortho_scale=1.226
    camera.rotation_euler=(spin@Matrix(((0,1,0),(0,0,-1),(-1,0,0)))).to_euler()
    camera.location=center+spin@Vector((0,-1.55,0))
    scene.camera=camera
    for label,xyz,power,w,h in [
        ('Long key',(.34,-.45,.61),14,.20,1.38),('Soft return',(-.37,-.36,.48),6,.34,1.24),
        ('Root glint',(-.06,-.26,-.21),3,.14,.42),('Spine light',(.06,.40,1.04),12,.18,.88)]:
        lamp=bpy.data.objects.new(label,bpy.data.lights.new(label,'AREA'))
        scene.collection.objects.link(lamp)
        lamp.location=xyz
        lamp.rotation_euler=(Vector((0,0,max(.055,min(1.,xyz[2]))))-lamp.location).to_track_quat('-Z','Y').to_euler()
        lamp.data.shape='RECTANGLE'
        lamp.data.size=w
        lamp.data.size_y=h
        lamp.data.energy=power
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
