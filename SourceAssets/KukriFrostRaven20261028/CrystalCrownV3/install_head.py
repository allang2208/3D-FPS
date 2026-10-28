"""Save the unified crystal crown texture and its existing frost HUD material."""
import hashlib
import json
from pathlib import Path

import unreal as u

P = Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriFrostRaven20261028/CrystalCrownV3/install_head.py').resolve().parent
BASE = '/Game/Weapons/Kukri20261020/FrostRaven20261028'
HUD, TEXTURE = BASE + '/M_FrostRavenEnergyHud', BASE + '/Textures/T_FrostRavenCrown'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End PIE before importing and saving the crystal HUD assets')
dirty = {str(package.get_path_name()) for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection({HUD, TEXTURE}):
    raise RuntimeError('Preserve unsaved frost crown/HUD packages')
hud = u.load_asset(HUD)
if not hud:
    raise RuntimeError('Missing active frost HUD material')
nodes = L.get_material_expressions(hud)
custom = next(node for node in nodes if isinstance(node, u.MaterialExpressionCustom))
head = next(node for node in nodes if isinstance(node, u.MaterialExpressionTextureObjectParameter)
            and str(node.get_editor_property('parameter_name')) == 'WolfHeadTex')
code = (P / 'FrostRavenCrystalHud.hlsl').read_text('utf-8')
source = P / 'Art/FrostRavenCrystal.png'
receipt = {'complete': False, 'material_compiled': False, 'saved_assets': [], 'runtime_tested': False,
           'source_image': str(source), 'source_image_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'hlsl_sha256': hashlib.sha256(code.encode()).hexdigest(),
           'layout': json.loads((P / 'crown-layout.json').read_text('utf-8')),
           'design': 'Unified sapphire eagle, integral crystal throat; original vessel and right-side HUD retained'}


def record():
    (P / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


record()
task = u.AssetImportTask()
task.filename, task.destination_path, task.destination_name = str(source), BASE + '/Textures', 'T_FrostRavenCrown'
task.automated, task.replace_existing, task.save = True, True, False
A.import_asset_tasks([task])
texture = u.load_asset(TEXTURE)
if not texture:
    raise RuntimeError('Crystal crown texture import failed')
texture.set_editor_properties({'srgb': False, 'never_stream': True, 'max_texture_size': 2048,
    'compression_settings': u.TextureCompressionSettings.TC_BC7,
    'lod_group': u.TextureGroup.TEXTUREGROUP_UI, 'mip_gen_settings': u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    'address_x': u.TextureAddress.TA_CLAMP, 'address_y': u.TextureAddress.TA_CLAMP})
E.set_metadata_tag(texture, 'SourceAuthoring', 'KukriFrostRaven20261028/CrystalCrownV3')
save(texture)
head.set_editor_properties({'texture': texture, 'sampler_type': u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR})
custom.set_editor_properties({'code': code, 'description': 'FrostRavenUnifiedCrystalCrownV3'})
E.set_metadata_tag(hud, 'SourceAuthoring', 'KukriFrostRaven20261028/CrystalCrownV3')
E.set_metadata_tag(hud, 'EnergyBarDesign', 'OriginalVessel_UnifiedSapphireEagle')
E.set_metadata_tag(hud, 'CrownJoin', 'IntegralCrystalRoot_WidthMatchedV1')
errors = L.recompile_material(hud)
if errors:
    raise RuntimeError('HUD material compilation failed: ' + str(errors))
if not u.PoisonMaggotMonster.compile_material_assets([hud]):
    raise RuntimeError('HUD material compilation failed')
receipt['material_compiled'] = True
record()
save(hud)
receipt['complete'] = True
record()
u.log('FROST_RAVEN_UNIFIED_CRYSTAL_CROWN_SAVED')
