from pathlib import Path
import json,re,hashlib,shutil
area=Path(__file__).resolve().parent
project=Path('D:/FPS3D/FPSGAME')
content=project/'Content'
base='/Game/Weapons/HighlandClaymore20260922/'
cat=json.loads((content/'ColdSteelData/highland-claymore-modules.json').read_bytes())
broad=project/'SourceAssets/HighlandBroadbladeGuardFinish20261106'
ridge=project/'SourceAssets/HighlandClaymoreMeshy20260922/WedgeSpineJunctionR4_20261106'
pkg=lambda x:x.split('.')[0]
blade=pkg(cat['slots']['blade_1']['highland_ridge_piercer']['mesh'])
cloven=pkg(cat['slots']['guard']['highland_cloven_guard']['mesh_by_blade']['highland_broadblade'])
mats=[pkg(x) for x in json.loads((broad/'saved-assets.json').read_bytes())['materials']]
targets=[blade,cloven,*mats]
def disk(p):return content/(p[6:]+'.uasset')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def exports(data):return {x.decode() for x in re.findall(rb'/Game/[A-Za-z0-9_/-]+',data)}
roots={blade,cloven,*mats,pkg(cat['slots']['guard']['highland_cloven_guard']['mesh']),base+'RidgePiercer20260927/WedgeSpine/M_RidgeWedgeSteel'}
queue=list(roots);seen=set()
while queue:
 k=queue.pop()
 if k in seen:continue
 seen.add(k)
 if not disk(k).is_file():continue
 b=disk(k).read_bytes();dst=area/'Host'/disk(k).relative_to(project);dst.parent.mkdir(parents=True,exist_ok=True)
 if k!=cloven:shutil.copy2(disk(k),dst)
 queue.extend(x for x in exports(b) if disk(x).is_file() and x not in seen)
before={}
for k in targets:
 f=disk(k);before[k]=sha(f);dst=area/'Before'/f.relative_to(content);dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists() and sha(dst)!=sha(f):raise RuntimeError('Snapshot exists '+str(dst))
 if not dst.exists():shutil.copy2(f,dst)
(area/'job.json').write_text(json.dumps(dict(targets=targets,blade=blade,cloven=cloven,mats=mats,before=before,r4fbx=json.loads((ridge/'authoring.json').read_bytes())['fbx']),indent=2))
print('Seeded',len(seen),'packages; saved',len(before),'pre-repair packages')
