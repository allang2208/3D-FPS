"""RSH-only material recipes. No mesh/animation edits and no shared parent changes."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
S = O.parent
D = '/Game/Weapons/RSH12/MaterialFinish20261005'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()

FOREGRIP_BINDINGS = {
    'Body_001': D + '/MI_RSH12_ForegripPolymer',
    'M_Prism_Polymer': D + '/M_RSH12_PrismPolymer',
    'M_M4_prism_1': D + '/MI_RSH12_PrismMetal',
    'M_TacticalVerticalForegrip_Candidate': D + '/M_RSH12_TacticalPolymer',
    'Resonance_Metal_M4': D + '/MI_RSH12_ResonanceMetal',
    'RSH_Foregrip_Insert': D + '/MI_RSH12_RailInsert',
}


def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing material input: ' + path)
    return obj


def scalar(mi, name, value):
    L.set_material_instance_scalar_parameter_value(mi, name, value)


def vector(mi, name, value):
    L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*value, 1.))


def instance(name, parent):
    path = D + '/' + name
    mi = u.load_asset(path) or A.create_asset(name, D, u.MaterialInstanceConstant,
                                           u.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', parent)
    return mi


def make_loader_materials(save):
    """Skeletal WS1 instances: pre-skinned local grain, one wet film/bead layer."""
    result = {}
    for label, preset, color, roughness, metallic, grain, stipple in (
        ('LoaderSteel', 'CleanPolishedSteel', (.22, .24, .26), .29, 1., .018, 0.),
        ('LoaderPolymer', 'CleanPolymer', (.022, .025, .028), .52, 0., .028, .055),
    ):
        parent = load('/Game/Weapons/WeaponSurface/Presets/MI_WS_' + preset)
        mi = instance('MI_RSH12_' + label, parent)
        values = dict(SourceColorWeight=0., SourceRoughnessWeight=0., Roughness=roughness,
                      Metallic=metallic, EdgeMetallic=metallic, MaskUVChannel=0.,
                      GrainTileCm=2., GrainRoughness=grain, Stipple=stipple,
                      MottleRoughness=0., MottleColor=0., EdgeWear=0., EdgeHighlight=0.,
                      ScratchAmount=0., CavityDarken=0., CavityRoughness=0.,
                      HandlingPolish=0., AOStrength=0., WeaponWetness=0., BeadScale=42.)
        for key, value in values.items():
            scalar(mi, key, value)
        vector(mi, 'FinishColor', color)
        L.update_material_instance(mi)
        E.set_metadata_tag(mi, 'RSHMaterialFinish',
                           'WS1; steel retainers / polymer carrier; undeformed local cm grain; native UV0 wet layer')
        save(mi)
        result[label] = mi
    return result


def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(src, dest, pin):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, out, dest, pin):
        raise RuntimeError('Cannot connect material input: ' + pin)


def output(src, prop):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_property(n, out, getattr(u.MaterialProperty, 'MP_' + prop)):
        raise RuntimeError('Cannot connect material output: ' + prop)


def custom(m, label, code, inputs, size):
    n = node(m, u.MaterialExpressionCustom, description=label, code=code,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for key, value in inputs.items():
        wire(value, n, key)
    return n


def source(m, prop):
    p = getattr(u.MaterialProperty, 'MP_' + prop)
    n = L.get_material_property_input_node(m, p)
    return (n, str(L.get_material_property_input_node_output_name(m, p))) if n else None


def compile_static(m, save):
    for flag in ('used_with_skeletal_mesh', 'used_with_morph_targets', 'used_with_clothing'):
        m.set_editor_property(flag, False)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compile failed: ' + m.get_path_name() + ': ' + str(errors))
    save(m)


def polymer_with_weather(label, source_path, save):
    """Private graph copy, preserving original dry texture/normal/Phong conversion."""
    original = load(source_path)
    graph_path = D + '/M_RSH12_' + label
    graph = u.load_asset(graph_path)
    if not graph:
        graph = E.duplicate_asset(original.get_base_material().get_path_name(), graph_path)
        if not graph:
            raise RuntimeError('Material copy failed: ' + graph_path)
        base = source(graph, 'BASE_COLOR')
        rough = source(graph, 'ROUGHNESS')
        normal = source(graph, 'NORMAL')
        if not base or not rough:
            raise RuntimeError('Missing original dry outputs: ' + source_path)
        if not normal:
            normal = node(graph, u.MaterialExpressionConstant3Vector,
                          constant=u.LinearColor(0., 0., 1., 1.))
        wet = node(graph, u.MaterialExpressionScalarParameter,
                   parameter_name='WeaponWetness', default_value=0.)
        uv = node(graph, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
        scale = node(graph, u.MaterialExpressionScalarParameter,
                     parameter_name='RSH_BeadScale', default_value=65.)
        hlsl = S / 'WeaponSurface20260930/hlsl'
        beads = custom(graph, 'RSH single wet layer', (hlsl / 'WS_Beads.hlsl').read_text(),
                       {'UV': uv, 'Wet': wet, 'Scale': scale}, 4)
        cr = custom(graph, 'Original dry surface', 'return float4(Base, Rough);',
                    {'Base': base, 'Rough': rough}, 4)
        film = custom(graph, 'RSH wet film', (hlsl / 'WS_Wet.hlsl').read_text(),
                      {'CR': cr, 'Data': beads}, 4)
        wetnormal = custom(graph, 'Original normal plus rain beads',
                           (hlsl / 'WS_WetNormal.hlsl').read_text(),
                           {'Base': normal, 'Data': beads}, 3)
        for channels, prop in [('rgb', 'BASE_COLOR'), ('a', 'ROUGHNESS')]:
            mask = node(graph, u.MaterialExpressionComponentMask,
                        r='r' in channels, g='g' in channels, b='b' in channels, a='a' in channels)
            wire(film, mask, '')
            output(mask, prop)
        output(wetnormal, 'NORMAL')
        E.set_metadata_tag(graph, 'RSHMaterialSource', source_path)
        E.set_metadata_tag(graph, 'RSHMaterialFinish', 'Original polymer dry detail retained; one WS wet layer')
    compile_static(graph, save)
    if isinstance(original, u.MaterialInstanceConstant):
        mi_path = D + '/MI_RSH12_' + label
        mi = u.load_asset(mi_path) or E.duplicate_asset(original.get_path_name(), mi_path)
        mi.set_editor_property('parent', graph)
        scalar(mi, 'WeaponWetness', 0.)
        L.update_material_instance(mi)
        save(mi)
        return mi
    return graph


def make_foregrip_materials(save):
    result = {}
    # This RSH parent is already static-only and uses local-space grain, neutral UV0 mask.
    parent = load('/Game/Weapons/RSH12/Optics20261004/Materials/MI_RSH12_RailSteel')
    reference = json.loads((S / 'RSH12Optics20261004/finish_reference.json').read_text())
    for label in ('RailInsert', 'PrismMetal', 'ResonanceMetal'):
        mi = instance('MI_RSH12_' + label, parent)
        for key, value in dict(Metallic=1., EdgeMetallic=1., Roughness=reference['roughness'][0],
                               MaskUVChannel=0., WeaponWetness=0., MottleRoughness=0.).items():
            scalar(mi, key, value)
        vector(mi, 'FinishColor', reference['base_color'])
        L.update_material_instance(mi)
        E.set_metadata_tag(mi, 'RSHMaterialFinish', 'RSH rail reference; no donor receiver atlas; existing geometry normals retained')
        save(mi)
        result[label] = mi
    for label, path in (
        ('ForegripPolymer', '/Game/Weapons/M4InfimaV3/Body_001'),
        ('PrismPolymer', '/Game/Weapons/PrismHandstopV1/M_Prism_Polymer'),
        ('TacticalPolymer', '/Game/Weapons/TacticalVerticalForegrip20260919/M4/M_TacticalVerticalForegrip'),
    ):
        result[label] = polymer_with_weather(label, path, save)
    return result


def register_weather(materials, save):
    table = load('/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials')
    mapping = dict(table.get_editor_property('wet_materials'))
    for m in materials:
        mapping[m.get_path_name()] = m
    table.set_editor_property('wet_materials', mapping)
    save(table)
