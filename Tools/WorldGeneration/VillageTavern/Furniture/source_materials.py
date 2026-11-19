"""Mirror the four rural surface graphs and the ruin's weathered wood in Blender."""
import os
from pathlib import Path

import bpy


def bind_surfaces(author_directory):
    root = author_directory.parents[3]
    sources = root / 'SourceAssets'
    chapel = sources / 'TemperateHillsOldChapel/Concept01/Surfaces/Prepared'
    sawn = sources / 'ApprenticeStaff20260927/SolidRepairV19/Inputs'
    cut = sources / 'HillsVillageCarpenter/Props/Authored'
    tavern = sources / 'HillsVillageTavern/Furniture'
    iron = sources / 'ProductionToolMaterials20260913/T_MetalRust_00A_BaseColor.png'
    definitions = {
        'Oak': (chapel/'Timber_Color.png', chapel/'Timber_NormalDX.png', chapel/'Timber_ARH.png',
                (.87,.85,.81), (0,0,0), 1),
        'Sawn': (sawn/'T_WoodSurface_00A_BaseColor.png', sawn/'T_WoodSurface_00A_Normal.png',
                 sawn/'T_WoodSurface_00A_RHAOM.png', (1.06,.91,.68), (.085,.058,.026), 0),
        'OiledOak': (sawn/'T_WoodSurface_00A_BaseColor.png', sawn/'T_WoodSurface_00A_Normal.png',
                     sawn/'T_WoodSurface_00A_RHAOM.png', (.88,.77,.59), (.022,.012,.007), 0),
        'Endgrain': (cut/'Cut_Color.png', cut/'Cut_Normal.png', cut/'Cut_ORM.png',
                     (1,1,1), (0,0,0), 1),
        'Rot': (tavern/'RottenWoodSurface_00A_BaseColor.png', tavern/'RottenWoodSurface_00A_Normal.png',
                tavern/'RottenWoodSurface_00A_RHAOM.png', (.85,.84,.76), (0,0,0), 0),
        'Iron': (iron, tavern/'MetalRust_00A_Normal.png', tavern/'MetalRust_00A_RHAOM.png',
                 (.12,.12,.12), (.06,.063,.062), 0),
    }
    for key, (base, normal, mask, tint, bias, rough_channel) in definitions.items():
        material = bpy.data.materials.get(key)
        if material is None:
            continue
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        nodes.clear()
        shader = nodes.new('ShaderNodeBsdfPrincipled')
        output = nodes.new('ShaderNodeOutputMaterial')
        links.new(shader.outputs['BSDF'],output.inputs['Surface'])

        def sample(path, space):
            node = nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(str(path),check_existing=True)
            node.image.colorspace_settings.name = space
            return node.outputs['Color']

        def vector_op(op, socket, values):
            node = nodes.new('ShaderNodeVectorMath')
            node.operation = op
            links.new(socket,node.inputs[0])
            node.inputs[1].default_value = values
            return node.outputs[0]

        colour = vector_op('MULTIPLY',sample(base,'sRGB'),tint)
        if any(bias):
            colour = vector_op('ADD',colour,bias)
        links.new(colour,shader.inputs['Base Color'])
        tangents = vector_op('MULTIPLY',sample(normal,'Non-Color'),(1,-1,1))
        normal_map = nodes.new('ShaderNodeNormalMap')
        if key == 'OiledOak':
            normal_map.inputs['Strength'].default_value = .58
        links.new(vector_op('ADD',tangents,(0,1,0)),normal_map.inputs['Color'])
        links.new(normal_map.outputs[0],shader.inputs['Normal'])
        channels = nodes.new('ShaderNodeSeparateColor')
        links.new(sample(mask,'Non-Color'),channels.inputs[0])
        rough = channels.outputs[rough_channel]
        if key in ('Iron','OiledOak'):
            scale = nodes.new('ShaderNodeMath')
            scale.operation = 'MULTIPLY_ADD'
            links.new(rough,scale.inputs[0])
            scale.inputs[1].default_value = .56 if key == 'Iron' else .22
            scale.inputs[2].default_value = .13 if key == 'Iron' else .34
            rough = scale.outputs[0]
            shader.inputs['Metallic'].default_value = .83 if key == 'Iron' else 0
        links.new(rough,shader.inputs['Roughness'])


def relative_to_blend(author_directory):
    for image in bpy.data.images:
        if image.source == 'FILE' and image.filepath:
            absolute = bpy.path.abspath(image.filepath)
            image.filepath = '//' + os.path.relpath(absolute,author_directory).replace(os.sep,'/')
