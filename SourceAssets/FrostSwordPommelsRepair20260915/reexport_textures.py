"""Re-export 512 voxel data at its actual grid size; reuse the fixed seeds."""
import json,time,urllib.request,urllib.parse
from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'FrostSwordPommels5080_20260915';B='http://192.168.3.142:8188'
def request(path,data=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(B+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=60))
for key in ['ballast_magic_orb','ballast_rune']:
    folder=P/key;folder.mkdir(exist_ok=True)
    if (folder/'receipt.json').exists():continue
    w=json.loads((OLD/key/'workflow.json').read_text())
    w['52']['inputs']['resolution']=512
    w['53']['inputs']['filename_prefix']=f'FrostSwordPommelsRepair20260915/{key}/textured_master'
    for node in ['50','51','130','131','132']:w.pop(node,None)
    (folder/'workflow.json').write_text(json.dumps(w,indent=2))
    r=request('/prompt',{'client_id':'FrostSwordPommelsRepair20260915','prompt':w})
    (folder/'receipt.json').write_text(json.dumps(r,indent=2));print('SUBMITTED',key,r,flush=True)
pending=['ballast_magic_orb','ballast_rune']
while pending:
    for key in list(pending):
        folder=P/key;pid=json.loads((folder/'receipt.json').read_text())['prompt_id'];h=request('/history/'+pid).get(pid)
        if not h:continue
        (folder/'history.json').write_text(json.dumps(h,indent=2))
        if h['status']['status_str']!='success':raise RuntimeError(json.dumps(h['status']))
        url=B+'/view?'+urllib.parse.urlencode({'filename':'textured_master_00001_.glb','subfolder':f'FrostSwordPommelsRepair20260915/{key}','type':'output'})
        urllib.request.urlretrieve(url,folder/'textured_master_00001_.glb');print('EXPORTED',key,flush=True);pending.remove(key)
    if pending:time.sleep(20)
