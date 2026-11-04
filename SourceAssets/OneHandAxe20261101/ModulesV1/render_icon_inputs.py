"""Actual factory-part production inputs for the three framed modification icons."""
import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'TacticalHatchet_Editable.blend'))
scene=bpy.context.scene
material=bpy.data.objects['SM_TacticalHatchet'].data.materials[0]
for o in list(scene.objects):
    if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
    else:o.hide_render=True;o.hide_set(True)
nt=material.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
link=next(l for l in nt.links if l.to_socket==bs.inputs['Base Color'])
source=link.from_socket;gray=nt.nodes.new('ShaderNodeRGBToBW');nt.links.new(source,gray.inputs[0]);nt.links.new(gray.outputs[0],bs.inputs['Base Color'])
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
if not scene.world:scene.world=bpy.data.worlds.new('IconWorld')
scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');background.inputs[0].default_value=(.2,.2,.2,1);background.inputs[1].default_value=.4
cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.clip_start=.0001
lights=[]
for label in ['Key','Fill','Rim']:
    o=bpy.data.objects.new(label,bpy.data.lights.new(label,'AREA'));scene.collection.objects.link(o);lights.append(o)
out=P/'IconInputs';out.mkdir(exist_ok=True)
for slot,kind in [('blade_1','Head'),('grip','Grip'),('pommel','Pommel')]:
    name='SM_TacticalHatchet_'+kind+'_Factory'
    bpy.ops.import_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')))
    obj=next(o for o in bpy.context.selected_objects if o.type=='MESH');obj.data.materials.clear();obj.data.materials.append(material)
    obj.hide_render=False;obj.hide_set(False)
    points=[obj.matrix_world@Vector(v) for v in obj.bound_box];center=sum(points,Vector())/8
    span=max(max(p.x for p in points)-min(p.x for p in points),max(p.z for p in points)-min(p.z for p in points))
    cam.location=center+Vector((0,-4*span,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=span/.78
    for light,offset,power,size in zip(lights,[(-.5,-1,1),(.7,-1,-.5),(.3,.5,1.2)],[80,35,70],[1.2,1.2,.8]):
        light.location=center+Vector(offset)*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power*span*span;light.data.size=size*span
    scene.render.filepath=str(out/(slot+'.png'));bpy.ops.render.render(write_still=True)
    obj.hide_render=True;obj.hide_set(True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_IconAuthoring.blend'))
(P/'icon_input_provenance.json').write_text(json.dumps({'source':str(P/'Export'),'factory_parts':['blade_1','grip','pommel'],
    'resolution':[1024,1024],'camera':'orthographic from -Y; +Z up; +X edge; no 2D mirror','color':'grayscale base only; source PBR retained',
    'purpose':'production modification icons; no gameplay acceptance rendering'},indent=2),encoding='utf-8')
print('HATCHET_FACTORY_ICON_INPUTS_SAVED')
