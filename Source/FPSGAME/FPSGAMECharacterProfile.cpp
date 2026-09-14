#include "FPSGAMECharacter.h"
#include "Production/ProductionToolComponent.h"
#include "Movement/FPSTraversalComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Weapons/GunsmithSystem.h"

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
    // Existing UE weapon tuning is retained as the weapon contribution; six-dimensional base attack is additive.
    const auto* Defaults=GetClass()->GetDefaultObject<AFPSGAMECharacter>();
    WeaponHandling=FWeaponHandling();
    BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale;
    ProjectileSpeedCM=9000.f;
    HipSpreadMultiplier=1.f;
    DamagePerShot=Defaults->DamagePerShot+Profile->Derived(TEXT("atk"));
    FireInterval=Defaults->FireInterval/FMath::Max(1.f,Profile->Derived(TEXT("aspd")));
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
        SetGunsmithTactical(VisualParts.FindRef(TEXT("tactical")));
        bDrumInstalled=Parts.FindRef(TEXT("magazine"))==TEXT("large_drum");
        bRevolverSpeedloaderInstalled=bUseDanWesson715&&Parts.FindRef(TEXT("reload_device"))==TEXT("dw715_speedloader");
        ADSInDuration=Defaults->ADSInDuration;
        MagazineCapacity=Defaults->MagazineCapacity;ReloadDuration=Defaults->ReloadDuration;EmptyReloadDuration=Defaults->EmptyReloadDuration;
        if(I&&Gunsmith->Weapon(I->Definition))
        {const auto Stats=Gunsmith->Calculate(I->Definition,Parts);ADSInDuration=Stats.ADS;MagazineCapacity=Stats.Capacity;ReloadDuration=Stats.Reload;EmptyReloadDuration=Stats.EmptyReload;
            WeaponHandling=Stats.Handling;BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale*WeaponHandling.RecoilScale;ProjectileSpeedCM=Stats.Speed*100.f;HipSpreadMultiplier=FMath::Max(0.f,static_cast<float>(Stats.Spread));
            if(I->Definition==TEXT("ue_akm")||I->Definition==TEXT("ue_qbz191")||(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_dan_wesson715"))){DamagePerShot=Stats.Damage+Profile->Derived(TEXT("atk"));FireInterval=Stats.Interval/FMath::Max(1.f,Profile->Derived(TEXT("aspd")));}}
    }
    if(I)DamagePerShot=Profile->RifleWeaponDamage(*I,DamagePerShot-Profile->Derived(TEXT("atk")))+Profile->Derived(TEXT("atk"));
    MagazineAmmo=I?FMath::Clamp(I->Magazine,0,MagazineCapacity):0;ReserveAmmo=Profile->AmmoCount();
    if (bUseDanWesson715 && I)
        RevolverCaseCount = FMath::Clamp(static_cast<int32>(ColdSteelInventory::Number(*I, TEXT("revolver_case_count"), I->Magazine)), MagazineAmmo, 6);
    // Attachment setters above own each child's equipped visibility. Propagating
    // here would resurrect optics and tactical bodies just switched to factory.
    AKMViewmodel->SetVisibility(bInventoryWeaponReady && !IsTraversing());
    // Reapply held input only after the new pistol's magazine and stats exist.
    // A held trigger starts one semiautomatic shot, then still requires release.
    if(ResumePistolAim)AimPressed();
    if(ResumePistolFire)FirePressed();
}
void AFPSGAMECharacter::EndPlay(const EEndPlayReason::Type Reason)
{
    StopMechanicalAudio();
    if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->SaveNow();
    Super::EndPlay(Reason);
}
