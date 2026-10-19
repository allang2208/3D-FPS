"""Build reviewed S12K-only publication candidates, without changing shared sources.

Uses the per-file pre-task snapshots, not the entire dirty working tree.
Run only for this publication; current live sources are already integrated.
"""
import difflib, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LOCAL=ROOT/'Saved/Saiga12KPublication20261019'
PUB=ROOT/'Docs/Publication/Saiga12K20261019'
PATCH=PUB/'Integration';PATCH.mkdir(parents=True,exist_ok=True)
CANDIDATES=LOCAL/'IndexCandidates';CANDIDATES.mkdir(exist_ok=True)
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
manifest=[];index=[]

def read(p):return (ROOT/p).read_text(encoding='utf-8-sig')
def sha(s):return hashlib.sha256(s.encode('utf8')).hexdigest()
def githead(p):return subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT).decode('utf-8-sig')
def patch(p,base,result,origin):
    if base==result:return
    name=p.replace('/','__')+'.patch'
    text='diff --git a/'+p+' b/'+p+'\n'+''.join(difflib.unified_diff(base.splitlines(True),result.splitlines(True),fromfile='a/'+p,tofile='b/'+p,n=3))
    (PATCH/name).write_text(text,encoding='utf8')
    private=ROOT/'SourceAssets/Saiga12KPublication20261019/Prerequisites'
    prior=private/'Before'/p;after=private/'After'/p
    prior.parent.mkdir(parents=True,exist_ok=True);after.parent.mkdir(parents=True,exist_ok=True)
    prior.write_text(base,encoding='utf8');after.write_text(result,encoding='utf8')
    manifest.append({'target':p,'patch':'Integration/'+name,'baseline':origin,
      'local_baseline':prior.relative_to(ROOT).as_posix(),
      'local_result':after.relative_to(ROOT).as_posix(),
      'baseline_sha256_utf8_lf':sha(base),'result_sha256_utf8_lf':sha(result),
      'current_workspace_sha256_utf8_lf':sha(read(p)),
      'note':'Apply only after restoring this named per-file prerequisite, not blindly to Git HEAD. Live workspace is already integrated.'})
def candidate(p,result):
    path=CANDIDATES/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(result,encoding='utf8')
    index.append({'target':p,'candidate':path.relative_to(ROOT).as_posix(),'sha256':sha(result)})

# Reviewed opcode numbers in the frozen pre-task snapshot inventory.
selection={
 'FPSGAMECharacter.cpp':[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,18,19,21,22,24,25,28],
 'FPSGAMECharacterProfile.cpp':[0,1,2,3],
 'ColdSteelPlayerState.cpp':[3,7],
 'CasingPortCalibration.h':[0],
 'GunsmithModificationTier.h':[0,1],
 'M4GunsmithVisual.cpp':[2,6],
 'M4MuzzleVisual.cpp':[0,2,3,6,8,10,11],
 'RifleHipFraming.cpp':[0,1,2,3,4,5,7],
 'SVDGripProfiles.cpp':[0,3],
 'TacticalDeviceComponent.cpp':[0,1,2,3,4,5,8],
 'WeaponReloadStages.cpp':[2],
}
special={'FPSPlayerBodyEquipment.cpp','FPSPreloadAssetRegistry.gen.h','M4DrumVisual.cpp'}
for row in json.loads((LOCAL/'baselines.json').read_text()):
    p=row['target'];name=Path(p).name
    if name.startswith('Saiga12K') or name in special:continue
    base=read(row['baseline']);a=base.splitlines(True);z=read(p).splitlines(True)
    ops=[op for op in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes() if op[0]!='equal']
    if ops!=[tuple(x) for x in row['ops']]:raise RuntimeError('Source changed since review: '+p)
    chosen=selection.get(name,list(range(len(ops))));result=a[:]
    for n in sorted(chosen,reverse=True):
        _,i,j,k,l=ops[n];new=''.join(z[k:l])
        if name=='FPSGAMECharacter.cpp' and n==3:new=new.replace(' || SVCHWeaponAssets::Matches(AKMViewmodel)','')
        if name=='RifleHipFraming.cpp' and n==0:new=new.replace('#include "SVCHWeaponAssets.h"\n','')
        if name=='ColdSteelWarehouseModel.cpp' and n==0:new=new.replace('TEXT("ue_zhanmadao"), ','')
        result[i:j]=new.splitlines(True)
    patch(p,base,''.join(result),row['baseline'])

# Earlier magazine and factory-section integration predates its later snapshots.
# Reverse only the exact S12K blocks to retain all unrelated current prerequisites.
def strip_block(text,marker):
    start=text.index(marker);opening=text.index('{',start);level=0;end=None
    for n in range(opening,len(text)):
        if text[n]=='{':level+=1
        elif text[n]=='}':
            level-=1
            if level==0:end=n+1;break
    if end is None:raise RuntimeError(marker)
    if text[end:end+1]=='\n':end+=1
    return text[:start]+text[end:]

