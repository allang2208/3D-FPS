"""Advance import entrypoints only after the new animation is actually saved."""
from pathlib import Path
from datetime import datetime
import json,shutil
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt['complete'] or receipt['revision']!='EarlyLeftReleaseV7_20261015':raise RuntimeError('Animation save is incomplete')
for version in ('WhirlwindV1','WhirlwindGripV2','WhirlwindReleaseV3','WhirlwindFlowV4','WhirlwindHandoffV5','WhirlwindDropV6'):
    old=P.parent/version/'import_assets.py'
    backup=P/'Before'/(old.parent.name+'_import_assets.py')
    if not backup.exists():shutil.copy2(old,backup)
    old.write_text('"""Import the current early-release whirlwind animation."""\nfrom pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).resolve().parent.parent/"WhirlwindEarlyReleaseV7/import_assets.py"),run_name="__main__")\n',encoding='utf-8')
doc=R/'Docs/Weapons/steel-warhammer-whirlwind-drop-v6-20261015.md'
text=doc.read_text(encoding='utf-8')
notice='\n> 后续用户指出本版松手太晚；已保留外甩路线并提前交接，当前正式动画为 [V7](steel-warhammer-whirlwind-early-release-v7-20261015.md)。V6 作者源保留，导入入口指向 V7。\n'
if notice.strip() not in text:doc.write_text(text+notice,encoding='utf-8')
delivery={**receipt,'finished':datetime.now().isoformat(timespec='seconds'),'legacy_import_entrypoints_updated':True,
          'cpp_build_required':False,'runtime_tested':False,'preview_rendered':False}
(P/'delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print(json.dumps(delivery))
