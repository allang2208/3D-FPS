"""Publish the expanded palm coverage and retain the earlier pose work as history."""
import json,runpy
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world and ('UEDPIE' in world.get_name() or 'PIE_' in world.get_name()):
    raise RuntimeError('End PIE before saving glove assets')
pickup='/Game/Characters/ModularOutfit20260924/FingerlessHuntV2/Pickups/SM_FingerlessHunt_Pickup'
if pickup in {package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Glove pickup already has unsaved editor changes')
runpy.run_path(str(P/'Tools/ModularOutfit/publish_coupled_fingerless.py'))
itempath=P/'Content/ColdSteelData/items.json'
items=json.loads(itempath.read_text(encoding='utf-8-sig'))
items['ue_field_gloves']['desc']='皮革完整覆盖掌心、手背与虎口，边缘延伸到手掌与手指交界，五指露出。保留短腕口、薄卷边与缝线，可与衣袖独立搭配。'
itempath.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('published.json','coupled-published.json'):
    path=R/name;receipt=json.loads(path.read_text())
    receipt.update(coverage_revision='CoverageToRoots20260927',root_weight=.50,
                   coverage='full palm, back and thumb web to palm-finger junction',
                   animations_changed_this_revision=0,runtime_tested=False,
                   clearance_checked_this_revision=False,
                   previous_clearance_report='ClearanceAfter/final-summary.json (20260926 geometry only)')
    path.write_text(json.dumps(receipt,indent=2)+'\n')
receipt=json.loads((R/'coupled-published.json').read_text())
receipt['glove_assets']=json.loads((R/'asset-receipt.json').read_text())
receipt['combined_assets']=json.loads((R/'SkinCoverage/asset-receipt.json').read_text())
(R/'CoverageToRoots20260927/saved.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('ROOT_COVERAGE_PUBLISHED',len(receipt['combined_assets']['profiles']),flush=True)
