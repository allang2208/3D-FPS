"""Update only M24's two catalog reload durations, retaining file formatting."""
import json,re
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
path=root/'Content/ColdSteelData/gunsmith.json'
raw=path.read_bytes();text=raw.decode('utf-8')
start=text.index('"id": "ue_m24"');base=text.index('"base":',start)
begin=text.index('{',base);value,end=json.JSONDecoder().raw_decode(text[begin:]);end+=begin
expected={'reload_time':4.2,'empty_reload_time':5.866666666666666}
updated={'reload_time':4.7,'empty_reload_time':6.366666666666666}
section=text[begin:end]
for key,before in expected.items():
    if value[key]!=before:raise RuntimeError('Concurrent M24 duration edit: '+key)
    section,count=re.subn(r'("'+key+r'"\s*:\s*)[0-9.]+',lambda m:m[1]+repr(updated[key]),section,count=1)
    if count!=1:raise RuntimeError('M24 duration not found: '+key)
result=text[:begin]+section+text[end:]
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed while preparing the M24 edit')
path.write_bytes(result.encode('utf-8'))
(Path(__file__).parent/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m24','before':expected,'after':updated,'runtime_tested':False},indent=2))
print('M24_RELOAD_GAP_CATALOG_SAVED')
