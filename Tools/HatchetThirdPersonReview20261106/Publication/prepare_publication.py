"""Prepare this publication's text-only subset without altering the shared index."""
from pathlib import Path
import subprocess, json, hashlib, difflib, shutil, os

ROOT=Path('D:/FPS3D/FPSGAME')
P=Path(__file__).resolve().parent
DOC=ROOT/'Docs/Publication/HatchetThirdPerson20261106'
STAGE=P/'Selected'
ENV=dict(os.environ,GIT_INDEX_FILE=str(P/'publication.index'))

def git(*args,env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=env,stderr=subprocess.PIPE)
def text(path):return Path(path).read_text(encoding='utf-8-sig')
def normalized(data):return data.decode('utf-8-sig').replace('\r\n','\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def replace_once(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Expected one owned anchor: '+old[:100])
    return s.replace(old,new,1)

base=git('rev-parse','HEAD').decode().strip()
selected={}
def indexed(path):
    a=git('show',':'+path);b=git('show',base+':'+path)
    if a!=b:raise RuntimeError('Existing staged content on owned path: '+path)
    return normalized(a)
def put(path,s):selected[path]=s.rstrip()+'\n'
def whole(path):put(path,text(ROOT/path))

# Independent runtime changes: do not copy unrelated changes in shared hosts.
path='Source/FPSGAME/Characters/FPSPlayerBodyComponent.h'
s=indexed(path)
anchor='    TArray<FFPSBodyMotionBinding> MotionBindings;'
live=text(ROOT/path);start=live.index('    // Keep the observer trail ready');end=live.index('\n    FDelegateHandle',start)
put(path,replace_once(s,anchor,live[start:end]+'\n'+anchor))
path='Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp'
s=indexed(path);live=text(ROOT/path);start=live.index('    const bool NeedsKukriRift=');end=live.index('    for(auto Device:WorldTacticalDevices)',start)
if '#include "../Weapons/Kukri/KukriRhythm.h"' not in s:
    s=replace_once(s,'#include "FPSPlayerBodyComponent.h"','#include "FPSPlayerBodyComponent.h"\n#include "../Weapons/Kukri/KukriRhythm.h"')
anchor='    UFPSPerformanceMetricsSubsystem::CountEquipmentRebuild(this);\n'
put(path,replace_once(s,anchor,anchor+live[start:end]))
path='Source/FPSGAME/Characters/FPSPlayerBodyNetwork.cpp'
s=indexed(path)
s=replace_once(s,'#include "FPSPlayerBodyComponent.h"','#include "FPSPlayerBodyComponent.h"\n#include "FPSBodyKukriMotion.h"')
anchor='        ||A.bHasHandholds!=B.bHasHandholds'
s=replace_once(s,anchor,'        ||(FPSBodyKukriMotion::HasExecutorClock(A)&&FPSBodyKukriMotion::HasExecutorClock(B)\n            &&FMath::IsNearlyZero(A.ActionProgressRate)!=FMath::IsNearlyZero(B.ActionProgressRate))\n'+anchor)
anchor='            DisplayState.ActionProgressRate=Rate(DisplayState.ActionProgress,P.ActionProgress,Delta);'
s=replace_once(s,anchor,'            // Preserve the executor rate at hit-stop and resume transitions.\n            if(!FPSBodyKukriMotion::HasExecutorClock(DisplayState))\n    '+anchor)
put(path,s)
path='Source/FPSGAME/Characters/FPSBodyKukriMotion.h'
indexed(path);s=text(ROOT/path)
s=replace_once(s,'    case EFPSBodyAction::Equip:\n        if(S.ActionVariant==TEXT("OffhandKukriEquip"))return TEXT("Kukri.Offhand.Equip");\n        if(S.ActionVariant==TEXT("OffhandHatchetEquip"))return TEXT("Kukri.Offhand.HatchetEquip");\n        return TEXT("Kukri.FullBody.Equip");','    case EFPSBodyAction::Equip:return TEXT("Kukri.FullBody.Equip");')
s=replace_once(s,'    return Key==TEXT("Kukri.Offhand.Equip")||Key==TEXT("Kukri.Offhand.HatchetEquip")||\n        Key==TEXT("Kukri.Hatchet.DualChop")||','    return Key==TEXT("Kukri.Hatchet.DualChop")||')
s=replace_once(s,'    if(S.Family==TEXT("Kukri")&&S.Action==EFPSBodyAction::Equip&&\n        (S.ActionVariant==TEXT("OffhandKukriEquip")||S.ActionVariant==TEXT("OffhandHatchetEquip")))return 0;\n','')
put(path,s)
path='Source/FPSGAME/Characters/FPSBodyKukriRifts.cpp';indexed(path);whole(path)
for rel in ['SwiftFalconHeavy.h','SwiftFalconRibbons.h']:
    whole('Source/FPSGAME/Weapons/Kukri/'+rel)
