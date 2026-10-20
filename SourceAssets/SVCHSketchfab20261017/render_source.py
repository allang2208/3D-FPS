import bpy, math, os
from mathutils import Vector
src=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\download\svch.glb"
out=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\Previews"
os.makedirs(out,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
keep=[]
for o in list(bpy.context.scene.objects):
    if o.type=='MESH' and len(o.vertex_groups): keep.append(o)
for o in list(bpy.context.scene.objects):
    if o not in keep:
        try: bpy.data.objects.remove(o,do_unlink=True)
        except Exception: pass
sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=48
sc.render.resolution_x=1600; sc.render.resolution_y=900
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.20,0.21,0.23,1)
w.node_tree.nodes['Background'].inputs[1].default_value=1.6
sun=bpy.data.objects.new('Sun',bpy.data.lights.new('Sun',type='SUN')); sun.data.energy=4.0
sun.rotation_euler=(math.radians(55),0,math.radians(35)); sc.collection.objects.link(sun)
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'
def shot(name, loc, look, ortho=120):
    cam.data.ortho_scale=ortho
    cam.location=Vector(loc); cam.rotation_euler=(Vector(look)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=str(os.path.join(out,name)); bpy.ops.render.render(write_still=True)
    print("SHOT",name)
shot('side_right', (0,0,200), (0,0,0))
shot('top', (0,200,0), (0,0,0))
shot('three_quarter', (150,90,150), (0,0,0))
print("RENDER_DONE")
