#include "FPSGAMECharacter.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Production/ProductionToolComponent.h"
#include "Weapons/Bow/BowWeaponComponent.h"
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

void AFPSGAMECharacter::ApplyWeaponAttachmentPresentation(const TMap<FString,FString>& Parts)
{
    if(bWeaponVisualPartsApplied && AppliedWeaponVisualParts.OrderIndependentCompareEqual(Parts))return;
    const auto Changed=[&](const TCHAR* Slot)
    {
        return !bWeaponVisualPartsApplied || Parts.FindRef(Slot)!=AppliedWeaponVisualParts.FindRef(Slot);
    };
    if(Changed(TEXT("optic")))SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));
    if(Changed(TEXT("magazine")))SetGunsmithMagazineAttachment(Parts.FindRef(TEXT("magazine")));
    if(Changed(TEXT("muzzle")))SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));
    if(Changed(TEXT("underbarrel")))SetGunsmithHandstop(Parts.FindRef(TEXT("underbarrel")));
    if(Changed(TEXT("bipod")))SetGunsmithBipod(Parts.FindRef(TEXT("bipod")));
    if(Changed(TEXT("stock")))SetGunsmithStock(Parts.FindRef(TEXT("stock")));
    if(Changed(TEXT("reargrip")))SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")));
    if(Changed(TEXT("tactical")))SetGunsmithTactical(Parts.FindRef(TEXT("tactical")));
    AppliedWeaponVisualParts=Parts;
    bWeaponVisualPartsApplied=true;
}

