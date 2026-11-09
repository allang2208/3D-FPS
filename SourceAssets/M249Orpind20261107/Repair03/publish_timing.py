from pathlib import Path
import json,re,os,tempfile
root=Path(__file__).resolve().parent;project=root.parents[2]
p=project/'Content/ColdSteelData/gunsmith.json';before=p.read_bytes();text=before.decode('utf-8-sig')
m=re.search(r'\{\s*"id":\s*"ue_m249",',text)
if not m:raise RuntimeError('Missing M249 catalogue entry')
entry,count=json.JSONDecoder().raw_decode(text[m.start():])
entry['base']['reload_time']=8.8;entry['base']['empty_reload_time']=9.6
pad=len(text[text.rfind('\n',0,m.start())+1:m.start()])
new=json.dumps(entry,ensure_ascii=False,indent=2).replace('\n','\n'+' '*pad)
text=text[:m.start()]+new+text[m.start()+count:]
with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:
 tmp=Path(f.name);f.write(text.encode('utf-8-sig' if before.startswith(b'\xef\xbb\xbf') else 'utf8'))
if p.read_bytes()!=before:tmp.unlink();raise RuntimeError('Concurrent catalogue edit')
os.replace(tmp,p)
print('M249_RELOAD_TIMING',8.8,9.6)
