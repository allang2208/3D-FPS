"""Render the requested source-motion reference before adapting the miner."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913')
OUT=ROOT/'PickaxeSingleHand/Reference'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'Reference/A_Mannequin_PickAxe_Act.fbx'),anim_offset=0)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=8
scene.cycles.use_denoising=True
scene.render.resolution_x=600;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('SourceWorld');world.use_nodes=True;scene.world=world
next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.5
material=bpy.data.materials.new('ReferenceGray');material.diffuse_color=(.32,.36,.4,1)
for obj in scene.objects:
    if obj.type=='MESH':obj.data.materials.clear();obj.data.materials.append(material)
for location,power in [((3,-4,5),1000),((-3,-2,3),700)]:
    data=bpy.data.lights.new('SourceSoftbox','AREA');data.energy=power;data.size=4
    light=bpy.data.objects.new('SourceSoftbox',data);scene.collection.objects.link(light)
    light.location=location;light.rotation_euler=(Vector((0,0,1.1))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('SourceCamera');data.type='ORTHO';data.ortho_scale=2.8
camera=bpy.data.objects.new('SourceCamera',data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=(3,-5,2.1);camera.rotation_euler=(Vector((0,-.05,1.05))-camera.location).to_track_quat('-Z','Y').to_euler()
for frame in [0,12,21,27]:
    scene.frame_set(frame);scene.render.filepath=str(OUT/f'Pickaxe_Source_{frame:02}.png')
    bpy.ops.render.render(write_still=True)
