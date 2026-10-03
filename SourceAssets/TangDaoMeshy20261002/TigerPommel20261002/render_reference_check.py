"""User-requested front/side comparison renders, using actual geometry and color PBR."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'TangDao_TigerPommel_Editable.blend'))
manifest=json.loads((P/'pommel_manifest.json').read_text(encoding='utf-8-sig'))
obj=bpy.data.objects[manifest['mesh_name']+'_LOD0'];scene=bpy.context.scene
diagnostic='--clay' in sys.argv
if diagnostic:
    mat=bpy.data.materials.new('Shell diagnostic neutral clay');mat.use_nodes=True
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.18,.18,.18,1);bs.inputs['Roughness'].default_value=.68
    scene.view_layers[0].material_override=mat
for x in scene.objects:
    if x.type=='MESH':x.hide_render=x!=obj
obj.hide_set(False)
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-2.65
scene.world=bpy.data.worlds.new('Reference comparison neutral studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.2,.2,.2,1);bg.inputs['Strength'].default_value=.65
cam=bpy.data.objects.new('Requested comparison camera',bpy.data.cameras.new('Requested comparison camera'))
scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.001
lights=[]
for name,energy,size in [('Key',32,.35),('Fill',16,.28),('Rim',25,.26)]:
    light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light)
    light.data.energy=energy;light.data.shape='DISK';light.data.size=size;lights.append(light)
(P/'ReferenceCheck').mkdir(exist_ok=True)
for job,center,delta,scale in [
    ('front',Vector((.002,0,-.101)),Vector((.018,0,-.5)),.135),
    ('side',Vector((.004,0,-.085)),Vector((.0,-.5,0)),.210),
    ('threequarter',Vector((.007,0,-.085)),Vector((.035,-.36,-.4)),.20),
    ('bottom',Vector((-.004,0,-.092)),Vector((-.42,-.06,-.28)),.20)]:
    if diagnostic and job not in ['side','bottom']:continue
    if '--connector' in sys.argv and job not in ['side','threequarter']:continue
    cam.location=center+delta;direction=(center-cam.location).normalized()
    up=Vector((0,0,-1)) if job=='bottom' else Vector((1,0,0));right=direction.cross(up).normalized();up=right.cross(direction).normalized()
    cam.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler();cam.data.ortho_scale=scale
    front=delta.normalized();right=front.cross(Vector((1,0,0))).normalized()
    for light,offset in zip(lights,[front*.32+right*.18+Vector((.18,0,0)),front*.25-right*.24-Vector((.07,0,0)),-front*.26+Vector((.15,0,0))]):
        light.location=center+offset;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(P/'ReferenceCheck'/('TigerPommel_'+job+('_clay' if diagnostic else '')+'.png'));bpy.ops.render.render(write_still=True)
    print('TIGER_REFERENCE_CHECK_RENDER '+job,flush=True)
