"""Stage the exact 2011 publication scope; preserve unrelated working changes."""
import hashlib,json,re,subprocess,sys,textwrap
from pathlib import Path
P=Path(__file__).resolve().parents[2];O=P/'SourceAssets/PitViper2011Publication20261003'
def git(*args,input=None):return subprocess.run(['git',*args],cwd=P,input=input,capture_output=True,check=True).stdout
finish_only=sys.argv[1:]==['--finish']
if sys.argv[1:] and not finish_only:raise RuntimeError('Use no arguments or --finish')
if not finish_only and git('diff','--cached','--name-only').strip():raise RuntimeError('Preserve existing staged changes before this publication')
paths=[]
for batch in sorted((P/'SourceAssets').glob('PitViper*')):
    for file in sorted(batch.rglob('*')):
        if not file.is_file() or file.suffix not in ('.py','.ps1','.md'):continue
        if any(n.startswith('Before') or n in ('Backup','History','Inputs','__pycache__') for n in file.relative_to(batch).parts):continue
        paths.append(file.relative_to(P).as_posix())
paths.extend(f.relative_to(P).as_posix() for f in (P/'Docs/Weapons').glob('pit-viper2011*.md'))
paths.extend(['Docs/Weapons/pistol-shared-suppressed-and-pit-viper-normal-20261002.md',
    'Tools/Weapons/pit_viper_grip_fitting.py','Tools/Weapons/pit_viper_longitudinal_grip.py','Tools/Weapons/pit_viper_si_extension.py',
    'Tools/Publication/prepare_pit_viper_closeout_20261003.py','Tools/Publication/archive_pit_viper_closeout_20261003.ps1',
    'Tools/Publication/stage_pit_viper_closeout_20261003.py',
    'Source/FPSGAME/Weapons/PistolGripSurface.cpp','Source/FPSGAME/Weapons/PistolGripSurface.h',
    'Source/FPSGAME/Weapons/PitViper2011SICompensator.cpp','Source/FPSGAME/Weapons/PitViper2011SICompensator.h',
    'Source/FPSGAME/Weapons/PistolAudioAssets.h','Source/FPSGAME/Weapons/CommonHK416Parts.h',
    'Source/FPSGAME/Weapons/M1911AttachmentVisual.cpp','Source/FPSGAME/UI/ColdSteelIconResources.cpp',
    'skills/ue5-weapon-workflow/references/pistol-surface-and-optic-refinement.md',
    'SourceAssets/PitViper2011Publication20261003/archive-manifest.json',
    'SourceAssets/PitViper2011Publication20261003/retained-recovery-dependencies.json'])
paths=sorted(set(paths))
for path in paths:
    if not (P/path).is_file():raise RuntimeError('Missing publication file '+path)
partial_paths=['Source/FPSGAME/UI/M4GunsmithLayout.cpp','Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',
    'skills/ue5-weapon-workflow/SKILL.md','Docs/AssetSetup.md','.gitignore','Content/ColdSteelData/gunsmith.json']
manifest='SourceAssets/PitViper2011Publication20261003/published-files.json'
if finish_only:
    staged=set(git('diff','--cached','--name-only','-z').decode('utf8').strip('\0').split('\0'))
    expected=set(paths+partial_paths)
    if staged-(expected|{manifest}) or (expected-staged)-{'Content/ColdSteelData/gunsmith.json'}:
        raise RuntimeError('Staged scope changed; preserve it for manual review')
else:
    (O/'exact-paths.txt').write_bytes(b'\0'.join(p.encode('utf8') for p in paths)+b'\0')
    git('add','--pathspec-from-file='+str(O/'exact-paths.txt'),'--pathspec-file-nul')
def head(path):return git('show','HEAD:'+path).decode('utf8')
def index(path,content):
    blob=git('hash-object','-w','--stdin',input=content.encode('utf8')).decode().strip()
    git('update-index','--add','--cacheinfo','100644,'+blob+','+path);paths.append(path)
