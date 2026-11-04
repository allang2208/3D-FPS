"""Actual model inputs for the approved-frame imagegen icon workflow."""
import bpy,json,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
gray=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
jobs=[]
for kind in ['SwiftCrescent','HeavyCleaver','FoldedArc']:
    source=P.parent/'CrescentReferenceR4_20261104' if kind=='SwiftCrescent' else P
    entry=json.loads((source/(kind+'.json')).read_text('utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(source/(kind+'_Editable.blend')))
    obj=bpy.data.objects[entry['object']]
    for other in list(bpy.context.scene.objects):
        if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
    obj.hide_set(False);obj.hide_render=False;gray['apply_grayscale']([obj])
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
    scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    for layer in scene.view_layers:layer.material_override=None
    scene.world=bpy.data.worlds.new('NeutralInputWorld');scene.world.use_nodes=True
    bg=next(node for node in scene.world.node_tree.nodes if node.type=='BACKGROUND')
    bg.inputs[0].default_value=(.18,.18,.18,1);bg.inputs[1].default_value=.25
    points=[obj.matrix_world@Vector(v) for v in obj.bound_box];center=sum(points,Vector())/8
    span=max(max(v.x for v in points)-min(v.x for v in points),max(v.z for v in points)-min(v.z for v in points))
    camera=bpy.data.objects.new('InputCamera',bpy.data.cameras.new('InputCamera'));scene.collection.objects.link(camera);scene.camera=camera
    camera.data.type='ORTHO';camera.data.ortho_scale=span/.80;camera.data.clip_start=.001
    camera.location=center+Vector((0,4,0))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    for name,offset,power,size in [('Key',(-.8,1.3,1.6),80,.7),('Fill',(1.2,1.1,-.1),20,1.5),('Rim',(.5,-.8,1.4),80,.8)]:
        light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light)
        light.location=center+Vector(offset)*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
        light.data.energy=power*span*span;light.data.size=size*span
    gray['neutral_output'](scene)
    path=P/'IconInputs'/(kind+'.png');scene.render.filepath=str(path)
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'IconInputs'/(kind+'.blend')))
    bpy.ops.render.render(write_still=True)
    jobs.append({'id':entry['id'],'kind':kind,'key':'blade_1_'+entry['id'],'input':str(path),
        'model':entry['mesh'],'source_blend':str(source/(kind+'_Editable.blend')),
        'frame_reference':str(P.parents[2]/'FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'),
        'source':str(P/'Icons'/('blade_1_'+entry['id']+'.png')),
        'method':'imagegen edit: approved frame plus current real-model input',
        'camera':'+Y orthographic; installed +Z up and +X cutting edge left'})
(P/'icon_jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('THREE_ACTUAL_MODEL_ICON_INPUTS_RENDERED',flush=True)
