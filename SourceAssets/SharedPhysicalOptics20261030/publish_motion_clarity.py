"""Update the four installed glass materials without rebuilding meshes or textures."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import unreal as u

source = Path(__file__).resolve().parent
glass = runpy.run_path(str(source/'late_glass.py'))
shader = (source/'lens.hlsl').read_text(encoding='utf-8')
shared = '/Game/Weapons/SharedPhysicalOptics20261030/'
bow = '/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/'
paths = (shared+'M_PhysicalScopeLens', shared+'M_PeakwatchVariableLens',
         bow+'M_BowOptic_Glass4x', bow+'M_BowOptic_Glass2x')
bow_author=runpy.run_path(str(source.parent/'BowSingleLensOptics20260927/ReticleReadability/materials.py'))
library = u.MaterialEditingLibrary
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):
    raise RuntimeError('Unsaved lens edits: ' + str(dirty.intersection(paths)))

def pixel_instructions(material):
    return library.get_statistics(material).num_pixel_shader_instructions

records = []
for path in paths:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing ' + path)
    before = pixel_instructions(material)
    previous_pass = str(material.get_editor_property('translucency_pass'))
    if path.startswith(shared):
        glass['set_picture_shader'](material, shader)
    else:
        bow_author['build_lens'](material,4 if path.endswith('4x') else 2)
    glass['configure_late_glass'](material)
    errors = library.recompile_material(material)
    if errors:
        raise RuntimeError(path + ' ' + str(errors))
    after = pixel_instructions(material)
    if after <= 0:
        raise RuntimeError('Missing compiled shader for ' + path)
    records.append((material, {'path': path, 'pass_before': previous_pass,
                    'pass_after': str(material.get_editor_property('translucency_pass')),
                    'pixel_instructions_before': before, 'pixel_instructions_after': after}))

for material, record in records:
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Failed to save ' + record['path'])
    package = Path(u.Paths.project_content_dir())/(record['path'][6:]+'.uasset')
    record['sha256'] = hashlib.sha256(package.read_bytes()).hexdigest()
    u.log('SCOPE_CLARITY_SAVED ' + json.dumps(record))
if receipt := os.environ.get('FPS_OPTICS_RECEIPT'):
    Path(receipt).write_text(json.dumps({'materials': [r for _, r in records],
        'in_game_frame_times_measured': False}, indent=2), encoding='utf-8')
