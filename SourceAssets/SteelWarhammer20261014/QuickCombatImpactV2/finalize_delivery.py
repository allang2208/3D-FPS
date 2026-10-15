"""Publish the current entrypoints only after actual save and formal builds."""
from pathlib import Path
from datetime import datetime
import json

P=Path(__file__).resolve().parent
R=P.parents[2]
imported=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
built=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not imported['complete'] or imported['revision']!='ShaftCheckImpactV2_20261015':
    raise RuntimeError('Animation save is incomplete')
if not built['complete'] or any(x['exit_code']!=0 for x in built['targets']):
    raise RuntimeError('Formal builds are incomplete')

# Keep the previous actual sources in Before. Established launchers now use
# the refined version, so a later import cannot silently restore V1.
for script in ('author_quick_combat.py','import_assets.py'):
    redirect=('"""Current warhammer quick-combat source is QuickCombatImpactV2."""\n'
              'from pathlib import Path\nimport runpy\n'
              'runpy.run_path(str(Path(__file__).resolve().parent.parent/'
              f'"QuickCombatImpactV2/{script}"),run_name="__main__")\n')
    (P.parent/'QuickCombatV1'/script).write_text(redirect,encoding='utf-8')

doc=R/'Docs/Weapons/steel-warhammer-quick-combat-v1-20261015.md'
original=(P/'Before'/doc.name).read_text(encoding='utf-8')
notice=('> 当前动作为 [前顶强化 V2](steel-warhammer-quick-combat-impact-v2-20261015.md)。'
        '以下为 V1 历史记录；原制作脚本和正式动画备份保留在 '
        '`SourceAssets/SteelWarhammer20261014/QuickCombatImpactV2/Before/`。\n\n')
doc.write_text(notice+original,encoding='utf-8')
receipt={'revision':imported['revision'],'saved_assets':imported['saved'],'builds':built['targets'],
         'seconds':.5,'prepare_seconds':.075,'contact_seconds':.15,'forward_apex_m':.24,
         'finished':datetime.now().isoformat(timespec='seconds'),
         'runtime_tested':False,'multiplayer_tested':False,'preview_rendered':False}
(P/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
