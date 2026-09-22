"""Freeze only the rune-sword blade-II icon targets before this revision."""
from pathlib import Path
import json,shutil,hashlib
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
before=P/'Before';before.mkdir(exist_ok=True)
catalog=json.loads((ROOT/'Content/ColdSteelData/melee-gunsmith.json').read_text(encoding='utf-8-sig'))
column=next(c for c in catalog['columns'] if c['key']=='blade_2')
rows=[];baseline=[]
for option in [{'id':'false','name':column['default']}]+column['options']:
    if option.get('weapons') and 'ue_rune_sword' not in option['weapons']:continue
    rows.append({'id':option['id'],'name':option['name'],'key':'ue_rune_sword_blade_2_'+option['id']})
rows.append({'id':'category','name':'剑身Ⅱ分类','key':'ue_rune_sword_category_blade_2','copy':'ue_rune_sword_blade_2_false'})
for row in rows:
    for ext in ['.png','.uasset']:
        f=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(row['key']+ext)
        if f.exists():
            target=before/f.name
            if not target.exists():shutil.copy2(f,target)
            baseline.append({'path':str(f),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(P/'targets.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'baseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
(P/'options_snapshot.json').write_text(json.dumps(column,ensure_ascii=False,indent=2),encoding='utf-8')
print('RUNE_GLYPH_TARGETS_PREPARED',len(rows))
