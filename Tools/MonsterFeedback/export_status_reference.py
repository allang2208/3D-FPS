"""Extract the original status-bar display catalog; retain reference hashes."""
from pathlib import Path
import json,re,hashlib
root=Path('D:/FPS3D/FPSGAME')
source=Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
js=(source/'src/ui/status-bar.js').read_text(encoding='utf-8')
items=[]
for key,icon,name,color,desc in re.findall(r"(\w+): \{ icon: '([^']*)', name: '([^']*)', color: '([^']*)', desc: '([^']*)' \}",js):
 items.append(dict(type=key,icon=icon,name=name,color=color,description=desc))
assert len(items)>=30
(root/'Content/ColdSteelData/status_effects.json').write_text(json.dumps({'effects':items},ensure_ascii=False,indent=2),encoding='utf-8')
files=['src/ui/status-bar.js','src/ui/panels/hud-core.js','game-style.css']
record={'source':str(source),'files':{p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in files},'layout_px':{'left':104,'top':12,'width':252,'height':44,'tile_width':54,'tile_height':44,'column_gap':12,'row_gap':6,'radius':7,'border':2},'catalog_count':len(items)}
(root/'SourceAssets/MonsterFeedback20260911/reference/source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('STATUS_REFERENCE_EXPORTED',len(items))
