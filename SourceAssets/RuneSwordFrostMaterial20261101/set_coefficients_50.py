"""Apply the 2026-11-01 user-requested 50% frost coefficients, no tests."""
from pathlib import Path
import json,re

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
BACKUP=P/'BeforeBalance50';BACKUP.mkdir(exist_ok=True)

def save(path,before,after):
    backup=BACKUP/path.name
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent edit: '+str(path))
    path.write_bytes(after)

path=ROOT/'Content/ColdSteelData/items.json'
before=path.read_bytes();after=before
for key in [b'innate_erosion_intelligence',b'innate_erosion_wisdom']:
    pattern=rb'("'+key+rb'"\s*:\s*)[0-9.]+'
    after,count=re.subn(pattern,lambda m:m[1]+b'0.5',after)
    if count!=1:raise RuntimeError('Ambiguous frost item coefficient: '+key.decode())
save(path,before,after)

path=ROOT/'Content/ColdSteelData/melee-gunsmith.json'
before=path.read_bytes();text=before.decode('utf-8-sig')
# Restrict additive magic edits to this material's object. Ordinary erosion
# runes retain their own 10% coefficients.
marker=text.index('"id": "frost_crystal"')
start=text.rfind('{',0,marker)
option,length=json.JSONDecoder().raw_decode(text[start:])
section=text[start:start+length]
for key in ['rune_intelligence','rune_wisdom']:
    section,count=re.subn(r'("'+key+r'"\s*:\s*)[0-9.]+',lambda m:m[1]+'0.5',section)
    if count!=1:raise RuntimeError('Missing material coefficient: '+key)
text=text[:start]+section+text[start+length:]
text=text.replace('合计：智力×20% + 精神×20%','合计：智力×100% + 精神×100%')
text=text.replace('自带侵蚀：近战附加 智力×10%＋精神×10% 的魔法伤害',
                  '自带侵蚀：近战附加 智力×50%＋精神×50% 的魔法伤害')
encoded=text.encode('utf-8')
if before.startswith(b'\xef\xbb\xbf'):encoded=b'\xef\xbb\xbf'+encoded
save(path,before,encoded)
(P/'balance50-receipt.json').write_text(json.dumps({
    'date':'2026-11-01','requested_coefficients':{'intelligence':.5,'wisdom':.5},
    'weapons':['ue_frost_crystal_sword','ue_rune_sword:blade_material:frost_crystal'],
    'spirit_burst_multiplier_unchanged':2.,'spirit_burst_result':{'intelligence':1.,'wisdom':1.},
    'gameplay_tested':False,'build_required':False
},indent=2)+'\n',encoding='utf8')
print('FROST_COEFFICIENTS_SAVED: 50% intelligence + 50% wisdom; spirit burst remains x2')
