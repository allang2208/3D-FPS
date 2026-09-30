"""Produce the required gunsmith option icon from the actual cloth pouch."""
import bpy,json,importlib.util
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;OUT=O/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
src=bpy.data.objects['AmmoBag'];me=src.data.copy();cp=bpy.data.objects.new('Cloth201_Icon',me)
sc=bpy.data.scenes.new('201_ClothIcon');bpy.context.window.scene=sc;sc.collection.objects.link(cp)
spec=importlib.util.spec_from_file_location('gray','C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py');gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([cp]);gray.neutral_output(sc)
pts=[v.co for v in me.vertices];center=Vector(tuple((min(v[i] for v in pts)+max(v[i] for v in pts))*.5 for i in range(3)))
size=max(max(v.z for v in pts)-min(v.z for v in pts),max(v.y for v in pts)-min(v.y for v in pts))/.80
cd=bpy.data.cameras.new('PouchIconCamera');cam=bpy.data.objects.new('PouchIconCamera',cd);sc.collection.objects.link(cam);cam.location=center+Vector((2,0,0));cam.rotation_euler=Vector((-1,0,0)).to_track_quat('-Z','Y').to_euler();sc.camera=cam;cd.type='ORTHO';cd.ortho_scale=size
for name,xyz,power in [('Key',(1,-.3,1.4),130),('Fill',(1,.9,.45),60),('Rim',(-.8,.4,1),100)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power*size*size;ld.shape='DISK';ld.size=size*1.8
 lamp=bpy.data.objects.new(name,ld);sc.collection.objects.link(lamp);lamp.location=center+Vector(xyz)*size*2;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
sc.world=bpy.data.worlds.new('ClothIconWorld');sc.world.use_nodes=True;next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.25,.25,.25,1)
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.film_transparent=True
sc.render.resolution_x=sc.render.resolution_y=512;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.view_settings.view_transform='AgX'
key='ue_lmg201_magazine_lmg201_cloth_box';sc.render.filepath=str(OUT/(key+'.png'));bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'.blend')))
(O/'icon.json').write_text(json.dumps({'key':key,'file':str(OUT/(key+'.png')),'purpose':'production gunsmith option icon; not a runtime validation render'},indent=2))
print('CLOTH33_ICON_AUTHORED',flush=True)
