"""Apply only M870 integration hunks to the current shared working files."""
from pathlib import Path
import re,json
O=Path(__file__).parent;P=O.parents[1];changed=[]
def edit(file,fn):
 p=P/file;old=p.read_text(encoding='utf-8-sig');new=fn(old)
 if old==new:return
 backup=O/'Before'/file;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(p.read_bytes())
 p.write_text(new,encoding='utf-8',newline='');changed.append(file)
def once(text,old,new):
 if old not in text:raise RuntimeError('Missing integration anchor: '+old[:100])
 return text.replace(old,new,1)
def include(s):return once(s,'#include "Super90WeaponAssets.h"','#include "Super90WeaponAssets.h"\n#include "TubeShotgunAssets.h"') if '#include "Super90WeaponAssets.h"' in s else once(s,'#include "../Weapons/Super90WeaponAssets.h"','#include "../Weapons/Super90WeaponAssets.h"\n#include "../Weapons/TubeShotgunAssets.h"')
def character(s):
 s=once(s,'#include "Weapons/Super90WeaponAssets.h"','#include "Weapons/Super90WeaponAssets.h"\n#include "Weapons/TubeShotgunAssets.h"')
 s=s.replace('IsSuper90Weapon()','IsTubeShotgunWeapon()')
 s=once(s,'LoadObject<USkeletalMesh>(nullptr,Super90WeaponAssets::MeshPath)','LoadObject<USkeletalMesh>(nullptr,IsM870Weapon()?M870WeaponAssets::MeshPath:Super90WeaponAssets::MeshPath)')
 s=once(s,'*Super90WeaponAssets::AnimationPath(TEXT("quick_melee"))','*(IsM870Weapon()?M870WeaponAssets::AnimationPath(TEXT("quick_melee")):Super90WeaponAssets::AnimationPath(TEXT("quick_melee")))')
 s=once(s,': IsTubeShotgunWeapon() ? ERifleSprintWeapon::Super90',': IsM870Weapon() ? ERifleSprintWeapon::M870\n            : IsSuper90Weapon() ? ERifleSprintWeapon::Super90')
 s=once(s,'ServiceRevolverReloadAfterFire();','UpdateM870PumpAudio();\n    ServiceRevolverReloadAfterFire();')
 s=once(s,'FMath::Max(Super90WeaponAssets::MinimumAttackInterval,Interval)','FMath::Max(TubeShotgunAssets::MinimumInterval(ActiveInventoryWeaponDefinition),Interval)')
 s=once(s,'const float ShotLength=Animation==PistolFireLastAnimation','const float ShotLength=!IsM870Weapon()&&Animation==PistolFireLastAnimation')
 s=once(s,'PlayWeaponAnimation(Animation, false, ShotAnimationRate);','PlayWeaponAnimation(Animation, false, ShotAnimationRate);\n    if(IsM870Weapon())M870PumpCueMask=0;')
 s=once(s,'if(IsTubeShotgunWeapon() && Animation == PistolFireLastAnimation)','if(IsSuper90Weapon() && Animation == PistolFireLastAnimation)')
 s=once(s,'return LoadObject<UAnimSequence>(nullptr,*Super90WeaponAssets::AnimationPath(*Clip));','if(IsM870Weapon()&&Clip==TEXT("fire_last"))Clip=TEXT("fire");\n        return LoadObject<UAnimSequence>(nullptr,*(IsM870Weapon()?M870WeaponAssets::AnimationPath(*Clip):Super90WeaponAssets::AnimationPath(*Clip)));')
 s=once(s,'if(Cue)return LoadObject<USoundBase>(nullptr,*FString::Printf(','''if(IsM870Weapon())
        {
            if(FCString::Strcmp(AssetName,TEXT("S_AKM_ChargePull"))==0)Cue=TEXT("PumpPull");
            else if(FCString::Strcmp(AssetName,TEXT("S_AKM_ChargeRelease"))==0)Cue=TEXT("PumpPush");
            else if(FCString::Strcmp(AssetName,TEXT("S_AKM_Equip"))==0)Cue=TEXT("Equip");
            if(Cue)return LoadObject<USoundBase>(nullptr,*M870WeaponAssets::SoundPath(Cue));
        }
        if(Cue)return LoadObject<USoundBase>(nullptr,*FString::Printf(''')
 s=once(s,'const bool bGunBusy=HasOffhandPistol()?DualPistols->IsReloading():','const bool bPumpBusy=IsM870Weapon()&&IsRevolverFireActionPlaying();\n    const bool bGunBusy=HasOffhandPistol()?DualPistols->IsReloading():')
 s=once(s,'return IsDoorPushActive() || IsTraversing() || Traversal->IsWeaponRecovering()', 'return bPumpBusy || IsDoorPushActive() || IsTraversing() || Traversal->IsWeaponRecovering()')
 return s
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda s:once(s,'    bool IsSuper90Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_super90"); }','''    bool IsSuper90Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_super90"); }
    bool IsM870Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_m870"); }
    bool IsTubeShotgunWeapon() const { return IsSuper90Weapon() || IsM870Weapon(); }
    float M870PumpPlayRate() const;
    void UpdateM870PumpAudio();
    uint8 M870PumpCueMask=0;'''))
