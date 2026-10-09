"""Produce the actual prop image used to author its catalog icon (not a QA render)."""
import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Super90_Speedloader_Editable.blend'))
s=bpy.context.scene;s.frame_set(60);bpy.context.view_layer.update()
rig=bpy.data.objects['SK_Super90'];gun=rig.pose.bones['WPN_root'].matrix.copy()
rest=rig.data.bones['WPN_root'].matrix_local.copy();align=rest@gun.inverted()
dg=bpy.context.evaluated_depsgraph_get();parts=[]
for name in ('SpeedloaderTube','SpeedloaderPlunger'):
    src=bpy.data.objects[name];evaluated=src.evaluated_get(dg)
    mesh=bpy.data.meshes.new_from_object(evaluated);mesh.transform(align@src.matrix_world)
    obj=bpy.data.objects.new('Icon_'+name,mesh);s.collection.objects.link(obj);parts.append(obj)
for obj in list(s.objects):
    if obj not in parts:bpy.data.objects.remove(obj,do_unlink=True)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale(parts);neutral_output(s)
points=[obj.matrix_world@v.co for obj in parts for v in obj.data.vertices]
low=Vector(tuple(min(v[i] for v in points) for i in range(3)));high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
center=(low+high)*.5;size=max(high-low)
def aim(obj,pos):obj.location=pos;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('Icon camera');obj=bpy.data.objects.new('Icon camera',cam);s.collection.objects.link(obj)
aim(obj,center+Vector((-1,-.12,.18))*size*3);cam.type='ORTHO';cam.ortho_scale=size*1.20;s.camera=obj
for name,pos,power,scale in [('Key',(-1,-.4,1.4),75,1.3),('Fill',(-1,.8,.2),25,1.2),('Rim',(.5,.2,.7),60,.7)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power*(size/.4)**2;light.shape='DISK';light.size=size*scale
    obj=bpy.data.objects.new(name,light);s.collection.objects.link(obj);aim(obj,center+Vector(pos)*size*2)
s.world=bpy.data.worlds.new('Neutral icon world');s.world.use_nodes=True
next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.07,.07,.07,1)
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(O/'speedloader_icon_source.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Speedloader_Icon_Editable.blend'));bpy.ops.render.render(write_still=True)
print('SUPER90_SPEEDLOADER_ICON_SOURCE_SAVED',flush=True)