whole('Source/FPSGAME/Development/KukriEnchantAuditFixture.h')

# Config leaves only. This text is for the index and never replaces the work file.
cfgpath='Content/ColdSteelData/player_body.json';original=indexed(cfgpath)
cfg=json.loads(original);livecfg=json.loads(text(ROOT/cfgpath));roles={};variants={}
for name in ['Kukri.Falcon.Charge','Kukri.Falcon.Release','Kukri.Falcon.DualCharge','Kukri.Falcon.DualRelease','Kukri.Hatchet.DualChop']:
    roles[name]=livecfg['clips'][name];cfg['clips'][name]=roles[name]
    variants[name]=livecfg['body_variants']['kaitlin']['clips'][name]
    cfg['body_variants']['kaitlin']['clips'][name]=variants[name]
# Preserve JSON formatting except adding the ten owned keys to their objects.
for owner,values in [('clips',roles),('kaitlin',variants)]:
    marker='"clips": {' if owner=='clips' else '"kaitlin": {'
    start=original.index(marker)
    if owner=='kaitlin':start=original.index('"clips": {',start)
    insert=original.index('\n',start)+1
    indent=original[insert:len(original)-len(original[insert:].lstrip(' '))]
    addition=''.join(indent+json.dumps(k)+': '+json.dumps(v)+',\n' for k,v in values.items())
    original=original[:insert]+addition+original[insert:]
if json.loads(original)!=cfg:raise RuntimeError('Config subset drifted outside owned leaves')
put(cfgpath,original)

# Append only this task's lessons, preserving all pre-existing index content.
for skill,rel in [('ue5-fps-arms-animation','hatchet-dedicated-actions.md'),('ue5-save-load-replication','equipment-runes-and-attack-receipts.md')]:
    path=f'skills/{skill}/references/{rel}'
    put(path,indexed(path).rstrip()+'\n\n'+text(P/(skill+'.addition.md')).lstrip())

task='SourceAssets/HatchetDualChopRepair20261106/'
recipes=['author.py','elbow_skin.py','pull_arm.py','read_source.py','save_assets.py','read_saved.py','inspect_motion.py','inspect_skin.py','ue_job.ps1',
 'ElbowAnatomy/author_helpers.py','ElbowAnatomy/save_corrected.py','ElbowAnatomy/diagnose_saved.py',
 'PullAnatomy/author_pull.py','PullAnatomy/read_pull.py','PullAnatomy/save_pull.py','PullAnatomy/readback.py','PullAnatomy/check_saved.py','PullAnatomy/render_body.py','PullAnatomy/SelfReview/render_body.py']
for rel in recipes:whole(task+rel)
tools='Tools/HatchetThirdPersonReview20261106/'
for rel in ['build.ps1','run_native.ps1','run_falcon_clock.ps1','run_wire.ps1','RuneFixtureMigration/build.ps1','RuneFixtureMigration/run.ps1']:
    whole(tools+rel)
