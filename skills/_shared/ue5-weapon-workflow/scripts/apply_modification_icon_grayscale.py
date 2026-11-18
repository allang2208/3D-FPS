"""Blender-only neutral finish for modification icons; never edit runtime materials.

Call apply_grayscale(objects) and neutral_output(scene) on an isolated icon scene.
Matches the 2026-09-27 bow icon palette. Preserve UVs, alpha, surface normals,
roughness and metallic masks; only colour inputs on copied shaders are changed.
"""
def apply_grayscale(objects):
    copied={}
    for obj in objects:
        for slot in obj.material_slots:
            original=slot.material
            if original is None:continue
            if original.get('ModificationIconPalette')=='neutral-grayscale-20260927':continue
            if original in copied:
                slot.material=copied[original];continue
            material=original.copy();material.name='IconGray_'+original.name
            copied[original]=material;slot.material=material
            material['ModificationIconPalette']='neutral-grayscale-20260927'
            if not material.use_nodes:continue
            nodes=material.node_tree.nodes;links=material.node_tree.links
            for shader in list(nodes):
                if not (shader.type.startswith('BSDF_') or shader.type in {'EMISSION','VOLUME_ABSORPTION','VOLUME_SCATTER'}):continue
                for socket in shader.inputs:
                    if socket.type!='RGBA':continue
                    source=socket.links[0].from_socket if socket.is_linked else None
                    gray=nodes.new('ShaderNodeRGBToBW');gray.label='Icon only: neutral luminance'
                    if source:links.new(source,gray.inputs[0])
                    else:gray.inputs[0].default_value=socket.default_value
                    value=gray.outputs[0]
                    if shader.type=='BSDF_PRINCIPLED' and socket.name=='Base Color':
                        clamp=nodes.new('ShaderNodeClamp');links.new(value,clamp.inputs[0])
                        power=nodes.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=.25
                        links.new(clamp.outputs[0],power.inputs[0])
                        scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY_ADD'
                        scale.inputs[1].default_value=.45;scale.inputs[2].default_value=.16
                        links.new(power.outputs[0],scale.inputs[0]);value=scale.outputs[0]
                    links.new(value,socket)
    return [m.name for m in copied.values()]

def neutral_output(scene):
    """Keep RGB path-tracing/denoise noise neutral while retaining film alpha (Blender 5.1)."""
    import bpy
    tree=bpy.data.node_groups.new('ModificationIcon_NeutralOutput','CompositorNodeTree')
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    scene.compositing_node_group=tree
    source=tree.nodes.new('CompositorNodeRLayers')
    gray=tree.nodes.new('CompositorNodeRGBToBW')
    alpha=tree.nodes.new('CompositorNodeSetAlpha');alpha.inputs['Type'].default_value='Replace Alpha'
    output=tree.nodes.new('NodeGroupOutput')
    tree.links.new(source.outputs['Image'],gray.inputs['Image'])
    tree.links.new(gray.outputs[0],alpha.inputs['Image'])
    tree.links.new(source.outputs['Alpha'],alpha.inputs['Alpha'])
    tree.links.new(alpha.outputs[0],output.inputs['Image'])
    scene.render.use_compositing=True;scene.render.dither_intensity=0
