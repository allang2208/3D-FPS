from pathlib import Path
import json
from datetime import datetime
P=Path(__file__).parent
read=lambda name:json.loads((P/name).read_text(encoding='utf-8-sig'))
assets=read('import-receipt.json');hud=read('hud-import-receipt.json')
game=read('build-FPSGAME.json');editor=read('build-FPSGAMEEditor.json');catalog=read('catalog-receipt.json')
result={'name':'疾律弓弦','option':'highland_cadence','weapon':'bow_woodsteel','slot':'string','tier':'Legendary',
 'finished':datetime.now().isoformat(timespec='seconds'),
 'saved_assets':list(assets['saved'].values())+hud['saved_assets'],
 'assets_saved':assets['complete'] and hud['complete'],
 'game_build_exit':game['exit_code'],'editor_build_exit':editor['exit_code'],
 'catalog_receipt':catalog,
 'hud':'Buff bar stack count and 4s timer ring; five ornate sigils at the shared Mountain Echo center HUD position, mutually exclusive by equipped string.',
 'gameplay_tested':False,'editor_opened':False,'game_started':False,
 'import_notes':'Background import completed with 0 errors. Warnings were existing ModelingService Python-name collisions, deprecated set_material_usage API, and the expected initial missing HUD material before its creation and save.'}
(P/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('CADENCE_DELIVERY_RECORDED')
