"""Composite the physical lens after temporal AA and keep opaque mesh occlusion."""
from pathlib import Path
import unreal as u


def input_names(node):
    return [str(pin.get_editor_property('input_name')) for pin in node.get_editor_property('inputs')]


def input_pin(name):
    pin=u.CustomInput()
    pin.set_editor_property('input_name',name)
    return pin


def set_picture_shader(material, code):
    library = u.MaterialEditingLibrary
    pending = [library.get_material_property_input_node(material, u.MaterialProperty.MP_EMISSIVE_COLOR)]
    connected = {}
    while pending:
        node = pending.pop()
        if node and node.get_path_name() not in connected:
            connected[node.get_path_name()] = node
            pending.extend(library.get_inputs_for_material_expression(material, node))
    picture, = (node for node in connected.values() if isinstance(node, u.MaterialExpressionCustom)
                and {'ScreenUV','ScreenToLens','Scene','ReticleStyle'}.issubset(input_names(node)))
    shape_path=Path(__file__).resolve().parent.parent/'BowSingleLensOptics20260927/ReticleReadability/Reticle.hlsl'
    # Dedicated bow glass has one silhouette. Compile out the gun patterns on it.
    family='7' if material.get_name() == 'M_PeakwatchVariableLens' else '(int)round(ReticleStyle)'
    etch_code=(f'const int family = {family};\n'
               'float4 position=float4(MeshPosition,1.);\n'
               'float2 UV=.5+.5*float2(dot(position,PlaneU),dot(position,PlaneV));\n'
               +shape_path.read_text(encoding='utf8'))
    if 'FixedEtch' in input_names(picture):
        etch,=(node for node in library.get_inputs_for_material_expression(material,picture)
               if isinstance(node,u.MaterialExpressionCustom) and 'MeshPosition' in input_names(node))
    else:
        etch=library.create_material_expression(material,u.MaterialExpressionCustom)
        etch.set_editor_properties(dict(desc='Fixed reticle in rear glass coordinates',
            inputs=[input_pin(n) for n in ('MeshPosition','PlaneU','PlaneV')]))
        local=library.create_material_expression(material,u.MaterialExpressionLocalPosition)
        local.set_editor_properties(dict(local_origin=u.LocalPositionOrigin.PRIMITIVE,
                                         included_offsets=u.PositionIncludedOffsets.EXCLUDE_OFFSETS))
        if not library.connect_material_expressions(local,'',etch,'MeshPosition'):
            raise RuntimeError('Cannot bind glass position')
        for name in ('PlaneU','PlaneV'):
            plane=library.create_material_expression(material,u.MaterialExpressionVectorParameter)
            plane.set_editor_property('parameter_name','Reticle'+name)
            if not library.connect_material_expressions(plane,'RGBA',etch,name):
                raise RuntimeError('Cannot bind '+name)
        pins=[pin for pin in picture.get_editor_property('inputs')
              if str(pin.get_editor_property('input_name')) not in ('Glyphs','CaptureTanHalfFOV')]
        picture.set_editor_property('inputs',pins+[input_pin('FixedEtch')])
        if not library.connect_material_expressions(etch,'',picture,'FixedEtch'):
            raise RuntimeError('Cannot connect the fixed reticle')
    # Reuse the selector already driven by the mounted optic. Both the picture and
    # the engraving read it, including when migrating an existing fixed-cross graph.
    if 'ReticleStyle' not in input_names(etch):
        pins = list(etch.get_editor_property('inputs'))
        etch.set_editor_property('inputs', pins + [input_pin('ReticleStyle')])
    style, = (node for node in library.get_inputs_for_material_expression(material, picture)
              if isinstance(node, u.MaterialExpressionScalarParameter)
              and str(node.get_editor_property('parameter_name')) == 'ReticleStyle')
    if not library.connect_material_expressions(style, '', etch, 'ReticleStyle'):
        raise RuntimeError('Cannot bind the optic family to its engraving')
    etch.set_editor_property('code',etch_code)
    etch.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
    if 'InkExposure' not in input_names(picture):
        pins=list(picture.get_editor_property('inputs'))
        picture.set_editor_property('inputs',pins+[input_pin('InkExposure')])
        one=library.create_material_expression(material,u.MaterialExpressionConstant)
        one.set_editor_property('r',1.)
        inverse=library.create_material_expression(material,u.MaterialExpressionEyeAdaptationInverse)
        for name in library.get_material_expression_input_names(inverse):
            if not library.connect_material_expressions(one,'',inverse,str(name)):
                raise RuntimeError('Cannot bind engraving exposure '+str(name))
        if not library.connect_material_expressions(inverse,'',picture,'InkExposure'):
            raise RuntimeError('Cannot connect engraving exposure')
    palette=shape_path.with_name('ReticleInk.hlsl').read_text(encoding='utf8')
    picture.set_editor_property('code',code.replace('// @include ReticleInk.hlsl',palette))
    # Select the physical rear element in the same space as LensCenter.
    # Its pixel position after first-person morphing belongs to another plane.
    if material.get_name() == 'M_PhysicalScopeLens':
        # The PSO shell includes a solid painted eyepiece ahead of the authored disk.
        # Move that disk to the inner face of its cup while ADS owns this material.
        # Other glass uses the zero default. Etching still reads unshifted mesh space.
        offset_property = u.MaterialProperty.MP_WORLD_POSITION_OFFSET
        offset = library.get_material_property_input_node(material, offset_property)
        if offset is None:
            offset = library.create_material_expression(material,u.MaterialExpressionVectorParameter)
            offset.set_editor_properties(dict(parameter_name='EyepieceOffset',default_value=u.LinearColor(0,0,0,0)))
            if not library.connect_material_property(offset,'RGB',offset_property):
                raise RuntimeError('Cannot position the display in the PSO cup')
        elif not isinstance(offset,u.MaterialExpressionVectorParameter) or str(offset.get_editor_property('parameter_name')) != 'EyepieceOffset':
            raise RuntimeError('Unexpected physical lens vertex offset')
        coverage, = (node for node in connected.values() if isinstance(node, u.MaterialExpressionCustom)
                     and {'Position','Center','Forward','Depth'}.issubset(
                     {str(pin.get_editor_property('input_name')) for pin in node.get_editor_property('inputs')}))
        position, = (node for node in library.get_inputs_for_material_expression(material, coverage)
                     if isinstance(node, u.MaterialExpressionWorldPosition))
        position.set_editor_property('world_position_shader_offset',
            u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)


def configure_late_glass(material):
    library = u.MaterialEditingLibrary
    opacity = u.MaterialProperty.MP_OPACITY
    source = library.get_material_property_input_node(material, opacity)
    if source is None:
        raise RuntimeError('Missing glass opacity on ' + material.get_path_name())
    material.set_editor_property('output_translucent_velocity', False)
    material.set_editor_property('enable_responsive_aa', False)
    material.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_MOTION_BLUR)
    # The After Motion Blur pass drops its hardware depth attachment. Compare
    # the glass depth to opaque scene depth in the pixel shader instead.
    if not isinstance(source, u.MaterialExpressionDepthFade):
        channel = library.get_material_property_input_node_output_name(material, opacity)
        fade = library.create_material_expression(material, u.MaterialExpressionDepthFade)
        fade.set_editor_property('fade_distance_default', .05)
        opacity_pin = str(library.get_material_expression_input_names(fade)[0])
        if not library.connect_material_expressions(source, channel, fade, opacity_pin):
            raise RuntimeError('Could not connect original glass opacity')
        if not library.connect_material_property(fade, '', opacity):
            raise RuntimeError('Could not connect depth-tested opacity')
