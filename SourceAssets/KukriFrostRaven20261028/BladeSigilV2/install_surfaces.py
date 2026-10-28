"""Save the fine frost blade sigil and its six existing surface material pairs only."""
import hashlib
import json
from pathlib import Path

import unreal as u

P = Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriFrostRaven20261028/BladeSigilV2/install_surfaces.py').resolve().parent
PRODUCTION = P.parent / 'ProductionV1'
BASE = '/Game/Weapons/Kukri20261020/FrostRaven20261028'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End PIE before saving the fine blade rune materials')
layouts = json.loads((P / 'projection-layouts.json').read_text('utf-8'))
targets = {BASE + '/Textures/T_FrostRavenGlyph'}
for row in layouts:
    targets.update({BASE + '/Materials/M_FrostRaven_' + row['kind'], BASE + '/Materials/MI_FrostRaven_' + row['kind']})
dirty = {str(package.get_path_name()) for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):
    raise RuntimeError('Preserve unsaved frost blade rune assets')
source = P / 'Art/RavenSigilFine.png'
receipt = {'complete': False, 'material_compiled': False, 'saved_assets': [], 'runtime_tested': False,
           'source_image': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'projection_layouts': layouts, 'preserved': ['Blade PBR and normals', 'HUD', 'Icon', 'Gameplay stats and networking']}


def record():
    (P / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


# Resolve the owned graph nodes before replacing their common texture.
graphs = []
for row in layouts:
    material = u.load_asset(BASE + '/Materials/M_FrostRaven_' + row['kind'])
    instance = u.load_asset(BASE + '/Materials/MI_FrostRaven_' + row['kind'])
    if not material or not instance:
        raise RuntimeError('Missing frost blade surface: ' + row['kind'])
    nodes = L.get_material_expressions(material)
    projection = next(node for node in nodes if isinstance(node, u.MaterialExpressionCustom)
                      and str(node.get_editor_property('description')) == 'BerserkerLocalProjection')
    texture_node = next(node for node in nodes if isinstance(node, u.MaterialExpressionTextureObjectParameter)
                        and str(node.get_editor_property('parameter_name')) == 'BerserkerGlyph')
    emission = next(node for node in nodes if isinstance(node, u.MaterialExpressionCustom)
                    and 'Mask*float3(' in str(node.get_editor_property('code'))
                    and 'Time' in str(node.get_editor_property('code')))
    graphs.append((row, material, instance, nodes, projection, texture_node, emission))
record()
task = u.AssetImportTask()
task.filename, task.destination_path, task.destination_name = str(source), BASE + '/Textures', 'T_FrostRavenGlyph'
task.automated, task.replace_existing, task.save = True, True, False
A.import_asset_tasks([task])
glyph = u.load_asset(BASE + '/Textures/T_FrostRavenGlyph')
if not glyph:
    raise RuntimeError('Fine rune texture import failed')
glyph.set_editor_properties({'srgb': False, 'never_stream': True, 'max_texture_size': 2048,
    'compression_settings': u.TextureCompressionSettings.TC_BC7,
    'lod_group': u.TextureGroup.TEXTUREGROUP_UI, 'mip_gen_settings': u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    'address_x': u.TextureAddress.TA_CLAMP, 'address_y': u.TextureAddress.TA_CLAMP})
E.set_metadata_tag(glyph, 'SourceAuthoring', 'KukriFrostRaven20261028/BladeSigilV2')
save(glyph)
materials = []
for row, material, instance, nodes, projection, texture_node, emission in graphs:
    center = u.LinearColor(*row['center_cm'], row['angle_radians'], 1)
    extent = u.LinearColor(row['width_cm'], row['height_cm'], 0, 1)
    texture_node.set_editor_properties({'texture': glyph, 'sampler_type': u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR})
    projection.set_editor_property('code', (PRODUCTION / 'RuneProjection.hlsl').read_text('utf-8'))
    emission.set_editor_property('code', (P / 'FineRuneGlow.hlsl').read_text('utf-8'))
    for node in nodes:
        if isinstance(node, u.MaterialExpressionVectorParameter):
            key = str(node.get_editor_property('parameter_name'))
            if key == 'BerserkerCenter':
                node.set_editor_property('default_value', center)
            elif key == 'BerserkerExtent':
                node.set_editor_property('default_value', extent)
    L.set_material_instance_texture_parameter_value(instance, 'BerserkerGlyph', glyph)
    L.set_material_instance_vector_parameter_value(instance, 'BerserkerCenter', center)
    L.set_material_instance_vector_parameter_value(instance, 'BerserkerExtent', extent)
    L.set_material_instance_vector_parameter_value(instance, 'RuneTint', u.LinearColor(.09, .27, .43, 1))
    L.update_material_instance(instance)
    E.set_metadata_tag(material, 'SourceAuthoring', 'KukriFrostRaven20261028/BladeSigilV2')
    E.set_metadata_tag(material, 'RuneProjection', 'FineSigil_LocalCentimeters_AspectPreserved')
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError(material.get_path_name() + ': ' + str(errors))
    materials.extend([material, instance])
if not u.PoisonMaggotMonster.compile_material_assets(materials):
    raise RuntimeError('Fine blade rune material compilation failed')
receipt['material_compiled'] = True
record()
for material in materials:
    save(material)
receipt['complete'] = True
record()
u.log('FROST_RAVEN_FINE_BLADE_SIGIL_SAVED ' + str(len(receipt['saved_assets'])))
