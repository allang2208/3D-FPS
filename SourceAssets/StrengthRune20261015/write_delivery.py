"""Collect production receipts without running gameplay or validation tools."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text(encoding='utf-8-sig'))
delivery={
 'option':read('option.json'),
 'art_source':'Original editable vector polygons authored in author_assets.py',
 'design':'StrengthRune_Design.png',
 'mask':'T_Mask_strength_rune.png',
 'icon':'blade_2_strength_rune.png',
 'icon_generation':read('icon-generation.json'),
 'assets':read('import_receipt.json'),
 'catalog':read('catalog_receipt.json'),
 'game_build':read('game-build-receipt.json'),
 'editor_livecoding_receipt':'livecoding-result-01.txt',
 'editor_livecoding_result':(P/'livecoding-result-01.txt').read_text(encoding='utf-8-sig'),
 'regular_editor_build':read('editor-build-receipt.json'),
 'editor_gui_started_or_closed':False,
 'game_launched':False,
 'runtime_tested':False,
 'runtime_acceptance':'User testing pending',
 'color':{'core_linear':[.82,.012,.018,1],'glow_linear':[1,.025,.032,1]},
 'hammer_placement':'Existing ShaftWrapV2 actual arc-length mapping, unchanged coverage and scale',
 'shared_scope':['sword blade_2 slot','steel warhammer rune slot'],
 'build_sequence':'Existing editor live compile was canceled; after that editor exited externally, a regular background Editor build was run.'
}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STRENGTH_RUNE_DELIVERY_WRITTEN')
