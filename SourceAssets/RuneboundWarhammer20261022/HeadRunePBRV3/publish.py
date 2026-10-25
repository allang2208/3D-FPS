"""Publish only the six completed replacement-head visual recipes."""
from pathlib import Path
import json,os,hashlib
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
imported=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not imported.get('complete') or len(imported['heads'])!=6:raise RuntimeError('Finish all six head imports first')
changes=[]
for path in (ROOT/'Content/ColdSteelData/runebound-warhammer-modules.json',P.parent/'ModulesV1/catalog_base.json'):
    before=path.read_bytes();value=json.loads(before.decode('utf-8-sig'));owned=[]
    for row in imported['heads']:
        option=row['id'];scope=('slots','hammer_heads',option);spec=value['slots']['hammer_heads'][option]
        for field,new in [('mesh',row['mesh']),('model_revision','HeadRunePBRV3')]:
            spec[field]=new;owned.append(scope+(field,))
        bindings=dict(row['materials'])
        # Preserve compatibility names while binding every actual new FBX slot.
        import re
        for key,material in row['materials'].items():bindings[re.sub(r'(?:[._]\d{3})+$','',key)]=material
        for key,material in bindings.items():
            spec.setdefault('materials',{})[key]=material;owned.append(scope+('materials',key))
    # These are modular-weapon catalogs, not the player-body configuration.
    # Save the freshly read catalog only while its on-disk input is unchanged.
    backup=P/'Before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    after=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog change; preserve it: '+str(path))
    temp=path.with_suffix('.head-rune-v3.tmp');temp.write_bytes(after)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog change before publication: '+str(path))
    os.replace(temp,path)
    changes.append({'path':str(path),'owned_paths':owned,'before_sha256':hashlib.sha256(before).hexdigest(),
        'after_sha256':hashlib.sha256(after).hexdigest()})
builds=json.loads((P/'build_receipt.json').read_text('utf-8-sig'))
(P/'published.json').write_text(json.dumps({'complete':True,'catalog_writes':changes,'heads':imported['heads'],
    'factory':'Original mesh/material/runes retained','builds':builds,'tested':False,'rendered':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('Published all six replacement heads; original factory head retained')
