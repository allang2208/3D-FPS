"""Restore V1 fur geometry and refine only exposed skin shading; texture production."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets')
SOURCE=ROOT/'ZombieDogV1/ZombieDog_Authoring.blend'
OUT=ROOT/'ZombieDogFineSkinV3'
(OUT/'Textures').mkdir(parents=True,exist_ok=True)
PARAMS={'texture_size':4096,'skin_repeat_per_metre':8.,'skin_relief_m':.00065,
    'wound_edge_relief_m':.0016,'pore_repeat_per_metre':320.,'pore_relief_m':.00009,
    'dry_skin_roughness':[.54,.70],'wound_roughness':.32,
    'skin_tone_low':[.055,.065,.042,1.],'skin_tone_high':[.145,.16,.11,1.]}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
rig.data.pose_position='REST'
mesh=obj.data
definitions=[]
for material in mesh.materials:
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    base=bs.inputs['Base Color'].links[0].from_node
    skin_wound=base.inputs[2].links[0].from_node
    tone=skin_wound.inputs[1].links[0].from_node
    tone.inputs[1].default_value=PARAMS['skin_tone_low']
    tone.inputs[2].default_value=PARAMS['skin_tone_high']
    for tex in [n for n in nodes if n.type=='TEX_IMAGE' and n.image and
                'T_ZombieSkinMaterial1_' in n.image.name and n.projection=='BOX']:
        tex.inputs['Vector'].links[0].from_node.inputs[1].default_value=(PARAMS['skin_repeat_per_metre'],)*3
    skin_rough=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'ZombieSkinMaterial1_roughness' in n.image.name)
    skin_ao=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'ZombieSkinMaterial1_ambientocclusion' in n.image.name)
    rough=bs.inputs['Roughness'].links[0].from_node
    exposure_rough=rough.inputs[1].links[0].from_node
    smooth_rough=nodes.new('ShaderNodeMapRange');smooth_rough.clamp=True
    smooth_rough.inputs['To Min'].default_value=PARAMS['dry_skin_roughness'][0]
    smooth_rough.inputs['To Max'].default_value=PARAMS['dry_skin_roughness'][1]
    links.new(skin_rough.outputs['Color'],smooth_rough.inputs['Value'])
    links.new(smooth_rough.outputs[0],exposure_rough.inputs[2])
    rough.inputs[2].default_value=(PARAMS['wound_roughness'],)*3+(1.,)
    ao_mix=next(n for n in nodes if n.type=='MIX_RGB' and n.inputs[2].is_linked and n.inputs[2].links[0].from_node==skin_ao)
    ao_soft=nodes.new('ShaderNodeMixRGB');ao_soft.inputs[0].default_value=.60
    ao_soft.inputs[1].default_value=(1,1,1,1)
    links.new(skin_ao.outputs['Color'],ao_soft.inputs[2]);links.new(ao_soft.outputs[0],ao_mix.inputs[2])
    normal=next(n for n in nodes if n.type=='NORMAL_MAP')
    strength=normal.inputs['Strength'].links[0].from_node
    strength.inputs[1].links[0].from_node.inputs[1].default_value=.645
    tissue=next(n for n in nodes if n.type=='BUMP' and n.inputs['Normal'].is_linked and n.inputs['Normal'].links[0].from_node==normal)
    tissue.inputs['Distance'].default_value=PARAMS['skin_relief_m']
    torn=bs.inputs['Normal'].links[0].from_node
    torn.inputs['Distance'].default_value=PARAMS['wound_edge_relief_m']
    rest=next(n for n in nodes if n.type=='ATTRIBUTE' and n.attribute_name=='ZombieRestPosition')
    pore=nodes.new('ShaderNodeTexNoise');pore.label='Fine skin pores'
    links.new(rest.outputs['Vector'],pore.inputs['Vector'])
    pore.inputs['Scale'].default_value=PARAMS['pore_repeat_per_metre']
    pore.inputs['Detail'].default_value=2.;pore.inputs['Roughness'].default_value=.55
    micro=nodes.new('ShaderNodeBump');micro.label='Sub-millimetre pore relief'
    micro.inputs['Distance'].default_value=PARAMS['pore_relief_m']
    micro_strength=nodes.new('ShaderNodeMath');micro_strength.operation='MULTIPLY'
    micro_strength.inputs[1].default_value=.18
    if base.inputs[0].is_linked:links.new(base.inputs[0].links[0].from_socket,micro_strength.inputs[0])
    else:micro_strength.inputs[0].default_value=base.inputs[0].default_value
    links.new(micro_strength.outputs[0],micro.inputs['Strength'])
    links.new(pore.outputs['Fac'],micro.inputs['Height'])
    links.new(tissue.outputs['Normal'],micro.inputs['Normal'])
    links.new(micro.outputs['Normal'],torn.inputs['Normal'])
    packed=nodes.new('ShaderNodeCombineColor')
    links.new(ao_mix.outputs[0],packed.inputs['Red']);links.new(rough.outputs[0],packed.inputs['Green'])
    packed.inputs['Blue'].default_value=0.
    alpha=bs.inputs['Alpha'].links[0].from_socket if bs.inputs['Alpha'].is_linked else 1.
    definitions.append((material,bs,out,{'BaseColor':base.outputs[0],'ORM':packed.outputs[0],'Opacity':alpha}))

bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
mesh.uv_layers.active=mesh.uv_layers['ZombieUV'];mesh.uv_layers['ZombieUV'].active_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.bake.margin=24;scene.render.bake.use_clear=True;scene.render.bake.use_selected_to_active=False
files={}
for semantic in ['BaseColor','ORM','Opacity','Normal']:
    img=bpy.data.images.new('T_ZombieDog_FineSkin_'+semantic,PARAMS['texture_size'],PARAMS['texture_size'],alpha=False)
    img.colorspace_settings.name='sRGB' if semantic=='BaseColor' else 'Non-Color'
    temporary=[]
    for material,bs,out,outputs in definitions:
        nodes=material.node_tree.nodes;links=material.node_tree.links
        target=nodes.new('ShaderNodeTexImage');target.image=img;nodes.active=target
        if semantic!='Normal':
            em=nodes.new('ShaderNodeEmission');value=outputs[semantic]
            if isinstance(value,bpy.types.NodeSocket):links.new(value,em.inputs['Color'])
            else:em.inputs['Color'].default_value=(value,value,value,1)
            links.new(em.outputs[0],out.inputs['Surface']);temporary.append((material,em))
    if semantic=='Normal':
        bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='NEG_Y',normal_b='POS_Z')
    else:bpy.ops.object.bake(type='EMIT')
    for material,em in temporary:material.node_tree.nodes.remove(em)
    for material,bs,out,_ in definitions:material.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    img.filepath_raw=str(OUT/'Textures'/(img.name+'.png'));img.file_format='PNG';img.save()
    files[semantic]=img.filepath_raw
    print('ZOMBIE_DOG_FINE_SKIN_BAKED',semantic,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ZombieDog_FineSkin_Authoring.blend'))
(OUT/'authoring_manifest.json').write_text(json.dumps({'source':str(SOURCE),'parameters':PARAMS,'textures':files,
    'geometry':'V1 body, ear cap and fur shell preserved without edits',
    'animations_modified':False,'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('ZOMBIE_DOG_FINE_SKIN_AUTHORED',flush=True)
