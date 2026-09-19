"""Remove the V1 fur geometry and bake full skin while preserving existing wounds."""
import bpy, bmesh, json
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets')
SOURCE=ROOT/'ZombieDogV1/ZombieDog_Authoring.blend'
OUT=ROOT/'ZombieDogSkinOnlyV2'
(OUT/'Textures').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
rig.data.pose_position='REST'
mesh=obj.data
fur_slots={i for i,m in enumerate(mesh.materials) if m and 'Fur' in m.name}
bm=bmesh.new();bm.from_mesh(mesh)
fur_faces=[f for f in bm.faces if f.material_index in fur_slots]
removed=len(fur_faces)
bmesh.ops.delete(bm,geom=fur_faces,context='FACES')
bm.to_mesh(mesh);bm.free()

# Retain the body and closed ear cap, including their original vertex weights.
old_materials=list(mesh.materials)
retained_indices=[i for i in range(len(old_materials)) if i not in fur_slots]
mapping={old:new for new,old in enumerate(retained_indices)}
face_slots=[mapping[p.material_index] for p in mesh.polygons]
mesh.materials.clear()
for index in retained_indices:mesh.materials.append(old_materials[index])
for p,slot in zip(mesh.polygons,face_slots):p.material_index=slot

definitions=[]
for material in mesh.materials:
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    # The outer BaseColor mix formerly chose between fur and wounded skin.
    skin_mix=bs.inputs['Base Color'].links[0].from_node
    for link in list(skin_mix.inputs[0].links):links.remove(link)
    skin_mix.inputs[0].default_value=1.
    wound_rough=bs.inputs['Roughness'].links[0].from_node
    exposure_rough=wound_rough.inputs[1].links[0].from_node
    for link in list(exposure_rough.inputs[0].links):links.remove(link)
    exposure_rough.inputs[0].default_value=1.
    # Remove the source fur's normal pattern, not only its color and shell.
    normal=next(n for n in nodes if n.type=='NORMAL_MAP')
    for link in list(normal.inputs['Strength'].links):links.remove(link)
    normal.inputs['Strength'].default_value=0.
    tissue_bump=next(n for n in nodes if n.type=='BUMP' and n.inputs['Normal'].is_linked
                     and n.inputs['Normal'].links[0].from_node==normal)
    for link in list(tissue_bump.inputs['Strength'].links):links.remove(link)
    tissue_bump.inputs['Strength'].default_value=.62
    skin_ao=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image
                 and 'ZombieSkinMaterial1_ambientocclusion' in n.image.name)
    packed=nodes.new('ShaderNodeCombineColor')
    links.new(skin_ao.outputs['Color'],packed.inputs['Red'])
    links.new(wound_rough.outputs[0],packed.inputs['Green'])
    packed.inputs['Blue'].default_value=0.
    bs.inputs['Alpha'].default_value=1.
    definitions.append((material,bs,out,{'BaseColor':skin_mix.outputs[0],'ORM':packed.outputs[0]}))

bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.context.view_layer.objects.active=obj
mesh.uv_layers.active=mesh.uv_layers['ZombieUV']
mesh.uv_layers['ZombieUV'].active_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=4
scene.render.bake.margin=12;scene.render.bake.use_clear=True
scene.render.bake.use_selected_to_active=False
files={}
for semantic in ['BaseColor','ORM','Normal']:
    image=bpy.data.images.new('T_ZombieDog_SkinOnly_'+semantic,2048,2048,alpha=False)
    image.colorspace_settings.name='sRGB' if semantic=='BaseColor' else 'Non-Color'
    temporary=[]
    for material,bs,out,outputs in definitions:
        nodes=material.node_tree.nodes;links=material.node_tree.links
        target=nodes.new('ShaderNodeTexImage');target.image=image;nodes.active=target
        if semantic!='Normal':
            emission=nodes.new('ShaderNodeEmission')
            links.new(outputs[semantic],emission.inputs['Color'])
            links.new(emission.outputs[0],out.inputs['Surface'])
            temporary.append((material,emission))
    if semantic=='Normal':
        bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='NEG_Y',normal_b='POS_Z')
    else:bpy.ops.object.bake(type='EMIT')
    for material,node in temporary:material.node_tree.nodes.remove(node)
    for material,bs,out,_ in definitions:material.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    image.filepath_raw=str(OUT/'Textures'/(image.name+'.png'));image.file_format='PNG';image.save()
    files[semantic]=image.filepath_raw
    print('ZOMBIE_DOG_SKIN_ONLY_BAKED',semantic,flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ZombieDog_SkinOnly_Authoring.blend'))
mesh.uv_layers.remove(mesh.uv_layers['SourceUV'])
rig.data.pose_position='POSE'
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_ZombieDog_SkinOnly.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=False,
    mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring_manifest.json').write_text(json.dumps({
    'source':str(SOURCE),'removed_fur_faces':removed,
    'material_change':'Entire body uses wounded organic skin; source fur color and normal contribution removed',
    'preserved':'Body and closed ear cap geometry; skeleton; skin weights; ZombieUV; wounds; gameplay',
    'textures':files,'runtime_tested':False,'preview_rendered':False,
},ensure_ascii=False,indent=2),encoding='utf-8')
print('ZOMBIE_DOG_SKIN_ONLY_AUTHORED',flush=True)
