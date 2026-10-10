"""Append the saved haste rune, preserving all other options and concurrent edits."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;root=P.parents[1]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save haste rune textures before making the option selectable.')
p=root/'Content/ColdSteelData/melee-gunsmith.json';raw=p.read_bytes();d=json.loads(raw.decode('utf-8-sig'))
option=json.loads((P/'option.json').read_text(encoding='utf-8'))
choices=next(c['options'] for c in d['columns'] if c['key']=='blade_2')
old=next((x for x in choices if x['id']==option['id']),None)
if old and old!=option:raise RuntimeError('Preserve an intervening haste catalog edit.')
if not old:choices.insert(0,option)
b=P/'Before/melee-gunsmith.json'
if not b.exists():shutil.copy2(p,b)
p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'))
shutil.copy2(P/'blade_2_haste_rune.png',root/'Content/ColdSteelData/AttachmentIcons20260913/blade_2_haste_rune.png')
(P/'catalog_receipt.json').write_text(json.dumps({'complete':True,'id':'haste_rune','slot':'blade_2','stats':option['stats'],'all_current_swords':True,'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
print('HASTE_RUNE_CATALOG_INSTALLED')
