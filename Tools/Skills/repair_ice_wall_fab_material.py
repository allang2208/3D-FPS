"""Correct the known color/normal sampler mismatch without reimporting ice meshes."""
import json
from pathlib import Path
import unreal as u

eal = u.EditorAssetLibrary
lib = u.MaterialEditingLibrary
root = Path(u.Paths.project_dir())
dest = '/Game/Skills/IceWall/FabIceV3'
source = '/Game/Ice/Textures/T_Ice6_basecolor'
path = dest + '/T_IceSurfaceColor'
texture = u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(source, path)
texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
texture.set_editor_property('srgb', True)
if not eal.save_loaded_asset(texture, False):
    raise RuntimeError('Ice color texture save failed')

material = u.load_asset(dest + '/M_IceWall')
corrected = 0
for sample in lib.get_material_expressions(material):
    if not isinstance(sample, u.MaterialExpressionTextureSample):
        continue
    original = sample.get_editor_property('texture')
    if original and (original.get_path_name().startswith(source + '.') or original == texture):
        sample.set_editor_property('texture', texture)
        sample.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        corrected += 1
errors = [str(e) for e in lib.recompile_material(material)]
if errors:
    raise RuntimeError('Ice wall material compile failed: ' + '\n'.join(errors))
if not eal.save_loaded_asset(material, False):
    raise RuntimeError('Ice wall material save failed')
receipt = {'material': material.get_path_name(), 'color_texture': texture.get_path_name(),
           'color_source': source, 'compression': 'TC_DEFAULT', 'srgb': True,
           'sampler_type': 'Color', 'corrected_samples': corrected, 'compile_errors': errors,
           'saved_assets': [texture.get_path_name(), material.get_path_name()],
           'gameplay_tested': False, 'meshes_reimported': False}
out = root / 'Saved/IceWallFabV3/sampler-repair.json'
out.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ICE_WALL_MATERIAL_REPAIRED ' + json.dumps(receipt))
