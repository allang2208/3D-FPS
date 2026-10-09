from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
def edit(path,old,new,count=1):
 p=P/path;s=p.read_text(encoding='utf-8-sig')
 if s.count(old)<count:raise RuntimeError('Patch anchor '+path+': '+old[:90])
 p.write_text(s.replace(old,new,count),encoding='utf-8')
def inc(path):edit(path,'#include "FPSGAMECharacter.h"','#include "FPSGAMECharacter.h"\n#include "Weapons/Super90WeaponAssets.h"')
inc('Source/FPSGAME/FPSGAMECharacter.cpp')
edit('Source/FPSGAME/FPSGAMECharacter.h','    bool IsHK416Weapon() const','    bool IsSuper90Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_super90"); }\n    bool IsHK416Weapon() const')
edit('Source/FPSGAME/FPSGAMECharacter.h','    void InitializeReloadStages(bool CycleOnly);','''    void BeginSuper90Reload();
    bool AdvanceSuper90Reload();
    void FinishSuper90Reload();
    float Super90ReloadSourceTime(float RuntimeTime) const;
    int32 Super90ReloadCount = 0;
    int32 Super90ReloadCommitted = 0;
    float Super90ReloadRate = 1.f;
    float Super90ReloadTail = 0.f;
    bool bSuper90CancelReload = false;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Super90WalkAnimation;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Super90RunAnimation;
    void InitializeReloadStages(bool CycleOnly);''')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    bUsingReplacement = ViewmodelMesh != nullptr;','''    if (IsSuper90Weapon())
    {
        ViewmodelMesh=LoadObject<USkeletalMesh>(nullptr,Super90WeaponAssets::MeshPath);
        bUsingM4Infima=ViewmodelMesh!=nullptr;
        bSingleShotTrigger=true;
        bPistolShotPending=false;
        HipViewmodelLocation=M4HipViewmodelLocation;
        ADSRearEyeDistance=18.f;
        if(!bPresentationOnly)QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*Super90WeaponAssets::AnimationPath(TEXT("quick_melee")));
    }
    bUsingReplacement = ViewmodelMesh != nullptr;''')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    AimAnimation = LoadAKMAnimation(TEXT("A_AKM_aim"));','''    Super90WalkAnimation=IsSuper90Weapon()?LoadAKMAnimation(TEXT("A_AKM_walk")):nullptr;
    Super90RunAnimation=IsSuper90Weapon()?LoadAKMAnimation(TEXT("A_AKM_run")):nullptr;
    AimAnimation = LoadAKMAnimation(TEXT("A_AKM_aim"));''')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','SVDWeaponAssets::Matches(AKMViewmodel)?nullptr:LoadObject<UAnimSequence>','(IsSuper90Weapon()||SVDWeaponAssets::Matches(AKMViewmodel))?nullptr:LoadObject<UAnimSequence>',2)
edit('Source/FPSGAME/FPSGAMECharacter.cpp','InspectAnimation = IsHK416Weapon()','InspectAnimation = IsSuper90Weapon() || IsHK416Weapon()')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','if (!bSharedDrum && bUsingM4Infima && !IsHK416Weapon()','if (!bSharedDrum && bUsingM4Infima && !IsSuper90Weapon() && !IsHK416Weapon()')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','if (bUsingM4Infima && !IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))','if (bUsingM4Infima && !IsSuper90Weapon() && !IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{','''UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)
{
    if(IsSuper90Weapon())
    {
        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));
        if(Clip==TEXT("aim"))Clip=TEXT("idle");
        else if(Clip==TEXT("aim_fire"))Clip=TEXT("fire");
        else if(Clip==TEXT("reload"))Clip=TEXT("reload_one");
        else if(Clip==TEXT("reload_empty"))Clip=TEXT("reload_full");
        else if(Clip.StartsWith(TEXT("equip")))Clip=TEXT("equip");
        return LoadObject<UAnimSequence>(nullptr,*Super90WeaponAssets::AnimationPath(*Clip));
    }''')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{','UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{\n    if(IsSuper90Weapon())return QuickCombatAnimation;')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    const bool ResumeCycle=PendingAmmoType.IsEmpty() && NeedsReloadCycle();','    if(IsSuper90Weapon()){BeginSuper90Reload();return;}\n    const bool ResumeCycle=PendingAmmoType.IsEmpty() && NeedsReloadCycle();')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    if(UnarmedIdle&&UnarmedIdle->IsEquipped()){UnarmedIdle->SetTriggerHeld(true);return;}','    if(UnarmedIdle&&UnarmedIdle->IsEquipped()){UnarmedIdle->SetTriggerHeld(true);return;}\n    if(IsSuper90Weapon()&&IsReloading())bSuper90CancelReload=true;')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','float AFPSGAMECharacter::ReloadSourceTime(float RuntimeTime) const\n{','float AFPSGAMECharacter::ReloadSourceTime(float RuntimeTime) const\n{\n    if(IsSuper90Weapon())return Super90ReloadSourceTime(RuntimeTime);')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','void AFPSGAMECharacter::FinishReload()\n{','void AFPSGAMECharacter::FinishReload()\n{\n    if(IsSuper90Weapon()){FinishSuper90Reload();return;}')
edit('Source/FPSGAME/FPSGAMECharacterReload.cpp','bool AFPSGAMECharacter::AdvanceReloadStages()\n{','bool AFPSGAMECharacter::AdvanceReloadStages()\n{\n    if(IsSuper90Weapon())return AdvanceSuper90Reload();')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','const bool bUseActionFraming = (bUsingM4Infima','const bool bUseActionFraming = !IsSuper90Weapon() && (bUsingM4Infima')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    if (ActiveActionAnimation)\n    {\n        // A reload','''    if(IsSuper90Weapon())
    {
        GunplayAnimation->SprintClip=bIsSprinting?Super90RunAnimation:Super90WalkAnimation;
        const float Length=GunplayAnimation->SprintClip?GunplayAnimation->SprintClip->GetPlayLength():1.f;
        GunplayAnimation->SprintTime=FMath::Fmod(FeedbackTime,FMath::Max(.01f,Length));
        GunplayAnimation->SprintAlpha=!IsWeaponBusy()&&!IsTraversing()&&!IsCastBlockingLeftHandAction()
            ? FMath::Clamp(HorizontalSpeed()/100.f,0.f,1.f)*(1.f-WeaponADSFactor):0.f;
    }
    if (ActiveActionAnimation)
    {
        // A reload''')
# The shared shot transaction fires sound/recoil once, then traces each pellet independently.
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    const float ShotDamage=DamagePerShot*ConvergenceScale;','    const int32 PelletCount=IsSuper90Weapon()?Super90WeaponAssets::PelletCount:1;\n    const float ShotDamage=DamagePerShot*ConvergenceScale/PelletCount;')
edit('Source/FPSGAME/FPSGAMECharacter.cpp','    FHitResult Hit;\n    FCollisionQueryParams Params(SCENE_QUERY_STAT(AKMFire)','''    for(int32 Pellet=0;Pellet<PelletCount;++Pellet)
    {
    const FVector PelletDirection=PelletCount>1?FMath::VRandCone(TraceDirection,FMath::DegreesToRadians(Super90WeaponAssets::PelletConeDegrees)):TraceDirection;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(AKMFire)''')
p=P/'Source/FPSGAME/FPSGAMECharacter.cpp';s=p.read_text(encoding='utf-8');start=s.index('    FHitResult Hit;\n    FCollisionQueryParams Params(SCENE_QUERY_STAT(AKMFire)');end=s.index('    ApplyShotFeedback();',start);block=s[start:end].replace('TraceDirection','PelletDirection').replace('    WeaponFX->OnShotAtMuzzle(bIsAiming,ShotMuzzle);\n','');s=s[:start]+block+'    }\n    WeaponFX->OnShotAtMuzzle(bIsAiming,ShotMuzzle);\n'+s[end:];p.write_text(s,encoding='utf-8')
# Explicit catalog/presentation allowlists.
edit('Source/FPSGAME/FPSGAMECharacterProfile.cpp','I->Definition==TEXT("ue_svd")','I->Definition==TEXT("ue_super90")||I->Definition==TEXT("ue_svd")')
edit('Source/FPSGAME/Weapons/RifleHipFraming.cpp','return Definition == TEXT("ue_m4a1")','return Definition == TEXT("ue_super90") || Definition == TEXT("ue_m4a1")')
edit('Source/FPSGAME/Weapons/RifleHipFraming.cpp','else if (Definition == TEXT("ue_svd")) Forward = 10.f;','else if (Definition == TEXT("ue_svd")) Forward = 10.f;\n    else if (Definition == TEXT("ue_super90")) Forward = 6.f;')
for file in ('ColdSteelPickupStudio.cpp','ColdSteelPickupWeapon.cpp'):
 edit('Source/FPSGAME/UI/'+file,'if(Item.Definition!=TEXT("ue_m4a1")','if(Item.Definition!=TEXT("ue_super90")&&Item.Definition!=TEXT("ue_m4a1")')
edit('Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp','||I.Definition==TEXT("ue_svd")','||I.Definition==TEXT("ue_super90")||I.Definition==TEXT("ue_svd")')
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp','#include "ColdSteelWeaponIcons.h"','#include "ColdSteelWeaponIcons.h"\n#include "Weapons/Super90WeaponAssets.h"')
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp','if(D==TEXT("ue_svd")){Add(', 'if(D==TEXT("ue_super90")){Add(Super90WeaponAssets::MeshPath,true);Add(Super90WeaponAssets::AnimationPath(TEXT("idle")),true);}\n        else if(D==TEXT("ue_svd")){Add(')
edit('Source/FPSGAME/Weapons/WeaponStatEvaluation.cpp','{TEXT("ammo_357"),TEXT(".357 MAG")}','{TEXT("ammo_12g"),TEXT("12 gauge")},{TEXT("ammo_357"),TEXT(".357 MAG")}')
inc('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp')
edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp','    if (FireTokenBucket < 1.f)','''    const float HitTokenCost=OutDeclaredItem&&OutDeclaredItem->Definition==Super90WeaponAssets::Definition
        && Report.AttackMeta==0?1.f/Super90WeaponAssets::PelletCount:1.f;
    if (FireTokenBucket < HitTokenCost)''')
edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp','    FireTokenBucket -= 1.f;','    FireTokenBucket -= HitTokenCost;')
edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp','    return Panel * ConvergenceScale\n        * WeaponDamageFalloff','    const float PelletScale=Item&&Item->Definition==Super90WeaponAssets::Definition?1.f/Super90WeaponAssets::PelletCount:1.f;\n    return Panel * ConvergenceScale * PelletScale\n        * WeaponDamageFalloff')
print('SUPER90_RUNTIME_WRITTEN')
