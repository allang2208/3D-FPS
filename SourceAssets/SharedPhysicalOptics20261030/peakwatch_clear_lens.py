"""Create the bow-only post-motion-blur lens using the shared reticle graph."""
from pathlib import Path
import runpy
import unreal as u

def save_peakwatch_lens():
    folder = '/Game/Weapons/SharedPhysicalOptics20261030/'
    path = folder + 'M_PeakwatchVariableLens'
    lib = u.EditorAssetLibrary
    if any(p.get_name() == path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Peakwatch lens has unsaved edits')
    if lib.does_asset_exist(path):
        lens = u.load_asset(path)
    else:
        source = folder + 'M_PeakwatchClearLens'
        lens = lib.duplicate_asset(source if lib.does_asset_exist(source) else folder + 'M_PhysicalScopeLens', path)
    shader = Path(__file__).with_name('lens.hlsl')
    glass = runpy.run_path(str(shader.with_name('late_glass.py')))
    glass['set_picture_shader'](lens, shader.read_text(encoding='utf-8'))
    glass['configure_late_glass'](lens)
    errors = u.MaterialEditingLibrary.recompile_material(lens)
    if errors:
        raise RuntimeError(str(errors))
    if not lib.save_loaded_asset(lens, False):
        raise RuntimeError('Failed to save ' + path)
    u.log('PEAKWATCH_CLEAR_LENS_SAVED ' + path)

if __name__ == '__main__':
    save_peakwatch_lens()
