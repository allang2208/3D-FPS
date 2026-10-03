"""Focused visual diagnosis of the repaired limb surface at run/strike extremes."""
import bpy, math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HundredEyedSlag_RuntimeV3.blend'))
scene=bpy.context.scene; rig=next(o for o in scene.objects if o.type=='ARMATURE')
scene.render.engine='CYCLES'; scene.cycles.samples=8; scene.cycles.use_denoising=True; scene.cycles.device='GPU'
prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='OPTIX'; prefs.get_devices()
for d in prefs.devices: d.use=d.type!='CPU'
scene.render.resolution_x=640; scene.render.resolution_y=480; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
if scene.world is None: scene.world=bpy.data.worlds.new('DiagnosisWorld')
scene.world.color=(.03,.03,.03)
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.006))
floor=bpy.context.object; material=bpy.data.materials.new('DiagnosisFloor'); material.diffuse_color=(.07,.08,.095,1)
floor.data.materials.append(material)
def aim(obj,point): obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy in [('Key',(2,-3,4),230),('Fill',(-2,2,3),130),('Rim',(-2,-1,2),110)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='DISK'; data.size=3
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=loc; aim(obj,(0,0,.55))
data=bpy.data.cameras.new('DiagnosisCamera'); camera=bpy.data.objects.new('DiagnosisCamera',data)
scene.collection.objects.link(camera); camera.location=(1.5,-3.0,1.12); aim(camera,(0,0,.52))
data.type='ORTHO'; data.ortho_scale=2.; scene.camera=camera; scene.view_settings.view_transform='AgX'
for role,frames in [('Run',[1,5,8,12]),('AttackSweep_R',[13,22]),('AttackSlam_R',[17,27])]:
    action=bpy.data.actions['A_HundredEyedSlag_'+role+'_V3']; rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
    for frame in frames:
        scene.frame_set(frame); scene.render.filepath=str(OUT/f'diagnosis_{role}_{frame:02d}.png')
        bpy.ops.render.render(write_still=True)
print('V3_LIMB_SURFACE_DIAGNOSIS_RENDERED',flush=True)
