"""201-only finish revision; keep UV0 structure and original regional masks."""
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = '/Game/Weapons/LMG201/Material21'
E = u.EditorAssetLibrary
M = u.MaterialEditingLibrary
STEEL = (.020, .024, .030)
GRAIN_SOURCE = '/Game/Weapons/A762/Refinement03/Textures/T_A762_RebuiltFinish'
GRAIN_PATH = P + '/Textures/T_LMG201_FineFinish'


def profile(name, params):
    p = {'scalar': {}, 'vector': {}}
    if 'A762CoatingRoughness' in params['scalar']:
        p['scalar'] = {'A762CoatingRoughness': .35, 'A762CoatingMetallic': .78}
        p['vector'] = {'A762CoatingColor': STEEL}
        return p
    if 'RoughnessCenter' not in params['scalar']:
        return p
    rough = params['scalar']['RoughnessCenter']
    if 'ReceiverReferenceCover' in name: rough = .35
    elif 'ReceiverReferenceRail' in name: rough = .37
    elif 'ReceiverReferenceHardware' in name: rough = .33
    elif 'ReferenceFrontSight' in name or 'ReferenceRearSight' in name: rough = .40
    elif 'Polymer' in name or 'RearGrip' in name: rough = .50
    elif name == 'M_LMG201_Handguard': rough = .49
    p['scalar']['RoughnessCenter'] = rough
    if 'Feed__' in name:
        if name.endswith('_Paint'):
            p['scalar'].update(Metallic=0., RoughnessCenter=.44, LMG201MicroRoughness=.024)
        elif name.endswith('_Case'):
            p['scalar'].update(Metallic=1., RoughnessCenter=.32, LMG201MicroRoughness=.018)
            p['vector']['FinishColor'] = (.45, .32, .14)
        elif name.endswith('_Copper'):
            p['scalar'].update(Metallic=1., RoughnessCenter=.30, LMG201MicroRoughness=.018)
            p['vector']['FinishColor'] = (.52, .25, .12)
        elif name.endswith('_Link'):
            p['scalar'].update(Metallic=.9, RoughnessCenter=.34)
    return p


def node(mat, cls, **props):
    n = M.create_material_expression(mat, cls)
    for k, v in props.items(): n.set_editor_property(k, v)
    return n


def wire(src, dest, pin):
    n, output = src if isinstance(src, tuple) else (src, '')
    if not M.connect_material_expressions(n, output, dest, pin):
        raise RuntimeError('Cannot connect ' + pin)


def output(src, prop):
    n, pin = src if isinstance(src, tuple) else (src, '')
    if not M.connect_material_property(n, pin, prop): raise RuntimeError(str(prop))


def parameter(mat, name, value, vector=False):
    cls = u.MaterialExpressionVectorParameter if vector else u.MaterialExpressionScalarParameter
    n = next((n for n in M.get_material_expressions(mat)
              if isinstance(n, cls) and str(n.get_editor_property('parameter_name')) == name), None)
    if n is None: n = node(mat, cls, parameter_name=name)
    n.set_editor_property('default_value', u.LinearColor(*value, 1) if vector else value)
    return n


def apply_graph(mat, settings, grain):
    for k, v in settings['scalar'].items(): parameter(mat, k, v)
    for k, v in settings['vector'].items(): parameter(mat, k, v, True)
    expressions = list(M.get_material_expressions(mat))
    # Reduce only the old roughness atlas variation, never the structural normal.
    for n in expressions:
        if isinstance(n, u.MaterialExpressionMultiply) and abs(n.get_editor_property('const_b') - .065) < .00001:
            inputs = M.get_inputs_for_material_expression(mat, n)
            if inputs and isinstance(inputs[0], u.MaterialExpressionTextureSample):
                tex = inputs[0].get_editor_property('texture')
                if tex and tex.get_name() == 'T_LMG201_roughness': n.set_editor_property('const_b', .024)
        if isinstance(n, u.MaterialExpressionAdd) and abs(n.get_editor_property('const_b') + .0325) < .00001:
            n.set_editor_property('const_b', -.012)
    has_detail = False
    for n in expressions:
        if isinstance(n, u.MaterialExpressionTextureSample):
            tex = n.get_editor_property('texture')
            if tex and tex.get_path_name().split('.')[0] == GRAIN_SOURCE:
                n.set_editor_property('texture', grain)
                n.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
                has_detail = True
    # These opaque PBR coating graphs retained an unrelated Phong specular output.
    # Disconnect that legacy branch; do not reinterpret Shininess as roughness.
    if 'A762CoatingRoughness' in settings['scalar']:
        spec = M.get_material_property_input_node(mat, u.MaterialProperty.MP_SPECULAR)
        if isinstance(spec, u.MaterialExpressionMaterialFunctionCall):
            output(parameter(mat, 'A762CoatingSpecular', .5), u.MaterialProperty.MP_SPECULAR)
    if has_detail: return 'existing independent UV finish preserved; texture made 201-private'
    if any(isinstance(n, u.MaterialExpressionCustom) and
           n.get_editor_property('description') == 'LMG20121 fine roughness' for n in expressions):
        return 'existing Material21 graph'
    base = M.get_material_property_input_node(mat, u.MaterialProperty.MP_ROUGHNESS)
    pin = M.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_ROUGHNESS)
    if not base: raise RuntimeError('Missing base roughness ' + mat.get_path_name())
    inputs = {'Base': (base, pin)}
    for label, cls in [('P', u.MaterialExpressionPreSkinnedPosition), ('N', u.MaterialExpressionPreSkinnedNormal)]:
        bridge = node(mat, u.MaterialExpressionVertexInterpolator)
        wire(node(mat, cls), bridge, 'VS')
        inputs[label] = bridge
    inputs['FinishTex'] = node(mat, u.MaterialExpressionTextureObject, texture=grain,
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    inputs['Amplitude'] = parameter(mat, 'LMG201MicroRoughness', .024)
    detail = node(mat, u.MaterialExpressionCustom, description='LMG20121 fine roughness',
        code=(O / 'FineRoughness.hlsl').read_text(encoding='utf8'),
        output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', name); pins.append(p)
    detail.set_editor_property('inputs', pins)
    for name, src in inputs.items(): wire(src, detail, name)
    output(detail, u.MaterialProperty.MP_ROUGHNESS)
    return '5 cm local triplanar roughness only, no extra normal'
