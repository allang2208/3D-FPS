"""Retire only this task's SS64 jobs; submit recorded SS32 replacements."""
import json,urllib.request,shutil
from pathlib import Path
P=Path(__file__).parent;BASE='http://192.168.3.142:8188'
KEYS=['ballast_hardened','ballast_rune','ballast_magic_orb']
def req(path,data=None):
    request=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as r:raw=r.read()
    return json.loads(raw) if raw else {}
old={k:json.loads((P/k/'receipt.json').read_text()) for k in KEYS}
if any(r.get('attempt')=='ss32' for r in old.values()):raise RuntimeError('Replacement already submitted; use existing receipts')
owned=[r['prompt_id'] for r in old.values()]
req('/queue',{'delete':owned})
for pid in owned:req('/interrupt',{'prompt_id':pid})
for key in KEYS:
    folder=P/key;archive=folder/'ss64_attempt';archive.mkdir(exist_ok=True)
    for name in ['receipt.json','workflow.json','view_mapping.json','upload.json']:
        shutil.copy2(folder/name,archive/name)
    h=req('/history/'+old[key]['prompt_id'])
    (archive/'history_at_replacement.json').write_text(json.dumps(h,indent=2))
    w=json.loads((folder/'workflow.json').read_text());w['4']['inputs']['sparse_structure_resolution']=32;w['4']['inputs']['verbose']=True
    for node,name in [('51','raw'),('53','textured_master')]:w[node]['inputs']['filename_prefix']=f'FrostSwordPommels5080_20260915/ss32/{key}/{name}'
    for i in range(3):w[str(130+i)]['inputs']['filename_prefix']=f'FrostSwordPommels5080_20260915/ss32/{key}/view{i}'
    (folder/'workflow.json').write_text(json.dumps(w,indent=2))
    receipt=req('/prompt',{'client_id':'FrostSwordPommels5080_20260915','prompt':w});receipt['attempt']='ss32'
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2));print(key,receipt,flush=True)
