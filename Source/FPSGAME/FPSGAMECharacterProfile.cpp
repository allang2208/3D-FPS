#include "FPSGAMECharacter.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Production/ProductionToolComponent.h"
#include "Weapons/RuneSwordComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelEnhancementSystem.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/WeaponStatEvaluation.h"
#include "Movement/FPSTraversalComponent.h"

void AFPSGAMECharacter::ApplyColdSteelProfile(UColdSteelStatusModel* Profile)
{
    if(!Profile)return;
    const auto P=Profile->Snapshot();
    if(auto* H=FindComponentByClass<UFPSCombatHealthComponent>()){H->MaxHealth=Profile->Derived(TEXT("maxHp"));H->Health=FMath::Clamp(P.Health,0.f,H->MaxHealth);}
    const auto* I=Profile->Equipped();const FString Id=I?I->InstanceId:TEXT("");
    const bool WasWeaponReady=bInventoryWeaponReady;
    bInventoryWeaponReady=!Profile->ActiveProductionTool()&&I&&(I->Definition==TEXT("ue_m4a1")||I->Definition==TEXT("ue_akm")||I->Definition==TEXT("ue_qbz191")||(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_dan_wesson715")));
    const bool ChangedWeapon=ActiveInventoryWeapon!=Id||WasWeaponReady!=bInventoryWeaponReady;
    const bool PistolInput=ChangedWeapon&&bInventoryWeaponReady&&(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_dan_wesson715"));
    const bool ResumePistolAim=PistolInput&&bAimHeld;
    const bool ResumePistolFire=PistolInput&&bFireHeld;
    if(ChangedWeapon){
        VisualRecoilUpdatedAt=-1.;LastVisualShotAt=VisualRecoverAt=-10.;VisualBurstIndex=0;
        GunKickPosition=GunKickPositionVelocity=GunKickRotation=GunKickRotationVelocity=FVector::ZeroVector;
        GunJitterPosition=GunJitterPositionVelocity=GunJitterRotation=GunJitterRotationVelocity=FVector::ZeroVector;
        GunFlip=GunFlipVelocity=0.f;
        bReloadAfterCasting=false;
        bRevolverReloadAfterFire=false;
        if (IsTraversing()) Traversal->Cancel();
        StopMechanicalAudio();
        FireReleased();AimReleased();
        ActiveInventoryWeapon=Id;
        if(bInventoryWeaponReady){bUseM4Infima=I->Definition==TEXT("ue_m4a1");bUseQBZ191=I->Definition==TEXT("ue_qbz191");bUseM1911=I->Definition==TEXT("ue_m1911");bUseDanWesson715=I->Definition==TEXT("ue_dan_wesson715");InitializeWeaponVisuals();StartEquipCharge();}
        else {WeaponState=EAKMWeaponState::Idle;WeaponStateElapsed=WeaponStateDuration=0;}
    }
    AKMViewmodel->SetVisibility(bInventoryWeaponReady && !IsTraversing(),true);
    if(auto* Tools=FindComponentByClass<UProductionToolComponent>())Tools->RefreshHeldTool();
    if(RuneSword)RuneSword->RefreshEquipment(Profile);
    // Handling stays in UE units; damage resolves through the canonical gamedev weapon formula below.
    const auto* Defaults=GetClass()->GetDefaultObject<AFPSGAMECharacter>();
    PistolMoveSpeedMultiplier=bInventoryWeaponReady?Profile->PistolMovementMultiplier():1.f;
    WalkSpeed=Defaults->WalkSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    SprintSpeed=Defaults->SprintSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    ADSWalkSpeed=Defaults->ADSWalkSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    CrouchSpeed=Defaults->CrouchSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    WeaponHandling=FWeaponHandling();
    BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale;
    ProjectileSpeedCM=9000.f;
    TraceDistance=Defaults->TraceDistance;
    EffectiveWeaponRangeCM=Defaults->TraceDistance;
    HipSpreadMultiplier=1.f;
    DamagePerShot=Defaults->DamagePerShot+Profile->Derived(TEXT("atk"));
    FireInterval=Defaults->FireInterval;
    ReloadDuration=Defaults->ReloadDuration;EmptyReloadDuration=Defaults->EmptyReloadDuration;
    if(auto* Gunsmith=GetGameInstance()->GetSubsystem<UGunsmithSystem>())
    {
        const auto Parts=I?Gunsmith->Installed(*I):FGunsmithParts();
        // Autosave republishes the profile every five seconds; keep the active
        // instance's transient preview until Apply/Undo/Close resolves it.
        const auto& VisualParts=I&&Gunsmith->IsOpen()&&Gunsmith->Instance()==I->InstanceId?Gunsmith->Draft():Parts;
        SetGunsmithOpticVariant(VisualParts.FindRef(TEXT("optic")));
        SetGunsmithDrum(VisualParts.FindRef(TEXT("magazine"))==TEXT("large_drum"));
        SetGunsmithMuzzle(VisualParts.FindRef(TEXT("muzzle")));
        SetGunsmithHandstop(VisualParts.FindRef(TEXT("underbarrel")));
        SetGunsmithStock(VisualParts.FindRef(TEXT("stock")));
        SetGunsmithRearGrip(VisualParts.FindRef(TEXT("reargrip")));
        SetGunsmithTactical(VisualParts.FindRef(TEXT("tactical")));
        bDrumInstalled=Parts.FindRef(TEXT("magazine"))==TEXT("large_drum");
        bRevolverSpeedloaderInstalled=bUseDanWesson715&&Parts.FindRef(TEXT("reload_device"))==TEXT("dw715_speedloader");
        ADSInDuration=Defaults->ADSInDuration;
        MagazineCapacity=Defaults->MagazineCapacity;ReloadDuration=Defaults->ReloadDuration;EmptyReloadDuration=Defaults->EmptyReloadDuration;
        if(I&&Gunsmith->Weapon(I->Definition))
        {const auto Stats=Gunsmith->Calculate(I->Definition,Parts);ADSInDuration=Stats.ADS;MagazineCapacity=Stats.Capacity;ReloadDuration=Stats.Reload;EmptyReloadDuration=Stats.EmptyReload;
            WeaponHandling=Stats.Handling;BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale*WeaponHandling.RecoilScale;ProjectileSpeedCM=Stats.Speed*100.f;
            HipSpreadMultiplier=FMath::Max(0.f,static_cast<float>(Stats.Spread));
            EffectiveWeaponRangeCM=FMath::Max(1.f,static_cast<float>(Stats.Range*100.));
            // Keep ballistic lifetime separate from the full-damage range.
            TraceDistance=FMath::Max(Defaults->TraceDistance,EffectiveWeaponRangeCM*3.f);
            DamagePerShot=Stats.Damage+Profile->Derived(TEXT("atk"));if(I->Definition!=TEXT("ue_m4a1"))FireInterval=Stats.Interval;}
    }
    // Rebuild from weapon/attachment values on each publication; never compound
    // the passive bonus into the previous duration. Active action clocks stay fixed.
    ReloadDuration=ColdSteelWeaponStats::Reload(Profile,ReloadDuration);
    EmptyReloadDuration=ColdSteelWeaponStats::Reload(Profile,EmptyReloadDuration);
    FireInterval=ColdSteelWeaponStats::Interval(I,Profile,FireInterval);
    if(I)DamagePerShot=ColdSteelWeaponStats::Damage(*I,Profile,DamagePerShot-Profile->Derived(TEXT("atk")));
    MagazineAmmo=I&&I->Definition!=TEXT("ue_rune_sword")?FMath::Clamp(I->Magazine,0,MagazineCapacity):0;ReserveAmmo=I&&I->Definition==TEXT("ue_rune_sword")?0:Profile->AmmoCount();
    if(RuneSword && RuneSword->IsEquipped())
    {DamagePerShot=RuneSword->EquippedDamage();FireInterval=RuneSword->AttackSeconds();MagazineCapacity=0;ReloadDuration=EmptyReloadDuration=0;}
    if (bUseDanWesson715 && I)
        RevolverCaseCount = FMath::Clamp(static_cast<int32>(ColdSteelInventory::Number(*I, TEXT("revolver_case_count"), I->Magazine)), MagazineAmmo, 6);
    // Attachment setters above own each child's equipped visibility. Propagating
    // here would resurrect optics and tactical bodies just switched to factory.
    AKMViewmodel->SetVisibility(bInventoryWeaponReady && !IsTraversing());
    // Reapply held input only after the new pistol's magazine and stats exist.
    // A held trigger starts one semiautomatic shot, then still requires release.
    if(DualPistols)DualPistols->RefreshEquipment(Profile);
    if(!IsDualWieldingPistols())
    {
        if(ResumePistolAim)AimPressed();
        if(ResumePistolFire)FirePressed();
    }
}
void AFPSGAMECharacter::EndPlay(const EEndPlayReason::Type Reason)
{
    StopMechanicalAudio();
    if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->SaveNow();
    Super::EndPlay(Reason);
}
