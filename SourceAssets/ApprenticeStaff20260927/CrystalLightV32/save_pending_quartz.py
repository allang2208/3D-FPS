"""Finish saving the one material edited by this batch before PIE blocked save."""
import unreal as u
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE has not stopped yet.')
path = '/Game/Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
material = u.load_asset(path)
errors = u.MaterialEditingLibrary.recompile_material(material)
if errors:
    raise RuntimeError(str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('Cannot save pending quartz material.')
print('Saved the pending exposure-aware quartz material: ' + path)
