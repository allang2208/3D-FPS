"""Append rain response to current melee surfaces, preserving their dry graphs."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).parent
L, E, A = u.MaterialEditingLibrary, u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
C = json.loads((O / 'audit.json').read_text(encoding='utf-8'))
DEST = '/Game/Weather/MeleeWetness20261002'
VERSION = '20261002-v1'
RP = O / 'install_receipt.json'
R = json.loads(RP.read_text()) if RP.exists() else {
    'version': VERSION, 'masters': {}, 'mapping': {}, 'excluded': {}, 'backups': {},
    'complete': False, 'runtime_tested': False, 'geometry_changed': False}

def record():
    RP.write_text(json.dumps(R, indent=2, ensure_ascii=False), encoding='utf-8')

def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

def sha(path):
    return hashlib.sha256(disk(path).read_bytes()).hexdigest()

def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing current asset ' + path)
    return obj

def backup(path):
    if path in R['backups']:
        return
    dest = O / 'Before' / disk(path).relative_to(P / 'Content')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(disk(path), dest)
    R['backups'][path] = str(dest)
    record()

def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Save failed ' + obj.get_path_name())

def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n

def wire(src, dest, pin):
    n, channel = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, channel, dest, pin):
        raise RuntimeError('Connection failed: ' + pin)

def output(src, prop):
    n, channel = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_property(n, channel, prop):
        raise RuntimeError('Material output connection failed ' + str(prop))

def constant(m, value):
    if isinstance(value, tuple):
        return node(m, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*value, 1.))
    return node(m, u.MaterialExpressionConstant, r=value)

def custom(m, label, code, inputs, size):
    n = node(m, u.MaterialExpressionCustom, description=label, code=code,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    entries = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        entries.append(pin)
    n.set_editor_property('inputs', entries)
    for key, src in inputs.items():
        wire(src, n, key)
    return n

def dry_output(m, channel, default):
    prop = getattr(u.MaterialProperty, 'MP_' + channel)
    src = L.get_material_property_input_node(m, prop)
    if src:
        return src, str(L.get_material_property_input_node_output_name(m, prop))
    return constant(m, default)

def material_surface(path):
    # The inventory contains combined viewmodels, so exclude their arm material.
    return not path.startswith('/Game/Characters/') and 'M_StaffCraft_IceInner_' not in path and 'M_StaffCraft_StormInner_' not in path

materials = {p: v for p, v in C['materials'].items() if material_surface(p)}
masters = {v['base'] for v in materials.values()}
dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE is active; preserve current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path in sorted(masters):
    expected = R['masters'].get(path, {}).get('sha256', C['masters'][path]['sha256'])
    if path.split('.')[0] in dirty or sha(path) != expected:
        raise RuntimeError('Current source changed or is unsaved: ' + path)
for p in C['materials']:
    if p not in materials:
        R['excluded'][p] = 'Combined viewmodel arm material' if p.startswith('/Game/Characters/') else 'Protected crystal interior; rain applies to the outer crystal'
if DEST + '/DA_MeleeWetMaterials' in dirty:
    raise RuntimeError('Unsaved melee wetness table')

collection = load('/Game/Weather/Materials/MPC_FPS_Weather.MPC_FPS_Weather')
beads_code = (P / 'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text()
beads_code = 'if (Wet <= 0.00001) return float4(0,0,0,0);\n' + beads_code

for path in sorted(masters):
    if path in R['masters']:
        continue
    m = load(path)
    backup(path)
    # Defaults retain the global weather response on dropped/world meshes.
    # Held MIDs set a nonnegative per-item value before they are bound.
    local = node(m, u.MaterialExpressionScalarParameter, parameter_name='WeaponWetness',
                 default_value=-1., group='Melee Rain')
    world = node(m, u.MaterialExpressionCollectionParameter, collection=collection,
                 parameter_name='WeatherWetness')
    wet = custom(m, 'MeleeRainResolvedWetness',
                 'return saturate(Local < 0 ? World : Local);', {'Local': local, 'World': world}, 1)
    uv = node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
    data = custom(m, 'MeleeRainBeads', beads_code, {'UV': uv, 'Wet': wet}, 4)

    # Capture before reconnecting any channel. Legacy and explicit Substrate
    # paths both retain the authored textures and their output channel masks.
    original = {key: dry_output(m, key, default) for key, default in [
        ('BASE_COLOR', (.5, .5, .5)), ('METALLIC', 0.), ('ROUGHNESS', .5), ('NORMAL', (0., 0., 1.))]}
    front = L.get_material_property_input_node(m, u.MaterialProperty.MP_FRONT_MATERIAL)
    substrate_original = None
    if front:
        if not isinstance(front, u.MaterialExpressionSubstrateShadingModels):
            raise RuntimeError('Unsupported current front surface ' + path)
        ins = L.get_inputs_for_material_expression(m, front)
        substrate_original = {}
        for key, index, default in [('BASE_COLOR', 0, (.5, .5, .5)), ('METALLIC', 1, 0.),
                                    ('ROUGHNESS', 3, .5), ('NORMAL', 6, (0., 0., 1.))]:
            src = ins[index]
            if src and sum(n == src for n in ins) > 1:
                raise RuntimeError('Ambiguous Substrate channel ' + path)
            substrate_original[key] = (src, str(L.get_input_node_output_name_for_material_expression(front, src))) if src else constant(m, default)

    is_glass = m.get_editor_property('blend_mode') == u.BlendMode.BLEND_TRANSLUCENT
    def wrappers(dry, suffix=''):
        darkening = '.055' if is_glass else 'lerp(.16,.045,saturate(Metal))'
        color = custom(m, 'MeleeRainColor' + suffix,
                       'return Base * (1 - Data.a * ' + darkening + ');',
                       {'Base': dry['BASE_COLOR'], 'Metal': dry['METALLIC'], 'Data': data}, 3)
        rough = custom(m, 'MeleeRainRoughness' + suffix,
                       'float film=min(Base,max(.045,Base*.70)); '
                       'return lerp(lerp(Base,film,Data.a),min(film,.055),Data.b*.72);',
                       {'Base': dry['ROUGHNESS'], 'Data': data}, 1)
        normal = custom(m, 'MeleeRainNormal' + suffix,
                        'if(Data.a<.00001)return Base; '
                        'return normalize(float3(Base.xy*(1-Data.b*.20)+Data.xy*.48,Base.z));',
                        {'Base': dry['NORMAL'], 'Data': data}, 3)
        return {'BASE_COLOR': color, 'ROUGHNESS': rough, 'NORMAL': normal}
    for key, src in wrappers(original).items():
        output(src, getattr(u.MaterialProperty, 'MP_' + key))
    if front:
        for key, src in wrappers(substrate_original, 'Substrate').items():
            wire(src, front, {'BASE_COLOR': 'BaseColor', 'ROUGHNESS': 'Roughness', 'NORMAL': 'Normal'}[key])
    E.set_metadata_tag(m, 'MeleeRainWetnessVersion', VERSION)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compilation failed ' + path + ': ' + str(errors))
    save(m)
    R['masters'][path] = {'sha256': sha(path), 'saved': True, 'substrate': bool(front),
                          'translucent': is_glass, 'local_default': -1.}
    record()
    u.log('CLOVEN_MELEE_WET_SAVED ' + path)

mapping = {path: load(path) for path in sorted(materials)}
cls = u.load_class(None, '/Script/FPSGAME.WeatherPresentationAssets')
factory = u.DataAssetFactory()
factory.set_editor_property('data_asset_class', cls)
table = u.load_asset(DEST + '/DA_MeleeWetMaterials') if E.does_asset_exist(DEST + '/DA_MeleeWetMaterials') else A.create_asset('DA_MeleeWetMaterials', DEST, cls, factory)
table.set_editor_property('wet_materials', mapping)
save(table)
R['mapping'] = {p: obj.get_path_name() for p, obj in mapping.items()}
R['table'] = table.get_path_name()
R['complete'] = True
record()
u.log('CLOVEN_MELEE_WETNESS_SAVED masters=%d mappings=%d' % (len(R['masters']), len(mapping)))
