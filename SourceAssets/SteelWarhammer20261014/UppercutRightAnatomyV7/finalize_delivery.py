"""Publish saved animation entrypoints while preserving the V6 donor source."""
from pathlib import Path
from datetime import datetime
import json,shutil
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt['complete'] or receipt['revision']!='RightAnatomyV7_20261015':raise RuntimeError('Animation save is incomplete')
for version in ('UppercutV1','UppercutIdleExitV3','UppercutRearHighV4','UppercutShiftWristV5','UppercutTiltClearanceV6'):
    scripts=['import_assets.py']
    if version!='UppercutTiltClearanceV6':scripts.append('author_uppercut.py')
    for script in scripts:
        old=P.parent/version/script;backup=P/'Before'/(version+'_'+script)
        if not backup.exists():shutil.copy2(old,backup)
        old.write_text('"""Use the current right-arm uppercut revision."""\nfrom pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).resolve().parent.parent/"UppercutRightAnatomyV7"/'+repr(script)+'),run_name="__main__")\n',encoding='utf-8')
arc_writer=P.parent/'UppercutV1/write_contact_arc.py';backup=P/'Before/write_contact_arc.py'
if not backup.exists():shutil.copy2(arc_writer,backup)
text=arc_writer.read_text(encoding='utf-8').replace('UppercutTiltClearanceV6/Warhammer_Uppercut_TiltClearance_Editable.blend','UppercutRightAnatomyV7/Warhammer_Uppercut_RightAnatomy_Editable.blend')
arc_writer.write_text(text,encoding='utf-8')
doc=R/'Docs/Weapons/steel-warhammer-uppercut-tilt-clearance-v6-20261015.md'
text=doc.read_text(encoding='utf-8')
notice='\n> 后续用户反馈上挑出手后的右肘／前臂仍扭曲；已保留本版武器与左手轨迹，继续制作至 [右臂解剖支撑 V7](steel-warhammer-uppercut-right-anatomy-v7-20261015.md)。本版源 Blend 和作者脚本保留为 V7 输入，当前导入入口指向 V7。\n'
if notice.strip() not in text:doc.write_text(text+notice,encoding='utf-8')
delivery={**receipt,'finished':datetime.now().isoformat(timespec='seconds'),'legacy_entrypoints_updated':True,
          'cpp_build_required':False,'runtime_tested':False,'preview_rendered':False}
(P/'delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print(json.dumps(delivery))