def owned_hunks(path,select):
    old=head(path);diff=git('diff','-U0','--',path).decode('utf8');lines=old.splitlines(keepends=True);changes=[]
    for chunk in re.split(r'(?=^@@)',diff,flags=re.M)[1:]:
        if not select(chunk):continue
        m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n',chunk)
        start,count=int(m[1]),int(m[2] or 1);at=start if count==0 else start-1
        body=chunk[m.end():].splitlines(keepends=True)
        before=[s[1:] for s in body if s.startswith('-')];after=[s[1:] for s in body if s.startswith('+')]
        if lines[at:at+count]!=before:raise RuntimeError('Preserve concurrent source change '+path)
        changes.append((at,count,after))
    for at,count,after in sorted(changes,reverse=True):lines[at:at+count]=after
    index(path,''.join(lines))
if not finish_only:
    owned_hunks('Source/FPSGAME/UI/M4GunsmithLayout.cpp',lambda h:'VipGrip' in h or 'SiMuzzle' in h)
    owned_hunks('Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',
        lambda h:not any(s in h for s in ('ColdSteelEnchantmentCombat','ColdSteelEnhancementSystem','SetBigBlindEnabled','ComposureHandling')))
    route='- 手枪握把防滑纹、纵向覆片、弹匣边界或纹理拉伸：[手枪表面与部件分界](references/pistol-surface-and-optic-refinement.md)。按握把本体轮廓制作，裁切后保持物理 UV，专属与通用纹理沿相同覆盖域。'
    path='skills/ue5-weapon-workflow/SKILL.md';index(path,head(path).rstrip()+'\n\n'+route+'\n')
    path='Docs/AssetSetup.md';section=(O/'asset-setup-section.txt').read_text(encoding='utf8')
    index(path,head(path).replace('# 恢复完整 UE5 内容\n\n','# 恢复完整 UE5 内容\n\n'+section,1))
    path='.gitignore';current=(P/path).read_text(encoding='utf8');block=current[current.index('# Pit Viper 2011 closeout:'):]
    index(path,head(path).rstrip()+'\n\n'+block)
path='Content/ColdSteelData/gunsmith.json';original=head(path);working=json.loads((P/path).read_text(encoding='utf-8-sig'))
weapon=next(w for w in working['weapons'] if w['id']=='ue_pit_viper2011')
array_start=re.search(r'"weapons"\s*:\s*(\[)',original).start(1)
decoder=json.JSONDecoder();old_weapons,array_size=decoder.raw_decode(original[array_start:])
if any(w.get('id')==weapon['id'] for w in old_weapons):
    start=array_start+1
    while True:
        while original[start] in ' \t\r\n,':start+=1
        row,size=decoder.raw_decode(original[start:])
        if row.get('id')==weapon['id']:break
        start+=size
    index(path,original[:start]+json.dumps(weapon,ensure_ascii=False,indent=2)+original[start+size:])
else:
    closing=array_start+array_size-1
    row=textwrap.indent(json.dumps(weapon,ensure_ascii=False,indent=2),'    ')
    prefix=original[:closing].rstrip()+(',' if old_weapons else '')+'\n'+row+'\n  '
    index(path,prefix+original[closing:])
entries=[]
for path in sorted(set(git('diff','--cached','--name-only','-z').decode('utf8').strip('\0').split('\0'))-{manifest}):
    data=git('show',':'+path);entries.append({'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
entries.append({'path':manifest,'self_manifest':True})
record={'date':'2026-10-03','base_commit':git('rev-parse','HEAD').decode().strip(),
    'public_scope':'Owned 2011 recipes, records, skill, exact catalog row and runtime integration; no source binary payloads',
    'files':entries,'game_tested':False,'acceptance_rendered':False,'native_rebuilt_for_publication':False}
(P/manifest).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');git('add','--',manifest)
print('PIT_VIPER_PUBLICATION_STAGED',len(entries),'files',sum(e.get('bytes',0) for e in entries),'bytes')
