from pathlib import Path
import json,copy,shutil
O=Path(__file__).parent;P=O.parents[2];B=O/'BeforeCode';B.mkdir(exist_ok=True)
def edit(rel,fn):
 p=P/rel;t=p.read_text(encoding='utf-8-sig');old=t;t=fn(t)
 if t==old:raise RuntimeError('No edit '+rel)
 backup=B/rel;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(p,backup)
 p.write_text(t,encoding='utf-8',newline='\r\n')
def sub(t,a,b):
 if a not in t:raise RuntimeError('Missing edit anchor '+a[:100])
 return t.replace(a,b)
W='Source/FPSGAME/Weapons/'
def header(t):return t.replace('#include "../FPSGAMECharacter.h"','#include "../FPSGAMECharacter.h"\n#include "A762Attachments.h"',1)
def sights(t):
 t=sub(t,'FoldingSightAngles.Add(I==0?90.f:-90.f);','FoldingSightAngles.Add(I==0?-90.f:90.f);')
 return t
edit(W+'M4FoldingSights.cpp',sights)
edit(W+'A762WeaponAssets.h',lambda t:sub(sub(t,'-.05576f,.09904f','-.05576f,.1065f'),'.49144f,.07504f','.49144f,.0935f'))
def optic(t):
 t=header(t)
 t=sub(t,'*(FString(TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/"))+Name)','*A762Attachments::MeshPath(Variant)')
 t=sub(t,'HolographicMount=FTransform(FQuat(FVector::UpVector,PI*.5f),A762WeaponAssets::OpticMount,FVector(.01f));','HolographicMount=A762Attachments::OpticMount(Variant);')
 # Only A762 branch; preserve other weapons' ring material and optics.
 pos=t.index('if(AKMSoviet::Matches(AKMViewmodel))')
 t=t[:pos].replace('TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVORing")','*A762Attachments::MeshPath(TEXT("lpvo_ring"))')+t[pos:]
 return t
edit(W+'M4GunsmithVisual.cpp',optic)
for file,family,mapname,component,setter in [
 ('M4VerticalForegrip.cpp','vertical','VerticalGripAnimations','VerticalForegrip','SetVerticalForegrip'),
 ('M4CantedForegrip.cpp','canted','CantedGripAnimations','CantedForegrip','SetCantedForegrip'),
 ('M4AngledForegrip.cpp','angled','ForegripAnimations','AngledForegrip','SetAngledForegrip'),
 ('M4HandstopVisual.cpp','prism','PrismGripAnimations','PrismHandstop','SetGunsmithHandstop')]:
 def grips(t,family=family,component=component,setter=setter):
  t=header(t)
  t=sub(t,'if(!bUsingM4Infima&&!AKMSoviet::Matches(AKMViewmodel))return;','if(!bUsingM4Infima&&!AKMSoviet::Matches(AKMViewmodel)&&!A762WeaponAssets::Matches(AKMViewmodel))return;')
  anchor='const FString ResolvedPath=' if 'const FString ResolvedPath=' in t else 'const FString Path='
  t=t.replace(anchor,anchor+'A762WeaponAssets::Matches(AKMViewmodel)?A762Attachments::AnimationPath(TEXT("'+family+'"),Pair.Value):',1)
  if family=='prism':
   a='if(bUseM16){PrismHandstop='
   t=sub(t,a,'if(A762WeaponAssets::Matches(AKMViewmodel)){PrismHandstop=A762Attachments::Configure(this,AKMViewmodel,PrismHandstop,TEXT("prism"),Variant==TEXT("prism_handstop")&&bInventoryWeaponReady);return;}\n    '+a)
   t=sub(t,'const FString Path=bUseM16?M16Attachments::MeshPath(TEXT("tactical_vertical")):', 'const FString Path=A762WeaponAssets::Matches(AKMViewmodel)?A762Attachments::MeshPath(TEXT("tactical_vertical")):bUseM16?M16Attachments::MeshPath(TEXT("tactical_vertical")):')
  else:
   a='if(bUseM16){'+component+'='
   t=sub(t,a,'if(A762WeaponAssets::Matches(AKMViewmodel)){'+component+'=A762Attachments::Configure(this,AKMViewmodel,'+component+',TEXT("'+family+'"),bEnabled&&bInventoryWeaponReady);return;}\n    '+a)
  return t
 edit(W+file,grips)
