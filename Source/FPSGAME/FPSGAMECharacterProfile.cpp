#include "FPSGAMECharacter.h"
#include "WorldGeneration/VillageOilCarry.h"
#include "Movement/FPSCharacterMovementComponent.h"
#include "Weapons/Kukri/HatchetCharmComponent.h"
#include "Items/FPSPotionUseComponent.h"
#include "Weapons/StarMarrowComponent.h"
#include "Weapons/M24Attachments.h"
#include "Weapons/LMGStabilityGrip.h"
#include "Weapons/FullAutoTrigger.h"
#include "Weapons/Saiga12KMagazineAssets.h"
#include "Weapons/JingangRuneComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Production/ProductionToolComponent.h"
#include "Weapons/RuneSwordComponent.h"
#include "Weapons/TangDaoGuardComponent.h"
#include "Weapons/PanChiGuardComponent.h"
#include "Weapons/ZhenmoRuneComponent.h"
#include "Weapons/TimeSandEchoComponent.h"
#include "Weapons/Kukri/KukriBerserkerComponent.h"
#include "Weapons/Kukri/KukriFrostRavenComponent.h"
#include "Weapons/Kukri/KukriRelentlessComponent.h"
#include "Weapons/Kukri/KukriDecisiveComponent.h"
#include "Weapons/Bow/BowWeaponComponent.h"
#include "Weapons/Staff/StaffWeaponComponent.h"
#include "Weapons/Staff/StaffOffhandMeleeComponent.h"
#include "Weapons/WoodenTorchComponent.h"
#include "Weapons/Kukri/KukriWeaponComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelEnhancementSystem.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Survival/FPSSurvivalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/LMG201WeaponAssets.h"
#include "Weapons/RSH12WeaponAssets.h"
#include "Weapons/Super90SpeedloaderAssets.h"
#include "Weapons/ShotgunDuckbillAssets.h"
#include "Weapons/WeaponStatEvaluation.h"
#include "Weapons/ColdSteelEnchantmentCombat.h"
#include "Weapons/DealerEnchantmentComponent.h"
#include "Movement/FPSTraversalComponent.h"
#include "Multiplayer/ColdSteelPlayerState.h"
#include "Net/UnrealNetwork.h"

void AFPSGAMECharacter::GrantDoorKey(FName KeyId)
{
    if(!HasAuthority()||KeyId.IsNone())return;
    DoorKeys.AddUnique(KeyId);
    if(auto* State=GetPlayerState<AColdSteelPlayerState>())State->GrantSessionDoorKey(KeyId);
    ForceNetUpdate();
}

bool AFPSGAMECharacter::HasDoorKey(FName KeyId) const
{
    if(KeyId.IsNone())return false;
    const auto* State=GetPlayerState<AColdSteelPlayerState>();
    return DoorKeys.Contains(KeyId)||(State&&State->HasSessionDoorKey(KeyId));
}

void AFPSGAMECharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    // 门钥匙环只复制给持有者：服务端 GrantDoorKey 写入权威集合，客机交互提示
    // （ColdSteelWorldInteraction 键门"有钥匙"分支）读本机 pawn 的镜像；其他端不需要。
    DOREPLIFETIME_CONDITION(AFPSGAMECharacter, DoorKeys, COND_OwnerOnly);
}

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
    if(Changed(IsM24Weapon()?TEXT("body"):TEXT("underbarrel")))SetGunsmithHandstop(Parts.FindRef(IsM24Weapon()?TEXT("body"):TEXT("underbarrel")));
    if(Changed(TEXT("bipod")))SetGunsmithBipod(Parts.FindRef(TEXT("bipod")));
    if(IsM24Weapon()&&Changed(TEXT("bolt")))M24Attachments::SetBoltMaterial(AKMViewmodel,Parts.FindRef(TEXT("bolt")));
    if(Changed(TEXT("stock"))||(IsM24Weapon()&&Changed(TEXT("body"))))SetGunsmithStock(Parts.FindRef(TEXT("stock")));
    if(Changed(TEXT("reargrip"))||Changed(TEXT("grip_body"))||(IsM24Weapon()&&(Changed(TEXT("stock"))||Changed(TEXT("body")))))SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")),nullptr,Parts.FindRef(TEXT("grip_body")));
    if(Changed(TEXT("tactical"))||Changed(TEXT("tactical_secondary"))||(IsM24Weapon()&&Changed(TEXT("body"))))SetGunsmithTactical(Parts.FindRef(TEXT("tactical")),Parts.FindRef(TEXT("tactical_secondary")));
    if(Changed(TEXT("reload_device")))SetSuper90Speedloader(IsTubeShotgunWeapon()&&Parts.FindRef(TEXT("reload_device"))==Super90SpeedloaderAssets::Id);
    AppliedWeaponVisualParts=Parts;
    bWeaponVisualPartsApplied=true;
}

