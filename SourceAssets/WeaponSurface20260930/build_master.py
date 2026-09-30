"""Build the shared weapon surface master, its textures and the surface-card presets.

Creates only new assets under /Game/Weapons/WeaponSurface; no existing weapon material
is touched. Re-running updates custom-node code and preset values in place (never
rebuilds a referenced graph). Receipt: logs/build_master_receipt.json.
"""
import json
import unreal as u
from pathlib import Path

O = Path(__file__).parent
ROOT = '/Game/Weapons/WeaponSurface'
MASTER = ROOT + '/Master/M_WeaponSurface'
VERSION = 'WS1-20260930'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
card = json.loads((O / 'surface_card.json').read_text(encoding='utf-8'))
receipt = {'version': VERSION, 'textures': {}, 'master': None, 'presets': {}, 'compile_errors': {},
           'game_tested': False, 'complete': False}
RECEIPT = O / 'logs' / 'build_master_receipt.json'
RECEIPT.parent.mkdir(exist_ok=True)


def record():
    RECEIPT.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())


def import_texture(name, srgb, compression, nomips=False):
    path = ROOT + '/Textures/' + name
    if not E.does_asset_exist(path):
        task = u.AssetImportTask()
        task.filename = str(O / 'Textures' / (name + '.png'))
        task.destination_path = ROOT + '/Textures'
        task.destination_name = name
        task.automated = True
        task.replace_existing = False
        task.save = False
        A.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError('Texture import failed ' + name)
    tex.set_editor_property('srgb', srgb)
    tex.set_editor_property('compression_settings', compression)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    if nomips:
        tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    E.set_metadata_tag(tex, 'WeaponSurfaceVersion', VERSION)
    save(tex)
    receipt['textures'][name] = tex.get_path_name()
    return tex


C = u.TextureCompressionSettings
grain_tex = import_texture('T_WS_Grain', False, C.TC_BC7)
mask_tex = import_texture('T_WS_MaskNeutral', False, C.TC_MASKS, True)
white_tex = import_texture('T_WS_White', True, C.TC_DEFAULT, True)
grey_tex = import_texture('T_WS_GreyLinear', False, C.TC_GRAYSCALE, True)
flat_normal = u.load_asset('/Engine/EngineMaterials/DefaultNormal')
record()

CODE = {name: (O / 'hlsl' / (name + '.hlsl')).read_text(encoding='utf-8-sig') for name in
        ['WS_Grain', 'WS_Wear', 'WS_ColorRough', 'WS_MetalAO', 'WS_Beads', 'WS_Wet', 'WS_WetNormal']}
SCALARS = card['master_defaults']['scalars']
VECTORS = card['master_defaults']['vectors']
GROUPS = card['master_defaults']['groups']


def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def wire(src, dest, pin):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, out, dest, pin):
        raise RuntimeError('Cannot connect %s.%s -> %s' % (n.get_name(), out, pin))


def output(src, prop):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_property(n, out, getattr(u.MaterialProperty, 'MP_' + prop)):
        raise RuntimeError('Cannot connect output ' + prop)


