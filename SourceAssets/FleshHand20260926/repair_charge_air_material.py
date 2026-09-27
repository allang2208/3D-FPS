"""Repair and compile only the giant-hand air material; no gameplay or visual test."""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OUT=ROOT/'ChargeVisual'/'MosaicRepair'
PATH='/Game/Monsters/FleshHand/ChargeVisual20260927/M_HandChargeAir'
TAG='FleshHandChargeVisualV2'
MASK_TAG='FleshHandChargeAirMaskV3'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Wrong project')
command_line=u.SystemLibrary.get_command_line().lower()
if '-run=' not in command_line:
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving the charge material')
if PATH in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserving unsaved charge material edits')

m=u.load_asset(PATH)
if not m or E.get_metadata_tag(m,'FleshHand.ChargeVisual')!=TAG:
    raise RuntimeError('Missing or unowned charge air material')
masks=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
       and n.get_editor_property('description') in (TAG,MASK_TAG)
       and {str(pin.get_editor_property('input_name')) for pin in n.get_editor_property('inputs')}=={'UV','Alpha','Clock','Mode'}]
if len(masks)!=1:
    raise RuntimeError('Expected one owned charge air mask; preserving material graph')

OUT.mkdir(parents=True,exist_ok=True)
backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/ChargeVisual/MosaicRepair/M_HandChargeAir.before.uasset')
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content'/(PATH.removeprefix('/Game/')+'.uasset'),backup)
mask=masks[0]
old_code=mask.get_editor_property('code')
new_code=(ROOT/'ChargeAir.hlsl').read_text(encoding='utf-8')
m.modify()
mask.modify()
mask.set_editor_property('code',new_code)
mask.set_editor_property('description',MASK_TAG)
errors=L.recompile_material(m)
if errors:
    raise RuntimeError('Charge air material compilation failed: '+str(errors))
# Finish this material's submitted shader jobs before saving the production asset.
L.get_statistics(m)
if not E.save_loaded_asset(m,False):
    raise RuntimeError('Charge air material save failed')
report={'state':'material_recompiled_and_saved','asset':m.get_path_name(),
        'utc':datetime.now(timezone.utc).isoformat(),
        'fix':'Replace reserved HLSL identifier line with trailMask',
        'source':str(ROOT/'ChargeAir.hlsl'),'code_changed':old_code!=new_code,
        'recompile_errors':[str(e) for e in errors],
        'null_rhi':'-nullrhi' in command_line,
        'runtime_tested':False,'visual_tested':False}
(OUT/'repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('FLESHHAND_CHARGE_AIR_REPAIRED '+json.dumps(report))
