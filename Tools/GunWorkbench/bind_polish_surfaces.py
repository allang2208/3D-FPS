"""Bind the authored PBR recipes to the editable Blender materials (shared globals)."""
surfaces=json.loads((OUT/'surface-materials.json').read_text(encoding='utf-8'))['materials']
for name,recipe in surfaces.items():
    mat=MATS[name];nodes=mat.node_tree.nodes;links=mat.node_tree.links
    nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    bsdf.inputs['Metallic'].default_value=recipe['metallic']
    if 'color' in recipe:
        bsdf.inputs['Base Color'].default_value=(*recipe['color'],1)
        bsdf.inputs['Roughness'].default_value=recipe['roughness']
        continue
    for ch,path in recipe['maps'].items():
        sample=nodes.new('ShaderNodeTexImage');sample.image=bpy.data.images.load(path,check_existing=True)
        sample.image.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
        sample.label=ch
        if ch=='BaseColor':
            mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
            links.new(sample.outputs['Color'],mix.inputs[1]);mix.inputs[2].default_value=(*recipe['color_tint'],1)
            links.new(mix.outputs[0],bsdf.inputs['Base Color'])
        elif ch in ('Roughness','ORM'):
            separate=nodes.new('ShaderNodeSeparateColor');links.new(sample.outputs['Color'],separate.inputs[0])
            rough=separate.outputs['Green' if ch=='ORM' else 'Red']
            if ch=='ORM':links.new(separate.outputs['Blue'],bsdf.inputs['Metallic'])
            scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY_ADD'
            links.new(rough,scale.inputs[0]);scale.inputs[1].default_value=recipe['roughness_scale'];scale.inputs[2].default_value=recipe['roughness_bias']
            links.new(scale.outputs[0],bsdf.inputs['Roughness'])
        elif ch=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=recipe['normal_strength']
            links.new(sample.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bsdf.inputs['Normal'])