def custom(m, name, inputs, size):
    n = node(m, u.MaterialExpressionCustom, code=CODE[name], description=name,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for key, src in inputs.items():
        wire(src, n, key)
    return n


def mask(m, src, channels):
    n = node(m, u.MaterialExpressionComponentMask, r='r' in channels, g='g' in channels,
             b='b' in channels, a='a' in channels)
    wire(src, n, '')
    return n


def build(m):
    L.set_material_usage(m, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    m.set_editor_property('two_sided', False)
    s = {}
    for name, value in SCALARS.items():
        s[name] = node(m, u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value,
                       group=GROUPS.get(name, 'Finish'))
    v = {}
    for name, value in VECTORS.items():
        v[name] = node(m, u.MaterialExpressionVectorParameter, parameter_name=name,
                       default_value=u.LinearColor(*value, 1), group=GROUPS.get(name, 'Finish'))
    ST = u.MaterialSamplerType
    src = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SourceBaseColor',
               texture=white_tex, sampler_type=ST.SAMPLERTYPE_COLOR, group='Source')
    srough = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SourceRoughness',
                  texture=grey_tex, sampler_type=ST.SAMPLERTYPE_LINEAR_GRAYSCALE, group='Source')
    nrm = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SurfaceNormal',
               texture=flat_normal, sampler_type=ST.SAMPLERTYPE_NORMAL, group='Source')
    msk = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SurfaceMask',
               texture=mask_tex, sampler_type=ST.SAMPLERTYPE_MASKS, group='Source')
    # Baked masks live on a unique layout: UV1 on meshes whose UV0 tiles, else UV0.
    mask_uv = node(m, u.MaterialExpressionLinearInterpolate)
    wire(node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=0), mask_uv, 'A')
    wire(node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=1), mask_uv, 'B')
    wire(s['MaskUVChannel'], mask_uv, 'Alpha')
    wire(mask_uv, msk, 'UVs')
    grain = node(m, u.MaterialExpressionTextureObjectParameter, parameter_name='GrainTexture',
                 texture=grain_tex, sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR, group='Micro')
    pos = node(m, u.MaterialExpressionVertexInterpolator)
    wire(node(m, u.MaterialExpressionPreSkinnedPosition), pos, 'VS')
    nor = node(m, u.MaterialExpressionVertexInterpolator)
    wire(node(m, u.MaterialExpressionPreSkinnedNormal), nor, 'VS')
    g = custom(m, 'WS_Grain', {'P': pos, 'N': nor, 'Tex': grain, 'TileCm': s['GrainTileCm']}, 4)
    mask_rgba = (msk, 'RGBA')
    wear = custom(m, 'WS_Wear', {'Mask': mask_rgba, 'Grain': g, 'EdgeWear': s['EdgeWear'],
                                 'EdgeBreakup': s['EdgeBreakup'], 'EdgeContrast': s['EdgeContrast'],
                                 'ScratchAmount': s['ScratchAmount']}, 4)
    cr = custom(m, 'WS_ColorRough', {
        'Src': (src, 'RGB'), 'SrcR': (srough, 'R'), 'Mask': mask_rgba, 'Grain': g, 'Wear': wear,
        'Finish': (v['FinishColor'], 'RGB'), 'SrcW': s['SourceColorWeight'], 'Rough': s['Roughness'],
        'SrcRW': s['SourceRoughnessWeight'], 'Pivot': s['SourceRoughnessPivot'],
        'GrainR': s['GrainRoughness'], 'MottleR': s['MottleRoughness'], 'MottleC': s['MottleColor'],
        'Stipple': s['Stipple'], 'EdgeColor': (v['EdgeColor'], 'RGB'), 'EdgeRough': s['EdgeRoughness'],
        'EdgeHL': s['EdgeHighlight'], 'CavDark': s['CavityDarken'], 'CavRough': s['CavityRoughness'],
        'Handling': s['HandlingPolish']}, 4)
    ma = custom(m, 'WS_MetalAO', {'Metal': s['Metallic'], 'EdgeMetal': s['EdgeMetallic'], 'Wear': wear,
                                  'Mask': mask_rgba, 'AOStrength': s['AOStrength']}, 4)
    uv = node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
    beads = custom(m, 'WS_Beads', {'UV': uv, 'Wet': s['WeaponWetness'], 'Scale': s['BeadScale']}, 4)
    wet = custom(m, 'WS_Wet', {'CR': cr, 'Data': beads}, 4)
    wn = custom(m, 'WS_WetNormal', {'Base': (nrm, 'RGB'), 'Data': beads}, 3)
    output(mask(m, wet, 'rgb'), 'BASE_COLOR')
    output(mask(m, wet, 'a'), 'ROUGHNESS')
    output(mask(m, ma, 'r'), 'METALLIC')
    output(mask(m, ma, 'g'), 'AMBIENT_OCCLUSION')
    output(s['Specular'], 'SPECULAR')
    output(wn, 'NORMAL')


def refresh(m):
    """Existing master: update code and defaults in place (graph topology is versioned)."""
    for n in L.get_material_expressions(m):
        if isinstance(n, u.MaterialExpressionCustom):
            name = str(n.get_editor_property('description'))
            if name in CODE:
                n.set_editor_property('code', CODE[name])
        elif isinstance(n, u.MaterialExpressionScalarParameter):
            name = str(n.get_editor_property('parameter_name'))
            if name in SCALARS:
                n.set_editor_property('default_value', SCALARS[name])
        elif isinstance(n, u.MaterialExpressionVectorParameter):
            name = str(n.get_editor_property('parameter_name'))
            if name in VECTORS:
                n.set_editor_property('default_value', u.LinearColor(*VECTORS[name], 1))


if E.does_asset_exist(MASTER):
    master = u.load_asset(MASTER)
    if str(E.get_metadata_tag(master, 'WeaponSurfaceGraph')) != card['master_defaults']['graph']:
        raise RuntimeError('Master graph revision changed; create a new master asset name instead of rebuilding')
    refresh(master)
else:
    master = A.create_asset('M_WeaponSurface', ROOT + '/Master', u.Material, u.MaterialFactoryNew())
    build(master)
    E.set_metadata_tag(master, 'WeaponSurfaceGraph', card['master_defaults']['graph'])
E.set_metadata_tag(master, 'WeaponSurfaceVersion', VERSION)
E.set_metadata_tag(master, 'WeaponSurfaceCard', 'Docs/Weapons/weapon-surface-standard-20260930.md')
errors = [str(x) for x in L.recompile_material(master)]
if errors:
    receipt['compile_errors'][MASTER] = errors
    record()
    raise RuntimeError('Master compile errors: ' + str(errors[:4]))
save(master)
receipt['master'] = master.get_path_name()
receipt['master_expressions'] = len(L.get_material_expressions(master))
record()

for name, preset in card['presets'].items():
    path = ROOT + '/Presets/MI_WS_' + name
    mi = u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(
        'MI_WS_' + name, ROOT + '/Presets', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', master)
    for key, value in preset.get('scalars', {}).items():
        L.set_material_instance_scalar_parameter_value(mi, key, value)
    for key, value in preset.get('vectors', {}).items():
        L.set_material_instance_vector_parameter_value(mi, key, u.LinearColor(*value, 1))
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceVersion', VERSION)
    E.set_metadata_tag(mi, 'WeaponSurfaceSource', preset.get('source', ''))
    save(mi)
    receipt['presets'][name] = {'path': mi.get_path_name(),
                                'scalars': [str(p.parameter_info.name) for p in mi.get_editor_property('scalar_parameter_values')],
                                'vectors': [str(p.parameter_info.name) for p in mi.get_editor_property('vector_parameter_values')]}
    record()

receipt['complete'] = True
record()
print('WEAPON_SURFACE_MASTER_SAVED', json.dumps({'master': receipt['master'], 'expressions': receipt['master_expressions'],
      'presets': sorted(receipt['presets'])}), flush=True)
