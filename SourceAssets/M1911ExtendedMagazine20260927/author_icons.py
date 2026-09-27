"""Produce neutral catalog icons from the actual 1911 magazine meshes."""
import bpy,json,shutil,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;ROOT=O.parents[1];I=O/'Icons';I.mkdir(exist_ok=True)
DEST=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
sys.path.insert(0,str(ROOT/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'M1911_ExtendedMagazine_Editable.blend'))
auth=json.loads((O/'authoring.json').read_text());root=Matrix(auth['root_matrix'])
parts=[bpy.data.objects['SM_M1911_ext_mag'],bpy.data.objects['SM_M1911_factory_magazine']]
for part in parts:part.hide_set(False);part.data.transform(root.inverted())
palette=apply_grayscale(parts)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.use for d in prefs.devices):s.cycles.device='GPU'
except Exception:pass
s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';neutral_output(s)
s.world=bpy.data.worlds.new('M1911_CatalogWorld');s.world.use_nodes=True
s.world.node_tree.nodes.clear()
background=s.world.node_tree.nodes.new('ShaderNodeBackground');worldout=s.world.node_tree.nodes.new('ShaderNodeOutputWorld')
s.world.node_tree.links.new(background.outputs[0],worldout.inputs[0])
background.inputs[0].default_value=(.18,.18,.18,1);background.inputs[1].default_value=.35
cam=bpy.data.objects.new('M1911_CatalogCamera',bpy.data.cameras.new('M1911_CatalogCamera'));s.collection.objects.link(cam)
cam.data.type='ORTHO';cam.data.clip_start=.001;s.camera=cam
lamps=[]
for name,offset,power,size in [('Key',(.4,-.1,.42),32,.4),('Fill',(.2,.32,.13),18,.35),('Rim',(-.28,-.12,.3),35,.3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    lamp=bpy.data.objects.new(name,data);s.collection.objects.link(lamp);lamps.append((lamp,Vector(offset)))
records={}
for part,key in zip(parts,['ue_m1911_magazine_ext_mag','ue_m1911_magazine_false']):
    for ob in parts:ob.hide_render=ob!=part
    points=[v.co for v in part.data.vertices]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    center=(lo+hi)*.5;cam.location=center+Vector((1.5,0,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=max(hi.y-lo.y,hi.z-lo.z)/.82
    for lamp,offset in lamps:lamp.location=center+offset;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(I/(key+'.png'));bpy.ops.wm.save_as_mainfile(filepath=str(I/(key+'.blend')))
    bpy.ops.render.render(write_still=True);shutil.copy2(I/(key+'.png'),DEST/(key+'.png'))
    records[key]={'output':str(DEST/(key+'.png')),'source':str(O/'M1911_ExtendedMagazine_Editable.blend'),
        'object':part.name,'size':[1024,1024],'camera':'Orthographic +X; gun -Y forward screen left / +Z up',
        'palette':palette,'purpose':'Production gun-modification UI texture; no acceptance rendering'}
key='ue_m1911_category_magazine'
shutil.copy2(I/'ue_m1911_magazine_false.png',I/(key+'.png'));shutil.copy2(I/(key+'.png'),DEST/(key+'.png'))
records[key]={**records['ue_m1911_magazine_false'],'output':str(DEST/(key+'.png'))}
(O/'icons.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('M1911_EXTMAG_ICONS_SAVED',flush=True)
