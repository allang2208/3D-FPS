import bpy, math, os
import numpy as np
from mathutils import Vector
p=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\Authoring\SVCH_Viewmodel.blend"
src=r"D:\FPS3D\FPSGAME\SourceAssets\SVDCompletion20260923\SVD_Complete_Editable.blend"
out=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\Previews"
bpy.ops.wm.open_mainfile(filepath=p)
# append the accepted idle action
with bpy.data.libraries.load(src, link=False) as (a,b):
    b.actions=['A_SVD_idle']
act=bpy.data.actions['A_SVD_idle']
rig=bpy.data.objects['SK_M4_Infima']
rig.animation_data_create(); rig.animation_data.action=act
if getattr(act,'slots',None): rig.animation_data.action_slot=act.slots[0]
bpy.context.scene.frame_set(0); bpy.context.view_layer.update()
sc=bpy.context.scene
arms=bpy.data.objects['SVCH_BareArmsV9']
dg=bpy.context.evaluated_depsgraph_get()
ev=arms.evaluated_get(dg); me=ev.to_mesh(); P=np.array([[*v.co] for v in me.vertices]); ev.to_mesh_clear()
print("IDLE arms bbox", np.round(P.min(0),1), np.round(P.max(0),1))
body=bpy.data.objects['SM_SVCH_Body']
ev=body.evaluated_get(dg); me=ev.to_mesh(); Q=np.array([[*v.co] for v in me.vertices]); ev.to_mesh_clear()
print("IDLE gun  bbox", np.round(Q.min(0),1), np.round(Q.max(0),1))
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
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=48
sc.render.resolution_x=1600; sc.render.resolution_y=1000
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.17,0.18,0.20,1)
w.node_tree.nodes['Background'].inputs[1].default_value=1.5
sun=bpy.data.objects.new('Sun',bpy.data.lights.new('Sun',type='SUN')); sun.data.energy=5.0
sun.rotation_euler=(math.radians(60),0,math.radians(40)); sc.collection.objects.link(sun)
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'
def shot(name,loc,look,ortho=110):
    cam.data.ortho_scale=ortho; cam.location=Vector(loc)
    cam.rotation_euler=(Vector(look)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=os.path.join(out,name); bpy.ops.render.render(write_still=True); print('SHOT',name)
c=Vector(((P.min(0)+P.max(0))/2))
shot('idle_side_left',(c.x-260,c.y-20,c.z),(c.x,c.y,c.z))
shot('idle_side_right',(c.x+260,c.y-20,c.z),(c.x,c.y,c.z))
shot('idle_eye',(c.x,c.y-10,c.z+12),(c.x,c.y-30,c.z+8),60)
print('DONE')
