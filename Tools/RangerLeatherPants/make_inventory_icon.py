"""Produce the catalog thumbnail from the selected model, not an acceptance render."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from integration_common import *
R.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'RangerLeatherPants_Editable.blend'))
source=bpy.data.objects['SK_Jason_RangerLeatherPants']
for ob in bpy.data.objects:
    if ob.type=='MESH':ob.hide_render=True
source.hide_render=False;source.hide_set(False);source.parent.hide_set(False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=512;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True;scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('CatalogWorld');world.use_nodes=True;world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs['Surface']);bg.inputs[0].default_value=(.18,.18,.18,1);bg.inputs[1].default_value=.3;scene.world=world
def point(ob,p):ob.rotation_euler=(Vector(p)-ob.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('Key',(-1.5,-2,2.3),250,1.8),('Fill',(1.8,-1.3,1),90,2),('Rim',(.5,1.4,1.9),180,1.5)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=pos;point(ob,(0,0,.56))
data=bpy.data.cameras.new('CatalogCamera');data.type='ORTHO';data.ortho_scale=1.02;cam=bpy.data.objects.new('CatalogCamera',data);scene.collection.objects.link(cam);cam.location=(.16,-4,.56);point(cam,(0,0,.56));scene.camera=cam
scene.render.filepath=str(R/'ue_leather_pants.png');bpy.ops.render.render(write_still=True)
write(R/'icon_source.json',dict(completed=True,source=str(SOURCE/'RangerLeatherPants_Editable.blend'),icon=scene.render.filepath,purpose='Production inventory fallback thumbnail',runtime_tested=False))