exceptions='\n# Hatchet third-person authoring and explicit audit entry points (2026-11-06)\n'+''.join('!/'+p+'\n' for p in selected if p.startswith(('SourceAssets/','Tools/')))
put('.gitignore',indexed('.gitignore').rstrip()+'\n'+exceptions)

DOC.mkdir(parents=True,exist_ok=True)
evidence=DOC/'Evidence';evidence.mkdir(exist_ok=True)
records={
 'asset-references.json':ROOT/'Tools/HatchetThirdPersonReview20261106/asset-references.json',
 'audit-result.json':ROOT/'Tools/HatchetThirdPersonReview20261106/audit-result.json',
 'rune-fixture-result.json':ROOT/'Tools/HatchetThirdPersonReview20261106/RuneFixtureMigration/result.json',
 'native-188.json':ROOT/'Tools/HatchetThirdPersonReview20261106/RuneFixtureMigration/Run-20261106-170536/isolated.json',
 'rune-wire-6.json':ROOT/'Tools/HatchetThirdPersonReview20261106/RuneFixtureMigration/Run-20261106-170536/host.json',
 'falcon-clock-52.txt':ROOT/'Tools/HatchetThirdPersonReview20261106/falcon-clock.txt',
 'first-person-restoration.json':ROOT/task/'RollbackFirstPerson/asset-restoration.json',
 'saved-body-surface-review.json':ROOT/task/'PullAnatomy/SelfReview/review-result.json'}
for label,run in [('falcon-listen','Listen-20261106-163033'),('base-hatchet-listen','Listen-20261106-164507'),('falcon-dedicated','Dedicated-20261106-164813')]:
    records[label+'.json']=ROOT/tools/run/'host.json'
    records[label+'-receipt.json']=ROOT/tools/run/'receipt.json'
for name,source in records.items():shutil.copy2(source,evidence/name)
shutil.copy2(ROOT/'trash/HatchetThirdPerson20261106/cleanup-manifest.json',DOC/'cleanup-manifest.json')

# Exact follow-up patches against the recorded local hosts: no broad foreign diffs.
patches=[
 ('Source/FPSGAME/Multiplayer/ColdSteelKukriAuthority.cpp',ROOT/tools/'ColdSteelKukriAuthority.before.cpp'),
 ('Source/FPSGAME/Development/KukriCombatWireAudit.cpp',ROOT/tools/'KukriCombatWireAudit.before.cpp'),
 ('Source/FPSGAME/Multiplayer/KukriRuneAuditCases.cpp',ROOT/tools/'RuneFixtureMigration/KukriRuneAuditCases.before.cpp'),
 ('Source/FPSGAME/Development/KukriRuneWireAudit.cpp',ROOT/tools/'RuneFixtureMigration/KukriRuneWireAudit.before.cpp')]
integration=DOC/'Integration';integration.mkdir(exist_ok=True);prereqs=[]
for name,before in patches:
    old=text(before);new=text(ROOT/name)
    patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name,n=0))
    out=integration/(name.replace('/','__')+'.patch');out.write_text(patch,encoding='utf-8',newline='\n')
    prereqs.append({'host':name,'base_local_sha256':sha(before),'current_local_sha256':sha(ROOT/name),'patch':out.relative_to(DOC).as_posix(),'apply_option':'--unidiff-zero; require the recorded host base','status':'requires recorded local host; not applied to Source in this publication'})
name='Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp';s=text(ROOT/name)
parts=[]
for begin,end in [('        const FName KukriBaseKey=','        const FName NextSwordKey='),
                  ('        const bool KukriMatchedRelease=','        Controls.SwordTransitionSeconds='),
                  ('            Controls.LibraryPreserveHands=HasKukriAction','            if(NextSwordAsset!=SwordAsset)')]:
    start=s.index(begin);stop=s.index(end,start);parts.append(s[start:stop])
