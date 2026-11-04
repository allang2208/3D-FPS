"""Production input for the single exclusive modification icon; no acceptance render."""
import bpy,json,math,runpy
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
entry=json.loads((P/'hollow_grip.json').read_text('utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(P/'TacticalHatchet_GripAgile_HollowV2_Editable.blend'))
scene=bpy.context.scene;obj=bpy.data.objects[entry['object']]
for other in list(scene.objects):
    if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
obj.hide_set(False);obj.hide_render=False;obj.matrix_world=Matrix.Rotation(-math.pi/2,4,'Y')
gray=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
gray['apply_grayscale']([obj]);gray['neutral_output'](scene)
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.world=bpy.data.worlds.new('GripIconWorld');scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs[0].default_value=(.2,.2,.2,1)
background.inputs[1].default_value=.45
points=[obj.matrix_world@Vector(p) for p in obj.bound_box];center=sum(points,Vector())/8
span=max(max(p.x for p in points)-min(p.x for p in points),max(p.z for p in points)-min(p.z for p in points))
cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.clip_start=.0001;cam.data.ortho_scale=span/.73
cam.location=center+Vector((0,-4*span,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for name,offset,power,size in [('Key',(.5,-1,1),90,1.2),('Fill',(-.7,-1,-.5),40,1.2),('Rim',(-.3,.5,1.2),70,.8)]:
    light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light)
    light.location=center+Vector(offset)*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    light.data.energy=power*span*span;light.data.size=size*span
scene.render.filepath=str(P/'IconInputs/hatchet_grip_agile.png');bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_GripAgile_HollowV2_Icon.blend'))
(P/'icon_input_provenance.json').write_text(json.dumps({'source':str(P/'TacticalHatchet_GripAgile_HollowV2_Editable.blend'),
    'object':entry['object'],'purpose':'production modification icon','view':'horizontal; head joint toward left; no image mirror',
    'grayscale':'shared workflow material conversion','runtime_tested':False},indent=2)+'\n',encoding='utf-8')
print('AGILE_GRIP_ICON_INPUT_SAVED',flush=True)
