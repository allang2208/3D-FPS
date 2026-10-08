"""Production icon subjects from the final editable model; no gameplay run."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'XuanChi_Modular_Editable.blend'))
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
scene=bpy.context.scene
subjects={'blade_1':['SM_XuanChi_Blade'],'guard':['SM_XuanChi_Guard'],'grip':['SM_XuanChi_Grip'],'pommel':['SM_XuanChi_Pommel','SM_XuanChi_Tassel']}
objects=[bpy.data.objects[n] for names in subjects.values() for n in names]
apply_grayscale(objects);neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=3
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('IconWorld');scene.world.color=(.2,.2,.2);scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-2
cd=bpy.data.cameras.new('IconCamera');cam=bpy.data.objects.new('IconCamera',cd);scene.collection.objects.link(cam);cd.type='ORTHO';scene.camera=cam
lights=[]
for name,pos,power,size in [('Key',(-1,-2,2),380,2),('Fill',(1.5,-1,.1),180,1.5),('Rim',(.5,1,1),320,1.5)]:
    ld=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,ld);scene.collection.objects.link(o);lights.append((o,Vector(pos),power,size))
records=[]
for slot,names in subjects.items():
    for o in scene.objects:
        if o.type=='MESH':o.hide_render=o.name not in names
    pts=[o.matrix_world@Vector(c) for o in objects if o.name in names for c in o.bound_box]
    low=Vector(tuple(min(p[i] for p in pts) for i in range(3)));high=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    center=(low+high)*.5;span=max(high.x-low.x,high.z-low.z)*1.15
    cam.location=center+Vector((0,-span*3,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=span;cd.clip_start=.001
    for light,pos,power,size in lights:
        light.location=center+pos*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power*span*span;light.data.size=size*span
    scene.render.filepath=str(OUT/(slot+'_subject.png'));bpy.ops.render.render(write_still=True)
    records.append({'slot':slot,'objects':names,'source':'XuanChi_Modular_Editable.blend','view':'orthographic -Y, +Z up','image':scene.render.filepath})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'XuanChi_PartIcons_Editable.blend'))
(OUT/'subjects.json').write_text(json.dumps(records,indent=2));print('XUANCHI_ICON_SUBJECTS_SAVED')
