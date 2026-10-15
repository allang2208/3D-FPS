"""Isolated actual-mesh icon sources; runtime geometry/materials are never saved here."""
import bpy, bmesh, json, runpy
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
OUT=P/'Sources'; OUT.mkdir(parents=True,exist_ok=True)
HEADS=ROOT/'SourceAssets/CommonHammerHeads20261014/DesignBuildV2'
FACTORY=ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(HEADS/'CommonHammerHeads_DesignV2_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rows=json.loads((HEADS/'exports.json').read_text(encoding='utf-8'))['parts']
specs=[{'id':r['id'],'object':r['mesh'],'single_left':True,'keys':['hammer_heads_'+r['id']],
        'runtime_mesh':'/Game/Weapons/CommonHammerHeads20261014/DesignV2/'+r['mesh'],
        'source':str(HEADS/'CommonHammerHeads_DesignV2_Editable.blend')} for r in rows]
slots=['hammer_heads','head_mount','neck','shaft','grip','pommel']
names=['SM_Warhammer_'+s+'_factory' for s in slots]
with bpy.data.libraries.load(str(FACTORY),link=False) as (src,dst):dst.objects=list(names)
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
for slot,name in zip(slots,names):
    specs.append({'id':'factory_'+slot,'object':name,'single_left':slot=='hammer_heads',
        'keys':['ue_steel_warhammer_category_'+slot,'ue_steel_warhammer_'+slot+'_false'],
        'runtime_mesh':'/Game/Weapons/SteelWarhammer20261014/ModulesV1/'+name,'source':str(FACTORY)})
modules=[bpy.data.objects[s['object']] for s in specs]
for obj in list(bpy.context.scene.objects):
    if obj not in modules:bpy.data.objects.remove(obj,do_unlink=True)
for spec,obj in zip(specs,modules):
    obj.data=obj.data.copy()
    if spec['single_left']:
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x>0],context='VERTS')
        bm.to_mesh(obj.data);bm.free();obj.data.update()
    coords=[v.co for v in obj.data.vertices]
    lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    scale=1/max(hi-lo);center=(hi+lo)*.5
    obj.rotation_euler=(0,0,0);obj.scale=(scale,)*3;obj.location=-center*scale
    obj.hide_render=True
    spec.update(selection='left head only; paired installation unchanged' if spec['single_left'] else 'complete actual module',
                up='+Z',camera_direction=[-2,-5,0],image='Sources/'+spec['id']+'.png')
helper=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
helper['apply_grayscale'](modules)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.35,.35,.35,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.5
scene.view_settings.view_transform='AgX';helper['neutral_output'](scene)
bpy.ops.object.camera_add(location=(-2,-5,0));cam=bpy.context.object
cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.35;scene.camera=cam
for loc,power,size in [((-3,-4,3),600,4),((3,-2,1),400,3),((0,2,2),500,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object
    lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
for spec,obj in zip(specs,modules):
    obj.hide_render=False;scene.render.filepath=str(P/spec['image'])
    bpy.ops.render.render(write_still=True);obj.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_IconSources_Editable.blend'))
(P/'sources.json').write_text(json.dumps({'parts':specs,'resolution':[1024,1024],'palette':'neutral-grayscale-20260927',
    'frame_master':str(ROOT/'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png')},ensure_ascii=False,indent=2),encoding='utf-8')
