"""Render the actual six original parts for the standard framed-icon compositor."""
from pathlib import Path
import bpy,sys,json
from mathutils import Vector
r=Path(__file__).resolve().parent;root=r.parent;out=r/'Sources';out.mkdir(exist_ok=True)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.wm.open_mainfile(filepath=str(root/'M249_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
groups={'magazine':['Box'],'stock':['Stock'],'reargrip':['RearGrip'],'underbarrel':['Foregrip'],'muzzle':['Muzzle'],'optic':['Magnifier','MagnifierGlass','MagnifierReticle']}
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
apply_grayscale([bpy.data.objects['M249_'+n] for names in groups.values() for n in names]);neutral_output(scene)
scene.world=bpy.data.worlds.new('Factory grey studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.35,.35,.35,1);bg.inputs[1].default_value=.65
data=bpy.data.cameras.new('Factory side');cam=bpy.data.objects.new('Factory side',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
lights=[]
for name,offset,power,size in [('Key',(-.8,-.4,1),90,.8),('Fill',(.6,-.2,.4),55,.7),('Rim',(.2,.8,1),100,.6)]:
    lamp=bpy.data.lights.new(name,'AREA');lamp.energy=power;lamp.shape='DISK';lamp.size=size
    obj=bpy.data.objects.new(name,lamp);scene.collection.objects.link(obj);lights.append((obj,Vector(offset)))
manifest=[]
for key,names in groups.items():
    selected=[bpy.data.objects['M249_'+name] for name in names]
    for obj in scene.objects:
        if obj.type=='MESH':obj.hide_render=obj not in selected
    points=[obj.matrix_world@Vector(corner) for obj in selected for corner in obj.bound_box]
    center=(Vector(tuple(min(p[i] for p in points) for i in range(3)))+Vector(tuple(max(p[i] for p in points) for i in range(3))))*.5
    # Blender weapon-forward is +Y; view from -X gives muzzle-left without mirroring.
    direction=Vector((-1,-.35 if key=='optic' else 0,0)).normalized()
    cam.location=center+direction;cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    inv=cam.rotation_euler.to_matrix().transposed();q=[inv@(p-center) for p in points]
    data.ortho_scale=max(max(p.x for p in q)-min(p.x for p in q),max(p.y for p in q)-min(p.y for p in q))*1.3
    for lamp,offset in lights:
        lamp.location=center+offset;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
    manifest.append(dict(slot=key,objects=names,camera=list(direction),source=str(root/'M249_Editable.blend')))
bpy.ops.wm.save_as_mainfile(filepath=str(r/'M249_Factory_Icon_Studio.blend'))
(r/'icon_sources.json').write_text(json.dumps(manifest,indent=2))
print('M249_ICON_SOURCES',len(manifest),flush=True)
