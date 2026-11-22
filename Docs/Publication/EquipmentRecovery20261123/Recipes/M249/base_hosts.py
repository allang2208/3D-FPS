from shared import *
pub=R/'Docs/Publication/Conversation20261112/Integration'
snap=read(R/'Docs/Publication/M24920261109/Integration/shared-host-sections.json')
def key(s):return re.sub(r'\s+','',s)
lines={}
for p in (R/'Source/FPSGAME').rglob('*'):
 if p.suffix not in ('.h','.cpp','.inl'):continue
 t=p.read_text('utf-8-sig',errors='replace')
 for ln in t.splitlines():
  k=key(ln)
  if k:lines.setdefault(k,[]).append(p.name)
rows={}
for item in snap:
 path=item['source'];d=item
 found={};missing=set()
 for sec in d['regions']:
  for ln in sec['text'].splitlines():
   if not re.search(r'M249|LMGStabilityGrip|IsLMG|BipodSlot',ln,re.I):continue
   k=key(ln)
   if k in lines:found[ln.strip()]=lines[k]
   else:missing.add(ln.strip())
 if missing or found:rows[path]=dict(found=found,changed=sorted(missing))
write('base-hosts.json',rows)
for n,x in rows.items():
 print(n,len(x['found']),len(x['changed']))
 if x['changed']:print('\n'.join(x['changed'])[:300])
