import bpy
from pathlib import Path
from mathutils import Vector
import numpy as np
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
for name in ("Optic","Magnifier","Glass","Cover"):
    d=np.load(root/"Geometry"/(name+".npz"))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(d["positions"].tolist(),[],d["faces"].tolist())
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new(name);mat.diffuse_color={"Optic":(.26,.36,.46,1),"Magnifier":(.42,.32,.20,1),"Glass":(.1,.4,.45,1),"Cover":(.15,.15,.15,1)}[name]
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=mat.diffuse_color
    bsdf.inputs["Roughness"].default_value=.55
    obj.data.materials.append(mat)
scene=bpy.context.scene
scene.render.engine="CYCLES";scene.cycles.samples=16
scene.render.resolution_x=1100;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new("World");scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.18,.18,.18,1)
for pos,power in (((.1,-.3,.4),20),((.15,.3,.2),10)):
    data=bpy.data.lights.new("Softbox","AREA");data.energy=power;data.shape="DISK";data.size=.3
    obj=bpy.data.objects.new("Softbox",data);bpy.context.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((.11,0,.1))-obj.location).to_track_quat("-Z","Y").to_euler()
data=bpy.data.cameras.new("Camera");cam=bpy.data.objects.new("Camera",data);bpy.context.collection.objects.link(cam);scene.camera=cam;data.type="ORTHO";data.ortho_scale=.27
for label,pos in (("side",(.145,-.5,.19)),("rear",(.60,-.07,.17))):
    cam.location=pos;cam.rotation_euler=(Vector((.115,0,.1))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(root/"Repair02"/("optic_"+label+".png"));bpy.ops.render.render(write_still=True)
