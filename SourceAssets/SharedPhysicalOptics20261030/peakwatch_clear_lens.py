"""Create the bow-only post-motion-blur lens using the shared reticle graph."""
from pathlib import Path
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
    picture, = (node for node in u.MaterialEditingLibrary.get_material_expressions(lens)
                if isinstance(node, u.MaterialExpressionCustom)
                and 'CaptureTanHalfFOV' in node.get_editor_property('code')
                and 'BowDrawState' in node.get_editor_property('code'))
    shader = Path(__file__).with_name('lens.hlsl')
    picture.set_editor_property('code', shader.read_text(encoding='utf-8'))
    lens.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_MOTION_BLUR)
    errors = u.MaterialEditingLibrary.recompile_material(lens)
    if errors:
        raise RuntimeError(str(errors))
    if not lib.save_loaded_asset(lens, False):
        raise RuntimeError('Failed to save ' + path)
    u.log('PEAKWATCH_CLEAR_LENS_SAVED ' + path)

if __name__ == '__main__':
    save_peakwatch_lens()