def stock(t):
 t=header(t).replace('const bool AKM=AKMSoviet::Matches(Rifle);','const bool AKM=AKMSoviet::Matches(Rifle);\n    const bool A762=A762WeaponAssets::Matches(Rifle);')
 t=sub(t,'(bUsingM4Infima||AKM||bUseQBZ191)','(bUsingM4Infima||AKM||bUseQBZ191||A762)')
 t=sub(t,'LoadObject<UStaticMesh>(nullptr,bUseM16?','LoadObject<UStaticMesh>(nullptr,A762?*A762Attachments::MeshPath(Variant):bUseM16?')
 return sub(t,'StockMount=(bUseM16||bUseQBZ191)?','StockMount=(bUseM16||bUseQBZ191||A762)?')
edit(W+'SkeletonStockVisual.cpp',stock)
edit(W+'PhantomRearGripVisual.cpp',lambda t:sub(header(t),'const FString Path=bUseM16?','const FString Path=A762WeaponAssets::Matches(Rifle)?A762Attachments::MeshPath(Variant):bUseM16?'))
def magazine(t):
 t=header(t)
 t=sub(t,'const bool bRifle=bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel)||bUseQBZ191;','const bool A762=A762WeaponAssets::Matches(AKMViewmodel);\n    const bool bRifle=bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel)||bUseQBZ191||A762;')
 t=sub(t,'bDrum=bDrum&&(bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel))','bDrum=bDrum&&(bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel)||A762)')
 a='if(bUseQBZ191&&bDrum){'
 t=sub(t,a,'if(A762&&(bDrum||bExtMag)){\n        LargeDrum=A762Attachments::Configure(this,AKMViewmodel,LargeDrum,bDrum?TEXT("drum"):TEXT("ext_mag"),true,TEXT("WPN_SOCKET_Magazine"));\n        DrumMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));\n    }\n    '+a)
 t=sub(t,'if(bDrum&&!bUseQBZ191&&!AKMSoviet::Matches(AKMViewmodel))','if(bDrum&&!A762&&!bUseQBZ191&&!AKMSoviet::Matches(AKMViewmodel))')
 t=sub(t,'if(bExtMag)\n    {','if(bExtMag&&!A762)\n    {')
 t=t.replace('AKMSoviet::Matches(AKMViewmodel)?18.f','(AKMSoviet::Matches(AKMViewmodel)||A762WeaponAssets::Matches(AKMViewmodel))?18.f').replace('AKMSoviet::Matches(AKMViewmodel)?56.f','(AKMSoviet::Matches(AKMViewmodel)||A762WeaponAssets::Matches(AKMViewmodel))?56.f')
 t=sub(t,'const bool bAKMDrum=AKMSoviet::Matches(AKMViewmodel);','const bool bAKMDrum=AKMSoviet::Matches(AKMViewmodel)||A762WeaponAssets::Matches(AKMViewmodel);')
 return t
edit(W+'M4DrumVisual.cpp',magazine)
def muzzle(t):
 t=header(t)
 a='const FString Path=Key==TEXT("tactical_suppressor")?TacticalSuppressorAssets::MeshPath(TEXT("M4")):TEXT("/Game/Weapons/M4MuzzlesV1/SM_M4_")+Key;'
 t=sub(t,a,'const FString Path=A762Attachments::MeshPath(Key);')
 start=t.index('            const auto B=Part->GetBounds();');end=t.index('\n        }',start)
 t=t[:start]+'''            // Authored generic muzzle contract: local -Y points to the outlet.
            MuzzleLocalAxis=-FVector::RightVector;
            const double Length=Key==TEXT("tactical_suppressor")?18.68658:Key==TEXT("suppressor")?18.6:Key==TEXT("brake")?6.8:7.2;
            MuzzleLocalTip=MuzzleLocalAxis*Length;
            MuzzleAttachment->SetRelativeTransform(FTransform(FQuat(FVector::UpVector,PI),A762WeaponAssets::MuzzleMount,FVector(.01f)));'''+t[end:]
 return t