def reload(s):
 s=once(s,'#include "Weapons/Super90WeaponAssets.h"','#include "Weapons/Super90WeaponAssets.h"\n#include "Weapons/M870WeaponAssets.h"').replace('IsSuper90Weapon()','IsTubeShotgunWeapon()')
 s=once(s,'if(!bInventoryWeaponReady || IsWeaponBusy() || IsCastBlockingLeftHandAction())return;','if(IsM870Weapon()&&IsRevolverFireActionPlaying()){bRevolverReloadAfterFire=true;return;}\n    if(!bInventoryWeaponReady || IsWeaponBusy() || IsCastBlockingLeftHandAction())return;')
 s=s.replace('bReloadCycleOnly?CycleBoltReady:BoltRelease','IsM870Weapon()?(bReloadCycleOnly?M870WeaponAssets::PumpClosed:M870WeaponAssets::ReloadClosed):(bReloadCycleOnly?CycleBoltReady:BoltRelease)')
 s=s.replace('MechanicalCueTimes.Add(CycleBoltReleaseCue);','MechanicalCueTimes.Add(IsM870Weapon()?.40f:CycleBoltReleaseCue);')
 s=s.replace('MechanicalCueTimes.Add(NativeBoltReleaseCue);','MechanicalCueTimes.Add(IsM870Weapon()?6.48f:NativeBoltReleaseCue);')
 return s
edit('Source/FPSGAME/FPSGAMECharacterSuper90.cpp',reload)
def loader(s):
 s=include(s)
 s=once(s,'if(!IsSuper90Weapon())return;','''if(IsM870Weapon())
    {
        Super90LoaderEmpty.SetNum(1);
        Super90LoaderEmpty[0]=LoadObject<UAnimSequence>(nullptr,*M870WeaponAssets::AnimationPath(TEXT("cycle")));
        return;
    }
    if(!IsSuper90Weapon())return;''')
 # Shared shell visibility is part of the per-shell animation, not the loader.
 s=s.replace('void AFPSGAMECharacter::UpdateSuper90SpeedloaderVisual()\n{\n    if(!IsSuper90Weapon())return;','void AFPSGAMECharacter::UpdateSuper90SpeedloaderVisual()\n{\n    if(!IsTubeShotgunWeapon())return;')
 s=s.replace('if(IsSuper90Weapon())Super90WeaponAssets::SetLooseShellVisible','if(IsTubeShotgunWeapon())Super90WeaponAssets::SetLooseShellVisible')
 return s
edit('Source/FPSGAME/Weapons/Super90SpeedloaderVisual.cpp',loader)
for f in ('ColdSteelSuper90Authority.cpp','ColdSteelPlayerState.cpp'):
 def net(s):
  s=include(s).replace('IsSuper90Weapon()','IsTubeShotgunWeapon()')
  for expr in ('Gun->Definition','Item.Definition','I.Definition','OutDeclaredItem->Definition','Item->Definition','Report.ItemDefinition'):
   s=s.replace(expr+'!=Super90WeaponAssets::Definition','!TubeShotgunAssets::Supports('+expr+')').replace(expr+'==Super90WeaponAssets::Definition','TubeShotgunAssets::Supports('+expr+')')
  if f=='ColdSteelSuper90Authority.cpp':
   s=once(s,'R.CycleOnly?CycleBoltReady:BoltRelease','Pawn->IsM870Weapon()?(R.CycleOnly?M870WeaponAssets::PumpClosed:M870WeaponAssets::ReloadClosed):(R.CycleOnly?CycleBoltReady:BoltRelease)')
  return s
 edit('Source/FPSGAME/Multiplayer/'+f,net)
