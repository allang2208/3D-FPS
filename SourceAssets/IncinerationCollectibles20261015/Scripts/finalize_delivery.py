"""Assemble actual production/build receipts; does not launch tests or gameplay."""
from pathlib import Path
from datetime import datetime,timezone
import json
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text('utf-8-sig'))
model=read('model_manifest.json');icons=read('presentation.json');assets=read('Receipts/installation.json');data=read('Receipts/data-installation.json')
build=read('Receipts/build.json')
if {r['target'] for r in build['results'] if r['exit_code']==0}!={'FPSGAME','FPSGAMEEditor'}:raise RuntimeError('Game and Editor builds are not both complete')
report=dict(stage='assets_data_and_native_builds_complete',completed_utc=datetime.now(timezone.utc).isoformat(),
    items=[dict(id=x['id'],name=x['name'],rarity=x['rarity'],grid=x['grid'],sell_souls=x['value'],triangles=x['triangles_lod0']) for x in model['assets'].values()],
    ue_packages=len(assets['packages']),icons=len(icons['icons']),fixed_candidate_bindings=data['fixed_candidate_bindings'],
    search_entries_per_run=data['search_entries_per_run'],loot_profiles=len(data['pools']),rarity_floor='rare',
    builds=build['results'],tests_run=False,game_run=False,multiplayer_tested=False,visual_acceptance=False,
    interactive_editor_launched=False,inventory_icons_rendered=True,
    note='Production inventory icons were rendered from delivered GLBs. No acceptance previews or game captures. Existing settled containers retain their content/empty state.')
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATION_DELIVERY_SAVED')