edit(W+'M4MuzzleVisual.cpp',muzzle)
def tactical(t):
 t=t.replace('#include "TacticalDeviceComponent.h"','#include "TacticalDeviceComponent.h"\n#include "A762Attachments.h"',1)
 t=sub(t,'const FString Path=Family==TEXT("M16")?','const FString Path=Family==TEXT("A762")?A762Attachments::MeshPath(Variant):Family==TEXT("M16")?')
 t=t.replace('if(!Pistol&&!ASH&&Family!=TEXT("M16")','if(!Pistol&&!ASH&&Family!=TEXT("A762")&&Family!=TEXT("M16")')
 return sub(t,'const FString Family=bUseM16?','const FString Family=A762WeaponAssets::Matches(AKMViewmodel)?TEXT("A762"):bUseM16?')
edit(W+'TacticalDeviceComponent.cpp',tactical)
edit(W+'GunsmithSystem.cpp',lambda t:sub(t,'W.Base.BurstCount=FMath::Max','W.Base.StabilityMultiplier=Num(B,TEXT("stability_mult"),1);\n        W.Base.BurstCount=FMath::Max'))
def character(t):
 t=t.replace('#include "Weapons/A762WeaponAssets.h"','#include "Weapons/A762WeaponAssets.h"\n#include "Weapons/A762Attachments.h"',1)
 t=sub(t,'if (IsPistolWeapon() || A762WeaponAssets::Matches(AKMViewmodel)) { DrumReloadAnimation = nullptr; DrumReloadEmptyAnimation = nullptr; }', '''if (IsPistolWeapon()) { DrumReloadAnimation = nullptr; DrumReloadEmptyAnimation = nullptr; }
    if (A762WeaponAssets::Matches(AKMViewmodel))
    {
        DrumReloadAnimation=LoadObject<UAnimSequence>(nullptr,*A762Attachments::AnimationPath(TEXT("base"),TEXT("drum_reload")));
        DrumReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,*A762Attachments::AnimationPath(TEXT("base"),TEXT("drum_reload_empty")));
    }''')
 return sub(t,'if(AKMSoviet::Matches(AKMViewmodel)&&bDrumInstalled)MechanicalCueTimes[0]', 'if((AKMSoviet::Matches(AKMViewmodel)||A762WeaponAssets::Matches(AKMViewmodel))&&bDrumInstalled)MechanicalCueTimes[0]')
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)

def catalog(t):
 data=json.loads(t);akm=next(w for w in data['weapons'] if w['id']=='ue_akm');a=next(w for w in data['weapons'] if w['id']=='ue_a762')
 a['allowed']=copy.deepcopy(akm['allowed']);a['options']=copy.deepcopy(akm['options'])
 for slot,options in a['options'].items():
  for v in options:
   v['description']=v['description'].replace('AKM 木护木底部','A762 护木底部').replace('AKM 木护木','A762 护木').replace('AKM','A762')
   if slot=='optic' and v['id']!='false':v['description']+=' 贴合 A762 顶部导轨，前后机械瞄具向内折叠。'
 a['options']['magazine'][2]['description']='沿 A762 原厂曲面加长的 40 发弹匣，保留供弹口、加强筋和完整底板。'
 a['base']['damage']=round(akm['base']['damage']*.95,6);a['base']['recoil']=akm['base']['recoil']*.75
 a['base']['camera_shake']=akm['base']['camera_shake'];a['base']['stability_mult']=akm['base'].get('stability_mult',1)*1.25
 a['base']['fire_interval']=60/900
 return json.dumps(data,ensure_ascii=False,indent=2)+'\n'
edit('Content/ColdSteelData/gunsmith.json',catalog)
def formula(t):
 data=json.loads(t);a=copy.deepcopy(data['ue_akm']);a['source']='A762_ITEM'
 for k in ['base','enhanceFlat']:a[k]=round(a[k]*.95,8)
 for v in a['attrs']:
  for k in ['base','perEnhance']:v[k]=round(v[k]*.95,8)
 data['ue_a762']=a
 return json.dumps(data,ensure_ascii=False,indent=2)+'\n'
edit('Content/ColdSteelData/combat-weapon-formulas.json',formula)
print('A762_CODE_AND_CATALOG_WRITTEN')
