from pathlib import Path
O=Path(__file__).parent
note=(O/'workflow_note.md').read_text(encoding='utf-8')
for p in [O.parents[1]/'Docs/VerticalGripClass.md',O.parents[1]/'skills/ue5-fps-arms-animation/references/vertical-grip-family.md',Path('C:/Users/allan/.codex/skills/ue5-fps-arms-animation/references/vertical-grip-family.md')]:
 text=p.read_text(encoding='utf-8')
 if '## 2026-09-11 实拍包握参考：当前运行修订' not in text:text=text.rstrip()+note
 p.write_text(text.rstrip()+'\n',encoding='utf-8')
