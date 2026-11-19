"""Use the game's oak, iron and kiln texture sets in the editable service blend."""
import os
import sys
from pathlib import Path

import bpy


def bind_service_surfaces(texture_directory):
    joinery=Path(__file__).resolve().parents[1]/'Furniture'
    sys.path.insert(0,str(joinery))
    from source_materials import bind_surfaces
    bind_surfaces(joinery)

    for name,tint,bare in (
        ('Clay',(.32,.123,.058),1.),('AshGlaze',(.53,.43,.29),.35),
        ('OliveGlaze',(.114,.138,.066),.16),('HoneyGlaze',(.34,.151,.042),.12)):
        material=bpy.data.materials[name]
        material.use_nodes=True
        nodes,links=material.node_tree.nodes,material.node_tree.links
        nodes.clear()
        shader=nodes.new('ShaderNodeBsdfPrincipled')
        output=nodes.new('ShaderNodeOutputMaterial')
        links.new(shader.outputs['BSDF'],output.inputs['Surface'])

        def sample(suffix):
            tex=nodes.new('ShaderNodeTexImage')
            tex.image=bpy.data.images.load(str(texture_directory/('T_Kiln'+suffix+'.png')),check_existing=True)
            tex.image.colorspace_settings.name='sRGB' if suffix=='Albedo' else 'Non-Color'
            return tex.outputs['Color']

        colour=nodes.new('ShaderNodeVectorMath')
        colour.operation='MULTIPLY'
        links.new(sample('Albedo'),colour.inputs[0])
        colour.inputs[1].default_value=tint
        links.new(colour.outputs[0],shader.inputs['Base Color'])
        masks=nodes.new('ShaderNodeSeparateColor')
        links.new(sample('Masks'),masks.inputs[0])
        rough=nodes.new('ShaderNodeMixRGB')
        rough.inputs[0].default_value=bare
        links.new(masks.outputs[1],rough.inputs[1])
        links.new(masks.outputs[2],rough.inputs[2])
        links.new(rough.outputs[0],shader.inputs['Roughness'])
        dx=nodes.new('ShaderNodeVectorMath')
        dx.operation='MULTIPLY_ADD'
        dx.inputs[1].default_value=(1,-1,1)
        dx.inputs[2].default_value=(0,1,0)
        links.new(sample('Normal'),dx.inputs[0])
        normal=nodes.new('ShaderNodeNormalMap')
        links.new(dx.outputs[0],normal.inputs['Color'])
        links.new(normal.outputs[0],shader.inputs['Normal'])

    for image in bpy.data.images:
        if image.source=='FILE' and image.filepath:
            absolute=bpy.path.abspath(image.filepath)
            image.filepath='//'+os.path.relpath(absolute,texture_directory).replace(os.sep,'/')
