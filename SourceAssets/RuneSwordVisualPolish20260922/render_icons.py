"""Current installed parts, one instance per icon, mechanical +Z toward left."""
import bpy,json,math,shutil
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;SRC=P.parent;OUT=P/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
rows=json.loads((P/'icon_manifest.json').read_text(encoding='utf-8'))
sources={};source_paths={}
libraries={
 'RuneSwordModules20260919/RuneSword_Modular_Editable.blend':[
 'SM_RuneSword_Blade_factory','SM_RuneSword_Guard_factory','SM_RuneSword_Grip_factory','SM_RuneSword_Pommel_factory',
 'SM_RuneSword_Guard_bastion_guard','SM_RuneSword_Guard_riposte_guard','SM_RuneSword_Guard_light_guard',
 'SM_RuneSword_Grip_shock_wrap','SM_RuneSword_Grip_swift_grip','SM_RuneSword_Grip_long_twohand'],
 'RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend':['SM_RunePommel_Meteor','SM_RunePommel_JadeStar','SM_RunePommel_Swiftstar'],
 'SixSharedSwordPommels20260920/SixSharedPommels_RuneFit.blend':['SM_FrostPommel_ballast_hardened','SM_FrostPommel_ballast_rune','SM_FrostPommel_ballast_magic_orb','SM_SwordPommel_RuneToFrost']}
for file,names in libraries.items():
    with bpy.data.libraries.load(str(SRC/file),link=False) as (a,b):b.objects=list(names)
    for name,obj in zip(names,b.objects):
        if not obj:raise RuntimeError('Missing current source object '+name)
        sources[name]=obj;source_paths[name]=str(SRC/file)

def texture(nt,file,data=False):
    n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(P/'IconMaterials'/file),check_existing=True)
    n.image.colorspace_settings.name='Non-Color' if data else 'sRGB'
    return n

def rune_material(source,key):
    mat=source.copy();mat.name='IconFrame_'+key;nt=mat.node_tree
    bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    if key=='golden_glow_rune':
        nt.links.new(texture(nt,'gold_base.png').outputs['Color'],bs.inputs['Base Color'])
        nt.links.new(texture(nt,'gold_emission.png').outputs['Color'],bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value=1
    else:
        output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
        coverage=texture(nt,key+'_coverage.png',True)
        emission=nt.nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=4
        nt.links.new(texture(nt,key+'_emission.png').outputs['Color'],emission.inputs['Color'])
        mix=nt.nodes.new('ShaderNodeMixShader');nt.links.new(coverage.outputs['Color'],mix.inputs[0])
        nt.links.new(bs.outputs[0],mix.inputs[1]);nt.links.new(emission.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],output.inputs['Surface'])
    return mat

world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.28,.28,.28,1);bg.inputs[1].default_value=.45
rotation=Matrix.Rotation(-math.pi/2,4,'Y') # native +Z to screen -X; native +X to screen +Z
receipt=[];scenes={}
for row in rows:
    alias=row.get('copy')
    if row.get('numeric_only') or (row['slot']=='blade_2' and row['id']=='false'):alias='ue_rune_sword_blade_1_false'
    file=OUT/(row['key']+'.png')
    if alias:
        shutil.copy2(OUT/(alias+'.png'),file)
        receipt.append(dict(key=row['key'],image=str(file),alias=alias,numeric_only=row.get('numeric_only',False)))
        continue
    spec=row['spec'];name=spec['mesh'].split('/')[-1].split('.')[0];names=[name]
    if spec.get('adapter'):names.append(spec['adapter']['mesh'].split('/')[-1].split('.')[0])
    scene=bpy.data.scenes.new(row['key']);bpy.context.window.scene=scene;scene.world=world;scenes[row['key']]=scene
    scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=8
    scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.25
    models=[]
    for mesh_name in names:
        model=sources[mesh_name].copy();model.data=model.data.copy();model.name=row['key']+'_'+mesh_name
        scene.collection.objects.link(model);model.parent=None;model.hide_set(False);model.hide_render=False
        # Sources with an adapter already record the 6 mm body offset at the mounting origin.
        if len(names)==1:model.location=Vector()
        model.matrix_world=rotation@model.matrix_world
        if row['slot']=='blade_2' and row['id']!='false':
            for i,mat in enumerate(model.data.materials):
                if mat.name.startswith('M_AzureRunesword'):model.data.materials[i]=rune_material(mat,row['id'])
        models.append(model)
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(p) for o in models for p in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center=(lo+hi)/2;span=max(hi.x-lo.x,hi.z-lo.z)
    cam=bpy.data.objects.new('Camera_'+row['key'],bpy.data.cameras.new(row['key']));scene.collection.objects.link(cam);scene.camera=cam
    cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.ortho_scale=span/.83
    cam.location=center+Vector((0,-4*span,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    for label,offset,power,size in [('Key',(-2,-3,3),850,2.4),('Fill',(2.5,-1.5,.7),550,2),('Rim',(.5,2.5,2),1100,1.8)]:
        light=bpy.data.objects.new(label+'_'+row['key'],bpy.data.lights.new(label,'AREA'));scene.collection.objects.link(light)
        light.location=center+Vector(offset)*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
        light.data.energy=power*span*span;light.data.size=size*span
    scene.render.filepath=str(file);bpy.ops.render.render(write_still=True,scene=scene.name)
    receipt.append(dict(key=row['key'],image=str(file),runtime_spec=spec,source=[dict(scene=source_paths[n],object=n) for n in names],
        axis='native +Z toward blade -> screen left; native +X -> screen up',view='-Y horizontal orthographic; no mirroring',resolution=[1024,1024],frame_fill=.83,
        material='current source PBR; native gold or projected rune shader snapshot at t=1s where installed',renderer='Cycles 48 samples, AgX; crystal transmission approximates UE'))
    (P/'icon_render_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RUNE_POLISH_ICON_RENDERED',row['key'],flush=True)
(P/'icon_render_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.window.scene=scenes['ue_rune_sword_blade_2_golden_glow_rune']
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneSword_AttachmentIcons.blend'))
print('RUNE_POLISH_ICONS_COMPLETE',len(receipt),flush=True)
