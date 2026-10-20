import bpy, math, os
from mathutils import Vector
p=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\Authoring\SVCH_Viewmodel.blend"
out=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\Previews"
bpy.ops.wm.open_mainfile(filepath=p)
sc=bpy.context.scene
COLOURS={'Body':(0.34,0.36,0.40),'Magazine':(0.20,0.55,1.0),'BoltCarrier':(0.55,0.30,0.95),
         'ChargingHandle':(0.55,0.30,0.95),'MagRelease':(1.0,0.35,0.85),'Selector':(1.0,0.95,0.35),
         'Cartridge':(0.95,0.25,0.25)}
for o in sc.objects:
    if o.type=='MESH' and o.name.startswith('SM_SVCH_'):
        part=o.name[len('SM_SVCH_'):]
        for m in o.data.materials:
            m.use_nodes=True
            bs=m.node_tree.nodes.get('Principled BSDF')
            if bs: bs.inputs['Base Color'].default_value=(*COLOURS.get(part,(0.8,0.8,0.8)),1)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=40
sc.render.resolution_x=1800; sc.render.resolution_y=900
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.16,0.17,0.19,1)
w.node_tree.nodes['Background'].inputs[1].default_value=1.3
sun=bpy.data.objects.new('Sun',bpy.data.lights.new('Sun',type='SUN')); sun.data.energy=5.0
sun.rotation_euler=(math.radians(60),0,math.radians(40)); sc.collection.objects.link(sun)
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'
def shot(name,loc,look,ortho=120):
    cam.data.ortho_scale=ortho; cam.location=Vector(loc)
    cam.rotation_euler=(Vector(look)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=os.path.join(out,name); bpy.ops.render.render(write_still=True); print('SHOT',name)
shot('bind_side_left',(-200,-20,-6),(6,-20,-6))
shot('bind_side_right',(200,-20,-6),(6,-20,-6))
shot('bind_top',(6,-20,200),(6,-20,-6))
print('DONE')
