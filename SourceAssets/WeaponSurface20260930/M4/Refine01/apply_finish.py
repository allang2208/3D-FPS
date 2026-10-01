"""Save M4 finish while retaining authored decoration and structural inputs.

Private adapters protect source graphs and preserve existing runtime mesh paths.
No mesh reimport or game tests.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
L, E, A = u.MaterialEditingLibrary, u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
C = json.loads((O / 'Input/current.json').read_text())
R = json.loads((O / 'recipe.json').read_text())
ROOT = R['root']
RP = O / 'apply_receipt.json'
receipt = json.loads(RP.read_text()) if RP.exists() else {'version': R['version'], 'textures': {},
    'masters': {}, 'instances': {}, 'overrides': {}, 'meshes': {}, 'weather': {}, 'backups': {},
    'complete': False, 'geometry_changed': False, 'tested': False}


def record():
    RP.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing production asset ' + path)
    return obj


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Asset save failed ' + obj.get_path_name())


def backup(path):
    if path in receipt['backups']:
        return
    dest = O / 'Before' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(disk(path), dest)
    receipt['backups'][path] = str(dest)
    record()


dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE active; preserve current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
pending_paths = set(receipt.get('pending_masters', {}).values())
if any(p.startswith(ROOT + '/') and p not in pending_paths for p in dirty):
    raise RuntimeError('Unsaved M4 finish assets')
for path in {t[k] for t in R['targets'].values() for k in ('source', 'wet_source', 'base') if t[k]}:
    if not path.startswith('/Game/'):
        continue
    expected = receipt['overrides'].get(path, {}).get('sha256', C['sources'][path])
    if path.split('.')[0] in dirty or sha(disk(path)) != expected:
        raise RuntimeError('Changed or unsaved source ' + path)
for path, bindings in R['bindings'].items():
    if path.split('.')[0] in dirty:
        raise RuntimeError('Unsaved target mesh ' + path)
    mesh = load(path)
    prop = 'materials' if C['meshes'][path]['skeletal'] else 'static_materials'
    slots = list(mesh.get_editor_property(prop))
    for b in bindings:
        s = slots[b['index']]
        target = R['targets'][b['key']]['asset']
        expected = target + '.' + target.rsplit('/', 1)[1] if path in receipt['meshes'] else b['before']
        if str(s.material_slot_name) != b['slot'] or s.material_interface.get_path_name() != expected:
            raise RuntimeError('Changed target slot ' + path + ' ' + b['slot'])
wetpath = C['weather']['path']
if wetpath.split('.')[0] in dirty:
    raise RuntimeError('Unsaved weather table')
weather = load(wetpath)

spec = R['texture']
if sha(Path(spec['source'])) != spec['sha256']:
    raise RuntimeError('Texture source changed')
if not receipt['textures']:
    if E.does_asset_exist(spec['asset']):
        raise RuntimeError('Texture destination occupied')
    task = u.AssetImportTask()
    task.filename = spec['source']
    task.destination_path, task.destination_name = spec['asset'].rsplit('/', 1)
    task.automated, task.replace_existing, task.save = True, False, False
    A.import_asset_tasks([task])
    tex = load(spec['asset'])
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    tex.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
    tex.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
    E.set_metadata_tag(tex, 'WeaponSurfaceVersion', R['version'])
    save(tex)
    receipt['textures'][spec['asset']] = {'saved': True, 'source_sha256': spec['sha256']}
    record()
grain = load(spec['asset'])

# Author maps were present as source PNGs, but the old Phong material never
# sampled metallic and interpreted roughness as shininess. Import private linear
# copies; do not alter textures or master materials shared with other weapons.
for key, entry in R['pbr_textures'].items():
    if entry['asset'] in receipt['textures']:
        continue
    if sha(Path(entry['file'])) != entry['sha256']:
        raise RuntimeError('Authored PBR source changed ' + key)
    if E.does_asset_exist(entry['asset']):
        raise RuntimeError('PBR texture destination occupied ' + entry['asset'])
    task = u.AssetImportTask()
    task.filename = entry['file']
    task.destination_path, task.destination_name = entry['asset'].rsplit('/', 1)
    task.automated, task.replace_existing, task.save = True, False, False
    A.import_asset_tasks([task])
    tex = load(entry['asset'])
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    E.set_metadata_tag(tex, 'WeaponSurfaceVersion', R['version'])
    save(tex)
    receipt['textures'][entry['asset']] = {'saved': True, 'source_sha256': entry['sha256']}
    record()
coat = R['linear_coat']
if coat['asset'] not in receipt['textures']:
    if E.does_asset_exist(coat['asset']):
        raise RuntimeError('Coat texture destination occupied')
    tex = E.duplicate_asset(coat['source'], coat['asset'])
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    save(tex)
    receipt['textures'][coat['asset']] = {'saved': True, 'source': coat['source']}
    record()


def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for name, value in props.items():
        n.set_editor_property(name, value)
    return n


def wire(src, dest, pin):
    n, output = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, output, dest, pin):
        raise RuntimeError('Material connection failed ' + pin)


def custom(m, label, code, inputs, size):
    n = node(m, u.MaterialExpressionCustom, description=label, code=code,
        output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for name in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for name, src in inputs.items():
        wire(src, n, name)
    return n


def output(m, src, prop):
    n, channel = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_property(n, channel, prop):
        raise RuntimeError('Material output connection failed')


def source_output(m, prop, default=None):
    n = L.get_material_property_input_node(m, prop)
    if n:
        return n, str(L.get_material_property_input_node_output_name(m, prop))
    if default is None:
        raise RuntimeError('Missing required source material output ' + str(prop))
    return node(m, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*default, 1.)) if isinstance(default, tuple) else node(m, u.MaterialExpressionConstant, r=default)


def input_of(m, n, name):
    names = [str(p.get_editor_property('input_name')) for p in n.get_editor_property('inputs')]
    src = L.get_inputs_for_material_expression(m, n)[names.index(name)]
    return src, str(L.get_input_node_output_name_for_material_expression(n, src))


def wet_wrapper(n):
    if not isinstance(n, u.MaterialExpressionCustom):
        return False
    names = {str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')}
    return names == {'Base', 'Data'} and 'Data.a' in str(n.get_editor_property('code'))


def dry_input(m, prop, wet):
    src = source_output(m, prop)
    if not wet:
        return src, None
    outer = src[0]
    if not wet_wrapper(outer):
        raise RuntimeError('Expected existing wet wrapper ' + str(prop))
    # Some source graphs already contain nested import-time wet wrappers. Keep
    # the outer one and reconnect it to the truly dry surface in our private copy.
    while wet_wrapper(src[0]):
        src = input_of(m, src[0], 'Base')
    return src, outer


def connection(m, expression, index):
    src = L.get_inputs_for_material_expression(m, expression)[index]
    return src, str(L.get_input_node_output_name_for_material_expression(expression, src))


def restore_pbr(m, src, channel, target):
    n = src[0] if isinstance(src, tuple) else src
    if isinstance(n, u.MaterialExpressionMaterialFunctionCall):
        function = n.get_editor_property('material_function')
        if function and function.get_name() == 'MF_PhongToMetalRoughness':
            if channel == 'BASE_COLOR':
                return connection(m, n, 1)
            if channel == 'ROUGHNESS':
                if target['native_pbr']:
                    sample = next(x for x in L.get_material_expressions(m)
                                  if isinstance(x, u.MaterialExpressionTextureSampleParameter2D)
                                  and str(x.get_editor_property('parameter_name')) == 'ShininessMap')
                    sample.set_editor_property('texture', load(target['textures']['ShininessMap']))
                    sample.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
                    return sample, 'R'
                rough_input = connection(m, n, 3)
                return (rough_input[0], 'R') if isinstance(rough_input[0], u.MaterialExpressionTextureSample) else rough_input
            if channel == 'METALLIC':
                if not target['native_pbr']:
                    # These authored coating branches already have explicit
                    # metal-region masks (UV/vertex/texture); only that branch changes.
                    return node(m, u.MaterialExpressionConstant, r=1.)
                sample = node(m, u.MaterialExpressionTextureSampleParameter2D,
                    parameter_name='R01_AuthorMetallic', texture=load(target['textures']['R01_AuthorMetallic']),
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS, group='M4 Authored Finish')
                diffuse = next(x for x in L.get_material_expressions(m)
                               if isinstance(x, u.MaterialExpressionTextureSampleParameter2D)
                               and str(x.get_editor_property('parameter_name')) == 'DiffuseColorMap')
                if L.get_inputs_for_material_expression(m, diffuse)[0]:
                    wire(connection(m, diffuse, 0), sample, 'UVs')
                return sample, 'R'
    if isinstance(n, u.MaterialExpressionLinearInterpolate):
        for index, pin in enumerate(('A', 'B')):
            original = connection(m, n, index)
            if original[0]:
                restored = restore_pbr(m, original, channel, target)
                if restored != original:
                    wire(restored, n, pin)
    return src


def adapt(m, t):
    for n in L.get_material_expressions(m):
        if isinstance(n, u.MaterialExpressionTextureSample):
            texture = n.get_editor_property('texture')
            if texture and texture.get_path_name().split('.')[0] == coat['source']:
                n.set_editor_property('texture', load(coat['asset']))
                n.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    base_color, color_wet = dry_input(m, u.MaterialProperty.MP_BASE_COLOR, bool(t['wet_source']))
    base_rough, rough_wet = dry_input(m, u.MaterialProperty.MP_ROUGHNESS, bool(t['wet_source']))
    metal = source_output(m, u.MaterialProperty.MP_METALLIC, 0.)
    base_color = restore_pbr(m, base_color, 'BASE_COLOR', t)
    base_rough = restore_pbr(m, base_rough, 'ROUGHNESS', t)
    metal = restore_pbr(m, metal, 'METALLIC', t)
    output(m, metal, u.MaterialProperty.MP_METALLIC)
    region = node(m, u.MaterialExpressionConstant, r=1.)
    if t['region'] == 'colour_lerp_alpha':
        colour_node = base_color[0]
        if not isinstance(colour_node, u.MaterialExpressionLinearInterpolate):
            raise RuntimeError('Expected source region blend')
        alpha = L.get_inputs_for_material_expression(m, colour_node)[2]
        region = alpha, str(L.get_input_node_output_name_for_material_expression(colour_node, alpha))
    elif t['region'] == 'vertex_red':
        region = node(m, u.MaterialExpressionVertexColor), 'R'
    settings = {}
    for name, value in t['scalars'].items():
        if name.startswith(('R01_', 'R02_')):
            settings[name] = node(m, u.MaterialExpressionScalarParameter, parameter_name=name,
                default_value=value, group='M4 Authored Finish')
    tone = node(m, u.MaterialExpressionVectorParameter, parameter_name='R01_ToneScale',
        default_value=u.LinearColor(*t['vectors']['R01_ToneScale'], 1.), group='M4 Authored Finish')
    tex = node(m, u.MaterialExpressionTextureObjectParameter, parameter_name='R01_GrainTexture',
        texture=grain, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, group='M4 Authored Finish')
    pos = node(m, u.MaterialExpressionVertexInterpolator)
    nor = node(m, u.MaterialExpressionVertexInterpolator)
    wire(node(m, u.MaterialExpressionPreSkinnedPosition), pos, 'VS')
    wire(node(m, u.MaterialExpressionPreSkinnedNormal), nor, 'VS')
    detail = custom(m, 'M4 R01 physical fine roughness', (O / 'FineGrain.hlsl').read_text(), {'P': pos, 'N': nor, 'T': tex}, 4)
    poly_tint = node(m, u.MaterialExpressionVectorParameter, parameter_name='R01_PolymerTint',
        default_value=u.LinearColor(*t['vectors']['R01_PolymerTint'], 1.), group='M4 Authored Finish')
    polymer_colour = custom(m, 'M4 R01 polymer colour', (O / 'PolymerColor.hlsl').read_text(),
        {'Base': base_color, 'Metal': metal, 'Tint': poly_tint,
         'Strength': settings['R01_PolymerStrength']}, 3)
    polymer_rough = custom(m, 'M4 R01 polymer roughness', (O / 'PolymerRoughness.hlsl').read_text(),
        {'Base': base_rough, 'Colour': base_color, 'Metal': metal,
         'Center': settings['R01_PolymerRoughness'], 'Pivot': settings['R01_PolymerPivot'],
         'SourceWeight': settings['R01_PolymerSourceWeight'], 'Strength': settings['R01_PolymerStrength']}, 1)
    colour = custom(m, 'M4 R01 authored colour and wear retained', (O / 'FinishColor.hlsl').read_text(),
        {'Base': polymer_colour, 'Metal': metal, 'Region': region, 'Strength': settings['R01_Strength'], 'ToneScale': tone, 'SourceContrast': settings['R02_SourceColorContrast']}, 3)
    rough = custom(m, 'M4 R01 source roughness detail retained', (O / 'FinishRoughness.hlsl').read_text(),
        {'Base': polymer_rough, 'Colour': base_color, 'Metal': metal, 'Region': region,
            'Center': settings['R01_Roughness'], 'Pivot': settings['R01_SourcePivot'],
            'SourceWeight': settings['R01_SourceRoughnessWeight'], 'Detail': detail,
            'Grain': settings['R01_Grain'], 'Variation': settings['R01_Variation'], 'Strength': settings['R01_Strength']}, 1)
    if color_wet:
        dry_normal, normal_wet = dry_input(m, u.MaterialProperty.MP_NORMAL, True)
        wire(dry_normal, normal_wet, 'Base')
        wire(colour, color_wet, 'Base')
        wire(rough, rough_wet, 'Base')
        # The old weather graph can generate a few beads at zero wetness.
        # Self-wet instances require the truly dry input when WeaponWetness=0.
        for n in L.get_material_expressions(m):
            if isinstance(n, u.MaterialExpressionCustom):
                code = str(n.get_editor_property('code'))
                if 'return float4(slope,beads,saturate(Wet));' in code:
                    n.set_editor_property('code', code.replace('return float4(slope,beads,saturate(Wet));',
                        'float coverage=saturate(Wet*20.);return float4(slope*coverage,beads*coverage,saturate(Wet));'))
    else:
        normal = source_output(m, u.MaterialProperty.MP_NORMAL, (0., 0., 1.))
        wet = node(m, u.MaterialExpressionScalarParameter, parameter_name='WeaponWetness', default_value=0.)
        exposure = custom(m, 'M4 R01 wet exterior', 'return saturate(Wet)*saturate(Region);', {'Wet': wet, 'Region': region}, 1)
        beads_code = (P / 'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text().replace(
            'return float4(slope,beads,saturate(Wet));', 'float coverage=saturate(Wet*20.);return float4(slope*coverage,beads*coverage,saturate(Wet));')
        beads = custom(m, 'M4 R01 single weather beads', beads_code,
            {'UV': node(m, u.MaterialExpressionTextureCoordinate), 'Wet': exposure}, 4)
        output(m, custom(m, 'M4 R01 single wet film', 'return Base*(1-Data.a*.07);', {'Base': colour, 'Data': beads}, 3), u.MaterialProperty.MP_BASE_COLOR)
        output(m, custom(m, 'M4 R01 wet roughness', 'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',
            {'Base': rough, 'Data': beads}, 1), u.MaterialProperty.MP_ROUGHNESS)
        output(m, custom(m, 'M4 R01 wet normal', 'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',
            {'Base': normal, 'Data': beads}, 3), u.MaterialProperty.MP_NORMAL)
    if t['usage'] == 'static':
        for prop in ('used_with_skeletal_mesh', 'used_with_morph_targets', 'used_with_clothing'):
            m.set_editor_property(prop, False)
    E.set_metadata_tag(m, 'WeaponSurfaceGraph', R['version'])
    E.set_metadata_tag(m, 'WeaponSurfaceSourceGraph', t['base'])
    E.set_metadata_tag(m, 'WeaponSurfacePreserved', 'Authored colour, markings, wear, normal/AO and source UVs; restored linear PBR inputs; one weather layer')
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compilation failed ' + m.get_path_name() + ': ' + str(errors))


def master(t):
    key = t['base'] + '|' + t['usage'] + '|' + t['region']
    if key in receipt['masters']:
        return load(receipt['masters'][key]['path'])
    path = ROOT + '/Master/M_M4_R01_' + hashlib.sha1(key.encode()).hexdigest()[:12]
    if E.does_asset_exist(path):
        if receipt.get('pending_masters', {}).get(key) != path:
            raise RuntimeError('Adapter destination occupied ' + path)
        m = load(path)
        if any(isinstance(n, u.MaterialExpressionCustom) and str(n.get_editor_property('description')).startswith('M4 R01') for n in L.get_material_expressions(m)):
            raise RuntimeError('Partly adapted graph requires explicit recovery ' + path)
    else:
        receipt.setdefault('pending_masters', {})[key] = path
        record()
        m = E.duplicate_asset(t['base'], path)
    if not m:
        raise RuntimeError('Material clone failed')
    adapt(m, t)
    save(m)
    receipt['masters'][key] = {'path': m.get_path_name(), 'source': t['base'], 'usage': t['usage'], 'saved': True}
    receipt.get('pending_masters', {}).pop(key, None)
    record()
    return m


for index, (key, t) in enumerate(R['targets'].items()):
    if t['direct_override']:
        if t['source'] not in receipt['overrides']:
            m = load(t['source'])
            if not isinstance(m, u.Material) or '/M4/' not in t['source']:
                raise RuntimeError('Expected M4-only direct runtime material')
            backup(t['source'])
            adapt(m, t)
            save(m)
            receipt['overrides'][t['source']] = {'path': m.get_path_name(), 'saved': True, 'sha256': sha(disk(t['source']))}
            record()
        continue
    if key in receipt['instances']:
        continue
    parent = master(t)
    path = t['asset']
    if E.does_asset_exist(path):
        raise RuntimeError('Instance destination occupied ' + path)
    original = load(t['source'])
    if isinstance(original, u.MaterialInstanceConstant):
        mi = E.duplicate_asset(t['source'], path)
    else:
        dest, name = path.rsplit('/', 1)
        mi = A.create_asset(name, dest, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    if not mi:
        raise RuntimeError('Create instance failed ' + path)
    L.set_material_instance_parent(mi, parent)
    params = C['materials'][t['source']]['parameters']
    for name, value in {**params['scalar'], **t['scalars']}.items():
        L.set_material_instance_scalar_parameter_value(mi, name, float(value))
    for name, value in {**params['vector'], **t['vectors']}.items():
        L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*(value if len(value) == 4 else value + [1.])))
    for name, value in {**params['texture'], **t['textures']}.items():
        if value:
            L.set_material_instance_texture_parameter_value(mi, name, load(value))
    L.set_material_instance_texture_parameter_value(mi, 'R01_GrainTexture', grain)
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][key] = {'path': mi.get_path_name(), 'parent': parent.get_path_name(), 'role': t['role'], 'saved': True}
    record()
    if (index + 1) % 10 == 0:
        print('WEAPON_SURFACE_M4_R01_MATERIALS', index + 1, flush=True)

if not receipt['weather']:
    mapping = dict(weather.get_editor_property('wet_materials'))
    targets = list(receipt['instances'].values()) + list(receipt['overrides'].values())
    for row in targets:
        mapping[row['path']] = load(row['path'])
    backup(wetpath)
    weather.set_editor_property('wet_materials', mapping)
    save(weather)
    receipt['weather'] = {'path': wetpath, 'added_self_mappings': len(targets), 'saved': True}
    record()
for path, bindings in R['bindings'].items():
    if path in receipt['meshes']:
        continue
    mesh = load(path)
    prop = 'materials' if C['meshes'][path]['skeletal'] else 'static_materials'
    slots = list(mesh.get_editor_property(prop))
    selected = {}
    for b in bindings:
        slot = slots[b['index']]
        slot.material_interface = load(R['targets'][b['key']]['asset'])
        slots[b['index']] = slot
        selected[b['slot']] = slot.material_interface.get_path_name()
    backup(path)
    mesh.set_editor_property(prop, slots)
    E.set_metadata_tag(mesh, 'M4SurfaceFinishRevision', R['version'])
    save(mesh)
    receipt['meshes'][path] = {'saved': True, 'bindings': selected, 'geometry_changed': False, 'saved_sha256': sha(disk(path))}
    record()
    print('WEAPON_SURFACE_M4_R01_BOUND', path, len(selected), flush=True)
receipt['complete'] = True
record()
print('WEAPON_SURFACE_M4_R01_SAVED', len(receipt['instances']), 'instances', len(receipt['masters']),
    'adapters', len(receipt['overrides']), 'runtime override materials', len(receipt['meshes']),
    'meshes; geometry_changed=False; tested=False', flush=True)