parts.append(next(line for line in s.splitlines() if 'else if(HasKukriAction&&FPSBodyKukriMotion::UsesAuthoredClock(KukriKey))' in line)+'\n')
parts.append('// In the authored action branch, retain only hands owned by the library:\n'+next(line for line in s.splitlines() if 'Controls.ActionWristMask&=Controls.LibraryPreserveHands;' in line)+'\n')
(integration/'authored-kukri-selection.cpp.inc').write_text('// Selected consumer excerpts; requires the current shared authored-body host.\n\n'+'\n// ...\n'.join(parts),encoding='utf-8')
name='Source/FPSGAME/Characters/FPSPlayerBodyKukri.cpp';s=text(ROOT/name);start=s.index('void UFPSPlayerBodyComponent::SampleKukriState')
(integration/'sample-kukri-state.cpp.inc').write_text(s[start:],encoding='utf-8')
prereqs.extend([{'host':name,'current_local_sha256':sha(ROOT/name),'status':'current executor sampler excerpt; Falcon weapon executor and OffhandBladeDraw prerequisites are not published by this batch'},
 {'host':'Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp','current_local_sha256':sha(ROOT/'Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp'),'status':'shared authored-body library prerequisite; excerpt is not an applied main patch'},
 {'host':'Source/FPSGAME/Weapons/Kukri/KukriEnchantment.h','current_local_sha256':sha(ROOT/'Source/FPSGAME/Weapons/Kukri/KukriEnchantment.h'),'status':'live enchantment migration required before applying rune fixture patches; current catalog and consumer migration remain outside this publication'}])
(DOC/'integration-prerequisites.json').write_text(json.dumps(prereqs,indent=2)+'\n',encoding='utf-8')
assets=[]
for body,values in [('Jason',roles),('Kaitlin',variants)]:
    for key,value in values.items():
        package=value.split('.')[0];disk=ROOT/'Content'/(package.removeprefix('/Game/')+'.uasset')
        assets.append({'body':body,'role':key,'package':package,'bytes':disk.stat().st_size,'sha256':sha(disk),'publication':'local only; binary redistribution not approved'})
(DOC/'asset-dependencies.json').write_text(json.dumps({'assets':assets,'authoring_inputs':'Retain source JSON, NPZ, original skeleton/mesh and Before folders locally; generated actor animation data and source meshes are not in this text-only publication.','first_person':'Original restored packages retained; withdrawn candidates moved to trash.'},indent=2)+'\n',encoding='utf-8')
(DOC/'body-routes-manifest.json').write_text(json.dumps({'scope':'Selected hatchet third-person routes; does not prove shared runtime integration','config':cfgpath,'roles':roles,'body_variants':{'kaitlin':{'clips':variants}},'required_source_files':[x for x in selected if x.startswith('Source/FPSGAME/Characters/')],'required_cook_directories':['/Game/Weapons/TacticalHatchet20261101']},indent=2)+'\n',encoding='utf-8')
for file in DOC.rglob('*'):
    if file.is_file():whole(file.relative_to(ROOT).as_posix())

STAGE.mkdir(exist_ok=True)
for name,s in selected.items():
    out=STAGE/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s,encoding='utf-8',newline='\n')
git('read-tree',base,env=ENV)
entries=[]
for name in sorted(selected):
    oid=git('hash-object','-w','--path',name,str(STAGE/name)).decode().strip()
    git('update-index','--add','--cacheinfo','100644,'+oid+','+name,env=ENV)
    entries.append({'path':name,'blob':oid,'bytes':(STAGE/name).stat().st_size})
manifest={'base_commit':base,'index':ENV['GIT_INDEX_FILE'],'files':entries,'shared_index_untouched':True,'runtime_build_or_game_retested':False}
(P/'prepared.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(entries),'bytes':sum(x['bytes'] for x in entries),'base':base,'index':ENV['GIT_INDEX_FILE']}))
