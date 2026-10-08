"""Production attachment-icon subject from the finished guard, not a QA render."""
from pathlib import Path
import bpy,sys
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'PanChi_Guard_Editable.blend'))
scene=bpy.context.scene;obj=bpy.data.objects['SM_XuanChi_Guard_PanChiZhanYue_V1_LOD0']
for o in scene.objects:
    if o.type=='MESH':o.hide_render=o!=obj
obj.hide_set(False)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([obj]);neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('PanChi icon studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.55
pts=[obj.matrix_world@Vector(c) for c in obj.bound_box]
lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
center=(lo+hi)*.5;span=max(hi.x-lo.x,hi.z-lo.z)*1.17
cam=bpy.data.objects.new('PanChi icon camera',bpy.data.cameras.new('PanChi icon camera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=span;cam.data.clip_start=.001
cam.location=center+Vector((.10,-3,.045))*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for name,delta,power,size in [('Key',(-1,-2,2),380,2),('Fill',(1.5,-1,.1),180,1.5),('Rim',(.5,1,1),320,1.5)]:
    o=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(o)
    o.location=center+Vector(delta)*span;o.data.energy=power*span*span;o.data.size=size*span
    o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-2
scene.render.filepath=str(P/'Icons/guard_panchi_zhanyue_subject.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Icons/PanChi_Icon_Editable.blend'))
print('PANCHI_ICON_SUBJECT_SAVED',flush=True)