void AFPSGAMECharacter::ApplyColdSteelProfile(UColdSteelStatusModel* Profile)
{
    // Possession can publish a shadow profile before component initialization.
    // BeginPlay consumes NetShadowProfile after creating the base viewmodel.
    if(!HasActorBegunPlay() || !Profile || bResolvingActionInterrupt)return;
    if(auto* Carry=FindComponentByClass<UVillageOilCarry>();Carry && Carry->Occupied())Carry->RefreshEquipment(*Profile);
    if(auto* Core=FindComponentByClass<UStarMarrowComponent>())Core->Configure(Profile);
    if(auto* Guard=FindComponentByClass<UTangDaoGuardComponent>())Guard->Configure(Profile);
    if(auto* Guard=FindComponentByClass<UPanChiGuardComponent>())Guard->Configure(Profile);
    if(auto* Rune=FindComponentByClass<UZhenmoRuneComponent>())Rune->Configure(Profile);
    if(auto* Echo=FindComponentByClass<UTimeSandEchoComponent>())Echo->Configure(Profile);
    if(auto* Rune=FindComponentByClass<UKukriBerserkerComponent>())Rune->Configure(Profile);
    if(auto* Rune=FindComponentByClass<UKukriFrostRavenComponent>())Rune->Configure(Profile);
    if(auto* Pendant=FindComponentByClass<UKukriRelentlessComponent>())Pendant->Configure(Profile);
    if(HatchetCharms)HatchetCharms->Configure(Profile);
    if(auto* Pendant=FindComponentByClass<UKukriDecisiveComponent>())Pendant->Configure(Profile);
    if(auto* Rune=FindComponentByClass<UJingangRuneComponent>())Rune->Configure(Profile);
    const auto* I=Profile->ActiveFirearm();const FString Id=I?I->InstanceId:TEXT("");
    const FString Definition=I?I->Definition:TEXT("");
    // Inventory/HUD identify the lone pistol; its left-hand controller owns presentation.
    bLoneOffhandPistol=I&&!Profile->Equipped();
    const auto* Tool=Profile->ActiveProductionTool();
    const FString ToolId=Tool?Tool->InstanceId:FString();
    const bool WasWeaponReady=bInventoryWeaponReady;
    const bool WasDual=HasOffhandPistol();
    bInventoryWeaponReady=!Profile->ActiveProductionTool()&&I&&((I->Definition==TEXT("ue_m4a1")||I->Definition==TEXT("ue_hk416"))||I->Definition==TEXT("ue_akm")||I->Definition==TEXT("ue_a762")||I->Definition==TEXT("ue_lmg201")||I->Definition==TEXT("ue_super90")||I->Definition==TEXT("ue_m870")||I->Definition==TEXT("ue_svd")||(I->Definition==TEXT("ue_svch")||I->Definition==TEXT("ue_m24"))||I->Definition==TEXT("ue_saiga12k")||I->Definition==TEXT("ue_pkm_lowpoly")||I->Definition==TEXT("ue_m249")||I->Definition==TEXT("ue_qbz191")||I->Definition==TEXT("ue_ash12")||I->Definition==TEXT("ue_m16a2")||((I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_g18")||I->Definition==TEXT("ue_pit_viper2011"))||(I->Definition==TEXT("ue_dan_wesson715")||I->Definition==TEXT("ue_rsh12"))));
    const bool ChangedDual=DualPistols && !DualPistols->MatchesEquipment(Profile,bInventoryWeaponReady);
    const bool ChangedWeapon=ActiveInventoryWeapon!=Id||ActiveInventoryWeaponDefinition!=Definition
        ||WasWeaponReady!=bInventoryWeaponReady||ChangedDual||ActiveProductionToolInstance!=ToolId;
    auto P=Profile->Snapshot();
    const auto* Consumable=FindComponentByClass<UFPSPotionUseComponent>();
    if(ChangedWeapon || (Consumable && Consumable->EquippedHandsChanged(*Profile,P.ActiveWeaponSlot)))
    {
        // The same hand items can require new viewmodels. The carry component compares the actual slots above.
        ResetActionsForPriority(true);
        // Cancellation can publish a refund or finish a reserved cooldown.
        // Item pointers into the previous profile publication are now stale.
        I=Profile->ActiveFirearm();
        ActiveProductionToolInstance=ToolId;
        P=Profile->Snapshot();
    }
    if(auto* Dealer=FindComponentByClass<UDealerEnchantmentComponent>())Dealer->Configure(Profile);
    if(auto* Survival=FindComponentByClass<UFPSSurvivalComponent>())Survival->RestoreState(P.Survival);
    if(HasAuthority())if(auto* H=FindComponentByClass<UFPSCombatHealthComponent>()){H->MaxHealth=Profile->Derived(TEXT("maxHp"));H->Health=FMath::Clamp(P.Health,0.f,H->MaxHealth);}
    // A single-pistol swap retains its existing held-input behavior. Changing
    // between single and dual input mappings requires fresh trigger edges.
    const bool PistolInput=ChangedWeapon&&!WasDual&&!ChangedDual&&bInventoryWeaponReady&&((I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_g18")||I->Definition==TEXT("ue_pit_viper2011"))||(I->Definition==TEXT("ue_dan_wesson715")||I->Definition==TEXT("ue_rsh12")));
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
        if(bInventoryWeaponReady){bUseM4Infima=(I->Definition==TEXT("ue_m4a1")||I->Definition==TEXT("ue_hk416"));bUseQBZ191=I->Definition==TEXT("ue_qbz191");bUseASH12=I->Definition==TEXT("ue_ash12");bUseM16=I->Definition==TEXT("ue_m16a2");bUseM1911=(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_g18")||I->Definition==TEXT("ue_pit_viper2011"));bUseDanWesson715=(I->Definition==TEXT("ue_dan_wesson715")||I->Definition==TEXT("ue_rsh12"));InitializeWeaponVisuals();}
        else {WeaponState=EAKMWeaponState::Idle;WeaponStateElapsed=WeaponStateDuration=0;}
    }
    // 左手单持时主手视模整体退出，这把枪只由双持组件的左手网格呈现。
    AKMViewmodel->SetVisibility(bInventoryWeaponReady && !IsTraversing() && !bLoneOffhandPistol,ChangedWeapon);
    // 左手单持改由双持组件的左手网格呈现，主手视模既不显示也不镜像。
    SetViewmodelMirrored(false);
    if(auto* Tools=FindComponentByClass<UProductionToolComponent>())Tools->RefreshHeldTool();
    if(RuneSword)RuneSword->RefreshEquipment(Profile);
    // 弓走自己的视模：主手槽不是弓就收起，避免换枪后弓还挂在相机上。
    if(Bow)Bow->RefreshEquipment(Profile);
    if(Staff)Staff->RefreshEquipment(Profile);
    if(auto* Kukri=FindComponentByClass<UKukriWeaponComponent>())Kukri->RefreshEquipment(Profile);
    if(auto* Torch=FindComponentByClass<UWoodenTorchComponent>())Torch->RefreshEquipment(*Profile,P.ActiveWeaponSlot);
    // Handling stays in UE units; damage resolves through the canonical gamedev weapon formula below.
    const auto* Defaults=GetClass()->GetDefaultObject<AFPSGAMECharacter>();
    // 一个持枪移速乘区同时承载手枪精通加成与机枪类减速；工具或不持枪时为 1。
    PistolMoveSpeedMultiplier=bInventoryWeaponReady
        ?Profile->PistolMovementMultiplier()*Profile->MachineGunMovementMultiplier():1.f;
    WalkSpeed=Defaults->WalkSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    SprintSpeed=Defaults->SprintSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    ADSWalkSpeed=Defaults->ADSWalkSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    CrouchSpeed=Defaults->CrouchSpeed*PistolMoveSpeedMultiplier*Profile->CombatMoveMultiplier();
    if(auto* Movement=Cast<UFPSCharacterMovementComponent>(GetCharacterMovement()))Movement->RefreshSpeedLimits();
    WeaponHandling=FWeaponHandling();
    BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale;
    ProjectileSpeedCM=9000.f;
    TraceDistance=Defaults->TraceDistance;
    EffectiveWeaponRangeCM=Defaults->TraceDistance;
    HipSpreadMultiplier=1.f;
    ShotgunPelletSpreadMultiplier=1.f;bShotgunDuckbillInstalled=false;
    FirearmEquipRate=1.f;
    M24GearBoltDurationScale=1.f;
    DamagePerShot=Defaults->DamagePerShot+Profile->Derived(TEXT("atk"));
    FireInterval=Defaults->FireInterval;
    const bool PreviousSelectable=bSelectableAutoTrigger, PreviousAutomatic=bAutomaticTrigger;
    bSelectableAutoTrigger=false;bAutomaticTrigger=false;
    BurstShotCount=1;BurstRecoverySeconds=0.f;
    ReloadDuration=Defaults->ReloadDuration;EmptyReloadDuration=Defaults->EmptyReloadDuration;
    const bool HadStabilityGrip = bStabilityGripInstalled;
    bStabilityGripInstalled = false;
    if(auto* Gunsmith=GetGameInstance()->GetSubsystem<UGunsmithSystem>())
    {
        const auto Parts=I?Gunsmith->Installed(*I):FGunsmithParts();
        bStabilityGripInstalled = I && LMGStabilityGrip::Supports(I->Definition)
            && Parts.FindRef(TEXT("underbarrel")) == LMGStabilityGrip::Id;
        // Ballistics use the committed equipment, never the local workbench's
        // preview. Cache once per profile publication on owner and authority.
        if(I&&IsShotgunWeapon())ShotgunPelletSpreadMultiplier=float(Gunsmith->PelletSpreadMultiplier(I->Definition,Parts));
        bShotgunDuckbillInstalled=I&&(IsSuper90Weapon()||IsSaiga12KWeapon())&&Parts.FindRef(TEXT("muzzle"))==ShotgunDuckbillAssets::Part;
        bSelectableAutoTrigger=I&&FullAutoTrigger::Installed(I->Definition,Parts);
        bAutomaticTrigger=I&&FullAutoTrigger::Automatic(*I,bSelectableAutoTrigger);
        // Gameplay transactions can refresh stats while the gunsmith is open;
        // keep its transient preview until Apply/Undo/Close resolves it.
        const auto& VisualParts=I&&Gunsmith->IsOpen()&&Gunsmith->Instance()==I->InstanceId?Gunsmith->Draft():Parts;
        ApplyWeaponAttachmentPresentation(VisualParts);
        bDrumInstalled=Parts.FindRef(TEXT("magazine"))==TEXT("large_drum")
            ||(IsSaiga12KWeapon()&&Parts.FindRef(TEXT("magazine"))==Saiga12KMagazineAssets::DrumPart);
        bSuper90LoaderInstalled=IsTubeShotgunWeapon()&&Parts.FindRef(TEXT("reload_device"))==Super90SpeedloaderAssets::Id;
        bRevolverSpeedloaderInstalled=bUseDanWesson715&&Parts.FindRef(TEXT("reload_device"))==
            (IsRSH12Weapon()?RSH12WeaponAssets::Speedloader:DanWesson715WeaponAssets::Speedloader);
        ADSInDuration=Defaults->ADSInDuration;
        MagazineCapacity=Defaults->MagazineCapacity;ReloadDuration=Defaults->ReloadDuration;EmptyReloadDuration=Defaults->EmptyReloadDuration;
        if(I&&Gunsmith->Weapon(I->Definition))
        {auto Stats=Gunsmith->CalculateItem(*I,Parts);ColdSteelWeaponStats::ApplyFirearmEquipmentHandling(Stats,Profile);ADSInDuration=Stats.ADS*Profile->ADSTimeMultiplier();MagazineCapacity=Stats.Capacity;ReloadDuration=Stats.Reload;EmptyReloadDuration=Stats.EmptyReload;
            FirearmEquipRate=static_cast<float>(Stats.EquipRate());
            M24GearBoltDurationScale=float(Stats.M24BoltDurationScale);
            WeaponHandling=Stats.Handling;BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale*WeaponHandling.RecoilScale;ProjectileSpeedCM=Stats.Speed*100.f;
            HipSpreadMultiplier=FMath::Max(0.f,static_cast<float>(Stats.Spread));
            EffectiveWeaponRangeCM=FMath::Max(1.f,static_cast<float>(Stats.Range*100.));
            // Keep ballistic lifetime separate from the full-damage range.
            TraceDistance=FMath::Max(Defaults->TraceDistance,EffectiveWeaponRangeCM*3.f);
            const float AmmoRange=Profile->AmmoRangeMultiplier(*I);
            EffectiveWeaponRangeCM*=AmmoRange;
            TraceDistance*=AmmoRange;
            // Every catalog weapon, M4 included, drives cadence from the same
            // gunsmith data the panel and tooltips read. The old M4 exception
            // silently ignored the catalog fire interval.
            DamagePerShot=Stats.Damage+Profile->Derived(TEXT("atk"));FireInterval=Stats.Interval;
            BurstShotCount=Stats.BurstCount;BurstRecoverySeconds=Stats.BurstDelay;}
    }
    if (HadStabilityGrip != bStabilityGripInstalled || ChangedWeapon)
    {
        TriggerFirstShotWorldTime = -1.;
        LastShotGripRecoilMultiplier = 1.f;
    }
    if(!ChangedWeapon && !WasDual && (PreviousSelectable!=bSelectableAutoTrigger || PreviousAutomatic!=bAutomaticTrigger))
        bFireHeld=bPistolShotPending=false;
    // Rebuild from weapon/attachment values on each publication; never compound
    // the passive bonus into the previous duration. Active action clocks stay fixed.
    ReloadDuration=ColdSteelWeaponStats::Reload(I,Profile,ReloadDuration);
    EmptyReloadDuration=ColdSteelWeaponStats::Reload(I,Profile,EmptyReloadDuration);
    BurstRecoverySeconds=ColdSteelWeaponStats::Interval(I,Profile,BurstRecoverySeconds);
    FireInterval=ColdSteelWeaponStats::Interval(I,Profile,FireInterval);
    // 涡轮增压（附魔）参数随档案缓存，开火循环只做插值；换枪或失去附魔即清空累计秒数。
    TurboRampParams=ColdSteelCombat::TurboRamp(I?GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr,I);
    if(ChangedWeapon||!TurboRampParams.Enabled)TurboRampSeconds=0.0;
    // 汇聚（附魔）同样随档案缓存：开火时只按弹匣余弹算一次倍率。
    ConvergenceParams=ColdSteelCombat::Convergence(I?GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr,I);
    if(I)DamagePerShot=ColdSteelWeaponStats::Damage(*I,Profile,DamagePerShot-Profile->Derived(TEXT("atk")))*Profile->AmmoDamageMultiplier(*I);
    const bool HasNoAmmo=I&&(ColdSteelInventory::IsMeleeWeapon(*I)||ColdSteelInventory::IsStaff(*I));
    MagazineAmmo=I&&!HasNoAmmo?FMath::Clamp(I->Magazine,0,MagazineCapacity):0;
    ReserveAmmo=HasNoAmmo?0:Profile->AmmoCount();
    if(RuneSword && RuneSword->IsEquipped())
    {DamagePerShot=RuneSword->EquippedDamage();FireInterval=RuneSword->AttackSeconds();MagazineCapacity=0;ReloadDuration=EmptyReloadDuration=0;}
    if (bUseDanWesson715 && I)
        RevolverCaseCount = FMath::Clamp(static_cast<int32>(ColdSteelInventory::Number(*I, TEXT("revolver_case_count"), I->Magazine)), MagazineAmmo, MagazineCapacity);
    // Attachment setters own visibility while the gun is equipped. On stowing,
    // hide their children after those setters finish as well: a retained rifle
    // must not leave a sight or another camera-space part on the next weapon.
    // 左手单持时这把枪只由双持组件的左手网格呈现。判断必须用 bLoneOffhandPistol，
    // 不能用 !HasOffhandPistol()：左手单持本身就会让双持组件进入 offhand-only 激活，
    // HasOffhandPistol() 会因此变真，条件反过来导致主手枪视模也被显示 → 画面里两把枪、
    // 两只手同时出现。
    const bool bShowRifle=bInventoryWeaponReady && !IsTraversing() && !bLoneOffhandPistol;
    AKMViewmodel->SetVisibility(bShowRifle,!bShowRifle);
    // Reapply held input only after the new pistol's magazine and stats exist.
    // A held trigger starts one semiautomatic shot, then still requires release.
    if(DualPistols)DualPistols->RefreshEquipment(Profile);
    if(WeaponFX)WeaponFX->SetBigBlindEnabled(bInventoryWeaponReady&&!HasOffhandPistol()
        &&ColdSteelCombat::BigBlind(GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>(),I).Enabled);
    if(!HasOffhandPistol())
    {
        if(ChangedWeapon && bInventoryWeaponReady)
        {
            if(!IsM24Weapon()&&NeedsReloadCycle())ServicePendingReloadCycle();
            else StartEquipCharge();
        }
        if(ResumePistolAim)AimPressed();
        if(ResumePistolFire)FirePressed();
    }
}
void AFPSGAMECharacter::EndPlay(const EEndPlayReason::Type Reason)
{
    ReleaseThermalPresentation();
    CancelAmmoSelection();
    StopMechanicalAudio();
    // 联机：只有本机玩家的 pawn 才触发档案落盘——服务端远端 pawn 销毁不该写主机单例档。
    if(IsLocallyControlled())if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        PreserveInterruptedM24Cycle();
        Profile->SaveNow();
    }
    Super::EndPlay(Reason);
}
void AFPSGAMECharacter::OnRep_ReplicatedMovement()
{
    Super::OnRep_ReplicatedMovement();
    LastNetMovementAt = GetWorld()->GetTimeSeconds();
    if (GetLocalRole() == ROLE_SimulatedProxy)
    {
        if (UCharacterMovementComponent* Movement = GetCharacterMovement())
        {
            if (!Movement->IsComponentTickEnabled()) Movement->SetComponentTickEnabled(true); // 断流解冻
        }
    }
}
void AFPSGAMECharacter::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    // 服务端/单机的挂载点：spawn 后 Possess 时 Controller 就绪。
    TryAttachLocalProfile();
    // 联机：远端玩家重生/换乘后从 PlayerState 重绑影子档案——否则新 pawn 的
    // NetShadowProfile 为 null，攻防公式回退主机单例档案，直到下次档案上行才修正。
    if (!IsLocallyControlled())
    {
        if (auto* PS = GetPlayerState<AColdSteelPlayerState>())
        {
            if (UColdSteelStatusModel* Shadow = PS->GetShadowModel())
            {
                NetShadowProfile = Shadow;
                // Reset the previous life's dead snapshot before this pawn's
                // first replication. Applying it first can send Health=0 and
                // permanently disable the new owner's input/tick on receipt.
                Shadow->AttachPawn(this);
            }
        }
    }
}
void AFPSGAMECharacter::OnRep_Controller()
{
    Super::OnRep_Controller();
    // 客户端自主 pawn 的挂载点：Controller 复制到达时才谈得上"本机控制"。
    TryAttachLocalProfile();
}
void AFPSGAMECharacter::TryAttachLocalProfile()
{
    // Auto-possession may precede BeginPlay. Defer attachment until startup
    // finishes the base mesh; later possession still attaches immediately.
    if(!HasActorBegunPlay() || bLocalProfileAttached)return;
    // 只有本机玩家的 pawn 才能占用 GameInstance 单例档案；远端 pawn 在监听服/客户端
    // 一律跳过，否则会把主机（或本机）的档案抢走并整包重放（ApplyToPawn 武器风暴）。
    if(!IsLocallyControlled())return;
    bLocalProfileAttached=true;
    // A client may receive its controller after the offhand component's BeginPlay.
    if(auto* Pair=FindComponentByClass<UStaffOffhandMeleeComponent>())Pair->InitializeLocalPresentation();
    if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->AttachPawn(this);
}
