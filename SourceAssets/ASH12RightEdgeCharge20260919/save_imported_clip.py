"""Save the already imported animation package without changing PIE state."""
import json
from pathlib import Path
import unreal as u

SOURCE = Path(__file__).resolve().parent
clip = u.load_asset('/Game/Weapons/ASH12/ReloadReference20260919/A_ASH12_reload_empty')
imported_source = Path(clip.get_editor_property('asset_import_data').get_first_filename()).resolve()
if imported_source != (SOURCE / 'A_ASH12_reload_empty.fbx').resolve():
    raise RuntimeError('The editor no longer holds the right-edge revision; import it again before saving.')
if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outer()], False):
    raise RuntimeError('Could not save the imported ASH-12 animation package.')
receipt = {'revision': 'right-edge-reach-pull-return', 'asset': clip.get_path_name(),
           'source_fbx': clip.get_editor_property('asset_import_data').get_first_filename(),
           'duration': clip.get_play_length(),
           'previous_asset_copy': str(SOURCE / 'Before/A_ASH12_reload_empty.uasset'),
           'visual_test': 'Not run; user will assess in game.'}
(SOURCE / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ASH12_RIGHT_EDGE_SAVE_COMPLETE ' + json.dumps(receipt))
