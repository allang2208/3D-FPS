"""Author actual-part icon inputs, without running UE or rendering gameplay previews."""
import bpy, math
from pathlib import Path
from mathutils import Vector, Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Modules_Editable.blend'))
scene=bpy.context.scene
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('SM_Kukri_')]
for o in list(scene.objects):
    if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.2,.2,.2,1);bg.inputs['Strength'].default_value=.4
mat=parts[0].data.materials[0];nt=mat.node_tree
bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
base=next(n for n in nt.nodes if n.type=='TEX_IMAGE' and 'BaseColor' in n.image.name)
base.image=bpy.data.images.load(str(P.parent/'Kukri20261020/Textures/T_Kukri_BaseColor.png'))
gray=nt.nodes.new('ShaderNodeRGBToBW');nt.links.new(base.outputs['Color'],gray.inputs['Color']);nt.links.new(gray.outputs[0],bsdf.inputs['Base Color'])
for obj in parts:
    obj.matrix_world=Matrix.Rotation(-math.pi/2,4,'Y')@obj.matrix_world
cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.clip_start=.0001
lights=[]
for label in ['Key','Fill','Rim']:
    o=bpy.data.objects.new(label,bpy.data.lights.new(label,'AREA'));scene.collection.objects.link(o);lights.append(o)
dest=P/'IconInputs';dest.mkdir(exist_ok=True)
for obj in parts:
    for other in parts:other.hide_render=other!=obj
    obj.hide_set(False)
    points=[obj.matrix_world@Vector(c) for c in obj.bound_box];center=sum(points,Vector())/8
    span=max(max(p.x for p in points)-min(p.x for p in points),max(p.z for p in points)-min(p.z for p in points))
    cam.location=center+Vector((0,-4*span,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=span/.78
    for lamp,offset,power,size in zip(lights,[(-.5,-1,1),(.7,-1,-.5),(.3,.5,1.2)],[800,350,700],[1.2,1.2,.8]):
        lamp.location=center+Vector(offset)*span;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler();lamp.data.energy=power*span*span;lamp.data.size=size*span
    scene.render.filepath=str(dest/(obj.name+'.png'));bpy.ops.render.render(write_still=True)
print('KUKRI_ICON_INPUTS_AUTHORED '+str(dest))
