"""Carry the lake-to-quarry erosion survey into the scanned ground families."""
import unreal as ue

LIB = ue.MaterialEditingLibrary
MASTER = '/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround'
TAG = 'QuarryLakeSlope.'


def ancestors(mat, root):
    pending, seen = [root], set()
    while pending:
        node = pending.pop()
        if node and node.get_name() not in seen:
            seen.add(node.get_name())
            yield node
            pending.extend(LIB.get_inputs_for_material_expression(mat, node))


def named(mat, root, label):
    hits = [node for node in ancestors(mat, root) if str(node.get_editor_property('desc')) == label]
    if len(hits) != 1:
        raise RuntimeError('Expected one active ' + label + ', found ' + str(len(hits)))
    return hits[0]


def input_at(mat, node, pin):
    names = [str(item.get_editor_property('input_name')) for item in node.get_editor_property('inputs')]
    return LIB.get_inputs_for_material_expression(mat, node)[names.index(pin)]


def connect(source, node, pin):
    if not LIB.connect_material_expressions(source, '', node, pin):
        raise RuntimeError('Cannot connect ' + node.get_name() + '.' + pin)


def add_pin(node, name):
    pins = list(node.get_editor_property('inputs'))
    if name not in [str(pin.get_editor_property('input_name')) for pin in pins]:
        pin = ue.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
        node.set_editor_property('inputs', pins)


def apply_surface_families(mat, uv):
    color_root = LIB.get_material_property_input_node(mat, ue.MaterialProperty.MP_BASE_COLOR)
    families = named(mat, color_root, 'GroundFamilyWeights')
    upland = named(mat, color_root, 'HillsWet20261111.UplandColor')
    # The same weights drive scan sampling, heights, normals and roughness. Reuse
    # both patch noises from the original family selector to feather the deposits.
    original = 'return float4(grass,soil,gravel,dry)/max(grass+soil+gravel+dry,0.0001);'
    surveyed = '''
float4 natural = float4(grass,soil,gravel,dry)/max(grass+soil+gravel+dry,.0001);
float cover = saturate(Survey.x-4.);
float shoulder = saturate(U.y-2.);
float turf = smoothstep(.11,.65,U.x-2.+.20*(nb-.5)+.12*(na-.5));
float talus = smoothstep(.10,.72,shoulder+.20*(nb-.5));
float wash = saturate(max(1.25*Survey.y,2.-U.x));
// The shallow wash exposes moist soil. Coarse scree ends at its wet margin;
// on the higher spurs the gravel scan carries through the grass-free front.
float4 local = float4(.90*turf*(1.-talus)*(1.-wash),
    .22+.86*wash+.12*(1.-turf), .055+1.75*talus,
    .13*(1.-turf)*(1.-talus)*(1.-wash));
return lerp(natural,local/dot(local,float4(1,1,1,1)),smoothstep(0.,.92,cover));
'''.strip()
    finish = 'return lerp(distant,Scan.rgb*wet,Mask);'
    grade = '''
float3 surface = lerp(distant,Scan.rgb*wet,Mask);
float cover = smoothstep(0.,.92,saturate(Survey.x-4.));
float turf = smoothstep(.12,.64,Site.x-2.);
float talus = smoothstep(.12,.72,Site.y-2.);
float wash = saturate(max(1.25*Survey.y,2.-Site.x));
// Grade the combined near scans and distant ground together so the cool
// limestone and the darker turf survive the upland scan-distance transition.
float3 soil = surface*lerp(float3(.76,.71,.62),float3(.50,.46,.40),wash);
float3 grassBed = surface*float3(.62,.84,.63);
float3 stone = lerp(surface,dot(surface,float3(.30,.59,.11))*float3(.94,1.,1.04),.74)*.91;
float3 slopeColor = lerp(lerp(soil,grassBed,turf*(1.-wash)),stone,talus);
return lerp(surface,slopeColor,cover);
'''.strip()
    for expr, old, new in ((families, original, surveyed), (upland, finish, grade)):
        code = expr.get_editor_property('code')
        if old not in code and new not in code:
            raise RuntimeError('Unknown quarry surface expression ' + str(expr.get_editor_property('desc')))
        expr.modify()
        add_pin(expr, 'Survey')
        connect(uv, expr, 'Survey')
        expr.set_editor_property('code', code.replace(old, new))


def install(mat):
    root = LIB.get_material_property_input_node(mat, ue.MaterialProperty.MP_ROUGHNESS)
    mix = named(mat, root, 'HillRiverRoughness')
    ground = named(mat, input_at(mat, mix, 'A'), 'GroundRoughness')
    litter = named(mat, input_at(mat, mix, 'A'), 'ForestLitterRoughness')
    bank = input_at(mat, mix, 'B')
    # Modify the blend amount only. At full rain the exposed terrain still
    # shows its original per-texel roughness, sampled at its original scale.
    replacements = [
        (ground, 'WetRough,WetF)', 'WetRough,WetF*(1.-Drainage))'),
        (litter, '.38,Wet)', '.38,Wet*(1.-Drainage))'),
        (bank, '.25,max(M.g,saturate(Wet)))', '.25,max(M.g,saturate(Wet))*(1.-Drainage))'),
    ]
    for node, old, new in replacements:
        code = node.get_editor_property('code')
        if old not in code and new not in code:
            raise RuntimeError('Ground roughness graph changed at ' + node.get_name())
    wet = input_at(mat, bank, 'Wet')
    nodes = {str(node.get_editor_property('desc')): node for node in ancestors(mat, mix)}
    mat.modify()
    uv = nodes.get(TAG + 'SurveyUV')
    if uv is None:
        uv = LIB.create_material_expression(mat, ue.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('desc', TAG + 'SurveyUV')
        uv.set_editor_property('coordinate_index', 3)
    drainage = nodes.get(TAG + 'Drainage')
    if drainage is None:
        drainage = LIB.create_material_expression(mat, ue.MaterialExpressionCustom)
        drainage.set_editor_property('desc', TAG + 'Drainage')
        pins = []
        for name in ('Slope', 'Wet'):
            pin = ue.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        drainage.set_editor_property('inputs', pins)
        drainage.set_editor_property('output_type', ue.CustomMaterialOutputType.CMOT_FLOAT1)
    # Slope.y already includes coverage. Keep rain film along the low thalwegs.
    # Ordinary cells expose UV2 (<=3) or zero when the fourth UV is unbound.
    drainage.set_editor_property('code', '''
float cover = saturate(Slope.x - 4.);
return .48 * saturate(Wet) * max(0., cover - 1.35 * saturate(Slope.y));
''')
    connect(uv, drainage, 'Slope')
    connect(wet, drainage, 'Wet')
    for node, old, new in replacements:
        node.modify()
        add_pin(node, 'Drainage')
        connect(drainage, node, 'Drainage')
        node.set_editor_property('code', node.get_editor_property('code').replace(old, new))
    apply_surface_families(mat, uv)


if __name__ == '__main__':
    if any(p.get_path_name() == MASTER for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('The active ground material has unsaved edits')
    material = ue.load_asset(MASTER)
    install(material)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError(str(errors))
    if not ue.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + MASTER)
    ue.log('QUARRY_SLOPE_FINISH_SAVED ' + material.get_path_name())
