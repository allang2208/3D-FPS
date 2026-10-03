"""Save the V37 material already repaired in the current editor before PIE ended."""
import json
from pathlib import Path
import unreal as u

REPORT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/BodyClothMaterialV37/ue_body_cloth_material_v37.json')
MATERIAL = '/Game/Monsters/BlindSupplicantM07/Materials/M07_Body_OriginalV07'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('M07 V37 material is compiled; save is waiting for PIE to end.')
report = json.loads(REPORT.read_text(encoding='utf-8'))
material = u.load_asset(MATERIAL)
mel = u.MaterialEditingLibrary
if not material or material.get_path_name() != report['material']:
    raise RuntimeError('The repaired M07 material is absent.')
if not mel.has_material_usage(material, u.MaterialUsage.MATUSAGE_CLOTHING):
    raise RuntimeError('The in-memory V37 fix is absent; use the full repair script.')
if sorted(t.get_path_name() for t in mel.get_material_used_textures(material)) != report['textures_after']:
    raise RuntimeError('M07 material textures changed since repair; preserve current edits.')
if not u.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('M07 V37 material save failed.')
report.update(saved=True, save_resumed_after_pie=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('M07_V37_BODY_CLOTH_MATERIAL_SAVED '+str(REPORT))
