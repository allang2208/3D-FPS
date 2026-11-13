"""Create the bow-only post-motion-blur lens using the shared reticle graph."""
import unreal as u

def save_peakwatch_lens():
    folder = '/Game/Weapons/SharedPhysicalOptics20261030/'
    path = folder + 'M_PeakwatchClearLens'
    lib = u.EditorAssetLibrary
    if any(p.get_name() == path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Peakwatch lens has unsaved edits')
    if lib.does_asset_exist(path):
        lens = u.load_asset(path)
    else:
        lens = lib.duplicate_asset(folder + 'M_PhysicalScopeLens', path)
    lens.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_MOTION_BLUR)
    errors = u.MaterialEditingLibrary.recompile_material(lens)
    if errors:
        raise RuntimeError(str(errors))
    if not lib.save_loaded_asset(lens, False):
        raise RuntimeError('Failed to save ' + path)
    u.log('PEAKWATCH_CLEAR_LENS_SAVED ' + path)

if __name__ == '__main__':
    save_peakwatch_lens()
