"""Publish only the sleeve-free vest's viewmodel policy in both body variants."""
import json, os, sys, uuid
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import json_entries as entries
path=P/'Content/ColdSteelData/modular_outfits.json'
raw=path.read_bytes();text=raw.decode('utf-8-sig');data=json.loads(text)
for prefix in [['items'],['body_variants','kaitlin','items']]:
    route=prefix+['ue_modern_kevlar_vest'];obj=data
    for key in route:obj=obj[key]
    text=(entries.replace(text,route+['first_person_mode'],'body_only') if 'first_person_mode' in obj
          else entries.insert(text,route,'first_person_mode','body_only'))
if path.read_bytes()!=raw:raise RuntimeError('Outfit config changed; rerun the scoped update')
tmp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
tmp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
os.replace(tmp,path)
print('TS01_BODY_ONLY_PUBLISHED Jason Kaitlin')