edit('Source/FPSGAME/Weapons/WeaponStatEvaluation.cpp',lambda s:include(s).replace('Item->Definition==Super90WeaponAssets::Definition','TubeShotgunAssets::Supports(Item->Definition)').replace('Super90WeaponAssets::MinimumAttackInterval','TubeShotgunAssets::MinimumInterval(Item->Definition)'))
edit('Source/FPSGAME/FPSGAMECharacterProfile.cpp',lambda s:s.replace('I->Definition==TEXT("ue_super90")||','I->Definition==TEXT("ue_super90")||I->Definition==TEXT("ue_m870")||'))
for f in ('ColdSteelWeaponIcons.cpp','ColdSteelPickupStudio.cpp'):
 edit('Source/FPSGAME/UI/'+f,lambda s:s.replace('I.Definition==TEXT("ue_super90")||','I.Definition==TEXT("ue_super90")||I.Definition==TEXT("ue_m870")||').replace('D==TEXT("ue_super90")||','D==TEXT("ue_super90")||D==TEXT("ue_m870")||'))
edit('Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp',lambda s:s.replace('Item.Definition!=TEXT("ue_super90")&&','Item.Definition!=TEXT("ue_super90")&&Item.Definition!=TEXT("ue_m870")&&'))
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',lambda s:once(include(s),'if(D==TEXT("ue_super90")){Add(Super90WeaponAssets::MeshPath,true);Add(Super90WeaponAssets::AnimationPath(TEXT("idle")),true);}','if(D==TEXT("ue_super90")){Add(Super90WeaponAssets::MeshPath,true);Add(Super90WeaponAssets::AnimationPath(TEXT("idle")),true);}\n        if(D==M870WeaponAssets::Definition){Add(M870WeaponAssets::MeshPath,true);Add(M870WeaponAssets::AnimationPath(TEXT("idle")),true);}'))
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',lambda s:once(s,'{TEXT("ue_super90"), TEXT("ue_hk416")','{TEXT("ue_m870"), TEXT("ue_super90"), TEXT("ue_hk416")').replace('FString(Definition)==TEXT("ue_super90")','(FString(Definition)==TEXT("ue_super90")||FString(Definition)==TEXT("ue_m870"))'))
edit('Source/FPSGAME/Characters/FPSPlayerBodyGunEffects.cpp',lambda s:include(s).replace('W.GunDefinition==TEXT("ue_super90")','TubeShotgunAssets::Supports(W.GunDefinition)').replace('B.Definition.GunDefinition==TEXT("ue_super90")','TubeShotgunAssets::Supports(B.Definition.GunDefinition)'))
edit('Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp',lambda s:include(s).replace('Asset->GetPathName()==Super90WeaponAssets::MeshPath\n                    &&','TubeShotgunAssets::MatchesMesh(Asset->GetPathName())\n                    &&'))
edit('Source/FPSGAME/Weapons/RifleHipFraming.cpp',lambda s:s.replace('Definition == TEXT("ue_super90")','(Definition == TEXT("ue_super90") || Definition == TEXT("ue_m870"))'))
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.h',lambda s:s.replace('SVD, Super90 };','SVD, Super90, M870 };'))
def sprint(s):
 s=include(s)
 return once(s,'if (Weapon==ERifleSprintWeapon::Super90)','''if (Weapon==ERifleSprintWeapon::M870)
    {
        for(int32 Grip=0;Grip<6;++Grip)
            for(const TCHAR* Role:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*M870WeaponAssets::AnimationPath(Role)));
        return;
    }
    if (Weapon==ERifleSprintWeapon::Super90)''')
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.cpp',sprint)
edit('Source/FPSGAME/FPSGAMECharacterReload.cpp',lambda s:s.replace('IsSuper90Weapon()','IsTubeShotgunWeapon()'))
edit('Source/FPSGAME/UI/ColdSteelCrosshair.cpp',lambda s:s.replace('IsSuper90Weapon()','IsTubeShotgunWeapon()'))
edit('Source/FPSGAME/Weapons/M4MuzzleVisual.cpp',lambda s:s.replace('IsPistolWeapon()||IsSuper90Weapon()','IsPistolWeapon()||IsTubeShotgunWeapon()').replace('if(!IsSuper90Weapon())return 1.f;','if(!IsTubeShotgunWeapon())return 1.f;'))
for f in ('Source/FPSGAME/Characters/FPSPlayerBodyMotion.cpp','Source/FPSGAME/UI/M4GunsmithPreview.cpp'):
 def hidden(s):
  s=include(s)
  s=s.replace('Asset->GetPathName()==Super90WeaponAssets::MeshPath','TubeShotgunAssets::MatchesMesh(Asset->GetPathName())')
  s=s.replace('Binding.Definition.Mesh.ToSoftObjectPath().ToString()==Super90WeaponAssets::MeshPath','TubeShotgunAssets::MatchesMesh(Binding.Definition.Mesh.ToSoftObjectPath().ToString())')
  return s
 edit(f,hidden)
