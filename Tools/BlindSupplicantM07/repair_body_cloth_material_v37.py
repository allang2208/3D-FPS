"""Repair the body material's missing clothing shader usage after V36 binding."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001/BodyClothMaterialV37'
MESH = '/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18'
MATERIAL = '/Game/Monsters/BlindSupplicantM07/Materials/M07_Body_OriginalV07'
LIB = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V37 belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving the M07 body material.')
if any(p.get_path_name() == MATERIAL for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M07 body material has unsaved changes; preserved.')
mesh = u.load_asset(MESH)
material = u.load_asset(MATERIAL)
if not mesh or not material:
    raise RuntimeError('M07 display or body material is absent.')
slots = {str(s.get_editor_property('imported_material_slot_name')):
         s.material_interface.get_path_name() if s.material_interface else None for s in mesh.materials}
if slots.get('M07_Body') != material.get_path_name():
    raise RuntimeError('Body slot differs from the diagnosed material: '+str(slots))
OUT.mkdir(parents=True, exist_ok=True)
backup = OUT/'Before/M07_Body_OriginalV07.uasset'
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content/Monsters/BlindSupplicantM07/Materials/M07_Body_OriginalV07.uasset', backup)
report = dict(revision='BodyClothMaterialV37', saved=False, material=material.get_path_name(),
    body_slot=slots['M07_Body'], textures_before=sorted(t.get_path_name() for t in MEL.get_material_used_textures(material)),
    clothing_before=MEL.has_material_usage(material, u.MaterialUsage.MATUSAGE_CLOTHING),
    skeletal_before=MEL.has_material_usage(material, u.MaterialUsage.MATUSAGE_SKELETAL_MESH),
    cause='Body material missing Clothing usage after V36 also bound its membrane fold strips',
    texture_query_mode='shader resources; unavailable with -nullrhi' if '-nullrhi' in u.SystemLibrary.get_command_line().lower() else 'active editor shader resources',
    runtime_tested=False, rendered=False)
prior_report = OUT/'ue_body_cloth_material_v37.json'
if prior_report.exists():
    prior = json.loads(prior_report.read_text(encoding='utf-8'))
    report['initial_diagnosis'] = prior.get('initial_diagnosis', {
        key: prior[key] for key in ('clothing_before', 'skeletal_before', 'textures_before', 'compile_errors')
        if key in prior})
def receipt():
    (OUT/'ue_body_cloth_material_v37.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
receipt()
MEL.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_CLOTHING, True)
report['compile_errors'] = [str(e) for e in MEL.recompile_material(material)]
report['clothing_after'] = MEL.has_material_usage(material, u.MaterialUsage.MATUSAGE_CLOTHING)
report['textures_after'] = sorted(t.get_path_name() for t in MEL.get_material_used_textures(material))
receipt()
if report['compile_errors'] or not report['clothing_after']:
    raise RuntimeError('M07 body clothing material compile failed: '+str(report))
if not LIB.save_loaded_asset(material, False):
    raise RuntimeError('M07 body material save failed.')
report['saved'] = True
receipt()
print('M07_V37_BODY_CLOTH_MATERIAL_SAVED '+json.dumps(report, ensure_ascii=False))
