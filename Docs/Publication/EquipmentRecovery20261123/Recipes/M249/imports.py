from shared import *
def filemd(p):return hashlib.md5(p.read_bytes()).hexdigest()
def stored(p):
 raw=p.read_bytes()[:1048576]
 return sorted(set(i.decode().lower() for i in re.findall(rb'"FileMD5"\s*:\s*"([a-fA-F0-9]{32})"',raw)))
def ident(p,q):
 return dict(source=str(q),source_md5=filemd(q),package_md5=stored(p),match=filemd(q) in stored(p))
rows={};art={}
for f in sorted(S.rglob('ue_m249*.png')):
 art.setdefault(f.name,[]).append(f)
for d in (C/'ColdSteelData/AttachmentIcons20260913/FramedFirearms',C/'ColdSteelData/AttachmentIcons20260913',C/'ColdSteelData/Icons'):
 for p in sorted(d.glob('ue_m249*.uasset')):
  q=p.with_suffix('.png')
  if 'ue_m249_magazine_m249_side_mag_45'==p.stem:q=S/'Repair18/Icons'/q.name
  elif p.stem in ('ue_m249_bipod_false','ue_m249_category_bipod'):q=S/'BipodIcon42/M249_Bipod_Framed.png'
  elif not q.exists():
   other=C/'ColdSteelData/AttachmentIcons20260913/FramedFirearms'/q.name
   if other.exists():q=other
   elif q.name in art:q=art[q.name][-1]
  if q.is_file():rows[p.relative_to(R).as_posix()]=ident(p,q)
for folder,assets in ((S/'Textures',C/'Weapons/M249/Textures'),(S/'FireAudio',C/'Weapons/M249/Audio')):
 for p in assets.glob('*.uasset'):
  q=next(folder.glob(p.stem+'.*'),None)
  if q:rows[p.relative_to(R).as_posix()]=ident(p,q)
rec=S/'FireAudio/source.json';record=read(rec)
for p in (C/'Weapons/M249/Audio').glob('*.uasset'):
 raw=p.read_bytes();rows[p.relative_to(R).as_posix()]['recording_tag']=record['sha256'].encode() in raw
write('import-provenance.json',rows)
diffs={k:v for k,v in rows.items() if not v['match']}
print('source import signatures',len(rows),'match',len(rows)-len(diffs));print('\n'.join(k+' '+str(v['package_md5'])[:35] for k,v in diffs.items())[:2600])
k='Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_m249_bipod_false.png'
p=R/k;q=S/'BipodIcon42/M249_Bipod_Framed.png'
assert sha(q)==read(S/'BipodIcon42/deployment.json')['master_sha256']
if not p.exists():
 with p.open('xb') as out:out.write(q.read_bytes())
 write('png-restored.json',{k:dict(source=str(q),sha256=sha(q),previous=None)})