def reload_camera(s):
 s=s.replace('#include "Weapons/Super90WeaponAssets.h"','#include "Weapons/Super90WeaponAssets.h"\n#include "Weapons/M870WeaponAssets.h"').replace('IsSuper90Weapon()','IsTubeShotgunWeapon()')
 return once(s,'if(bPendingEmptyReload)Track.Add(bReloadCycleOnly?CycleBoltReady:\n                    Super90ReloadTail+BoltRelease-TailBegin,E::Release);','''if(bPendingEmptyReload)Track.Add(IsM870Weapon()
                    ?(bReloadCycleOnly?M870WeaponAssets::PumpClosed:Super90ReloadTail+M870WeaponAssets::ReloadClosed-TailBegin)
                    :(bReloadCycleOnly?CycleBoltReady:Super90ReloadTail+BoltRelease-TailBegin),E::Release);''')
edit('Source/FPSGAME/FPSGAMECharacterReloadCamera.cpp',reload_camera)
def fx(s):
 s=include(s)
 s=s.replace('InWeaponMesh->GetSkeletalMeshAsset()->GetPathName()==Super90WeaponAssets::MeshPath','TubeShotgunAssets::MatchesMesh(InWeaponMesh->GetSkeletalMeshAsset()->GetPathName())')
 s=s.replace('WeaponMesh->GetSkeletalMeshAsset()->GetPathName()==Super90WeaponAssets::MeshPath','TubeShotgunAssets::MatchesMesh(WeaponMesh->GetSkeletalMeshAsset()->GetPathName())')
 s=once(s,'void UFPSWeaponFXComponent::Initialize(USkeletalMeshComponent* InWeaponMesh, UCameraComponent* InCamera)\n{','void UFPSWeaponFXComponent::Initialize(USkeletalMeshComponent* InWeaponMesh, UCameraComponent* InCamera)\n{\n    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(PumpEjectTimer);')
 old='if (const auto* OwnerCharacter = Cast<AFPSGAMECharacter>(GetOwner()); bWorldGun?!bWorldRevolver:(bIndependentPistol?!bIndependentRevolver:(!OwnerCharacter || !OwnerCharacter->bUseDanWesson715))) SpawnCasing();'
 s=once(s,old,'''const auto* OwnerCharacter=Cast<AFPSGAMECharacter>(GetOwner());
    const bool Pump=bWorldGun?WorldGunDefinition==FName(M870WeaponAssets::Definition):OwnerCharacter&&OwnerCharacter->IsM870Weapon();
    if(Pump)
    {
        const float Rate=OwnerCharacter?OwnerCharacter->M870PumpPlayRate():1.f;
        const TWeakObjectPtr<USkeletalMeshComponent> FiredMesh=WeaponMesh;
        GetWorld()->GetTimerManager().SetTimer(PumpEjectTimer,FTimerDelegate::CreateWeakLambda(this,[this,FiredMesh]()
        {if(FiredMesh.IsValid()&&WeaponMesh==FiredMesh.Get())SpawnCasing();}),M870WeaponAssets::PumpEject/Rate,false);
    }
    else if(bWorldGun?!bWorldRevolver:(bIndependentPistol?!bIndependentRevolver:(!OwnerCharacter||!OwnerCharacter->bUseDanWesson715)))SpawnCasing();''')
 if '#include "TimerManager.h"' not in s:s=once(s,'#include "FPSWeaponFXComponent.h"','#include "FPSWeaponFXComponent.h"\n#include "TimerManager.h"')
 return s
edit('Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp',fx)
edit('Source/FPSGAME/Weapons/FPSWeaponFXComponent.h',lambda s:once(s,'    void SpawnCasing();','    FTimerHandle PumpEjectTimer;\n    void SpawnCasing();'))
(O/'runtime_changes.json').write_text(json.dumps(changed,indent=2));print('M870_RUNTIME_SOURCE',len(changed),'files')
(O/'runtime_changes.json').write_text(json.dumps(changed,indent=2));print('M870_RUNTIME_SOURCE',len(changed),'files')
