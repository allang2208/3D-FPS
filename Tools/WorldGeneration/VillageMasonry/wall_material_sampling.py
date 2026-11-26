"""Compile village wall permutations and share each relief layer's height lookup."""
import unreal as u

L = u.MaterialEditingLibrary
FLAT = 'Village Wall - NormalGlobal strength fixed at zero'
OFFSET = 'Shared Village Relief Offset'
RESULT = 'Village Relief Offset'
FLAT_RELIEF = ('MI_Main_StoneWall_00A', 'MI_Main_StoneWall_00B_Gray', 'MI_StoneWall_Pieces_00A')


def wire(src, output, dst, pin):
    if not L.connect_material_expressions(src, output, dst, pin):
        raise RuntimeError(f'Cannot connect {src.get_name()}.{output} to {dst.get_name()}.{pin}')


def matching(nodes, kind, prop, value):
    return [n for n in nodes if isinstance(n, kind) and str(n.get_editor_property(prop)) == value]


def add_zero_normal_switch(fn):
    nodes = L.get_material_function_expressions(fn)
    if matching(nodes, u.MaterialExpressionStaticSwitchParameter, 'parameter_name', FLAT):
        return False
    output, = matching(nodes, u.MaterialExpressionFunctionOutput, 'output_name', 'Result')
    original, = L.get_inputs_for_material_function_expression(fn, output)
    if not isinstance(original, u.MaterialExpressionMaterialFunctionCall) or original.get_editor_property('material_function').get_name() != 'MF_NormalIntensity':
        raise RuntimeError('Global normal function no longer has the audited layout')
    fn.modify()
    flat = L.create_material_expression_in_function(fn, u.MaterialExpressionConstant3Vector, 20, 230)
    flat.set_editor_property('constant', u.LinearColor(0, 0, 1, 0))
    switch = L.create_material_expression_in_function(fn, u.MaterialExpressionStaticSwitchParameter, 230, 70)
    switch.set_editor_property('parameter_name', FLAT)
    switch.set_editor_property('default_value', False)
    wire(flat, '', switch, 'True')
    wire(original, '', switch, 'False')
    wire(switch, '', output, '')
    L.update_material_function(fn)
    return True


def enable_flat(instance):
    if L.get_material_instance_scalar_parameter_value(instance, 'NormalGlobal_Intensity') != 0.0:
        raise RuntimeError('Nonzero global normal on '+instance.get_path_name())
    if FLAT not in {str(p) for p in L.get_static_switch_parameter_names(instance)}:
        raise RuntimeError('Missing global normal permutation on '+instance.get_path_name())
    if not L.get_material_instance_static_switch_parameter_value(instance, FLAT):
        L.set_material_instance_static_switch_parameter_value(instance, FLAT, True)
        L.update_material_instance(instance)
    if not L.get_material_instance_static_switch_parameter_value(instance, FLAT):
        raise RuntimeError('Could not enable flat global normal for '+instance.get_path_name())


def share_relief_height(fn, texture_set):
    nodes = L.get_material_function_expressions(fn)
    installed = matching(nodes, u.MaterialExpressionFunctionOutput, 'output_name', RESULT)
    if not installed:
        original, = matching(nodes, u.MaterialExpressionCustom, 'description', 'Near-field scan relief')
        shifts = [n for n in nodes if isinstance(n, u.MaterialExpressionCustom) and
                  str(n.get_editor_property('description')).startswith('Offset native ')]
        if len(shifts) != 3:
            raise RuntimeError('Expected three relief projections')
        fn.modify()
        shared = L.create_material_expression_in_function(fn, u.MaterialExpressionFunctionInput, -920, 4520)
        shared.set_editor_property('input_name', OFFSET)
        shared.set_editor_property('input_type', u.FunctionInputType.FUNCTION_INPUT_VECTOR3)
        shared.set_editor_property('use_preview_value_as_default', True)
        shared.set_editor_property('sort_priority', 1000)
        # Preserve the original result for callers that use this function on its own.
        wire(original, '', shared, 'Preview')
        output = L.create_material_expression_in_function(fn, u.MaterialExpressionFunctionOutput, -660, 4520)
        output.set_editor_property('output_name', RESULT)
        output.set_editor_property('sort_priority', 1000)
        wire(original, '', output, '')
        for shift in shifts:
            wire(shared, '', shift, 'Shift')
        L.update_material_function(fn)
    calls = [n for n in L.get_material_function_expressions(texture_set)
             if isinstance(n, u.MaterialExpressionMaterialFunctionCall) and n.get_editor_property('material_function') == fn]
    if len(calls) != 3:
        raise RuntimeError('Expected colour, packed mask and normal projections')
    def inputs(call):
        return dict(zip(map(str, L.get_material_expression_input_names(call)),
                        L.get_inputs_for_material_function_expression(texture_set, call)))
    for call in calls:
        if OFFSET not in inputs(call):
            previous = {k:(v, L.get_input_node_output_name_for_material_expression(call, v))
                        for k,v in inputs(call).items() if v}
            if not call.set_material_function(fn):
                raise RuntimeError('Could not refresh projection call pins')
            for k,(src,output) in previous.items():
                wire(src, output or '', call, k)
            if any(inputs(call).get(k) != v[0] for k,v in previous.items()):
                raise RuntimeError('Could not restore original links: '+repr(list(inputs(call))))
    maps = [inputs(c) for c in calls]
    # Only the tile size reaches the relief offset. Texture/normal-map switches
    # still belong to their respective projections.
    if any(OFFSET not in m or not m.get('Tile Size (cm)') for m in maps):
        raise RuntimeError('Projection call pins unavailable: '+repr([list(m) for m in maps]))
    if len({m['Tile Size (cm)'].get_path_name() for m in maps}) != 1:
        raise RuntimeError('Cannot share a lookup across different projection scales')
    producer, = [c for c,m in zip(calls,maps) if str(m['Texture'].get_editor_property('parameter_name')).endswith('_BaseColor')]
    if inputs(producer).get(OFFSET):
        raise RuntimeError('Colour projection must retain its local relief offset')
    texture_set.modify()
    for call in calls:
        if call != producer:
            wire(producer, RESULT, call, OFFSET)
    L.update_material_function(texture_set)

