"""Read back M_BallisticTracerVisibleV13 and report its tracer-relevant graph state.

Read-only: loads the asset and logs. No compilation, no save, no game.
"""
import unreal

TARGET = '/Game/Weapons/GunplayFX/M_BallisticTracerVisibleV13'
L = unreal.EditorAssetLibrary
LIB = unreal.MaterialEditingLibrary

material = unreal.load_asset(TARGET)
if not material:
    raise RuntimeError('Missing ' + TARGET)

nodes = LIB.get_material_expressions(material)
custom = [n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom)]
responsive = [n for n in nodes if isinstance(n, unreal.MaterialExpressionTemporalResponsivenessOutput)]
constant = [n for n in nodes if isinstance(n, unreal.MaterialExpressionConstant)]

unreal.log('VERIFY nodes=%d custom=%d responsive=%d constant=%d blend=%s' % (
    len(nodes), len(custom), len(responsive), len(constant),
    material.get_editor_property('blend_mode')))
for node in custom:
    code = node.get_editor_property('code')
    unreal.log('VERIFY custom desc="%s" taper=%s lines=%d' % (
        node.get_editor_property('description'), 'taper' in code, len(code.splitlines())))
for node in responsive:
    # get_inputs_for_material_expression returns the connected expressions themselves.
    for source in LIB.get_inputs_for_material_expression(material, node):
        unreal.log('VERIFY responsive source=%s value=%s' % (
            source.get_class().get_name() if source else 'None',
            source.get_editor_property('r') if isinstance(source, unreal.MaterialExpressionConstant) else '-'))
unreal.log('VERIFY source_tag=%s' % L.get_metadata_tag(material, 'Gunplay.TracerSource'))
unreal.log('VERIFY responsive_aa=%s' % material.get_editor_property('enable_responsive_aa'))