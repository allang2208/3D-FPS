"""Save new private finish assets and bind only TangDao's runtime recipe."""
import copy
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
S = P.parent
ROOT = S.parents[1]
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('TangDao surface import requires the FPSGAME project.')
D = '/Game/Weapons/TangDao20261002/SurfaceV2'
A = u.AssetToolsHelpers.get_asset_tools()
L = u.EditorAssetLibrary
E = u.MaterialEditingLibrary
receipt = {'revision': 'TangDao_RegionalSurfaceV2_20261002', 'assets': [], 'complete': False, 'tested': False}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('TangDao surface save failed: ' + asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return asset

def node(mat, cls, **props):
    n = E.create_material_expression(mat, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n

def link(a, output, b, pin):
    if not E.connect_material_expressions(a, output, b, pin):
        raise RuntimeError('TangDao material input failed: ' + pin)

def output(a, pin, prop):
    if not E.connect_material_property(a, pin, prop):
        raise RuntimeError('TangDao material output failed: ' + str(prop))

def material(name):
    path = D + '/Materials/' + name
    existing = u.load_asset(path)
    if existing:
        return existing, False
    return A.create_asset(name, D + '/Materials', u.Material, u.MaterialFactoryNew()), True

def surface(mat, inputs):
    mat.set_editor_property('use_material_attributes', False)
    mat.set_editor_property('used_with_nanite', True)
    mat.set_editor_property('used_with_skeletal_mesh', False)
    slab = node(mat, u.MaterialExpressionSubstrateShadingModels,
                shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for n, pin, prop, target in inputs:
        if target != 'AmbientOcclusion':
            link(n, pin, slab, 'Emissive Color' if target == 'EmissiveColor' else target)
        output(n, pin, prop)
    output(slab, '', u.MaterialProperty.MP_FRONT_MATERIAL)
    E.layout_material_expressions(mat)
    errors = list(E.recompile_material(mat) or [])
    if errors:
        raise RuntimeError('TangDao material build failed: ' + str(errors))
    L.set_metadata_tag(mat, 'TangDaoSurfaceRevision', receipt['revision'])
    return save(mat)

textures = {}
for key in ['BaseColor', 'ORM', 'Normal']:
    name = 'T_TangDao_' + key
    texture = u.load_asset(D + '/Textures/' + name)
    if not texture:
        task = u.AssetImportTask()
        task.filename = str(P / 'Textures' / ('TangDao_' + key + '.png'))
        task.destination_path = D + '/Textures'
        task.destination_name = name
        task.automated = True
        task.replace_existing = False
        task.save = False
        A.import_asset_tasks([task])
        texture = u.load_asset(D + '/Textures/' + name)
        if not texture:
            raise RuntimeError('TangDao refined texture import failed: ' + key)
    texture.set_editor_property('srgb', key == 'BaseColor')
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if key == 'Normal' else u.TextureCompressionSettings.TC_MASKS if key == 'ORM' else u.TextureCompressionSettings.TC_BC7)
    texture.set_editor_property('never_stream', False)
    if key == 'Normal':
        texture.set_editor_property('flip_green_channel', True)
    textures[key] = save(texture)

mat, new = material('M_TangDaoSurface')
if new:
    base = node(mat, u.MaterialExpressionTextureSample, texture=textures['BaseColor'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm = node(mat, u.MaterialExpressionTextureSample, texture=textures['ORM'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal = node(mat, u.MaterialExpressionTextureSample, texture=textures['Normal'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    surface(mat, [(base, 'RGB', u.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
                  (normal, 'RGB', u.MaterialProperty.MP_NORMAL, 'Normal'),
                  (orm, 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION, 'AmbientOcclusion'),
                  (orm, 'G', u.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
                  (orm, 'B', u.MaterialProperty.MP_METALLIC, 'Metallic')])
else:
    save(mat)

mount, new = material('M_TangDaoMountMetal')
if new:
    base = node(mount, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.55, .35, .14, 1))
    rough = node(mount, u.MaterialExpressionConstant, r=.32)
    metal = node(mount, u.MaterialExpressionConstant, r=1.)
    surface(mount, [(base, '', u.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
                    (rough, '', u.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
                    (metal, '', u.MaterialProperty.MP_METALLIC, 'Metallic')])
else:
    save(mount)

foreground = {}
def whirlwind(source):
    path = source.get_path_name().split('.')[0] + '_Whirlwind'
    target = u.load_asset(path)
    if not target:
        target = L.duplicate_asset(source.get_path_name(), path)
        temporal = node(target, u.MaterialExpressionTemporalResponsivenessOutput)
        one = node(target, u.MaterialExpressionConstant, r=1.)
        link(one, '', temporal, '')
        E.recompile_material(target)
    save(target)
    foreground[source.get_path_name()] = target.get_path_name()

for m in [mat, mount]:
    whirlwind(m)

# Rune-origin pommels retain their own normals, texture identity and emission.
sources = json.loads((ROOT / 'SourceAssets/RuneSwordPommels20260920/import_receipt.json').read_text(encoding='utf-8'))
parent, new = material('M_TangDaoPommelFinish')
if new:
    samples = {}
    for key, path in sources[0]['textures'].items():
        sampler = u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key == 'Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key in ['BaseColor', 'Emissive'] else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        samples[key] = node(parent, u.MaterialExpressionTextureSampleParameter2D,
                            parameter_name=key, texture=u.load_asset(path), sampler_type=sampler)
    mask = node(parent, u.MaterialExpressionSmoothStep, const_min=.10, const_max=.38)
    link(samples['Metallic'], 'R', mask, 'Value')
    color = node(parent, u.MaterialExpressionLinearInterpolate)
    tint = node(parent, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.55, .35, .14, 1))
    identity = node(parent, u.MaterialExpressionLinearInterpolate, const_alpha=.52)
    link(samples['BaseColor'], 'RGB', identity, 'A')
    link(tint, '', identity, 'B')
    link(samples['BaseColor'], 'RGB', color, 'A')
    link(identity, '', color, 'B')
    link(mask, '', color, 'Alpha')
    remap = node(parent, u.MaterialExpressionMultiply, const_b=.08)
    link(samples['Roughness'], 'R', remap, 'A')
    add = node(parent, u.MaterialExpressionAdd, const_b=.288)
    link(remap, '', add, 'A')
    rough = node(parent, u.MaterialExpressionLinearInterpolate)
    link(samples['Roughness'], 'R', rough, 'A')
    link(add, '', rough, 'B')
    link(mask, '', rough, 'Alpha')
    emission = node(parent, u.MaterialExpressionMultiply, const_b=3.)
    link(samples['Emissive'], 'RGB', emission, 'A')
    surface(parent, [(color, '', u.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
                     (rough, '', u.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
                     (mask, '', u.MaterialProperty.MP_METALLIC, 'Metallic'),
                     (samples['Normal'], 'RGB', u.MaterialProperty.MP_NORMAL, 'Normal'),
                     (emission, '', u.MaterialProperty.MP_EMISSIVE_COLOR, 'EmissiveColor')])
else:
    save(parent)

finish = {}
ids = {'meteor': 'ballast_hardened', 'jade_core': 'ballast_rune', 'swift': 'ballast_magic_orb'}
for source in sources:
    name = 'MI_TangDaoPommel_' + source['id']
    mi = u.load_asset(D + '/Materials/' + name) or A.create_asset(name, D + '/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    E.set_material_instance_parent(mi, parent)
    for key, path in source['textures'].items():
        E.set_material_instance_texture_parameter_value(mi, key, u.load_asset(path))
    E.update_material_instance(mi)
    save(mi)
    mesh = u.load_asset(source['asset'])
    finish[ids[source['id']]] = {'materials': {str(s.material_slot_name): mi.get_path_name() for s in mesh.static_materials if '_Opaque' in str(s.material_slot_name)}}

# Frost-origin bronze-only slots get private copies; crystals and silver inlays
# continue using their original slots. The old complex normal/emission wiring is retained.
library_path = ROOT / 'Content/ColdSteelData/shared-sword-pommels.json'
library = json.loads(library_path.read_text(encoding='utf-8-sig'))
clones = {}
for key in ['pommel_hardened', 'pommel_runic', 'pommel_mana_orb']:
    mesh = u.load_asset(library['options'][key]['mesh'])
    overrides = {}
    for slot in mesh.static_materials:
        label = str(slot.material_slot_name)
        source = slot.material_interface
        if not source or not any(s in label for s in ['Bronze', 'Collar', 'InlayBorder']):
            continue
        path = source.get_path_name()
        if path not in clones:
            name = 'M_TangDao_' + key + '_' + label.split('.')[0]
            dest = D + '/Materials/' + name
            cloned = u.load_asset(dest)
            if not cloned:
                cloned = L.duplicate_asset(path, dest)
                inputs = []
                for prop, target in [(u.MaterialProperty.MP_NORMAL, 'Normal'), (u.MaterialProperty.MP_EMISSIVE_COLOR, 'EmissiveColor'), (u.MaterialProperty.MP_AMBIENT_OCCLUSION, 'AmbientOcclusion')]:
                    n = E.get_material_property_input_node(cloned, prop)
                    if n:
                        inputs.append((n, E.get_material_property_input_node_output_name(cloned, prop), prop, target))
                old_base = E.get_material_property_input_node(cloned, u.MaterialProperty.MP_BASE_COLOR)
                if old_base:
                    base = node(cloned, u.MaterialExpressionLinearInterpolate, const_b=0., const_alpha=.45)
                    tint = node(cloned, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.55, .35, .14, 1))
                    link(old_base, E.get_material_property_input_node_output_name(cloned, u.MaterialProperty.MP_BASE_COLOR), base, 'A')
                    link(tint, '', base, 'B')
                else:
                    base = node(cloned, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.55, .35, .14, 1))
                rough = node(cloned, u.MaterialExpressionConstant, r=.32 if 'InlayBorder' not in label else .36)
                metal = node(cloned, u.MaterialExpressionConstant, r=1.)
                surface(cloned, inputs + [(base, '', u.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
                                         (rough, '', u.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
                                         (metal, '', u.MaterialProperty.MP_METALLIC, 'Metallic')])
            else:
                save(cloned)
            clones[path] = cloned.get_path_name()
            whirlwind(cloned)
        overrides[label] = clones[path]
    finish[key] = {'materials': overrides}

data = json.loads((S / 'exports.json').read_text(encoding='utf-8'))
bindings = {'slots': {}, 'adapters': {}, 'pommel_finish': finish}
for row in data['parts']:
    mesh = u.load_asset(data['ue_root'] + '/Meshes/' + row['mesh'])
    overrides = {str(slot.material_slot_name): mat.get_path_name() for slot in mesh.static_materials}
    bindings['slots'].setdefault(row['slot'], {})[row['id']] = overrides
for key, row in data['adapters'].items():
    mesh = u.load_asset(data['ue_root'] + '/Meshes/' + row['mesh'])
    bindings['adapters'][key] = {str(slot.material_slot_name): mount.get_path_name() for slot in mesh.static_materials}

# The independently authored blades use their own atlases and native rune graphs.
# Preserve both bindings when refreshing the base atlas.
import runpy
for relative in ['YanlingBlade20261002/catalog_extension.py', 'TengyunBlade20261002/catalog_extension.py',
                 'YanlingPommel20261002/catalog_extension.py', 'XuanCloudGuard20261002/catalog_extension.py',
                 'PhoenixFeatherGuard20261002/catalog_extension.py',
                 'TigerPommel20261002/catalog_extension.py',
                 'CloudRune20261002/catalog_extension.py']:
    extension_path = S / relative
    if extension_path.exists():
        extension = runpy.run_path(str(extension_path), run_name='tang_dao_blade_extension')
        if extension['installed']():
            extension['add_bindings'](bindings)

# Keep a fully assembled world fallback with the same material, without touching
# the currently loaded original mesh package or its authored geometry.
world_path = D + '/Meshes/SM_TangDao'
world = u.load_asset(world_path) or L.duplicate_asset(data['ue_root'] + '/Meshes/' + data['world_mesh'], world_path)
for index in range(len(world.static_materials)):
    world.set_material(index, mat)
save(world)
bindings['world_mesh'] = world.get_path_name()
bindings['revision'] = receipt['revision']
(P / 'bindings.json').write_text(json.dumps(bindings, indent=2) + '\n', encoding='utf-8')

backup = P / 'Before'
backup.mkdir(exist_ok=True)
def write_json(path, value):
    if not (backup / path.name).exists():
        shutil.copy2(path, backup / path.name)
    temp = path.with_suffix(path.suffix + '.tangsurface.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

# Re-read shared JSON immediately before merging only this new finish key.
library = json.loads(library_path.read_text(encoding='utf-8-sig'))
library['finishes']['tang_dao_surface_v2'] = finish
write_json(library_path, library)
catalog_path = ROOT / 'Content/ColdSteelData/tang-dao-modules.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8-sig'))
for slot, choices in bindings['slots'].items():
    for option, materials in choices.items():
        catalog['slots'][slot][option]['materials'] = materials
for key, materials in bindings['adapters'].items():
    catalog['pommel_profile']['interfaces'][key]['adapter']['materials'] = materials
catalog['pommel_profile']['finish'] = 'tang_dao_surface_v2'
catalog['surface_revision'] = receipt['revision']
write_json(catalog_path, catalog)
items_path = ROOT / 'Content/ColdSteelData/items.json'
items = json.loads(items_path.read_text(encoding='utf-8-sig'))
items['ue_tang_dao']['world_mesh'] = world.get_path_name()
write_json(items_path, items)
whirlwind_path = ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping = json.loads(whirlwind_path.read_text(encoding='utf-8-sig'))
mapping.update(foreground)
write_json(whirlwind_path, mapping)
receipt.update(complete=True, bindings=bindings, foreground_materials=foreground, geometry_changed=False,
               original_normal_preserved=True, holding_direction='Existing bone_mount preserved')
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('TANGDAO_SURFACE_V2_SAVED assets=' + str(len(receipt['assets'])) + '; original_and_modifications_bound=True')

# Keep the blade-only rune emission binding on subsequent surface imports.
import runpy
runpy.run_path(str(P / 'RuneRepairFollowup20261002/import_blade_runes.py'), run_name='__main__')
