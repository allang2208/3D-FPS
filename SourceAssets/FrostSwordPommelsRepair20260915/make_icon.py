"""Produce the installed pommel's 1024 RGBA option icon; not an acceptance render."""
import bpy,json,sys,math,shutil
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;KEY=sys.argv[sys.argv.index('--')+1];OUT=P/KEY
bpy.ops.wm.open_mainfile(filepath=str(OUT/'FrostPommel_Editable.blend'))
obj=bpy.data.objects['SM_FrostPommel_'+KEY]
for o in bpy.context.scene.objects:o.hide_render=o!=obj
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
coords=[v.co for v in obj.data.vertices];center=Vector((0,0,(min(v.z for v in coords)+max(v.z for v in coords))/2))
camera=bpy.data.objects.new('UI front orthographic camera',bpy.data.cameras.new('UI camera'));scene.collection.objects.link(camera)
camera.location=center+Vector((0,-.30,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO'
camera.data.ortho_scale=max(max(v.x for v in coords)-min(v.x for v in coords),max(v.z for v in coords)-min(v.z for v in coords))/.82;camera.data.clip_start=.001;scene.camera=camera
for name,location,energy,size in [('Key',(-.12,-.16,.10),12,.12),('Fill',(.15,-.06,.01),4,.14),('Rim',(.05,.09,.08),8,.1)]:
    light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light);light.location=center+Vector(location);light.data.energy=energy;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'pommel_icon.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Pommel_Icon_Editable.blend'));bpy.ops.render.render(write_still=True)
target=P.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'/('ue_frost_crystal_sword_pommel_'+KEY+'.png')
if target.exists() and not (OUT/'previous_option_icon.png').exists():shutil.copy2(target,OUT/'previous_option_icon.png')
shutil.copy2(OUT/'pommel_icon.png',target)
(OUT/'icon_authoring.json').write_text(json.dumps({'source_object':obj.name,'image':str(target),'view':'front, camera -Y, mount +Z up','dimensions':[1024,1024],'purpose':'gunsmith option UI asset, no visual test'},indent=2))
print('POMMEL_OPTION_ICON_WRITTEN',KEY,flush=True)
