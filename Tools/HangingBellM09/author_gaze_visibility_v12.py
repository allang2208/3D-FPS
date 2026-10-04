"""Increase existing charge/telegraph readability and save the live assets."""
import json, unreal as u
from pathlib import Path
PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/HangingBellM09Meshy20261003/GazeVisibilityV12'
RECORDS=ROOT/'Records'
RECORDS.mkdir(parents=True,exist_ok=True)
PATH='/Game/Monsters/HangingBellM09/V08/Materials/M_M09_GazeBeam_V08'
if not globals().get('M09_COMMANDLET',False):
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('End existing PIE before saving gaze materials')
if PATH in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve unsaved gaze beam material')
M09_CHARGE_OUTPUT='GazeVisibilityV12'
M09_UPDATE_EXISTING=True
exec(compile((PROJECT/'Tools/HangingBellM09/author_gaze_charge_v10.py').read_text(encoding='utf-8-sig'),
    'author_gaze_charge_v10.py','exec'))
receipt=json.loads((RECORDS/'import_saved.json').read_text(encoding='utf8'))
receipt.update(version='GazeVisibilityV12',complete=False)
(RECORDS/'import_saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
# The reused producer sets its own OUT/DEST; PATH remains this one beam asset.
mat=u.load_asset(PATH)
custom=next(x for x in u.MaterialEditingLibrary.get_material_expressions(mat)
    if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('description'))=='M09 original GazeBeam')
custom.set_editor_property('code',(PROJECT/'SourceAssets/HangingBellM09Meshy20261003/GazeV08/Authoring/GazeBeam.hlsl').read_text(encoding='utf8'))
errors=u.MaterialEditingLibrary.recompile_material(mat)
if errors:
    raise RuntimeError('Beam material compilation failed '+str(errors))
u.EditorAssetLibrary.set_metadata_tag(mat,'M09VisualRevision','GazeVisibilityV12')
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):
    raise RuntimeError('Beam material save failed')
receipt=json.loads((RECORDS/'import_saved.json').read_text(encoding='utf8'))
receipt['saved'].append(mat.get_path_name())
receipt.update(version='GazeVisibilityV12',complete=True,native_build_required=False,
    warning_opacity_multiplier=3.2,particle_emissive_multiplier=1.4,
    timing_changed=False,damage_changed=False,range_changed=False,preview_rendered=False,tested=False)
(RECORDS/'import_saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('M09_GAZE_VISIBILITY_V12_SAVED assets='+str(len(receipt['saved'])),flush=True)
