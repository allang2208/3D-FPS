from shared import *
import _winapi
H=W/'Host'
H.mkdir(exist_ok=True)
def copy(p,q):
 q.parent.mkdir(parents=True,exist_ok=True)
 if not q.exists():shutil.copy2(p,q)
def link(p,q):
 if q.exists():return
 q.parent.mkdir(parents=True,exist_ok=True);_winapi.CreateJunction(str(p),str(q))
def top(src,dst,private,skip=()):
 dst.mkdir(parents=True,exist_ok=True)
 for p in src.iterdir():
  if p.name in skip:continue
  q=dst/p.name
  if p.is_dir():
   if p.name not in private:link(p,q)
  else:copy(p,q)
copy(R/'FPSGAME.uproject',H/'FPSGAME.uproject')
for n in ('Shaders','Plugins'):link(R/n,H/n)
shutil.copytree(R/'Config',H/'Config',dirs_exist_ok=True)
for p in (R/'Binaries/Win64').glob('*'):
 if p.name=='UnrealEditor.modules' or (p.suffix=='.dll' and 'patch_' not in p.name):copy(p,H/'Binaries/Win64'/p.name)
top(C,H/'Content',{'Weapons','ColdSteelData'})
top(C/'Weapons',H/'Content/Weapons',{'M249','LMGStabilityGrip20261111'})
for n in ('M249','LMGStabilityGrip20261111'):shutil.copytree(C/'Weapons'/n,H/'Content/Weapons'/n,dirs_exist_ok=True)
top(C/'ColdSteelData',H/'Content/ColdSteelData',{'AttachmentIcons20260913','Icons'})
top(C/'ColdSteelData/AttachmentIcons20260913',H/'Content/ColdSteelData/AttachmentIcons20260913',{'FramedFirearms'})
for n in ('ColdSteelData/Icons','ColdSteelData/AttachmentIcons20260913/FramedFirearms'):
 (H/'Content'/n).mkdir(exist_ok=True,parents=True)
 for p in (C/n).glob('*[mM]249*'):
  if p.is_file():copy(p,H/'Content'/n/p.name)
D=H/'SourceAssets'/S.name
for n in ('GripMount40','BipodPin41','RearGrip43','RearGrip44','BipodIcon42'):
 x=S/n;y=D/n;y.mkdir(exist_ok=True,parents=True)
 for p in x.iterdir():
  if p.name=='Exports':link(p,y/p.name)
  elif p.is_file() and (p.suffix=='.py' or (p.suffix=='.json' and p.name!='saved.json')):copy(p,y/p.name)
for n in ('Wrist39','Wrist34','Repair08','Repair11','Repair20','ReloadAudit21'):link(S/n,D/n)
def extract(n,filterfn):
 with zipfile.ZipFile(S/n) as z:
  for f in z.namelist():
   if filterfn(f):
    assert f.startswith('Content/Weapons/') and '..' not in f
    with z.open(f) as src,(H/f).open('wb') as dest:shutil.copyfileobj(src,dest)
extract('GripMount40/before.zip',lambda f:True)
extract('Wrist39/accepted-before.zip',lambda f:'Handguard' in f)
extract('BipodPin41/before.zip',lambda f:True)
for p in (S/'GripMount40').glob('*.json.gz'):copy(p,D/'GripMount40'/p.name)
copy(S/'RearGrip43/saved.json',D/'RearGrip43/saved.json')
for n in ('BipodPin41','GripMount40'):
 inp=read(S/n/'inputs.json'); before41=read(S/'BipodPin41/inputs.json'); actual={k:sha(H/game(k)) for k in inp}
 for k,h in actual.items():assert h==before41.get(k,inp[k]),k
print('private content ready',H)
