from shared import *
rel='Content/ColdSteelData/gunsmith.json'
p=R/rel
old=p.read_bytes()
bom=b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b''
data=old[len(bom):].decode()
latest=read(R/'Docs/Publication/Conversation20261112/Integration/configuration.json')['gunsmith.json']['weapons'][0]
m=re.search(r'(?m)^( +)\{\r?\n\s*"id": "ue_m249",',data)
start=m.start()+len(m[1]); one,end=json.JSONDecoder().raw_decode(data[start:])
assert one['id']==latest['id'] and one['allowed']==latest['allowed'][:-1] and 'bipod' not in one['options']
one['allowed']=latest['allowed']
one['options']['bipod']=latest['options']['bipod']
one['base']={**{k:latest['base'][k] if k in ('ads_percent','ads_smooth') else one['base'][k] for k in latest['base']},**{k:v for k,v in one['base'].items() if k not in latest['base']}}
nl='\r\n' if '\r\n' in data else '\n'
new=bom+(data[:start]+json.dumps(one,indent=2,ensure_ascii=False).replace('\n',nl+m[1])+data[start+end:]).encode()
backup=W/'Before'/rel
backup.parent.mkdir(exist_ok=True,parents=True)
if backup.exists():assert backup.read_bytes()==old
else:backup.write_bytes(old)
temp=p.with_name('.gunsmith.m249-recovery.tmp')
assert not temp.exists()
temp.write_bytes(new)
if p.read_bytes()!=old:raise RuntimeError('Concurrent edit')
os.replace(temp,p)
print('Saved M249 gunsmith entry',len(old),len(new))