void AFPSGAMECharacter::ApplyColdSteelProfile(UColdSteelStatusModel* Profile)
{
    if(!Profile || bResolvingActionInterrupt)return;
    const auto* I=Profile->Equipped();const FString Id=I?I->InstanceId:TEXT("");
    const FString Definition=I?I->Definition:TEXT("");
    const auto* Tool=Profile->ActiveProductionTool();
    const FString ToolId=Tool?Tool->InstanceId:FString();
    const bool WasWeaponReady=bInventoryWeaponReady;
    const bool WasDual=IsDualWieldingPistols();
    bInventoryWeaponReady=!Profile->ActiveProductionTool()&&I&&(I->Definition==TEXT("ue_m4a1")||I->Definition==TEXT("ue_akm")||I->Definition==TEXT("ue_a762")||I->Definition==TEXT("ue_svd")||I->Definition==TEXT("ue_pkm_lowpoly")||I->Definition==TEXT("ue_qbz191")||I->Definition==TEXT("ue_ash12")||I->Definition==TEXT("ue_m16a2")||(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_dan_wesson715")));
    const bool ChangedDual=DualPistols && !DualPistols->MatchesEquipment(Profile,bInventoryWeaponReady);
    const bool ChangedWeapon=ActiveInventoryWeapon!=Id||ActiveInventoryWeaponDefinition!=Definition
        ||WasWeaponReady!=bInventoryWeaponReady||ChangedDual||ActiveProductionToolInstance!=ToolId;
    if(ChangedWeapon)
    {
        InterruptActionsForPriority(true);
        // Cancellation can publish a refund or finish a reserved cooldown.
        // Item pointers into the previous profile publication are now stale.
        I=Profile->Equipped();
        ActiveProductionToolInstance=ToolId;
    }
    const auto P=Profile->Snapshot();
    if(auto* H=FindComponentByClass<UFPSCombatHealthComponent>()){H->MaxHealth=Profile->Derived(TEXT("maxHp"));H->Health=FMath::Clamp(P.Health,0.f,H->MaxHealth);}
    // A single-pistol swap retains its existing held-input behavior. Changing
    // between single and dual input mappings requires fresh trigger edges.
    const bool PistolInput=ChangedWeapon&&!WasDual&&!ChangedDual&&bInventoryWeaponReady&&(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_dan_wesson715"));
    const bool ResumePistolAim=PistolInput&&bAimHeld;
    const bool ResumePistolFire=PistolInput&&bFireHeld;
    if(ChangedWeapon){
        CancelAmmoSelection();PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
        VisualRecoilUpdatedAt=-1.;LastVisualShotAt=VisualRecoverAt=-10.;VisualBurstIndex=0;
        GunKickPosition=GunKickPositionVelocity=GunKickRotation=GunKickRotationVelocity=FVector::ZeroVector;
        GunJitterPosition=GunJitterPositionVelocity=GunJitterRotation=GunJitterRotationVelocity=FVector::ZeroVector;
        GunFlip=GunFlipVelocity=0.f;
        ClipRecoilSeconds=-1.f;
        // A weapon change resets both hands so a new loadout starts from rest.
        for(auto& Dual:DualRecoil)Dual=FDualWieldRecoil();
        bReloadAfterCasting=false;
        bRevolverReloadAfterFire=false;
        if (IsTraversing()) Traversal->Cancel();
        StopMechanicalAudio();
        FireReleased();AimReleased();
        if(DualPistols)DualPistols->Deactivate();
        WeaponState=EAKMWeaponState::Idle;WeaponStateElapsed=WeaponStateDuration=0.f;
        bPendingEmptyReload=bReloadAmmoCommitted=bReloadCycleOnly=false;ReloadResumeElapsed=0.f;
        ActiveInventoryWeapon=Id;
        ActiveInventoryWeaponDefinition=Definition;
        bWeaponVisualPartsApplied=false;
        if(bInventoryWeaponReady){bUseM4Infima=I->Definition==TEXT("ue_m4a1");bUseQBZ191=I->Definition==TEXT("ue_qbz191");bUseASH12=I->Definition==TEXT("ue_ash12");bUseM16=I->Definition==TEXT("ue_m16a2");bUseM1911=I->Definition==TEXT("ue_m1911");bUseDanWesson715=I->Definition==TEXT("ue_dan_wesson715");InitializeWeaponVisuals();}
        else {WeaponState=EAKMWeaponState::Idle;WeaponStateElapsed=WeaponStateDuration=0;}
    }
    AKMViewmodel->SetVisibility(bInventoryWeaponReady && !IsTraversing(),ChangedWeapon);
    if(auto* Tools=FindComponentByClass<UProductionToolComponent>())Tools->RefreshHeldTool();
    // 弓走自己的视模：主手槽不是弓就收起，避免换枪后弓还挂在相机上。
    if(Bow)Bow->RefreshEquipment(Profile);
    if(RuneSword)RuneSword->RefreshEquipment(Profile);
    // Handling stays in UE units; damage resolves through the canonical gamedev weapon formula below.
    const auto* Defaults=GetClass()->GetDefaultObject<AFPSGAMECharacter>();
    // 一个持枪移速乘区同时承载手枪精通加成与机枪类减速；工具或不持枪时为 1。
    PistolMoveSpeedMultiplier=bInventoryWeaponReady
        ?Profile->PistolMovementMultiplier()*Profile->MachineGunMovementMultiplier():1.f;
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
    BurstShotCount=1;BurstRecoverySeconds=0.f;
    ReloadDuration=Defaults->ReloadDuration;EmptyReloadDuration=Defaults->EmptyReloadDuration;
    if(auto* Gunsmith=GetGameInstance()->GetSubsystem<UGunsmithSystem>())
    {
        const auto Parts=I?Gunsmith->Installed(*I):FGunsmithParts();
        // Gameplay transactions can refresh stats while the gunsmith is open;
        // keep its transient preview until Apply/Undo/Close resolves it.
        const auto& VisualParts=I&&Gunsmith->IsOpen()&&Gunsmith->Instance()==I->InstanceId?Gunsmith->Draft():Parts;
        ApplyWeaponAttachmentPresentation(VisualParts);
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
            // Every catalog weapon, M4 included, drives cadence from the same
            // gunsmith data the panel and tooltips read. The old M4 exception
            // silently ignored the catalog fire interval.
            DamagePerShot=Stats.Damage+Profile->Derived(TEXT("atk"));FireInterval=Stats.Interval;
            BurstShotCount=Stats.BurstCount;BurstRecoverySeconds=Stats.BurstDelay;}
    }
    // Rebuild from weapon/attachment values on each publication; never compound
    // the passive bonus into the previous duration. Active action clocks stay fixed.
    ReloadDuration=ColdSteelWeaponStats::Reload(I,Profile,ReloadDuration);
    EmptyReloadDuration=ColdSteelWeaponStats::Reload(I,Profile,EmptyReloadDuration);
    BurstRecoverySeconds=ColdSteelWeaponStats::Interval(I,Profile,BurstRecoverySeconds);
    FireInterval=ColdSteelWeaponStats::Interval(I,Profile,FireInterval);
    if(I)DamagePerShot=ColdSteelWeaponStats::Damage(*I,Profile,DamagePerShot-Profile->Derived(TEXT("atk")))*Profile->AmmoDamageMultiplier(*I);
    MagazineAmmo=I&&!ColdSteelInventory::IsMeleeWeapon(*I)?FMath::Clamp(I->Magazine,0,MagazineCapacity):0;ReserveAmmo=I&&ColdSteelInventory::IsMeleeWeapon(*I)?0:Profile->AmmoCount();
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
        if(ChangedWeapon && bInventoryWeaponReady)
        {
            if(NeedsReloadCycle())ServicePendingReloadCycle();
            else StartEquipCharge();
        }
        if(ResumePistolAim)AimPressed();
        if(ResumePistolFire)FirePressed();
    }
}
void AFPSGAMECharacter::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelAmmoSelection();
    StopMechanicalAudio();
    if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->SaveNow();
    Super::EndPlay(Reason);
}
