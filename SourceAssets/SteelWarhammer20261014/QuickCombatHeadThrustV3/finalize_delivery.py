"""Publish the head-thrust entrypoints after saved assets and formal builds."""
from pathlib import Path
from datetime import datetime
import json
P=Path(__file__).resolve().parent;R=P.parents[2]
imported=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
built=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not imported['complete'] or imported['revision']!='HeadThrustV3_20261015':raise RuntimeError('Animation save is incomplete')
if not built['complete'] or any(x['exit_code']!=0 for x in built['targets']):raise RuntimeError('Formal builds are incomplete')
for version in ('QuickCombatV1','QuickCombatImpactV2'):
    for script in ('author_quick_combat.py','import_assets.py'):
        redirect=('"""Current quick melee is the forward hammer-head thrust V3."""\n'
                  'from pathlib import Path\nimport runpy\n'
                  'runpy.run_path(str(Path(__file__).resolve().parent.parent/'
                  f'"QuickCombatHeadThrustV3/{script}"),run_name="__main__")\n')
        (P.parent/version/script).write_text(redirect,encoding='utf-8')
for name in ('steel-warhammer-quick-combat-v1-20261015.md','steel-warhammer-quick-combat-impact-v2-20261015.md'):
    doc=R/'Docs/Weapons'/name
    previous=doc.read_text(encoding='utf-8');backup=P/'Before'/name
    if not backup.exists():backup.write_text(previous,encoding='utf-8')
    notice=('> 当前快速近战已替换为 [锤头直刺 V3](steel-warhammer-quick-combat-head-thrust-v3-20261015.md)。'
            '本文横柄前顶方案已被用户否定，保留作历史恢复记录。\n\n')
    if not previous.startswith(notice):doc.write_text(notice+previous,encoding='utf-8')
receipt={'revision':imported['revision'],'saved_assets':imported['saved'],'builds':built['targets'],
         'seconds':.5,'prepare_seconds':.09,'contact_seconds':.15,'style':'forward hammer-head thrust',
         'finished':datetime.now().isoformat(timespec='seconds'),
         'runtime_tested':False,'multiplayer_tested':False,'preview_rendered':False}
(P/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
