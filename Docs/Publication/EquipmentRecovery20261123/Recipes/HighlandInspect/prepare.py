from pathlib import Path
import json,hashlib,shutil,re
W=Path(__file__).resolve().parent
project=Path('D:/FPS3D/FPSGAME')
C=project/'Content'
S=project/'SourceAssets/RuneSword20260913/InspectReverseV85'
receipt=json.loads((S/'import_receipt_v85.json').read_bytes())
standard,long=[r['asset'] for r in receipt['assets']]
profile='/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip'
targets=[standard,long,profile]; before={}
def disk(root,k):return root/(k[6:]+'.uasset')
for k in targets:
 f=disk(C,k);dest=disk(W/'Before',k);dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(f,dest)
 before[k]=hashlib.sha256(dest.read_bytes()).hexdigest()
 if hashlib.sha256(f.read_bytes()).hexdigest()!=before[k]:raise RuntimeError('Concurrent change')
hist={}
for line in (Path.home() / 'FPSGAME-Recovery-20261120/AuthoringRebuild/preloss-dependencies.jsonl').open('rb'):
 j=json.loads(line);hist[j['package']]=[e[0] for e in j['dependencies'] if e[0].startswith('/Game/')]
queue=[*targets,'/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny'];seen=set()
while queue:
 k=queue.pop()
 if k in seen:continue
 seen.add(k);f=disk(C,k)
 if not f.is_file():continue
 dst=disk(W/'Host/Content',k);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 for side in ['.ubulk','.uexp','.uptnl']:
  if f.with_suffix(side).is_file():shutil.copy2(f.with_suffix(side),dst.with_suffix(side))
 queue.extend(x for x in hist.get(k,[]) if x not in seen)
 queue.extend(s.decode() for s in set(re.findall(rb'/Game/[A-Za-z0-9_/\-]+',f.read_bytes())) if s.decode() not in seen and disk(C,s.decode()).is_file())
(W/'job.json').write_text(json.dumps(dict(targets=targets,before=before,standard=standard,long_grip=long,profile=profile),indent=2))
print('Staged package inputs',len(seen),flush=True)
