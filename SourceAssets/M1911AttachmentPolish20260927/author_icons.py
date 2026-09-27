"""Update three production modification icons from the revised geometry."""
import bpy,json,sys,shutil
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;ROOT=O.parents[1];I=O/'Icons';I.mkdir(exist_ok=True)
DEST=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
sys.path.insert(0,str(ROOT/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
mag=json.loads((O/'magazine_authoring.json').read_text());records={}
entries=[('magazine_ext_mag','M1911_RoundedMagazine_Editable.blend','SM_M1911_ext_mag_Rounded20260927',True),
 ('optic_holographic','M1911_holographic_RoundedMount_Editable.blend','SM_M1911_holographic_Rounded20260927',False),
 ('optic_panoramic_red_dot','M1911_panoramic_red_dot_RoundedMount_Editable.blend','SM_M1911_panoramic_red_dot_Rounded20260927',False)]
for suffix,file,name,is_mag in entries:
    bpy.ops.wm.open_mainfile(filepath=str(O/file));bpy.context.preferences.filepaths.save_version=0
    ob=bpy.data.objects[name];ob.hide_set(False);ob.hide_render=False
    if is_mag:ob.data.transform(Matrix(mag['root_matrix']).inverted())
    for other in list(bpy.context.scene.objects):
        if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
    palette=apply_grayscale([ob]);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if any(d.use for d in prefs.devices):s.cycles.device='GPU'
    except Exception:pass
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';neutral_output(s)
    s.world=bpy.data.worlds.new('AttachmentPolish_IconWorld');s.world.use_nodes=True;s.world.node_tree.nodes.clear()
    bg=s.world.node_tree.nodes.new('ShaderNodeBackground');out=s.world.node_tree.nodes.new('ShaderNodeOutputWorld')
    s.world.node_tree.links.new(bg.outputs[0],out.inputs[0]);bg.inputs[0].default_value=(.18,.18,.18,1);bg.inputs[1].default_value=.35
    pts=[v.co for v in ob.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);center=(lo+hi)*.5
    cam=bpy.data.objects.new('CatalogCamera',bpy.data.cameras.new('CatalogCamera'));s.collection.objects.link(cam)
    cam.data.type='ORTHO';cam.data.clip_start=.001;s.camera=cam
    cam.location=center+Vector((1.5,0,0) if is_mag else (0,1.5,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=max((hi.y-lo.y) if is_mag else (hi.x-lo.x),hi.z-lo.z)/.82
    for label,offset,power,size in [('Key',(.4,-.1,.42),32,.4),('Fill',(.2,.32,.13),18,.35),('Rim',(-.28,-.12,.3),35,.3)]:
        if not is_mag:offset=(-offset[1],offset[0],offset[2])
        data=bpy.data.lights.new(label,'AREA');data.energy=power;data.shape='DISK';data.size=size
        lamp=bpy.data.objects.new(label,data);s.collection.objects.link(lamp);lamp.location=center+Vector(offset)
        lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    key='ue_m1911_'+suffix;s.render.filepath=str(I/(key+'.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(I/(key+'.blend')));bpy.ops.render.render(write_still=True)
    records[key]={'file':str(I/(key+'.png')),'destination':str(DEST/(key+'.png')),'source':str(O/file),
       'palette':palette,'camera':'Orthographic, forward left, up vertical','purpose':'Production modification UI texture, no acceptance render'}
(O/'icons.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('M1911_REVISED_ICONS_AUTHORED',flush=True)
