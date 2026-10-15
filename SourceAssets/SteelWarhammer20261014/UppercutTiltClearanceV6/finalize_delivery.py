"""Point existing production entrypoints at the saved uppercut revision."""
import json,shutil
from datetime import datetime
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
imported=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
built=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not imported['complete'] or imported['revision']!='TiltClearanceV6_20261015':raise RuntimeError('Animation import/save is incomplete')
if built['exit_code']!=0:raise RuntimeError('Formal Editor build is incomplete')
for version in ('UppercutV1','UppercutIdleExitV3','UppercutRearHighV4','UppercutShiftWristV5'):
    for script in ('author_uppercut.py','import_assets.py'):
        dst=P.parent/version/script;backup=P/'Before'/(version+'_'+script)
        if not backup.exists():shutil.copy2(dst,backup)
        dst.write_text('"""Current uppercut production entrypoint; retained donor Blend is unchanged."""\nfrom pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).resolve().parent.parent/"UppercutTiltClearanceV6"/'+repr(script)+'),run_name="__main__")\n',encoding='utf-8')
arc_writer=P.parent/'UppercutV1/write_contact_arc.py'
text=arc_writer.read_text(encoding='utf-8').replace('UppercutShiftWristV5/Warhammer_Uppercut_ShiftWrist_Editable.blend','UppercutTiltClearanceV6/Warhammer_Uppercut_TiltClearance_Editable.blend')
arc_writer.write_text(text,encoding='utf-8')
doc=R/'Docs/Weapons/steel-warhammer-uppercut-shift-wrist-v5-20261015.md'
text=doc.read_text(encoding='utf-8')
notice='\n> 后续：用户认可本版整体右下位移；蓄势倾斜与右臂出手后肩口问题已继续制作至 [V6](steel-warhammer-uppercut-tilt-clearance-v6-20261015.md)。当前制作和导入入口指向 V6，V5 的实际脚本保存在 V6/Before。\n'
if notice.strip() not in text:doc.write_text(text+notice,encoding='utf-8')
receipt={'revision':imported['revision'],'saved_assets':imported['saved'],'editor_build':built,
         'finished':datetime.now().isoformat(timespec='seconds'),'runtime_tested':False,
         'preview_rendered':False,'legacy_entrypoints_updated':True}
(P/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
