"""Record the completed asset publication without launching validation or gameplay."""
import json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'G18Integration20260929'
icons=json.loads((O/'import_receipt.json').read_text())
muzzles=json.loads((O.parent/'G18MuzzleFit20260930/import_receipt.json').read_text())
if icons.get('status')!='g18_final_icons_published_imported_and_saved' or muzzles.get('status')!='three_g18_muzzles_imported_and_saved':
    raise RuntimeError('Publication has not completed; retain previous delivery status')
file=S/'delivery_status.json';status=json.loads(file.read_text())
status.update(muzzle_fit='../G18MuzzleFit20260930/import_receipt.json',
    final_icons='../G18IconsFinal20260930/import_receipt.json',
    final_icon_format='1024x1024 RGBA: 1 original-PBR equipment icon, 28 neutral-gray modification/category icons',
    titanium_brake='Excluded at user request; not imported or added to catalog',
    final_asset_batch_native_source_changes=False,
    interactive_editor_started=False,runtime_tested=False,visual_acceptance=False,
    remaining='User performs gameplay and visual testing; requested production/import work is saved')
file.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print('G18_DELIVERY_RECORDED',len(muzzles['meshes']),'muzzles',len(icons['saved']),'icons')
