"""Register one saved common rune, preserving the live catalogue and host modules."""
from pathlib import Path
import json, shutil
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
DATA=ROOT/'Content/ColdSteelData'
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save the mask and icon before registering this rune')
option=json.loads((P/'option.json').read_text(encoding='utf-8'))

def write(path,data):
    raw=path.read_bytes()
    backup=P/'Before'/path.relative_to(ROOT)
    if not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,backup)
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    path.write_bytes(text.replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'))

path=DATA/'melee-gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
choices=next(c['options'] for c in data['columns'] if c['key']=='blade_2')
for index,old in enumerate(choices):
    if old['id']==option['id']:
        # Re-importing art does not undo later approved balance edits.
        for key in ('stats','effects','special_effects'):
            if key in old:option[key]=old[key]
        choices[index]=option
        break
else:choices.insert(0,option)
write(path,data)
path=DATA/'warhammer-modules.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
data['slots']['rune'][option['id']]={'appearance':option['appearance']}
write(path,data)
(P/'catalog_receipt.json').write_text(json.dumps({'complete':True,'id':option['id'],
 'stats':option['stats'],'shared_source':'melee-gunsmith.json:blade_2',
 'sword_slot':'blade_2','warhammer_slot':'rune','runtime_tested':False},indent=2),encoding='utf-8')
print('STRENGTH_RUNE_REGISTERED',flush=True)
