from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;data=P.parents[1]/'Content/ColdSteelData'
settings=json.loads((P/'fit-settings.json').read_text());inventory=json.loads((P/'inventory.json').read_text());catalogs={r['definition']:r['catalog'] for r in inventory};receipt=[]
for definition,spec in settings.items():
    if not spec:continue
    path=data/catalogs[definition];original=path.read_bytes();doc=json.loads(original.decode('utf-8-sig'))
    base={k:v for k,v in spec.items() if k not in ['grips','guards']}
    previous=json.loads((P/'Before'/path.name).read_text(encoding='utf-8-sig'))
    if doc.get('hand_fit') not in [None,previous.get('hand_fit'),base]:raise RuntimeError('Concurrent hand_fit change: '+str(path))
    doc['hand_fit']=base
    for grip,fit in spec.get('grips',{}).items():doc['slots']['grip'][grip]['hand_fit']=fit
    for guard,fit in spec.get('guards',{}).items():doc['slots']['guard'][guard]['hand_fit']=fit
    encoded=(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.read_bytes()!=original:raise RuntimeError('Catalog changed during write: '+str(path))
    path.write_bytes(encoded);receipt.append({'path':str(path),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest()})
(P/'fit-install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('INSTALLED_HAND_FITS',len(receipt))
