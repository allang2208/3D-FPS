"""Author three production menu-icon subjects; not a gameplay/acceptance render."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'XuanChi_CommonBlades_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
spec=json.loads((P/'exports.json').read_text(encoding='utf-8'))
objects=[bpy.data.objects[r['mesh']] for r in spec['options']]
apply_grayscale(objects);scene=bpy.context.scene;neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Neutral blade icon world');scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs['Color'].default_value=(.15,.15,.15,1)
background.inputs['Strength'].default_value=.5
cd=bpy.data.cameras.new('PartIconCamera');cam=bpy.data.objects.new('PartIconCamera',cd)
scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.clip_start=.001
lights=[]
for name,pos,power,size in [('Key',(-1,-2,2),180,2),('Fill',(1.4,-1,.2),90,1.5),('Rim',(.5,1,1),140,1.5)]:
    ld=bpy.data.lights.new(name,'AREA');ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob)
    lights.append((ob,Vector(pos),power,size))
for row,obj in zip(spec['options'],objects):
    for other in scene.objects:
        if other.type=='MESH':other.hide_render=other!=obj
    obj.hide_set(False);obj.hide_render=False
    pts=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    low=Vector(tuple(min(p[i] for p in pts) for i in range(3)));high=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    center=(low+high)*.5;span=max(high.x-low.x,high.z-low.z)*1.13
    cam.location=center+Vector((.045*span,-span*3,0))
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=span
    for light,pos,power,size in lights:
        light.location=center+pos*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
        light.data.energy=power*span*span;light.data.size=size*span
    scene.render.filepath=str(OUT/(row['option']+'_subject.png'))
    bpy.ops.render.render(write_still=True)
    obj.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CommonBlades_IconSubjects.blend'))
print('XUANCHI_COMMON_BLADE_ICON_SUBJECTS_SAVED',flush=True)