p='Source/FPSGAME/Weapons/M4DrumVisual.cpp';result=read(p)
base=strip_block(result,'    if(IsSaiga12KWeapon())\n')
base=base.replace('#include "Saiga12KMagazineAssets.h"\n','').replace('||IsSaiga12KWeapon()','')
patch(p,base,result,'derived from current host by removing only S12K include, magazine block and native-drop predicate')
p='Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp';result=read(p)
base=strip_block(result,'    if(Character.IsValid()&&Source==Character->AKMViewmodel&&Character->IsSaiga12KWeapon())\n')
lines=base.splitlines(True)
for i,l in enumerate(lines):
    if 'if((Slot==TEXT("Saiga12K_Stock")' in l:
        del lines[i:i+2];break
base=''.join(lines)
patch(p,base,result,'derived from current host by removing only S12K factory masks and stable manifest ordering')

p='Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp'
base=read('SourceAssets/Saiga12KBodyHands20261018/Before/FPSPlayerBodyActions.cpp');a=base.splitlines(True);z=read(p).splitlines(True);result=a[:]
ops=list(difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes())
for tag,i,j,k,l in reversed(ops):
    change=''.join(z[k:l])
    if tag!='equal' and ('Camera/CameraComponent.h' in change or 'const FRotator Aim=IsThirdPersonViewEnabled()' in change):result[i:j]=z[k:l]
patch(p,base,''.join(result),'SourceAssets/Saiga12KBodyHands20261018/Before/FPSPlayerBodyActions.cpp')

for p in ['Source/FPSGAME/UI/M4GunsmithPreviewResources.cpp','Source/FPSGAME/Weapons/RifleHipFraming.h']:
    patch(p,githead(p),read(p),'Git '+HEAD+':'+p)
p='Source/FPSGAME/Characters/FPSBodyAssetPreloader.cpp';base=githead(p)
result=base.replace('        TEXT("/Game/Weapons/AKM/"),\n','        TEXT("/Game/Weapons/AKM/"),\n        TEXT("/Game/Weapons/Saiga12K/"),\n')
patch(p,base,result,'Git '+HEAD+':'+p)
p='Source/FPSGAME/UI/ColdSteelCrosshair.cpp';base=githead(p)
patch(p,base,base.replace('Character->HasInventoryWeapon()&&Character->IsTubeShotgunWeapon()','Character->HasInventoryWeapon()&&Character->IsShotgunWeapon()'),'Git '+HEAD+':'+p)
p='Source/FPSGAME/Weapons/RifleReloadHandoff.h';result=read(p)
base=result.replace('const FString& Definition, bool bDrum = false','const FString& Definition').replace('\n            || (Definition == TEXT("ue_saiga12k") && bDrum)','').replace(' || Definition == TEXT("ue_saiga12k")','')
patch(p,base,result,'derived from current host by removing only S12K drum handoff changes')

# Add only current S12K entries to the published data; do not publish other items.
for name in ['items.json','combat-weapon-formulas.json','gunsmith.json','modular_outfits.json']:
    p='Content/ColdSteelData/'+name;base=json.loads(githead(p));live=json.loads(read(p))
    if name=='gunsmith.json':
        base['weapons']=[w for w in base['weapons'] if w['id']!='ue_saiga12k']+[next(w for w in live['weapons'] if w['id']=='ue_saiga12k')]
    elif name=='modular_outfits.json':
        base['profiles'].update({k:v for k,v in live['profiles'].items() if '/Weapons/Saiga12K/' in k and '/Detail20261018/' in k})
    else:base['ue_saiga12k']=live['ue_saiga12k']
    candidate(p,json.dumps(base,ensure_ascii=False,indent=2)+'\n')
p='Config/DefaultGame.ini';base=githead(p);line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/Saiga12K")'
candidate(p,base.rstrip()+'\n[/Script/UnrealEd.ProjectPackagingSettings]\n'+line+'\n' if line not in base else base)
p='Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h';base=githead(p)
import re
new=[l for l in read(p).splitlines(True) if 'TEXT("/Game/Weapons/Saiga12K/' in l]
result=re.sub(r'^.*TEXT\("/Game/Weapons/Saiga12K/.*\n','',base,flags=re.M)
anchor='        TEXT("/Game/Weapons/ScopeOptics'
at=result.index(anchor);result=result[:at]+''.join(new)+result[at:]
result=re.sub(r'PathCount = \d+;',f'PathCount = {len(re.findall(r"^        TEXT",result,re.M))};',result)
candidate(p,result)

(PUB/'integration-manifest.json').write_text(json.dumps({'capture_commit':HEAD,'hash_encoding':'UTF-8 without BOM, LF','targets':manifest},indent=2)+'\n',encoding='utf8')
(LOCAL/'index-candidates.json').write_text(json.dumps(index,indent=2),encoding='utf8')
print(json.dumps({'patches':len(manifest),'data_candidates':len(index),'capture_commit':HEAD}))
