"""Render the six current shared pommel bodies for the requested UI icon rebuild."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;ROOT=P.parents[1];SRC=P.parent
OUT=P/'Sources';OUT.mkdir(exist_ok=True)
SCENES=P/'Scenes';SCENES.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True;scene.cycles.max_bounces=12
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX']
    for d in prefs.devices:d.use=d in devices
    if devices:scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX'
neutral_output(scene)
scene.world=bpy.data.worlds.new('SharedPommelNeutralStudio');scene.world.use_nodes=True
background=scene.world.node_tree.nodes.get('Background')
background.inputs[0].default_value=(.2,.2,.2,1);background.inputs[1].default_value=.45
camera=bpy.data.objects.new('SharedPommelFront',bpy.data.cameras.new('SharedPommelFront'))
scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.001
lights=[]
for name,offset,power,size in [('Key',(-2,-3,3),850,2.4),('Fill',(2.5,-1.5,.7),450,2),('Rim',(.5,2.5,2),950,1.8)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lights.append((lamp,Vector(offset),power,size))
rows=[
    ('ballast_hardened','陨星锤首','RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_Meteor'),
    ('ballast_rune','凝碧星核','RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_JadeStar'),
    ('ballast_magic_orb','疾星配重','RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_Swiftstar'),
    ('pommel_hardened','硬化配重','FrostSwordPommelsRepair20260915/ballast_hardened/FrostPommel_Editable.blend','SM_FrostPommel_ballast_hardened'),
    ('pommel_runic','符文配重','FrostSwordPommelsRepair20260915/ballast_rune/FrostPommel_Editable.blend','SM_FrostPommel_ballast_rune'),
    ('pommel_mana_orb','魔力球配重','FrostSwordPommelsRepair20260915/ballast_magic_orb/FrostPommel_Editable.blend','SM_FrostPommel_ballast_magic_orb'),
]
library=json.loads((ROOT/'Content/ColdSteelData/shared-sword-pommels.json').read_text(encoding='utf-8-sig'))
receipt=[]
for key,label,file,name in rows:
    for obj in list(scene.objects):
        if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
    with bpy.data.libraries.load(str(SRC/file),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0]
    if obj is None:raise RuntimeError('Missing current shared body '+name)
    scene.collection.objects.link(obj);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    obj.hide_set(False);obj.hide_render=False
    gray_materials=apply_grayscale([obj]);scene.view_layers[0].update()
    points=[v.co for v in obj.data.vertices]
    lo=Vector([min(p[i] for p in points) for i in range(3)])
    hi=Vector([max(p[i] for p in points) for i in range(3)])
    center=(lo+hi)*.5;span=max(hi.x-lo.x,hi.z-lo.z)
    camera.location=center+Vector((0,-4*span,0))
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=span/.81
    for lamp,offset,power,size in lights:
        lamp.location=center+offset*span;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
        lamp.data.energy=power*span*span;lamp.data.size=size*span
    key='pommel_'+key;scene.render.filepath=str(OUT/(key+'.png'))
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(SCENES/(key+'.blend')),compress=True)
    bpy.ops.render.render(write_still=True)
    receipt.append({'key':key,'label':label,'source_blend':str(SRC/file),'source_object':name,
        'runtime_mesh':library['options'][key[len('pommel_'):]]['mesh'],
        'source_image':str(OUT/(key+'.png')),'shared_body_only':True,
        'mount_axis':'+Z toward grip, body extends -Z','camera':'front -Y level orthographic',
        'materials':gray_materials,'purpose':'Requested production icon input; no game test'})
    (P/'source_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SHARED_POMMEL_ICON_SOURCE_SAVED '+key,flush=True)
