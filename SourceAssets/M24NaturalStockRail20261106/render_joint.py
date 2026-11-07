from pathlib import Path
import bpy
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_NaturalStock.blend'),use_scripts=False)
scene=bpy.context.scene
for ob in scene.objects:
    if ob.type=='MESH':ob.hide_render='Advanced' in ob.name
# Neutral receiver coating for the source-geometry close-up; UE keeps its saved material.
mat=bpy.data.materials.new('Preview receiver coating');mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.055,.065,.075,1);p.inputs['Metallic'].default_value=.75;p.inputs['Roughness'].default_value=.34
for ob in scene.objects:
    if ob.type=='MESH':
        for i,m in enumerate(ob.data.materials):
            if m and m.name.startswith('CS_Receiver'):ob.data.materials[i]=mat
cam_data=bpy.data.cameras.new('Joint camera');cam=bpy.data.objects.new('Joint camera',cam_data);scene.collection.objects.link(cam);scene.camera=cam
cam.location=(.45,-.052,.145);target=Vector((0,-.050,.076));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.type='ORTHO';cam_data.ortho_scale=.195
for name,loc,power,size in [('Soft key',(.22,-.01,.4),18,.3),('Rim',(-.2,-.12,.25),22,.2),('Fill',(.15,-.24,.08),5,.25)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
if not scene.world:scene.world=bpy.data.worlds.new('Studio')
scene.world.color=(.10,.10,.10);scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(O/'stock_joint_source.png');bpy.ops.render.render(write_still=True)
