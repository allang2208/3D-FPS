"""Advance whirlwind import entrypoints after the V8 asset has been saved."""
from pathlib import Path
from datetime import datetime
import json,shutil
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt['complete'] or receipt['revision']!='WiderInertiaV8_20261015':raise RuntimeError('Animation save is incomplete')
for version in ('WhirlwindV1','WhirlwindGripV2','WhirlwindReleaseV3','WhirlwindFlowV4','WhirlwindHandoffV5','WhirlwindDropV6','WhirlwindEarlyReleaseV7'):
    old=P.parent/version/'import_assets.py';backup=P/'Before'/(version+'_import_assets.py')
    if not backup.exists():shutil.copy2(old,backup)
    old.write_text('"""Import the current wider-inertia whirlwind animation."""\nfrom pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).resolve().parent.parent/"WhirlwindInertiaV8/import_assets.py"),run_name="__main__")\n',encoding='utf-8')
doc=R/'Docs/Weapons/steel-warhammer-whirlwind-early-release-v7-20261015.md'
text=doc.read_text(encoding='utf-8')
notice='\n> 后续用户认为单手惯性外带幅度仍小、动作不自然；当前正式动画为 [V8](steel-warhammer-whirlwind-inertia-v8-20261015.md)，扩大右手外带与锤子转角，并错开手臂、武器的减速时点。本版提前松手时序继续保留。\n'
if notice.strip() not in text:doc.write_text(text+notice,encoding='utf-8')
delivery={**receipt,'finished':datetime.now().isoformat(timespec='seconds'),'legacy_import_entrypoints_updated':True,
          'cpp_build_required':False,'runtime_tested':False,'preview_rendered':False}
(P/'delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print(json.dumps(delivery))
