"""Focused art diagnosis: side-view run and the animated portion of death."""
import bpy, math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HundredEyedSlag_PolishV2.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.cycles.use_denoising=True;scene.cycles.device='GPU'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
except Exception:scene.cycles.device='CPU'
scene.render.resolution_x=720;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
if scene.world is None:scene.world=bpy.data.worlds.new('PreviewWorld')
scene.world.color=(.025,.025,.025)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.007))
floor=bpy.context.object;mat=bpy.data.materials.new('PreviewGround');mat.diffuse_color=(.085,.095,.11,1);floor.data.materials.append(mat)
def aim(obj,point):obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,location,energy,size in [('Key',(1,-3,4),200,3),('Fill',(-2,2,3),110,3),('Rim',(-2,-1,2),100,2)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=location;aim(light,(0,0,.55))
data=bpy.data.cameras.new('PreviewCamera');camera=bpy.data.objects.new('PreviewCamera',data);scene.collection.objects.link(camera)
camera.location=(1.6,-3.0,1.25);aim(camera,(0,0,.52));data.type='ORTHO';data.ortho_scale=2.3;scene.camera=camera
scene.view_settings.view_transform='AgX'
for role,frames in [('Run',range(1,21)),('Death',[1,4,7,10,14])]:
    action=bpy.data.actions['A_HundredEyedSlag_'+role+'_V2'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    for frame in frames:
        scene.frame_set(frame);scene.render.filepath=str(OUT/('preview_'+role.lower()+'_%02d.png'%frame))
        bpy.ops.render.render(write_still=True)
print('SLAG_AUTHORING_PREVIEWS_COMPLETE',flush=True)
