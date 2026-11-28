#include "VillageSmartTurret.h"
#include "TemperateHillsWorld.h"
#include "VillageDefenseState.h"
#include "VillageSiegeEngine.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/FPSAttackQuery.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Monsters/HumanoidHitVolumeData.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelPickup.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWarehouseRules.h"
#include "../Weapons/ASH12WeaponAssets.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/LMG201WeaponAssets.h"
#include "../Weapons/M16WeaponAssets.h"
#include "../Weapons/M249WeaponAssets.h"
#include "../Weapons/M24WeaponAssets.h"
#include "../Weapons/M870WeaponAssets.h"
#include "../Weapons/PKMLowpolyWeaponAssets.h"
#include "../Weapons/RifleSuppressedAudioAssets.h"
#include "../Weapons/Saiga12KWeaponAssets.h"
#include "../Weapons/ShotgunSuppressorAssets.h"
#include "../Weapons/SniperSuppressorAssets.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/SVCHWeaponAssets.h"
#include "../Weapons/SVDWeaponAssets.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "Components/BoxComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundBase.h"

namespace
{
    constexpr double TurretPivotZCm = 145.;
    constexpr double TurretYawAttachZCm = 76.;
    constexpr double TurretCradleInYawZCm = 69.;
    constexpr float TurretMinPitchDeg = -42.f;
    constexpr float TurretMaxPitchDeg = 52.f;
    constexpr float TurretYawSpeedDegPerSec = 360.f;
    constexpr float TurretPitchSpeedDegPerSec = 280.f;
    constexpr float TurretIdleReturnSpeedDegPerSec = 180.f;
    constexpr float TurretFireToleranceDeg = 5.f;
    constexpr double TurretScanIntervalSec = 0.125;
    constexpr double TurretHysteresisRatio = 0.90;
    constexpr double TurretTubeInterruptRangeCm = 2200.;
    constexpr float TurretReloadTiltDeg = 18.f;
    constexpr float TurretMaxRecoilSlideCm = 3.8f;

    UStaticMeshComponent* MakeTurretPart(AVillageSmartTurret* Owner, USceneComponent* Parent, const TCHAR* Name, const FSoftObjectPath& Path, const FVector& Offset)
    {
        auto* Comp = NewObject<UStaticMeshComponent>(Owner, Name);
        Owner->AddInstanceComponent(Comp);
        Comp->SetupAttachment(Parent);
        Comp->SetRelativeLocation(Offset);
        Comp->SetStaticMesh(Cast<UStaticMesh>(Path.TryLoad()));
        Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Comp->SetGenerateOverlapEvents(false);
        Comp->SetCanEverAffectNavigation(false);
        Comp->RegisterComponent();
        return Comp;
    }

    bool InsertIntoBagOrCompartment(TArray<FColdSteelItem>& Items, FColdSteelItem Item)
    {
        if (ColdSteelInventory::Insert(Items, Item)) return true;
        if (ColdSteelInventory::CanRotate(Item))
        {
            FColdSteelItem Rot = Item;
            ColdSteelInventory::ApplyOrientation(Rot, Rot.bRotated ? 0 : 1);
            if (ColdSteelInventory::Insert(Items, Rot)) return true;
        }
        const FIntPoint Grid = ColdSteelInventory::CompartmentGrid(Items);
        const int32 TotalCells = Grid.X * Grid.Y;
        if (TotalCells <= 0) return false;
        Item.Place = ColdSteelInventory::ColdSteelCompartment::Place;
        Item.Container.Reset();
        Item.Map.Empty();
        Item.Position = FVector::ZeroVector;
        for (int32 Cell = 0; Cell < TotalCells; ++Cell)
        {
            const int32 OrientCount = ColdSteelInventory::CanRotate(Item) ? 2 : 1;
            for (int32 Ori = 0; Ori < OrientCount; ++Ori)
            {
                ColdSteelInventory::ApplyOrientation(Item, Ori);
                if (ColdSteelInventory::ColdSteelCompartment::Fits(Items, Item, Cell, Grid))
                {
                    Item.Cell = Cell;
                    Items.Add(MoveTemp(Item));
                    return true;
                }
            }
        }
        return false;
    }

    bool HasEquippedSuppressor(const FString& Def, const FGunsmithParts& Parts)
    {
        const FString Muzzle = Parts.FindRef(TEXT("muzzle"));
        if (Muzzle.IsEmpty() || Muzzle == TEXT("false")) return false;
        if (Muzzle == SniperSuppressorAssets::Zhiming)
            return SniperSuppressorAssets::SupportsZhiming(Def);
        return Muzzle == TEXT("true")
            || Muzzle == TEXT("tactical_suppressor")
            || Muzzle == TEXT("multi_caliber_suppressor")
            || (Def == TEXT("ue_m24") && Muzzle == TEXT("m24_factory_suppressor"))
            || (SniperSuppressorAssets::Supports(Def) && Muzzle == SniperSuppressorAssets::Part)
            || (Def == TEXT("ue_ash12") && Muzzle == TEXT("ash12_tactical_suppressor"))
            || ((Def == TEXT("ue_super90") || Def == TEXT("ue_saiga12k")) && Muzzle == TEXT("shotgun_suppressor"));
    }

    bool ResolvePhysicsBodyWorldCenter(const USkeletalMeshComponent* Mesh, const USkeletalBodySetup* Setup, FVector& OutCenter)
    {
        if (!Mesh || !Setup || Setup->AggGeom.GetElementCount() <= 0) return false;
        if (Mesh->GetBoneIndex(Setup->BoneName) == INDEX_NONE) return false;
        const FTransform BoneWorld = Mesh->GetSocketTransform(Setup->BoneName, RTS_World);
        const FBox Box = Setup->AggGeom.CalcAABB(BoneWorld);
        OutCenter = Box.IsValid ? Box.GetCenter() : BoneWorld.GetLocation();
        return true;
    }

    int32 ScoreTorsoBodyPriority(const FString& LowerBone)
    {
        if (LowerBone.Contains(TEXT("spine_02")) || LowerBone.Contains(TEXT("spine_03"))
            || LowerBone.Contains(TEXT("spine2")) || LowerBone.Contains(TEXT("spine3"))
            || LowerBone.Contains(TEXT("chest")) || LowerBone.Contains(TEXT("torso"))
            || LowerBone.Contains(TEXT("rib")))
        {
            return 3;
        }
        if (LowerBone.Contains(TEXT("spine")) || LowerBone.Contains(TEXT("body"))
            || LowerBone.Contains(TEXT("pelvis")) || LowerBone.Contains(TEXT("hip")))
        {
            return 2;
        }
        if (LowerBone.Contains(TEXT("weapon")) || LowerBone.Contains(TEXT("ik"))
            || LowerBone.Contains(TEXT("foot")) || LowerBone.Contains(TEXT("toe"))
            || LowerBone.Contains(TEXT("hand")) || LowerBone.Contains(TEXT("finger"))
            || LowerBone.Contains(TEXT("tail")))
        {
            return 0;
        }
        return 1;
    }
}

FSoftObjectPath AVillageSmartTurret::MeshAsset(const TCHAR* Suffix)
{
    return FSoftObjectPath(FString::Printf(
        TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SmartTurret/SM_SmartTurret%s.SM_SmartTurret%s"),
        Suffix, Suffix));
}

bool AVillageSmartTurret::IsMountableFirearm(const FString& Definition)
{
    return Definition == TEXT("ue_m4a1") || Definition == TEXT("ue_akm") || Definition == TEXT("ue_qbz191")
        || Definition == TEXT("ue_ash12") || Definition == TEXT("ue_m16a2") || Definition == TEXT("ue_a762")
        || Definition == TEXT("ue_hk416")
        || Definition == TEXT("ue_m249") || Definition == TEXT("ue_pkm_lowpoly") || Definition == TEXT("ue_lmg201")
        || Definition == TEXT("ue_super90") || Definition == TEXT("ue_m870") || Definition == TEXT("ue_saiga12k")
        || Definition == TEXT("ue_svd") || Definition == TEXT("ue_svch") || Definition == TEXT("ue_m24");
}

const TCHAR* AVillageSmartTurret::WeaponArchetypeLabel(const FString& Definition)
{
    if (Definition == TEXT("ue_m249") || Definition == TEXT("ue_pkm_lowpoly") || Definition == TEXT("ue_lmg201"))
        return TEXT("轻机枪");
    if (IsShotgunDefinition(Definition)) return TEXT("霰弹枪");
    if (Definition == TEXT("ue_svd") || Definition == TEXT("ue_svch") || Definition == TEXT("ue_m24"))
        return TEXT("狙击步枪");
    if (IsMountableFirearm(Definition)) return TEXT("突击步枪");
    return TEXT("非合规武器");
}

bool AVillageSmartTurret::IsShotgunDefinition(const FString& Definition)
{
    return Definition == TEXT("ue_super90") || Definition == TEXT("ue_m870") || Definition == TEXT("ue_saiga12k");
}

bool AVillageSmartTurret::IsTubeShotgunDefinition(const FString& Definition)
{
    return Definition == TEXT("ue_super90") || Definition == TEXT("ue_m870");
}

USoundBase* AVillageSmartTurret::ResolveWeaponFireSound(const FString& Definition, bool bSuppressed)
{
    if (bSuppressed)
    {
        if (IsShotgunDefinition(Definition))
            if (auto* S = LoadObject<USoundBase>(nullptr, ShotgunSuppressorAssets::SoundPath)) return S;
        if (const TCHAR* Bank = RifleSuppressedAudioAssets::Bank(Definition))
            if (auto* S = LoadObject<USoundBase>(nullptr, *RifleSuppressedAudioAssets::SoundPath(Bank, 1))) return S;
        if (auto* S = LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed.S_M4_Suppressed"))) return S;
    }
    if (Definition == TEXT("ue_m4a1") || Definition == TEXT("ue_hk416"))
        if (auto* S = LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/M4HK416Audio/S_HK416_Fire.S_HK416_Fire"))) return S;
    if (Definition == TEXT("ue_m16a2"))
        if (auto* S = LoadObject<USoundBase>(nullptr, M16WeaponAssets::FireSoundPath)) return S;
    if (Definition == TEXT("ue_ash12"))
        if (auto* S = LoadObject<USoundBase>(nullptr, ASH12WeaponAssets::FireSoundPath)) return S;
    if (Definition == TEXT("ue_m249"))
        if (auto* S = LoadObject<USoundBase>(nullptr, *M249WeaponAssets::FireSoundPath(1))) return S;
    if (Definition == TEXT("ue_lmg201"))
        if (auto* S = LoadObject<USoundBase>(nullptr, *LMG201WeaponAssets::FireSoundPath(1))) return S;
    if (Definition == TEXT("ue_pkm_lowpoly"))
        if (auto* S = LoadObject<USoundBase>(nullptr, PKMLowpolyWeaponAssets::FireSoundPath)) return S;
    if (Definition == TEXT("ue_super90"))
        if (auto* S = LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_Fire.S_Super90_Fire"))) return S;
    if (Definition == TEXT("ue_m870"))
        if (auto* S = LoadObject<USoundBase>(nullptr, *M870WeaponAssets::SoundPath(TEXT("Fire")))) return S;
    if (Definition == TEXT("ue_saiga12k"))
        if (auto* S = LoadObject<USoundBase>(nullptr, Saiga12KWeaponAssets::FireSoundPath)) return S;
    if (Definition == TEXT("ue_svd"))
        if (auto* S = LoadObject<USoundBase>(nullptr, *SVDWeaponAssets::FireSoundPath(1))) return S;
    if (Definition == TEXT("ue_svch"))
        if (auto* S = LoadObject<USoundBase>(nullptr, *SVCHWeaponAssets::FireSoundPath(1))) return S;
    if (Definition == TEXT("ue_m24"))
        if (auto* S = LoadObject<USoundBase>(nullptr, M24WeaponAssets::FireSoundPath)) return S;
    if (auto* S = LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/AKM/VideoAudio20260921/S_AKM_Fire.S_AKM_Fire"))) return S;
    return LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/AKM/Audio/S_AKM_Fire.S_AKM_Fire"));
}

FSmartTurretWeaponStats AVillageSmartTurret::ComputeWeaponStats(const FColdSteelItem& Item, UGameInstance* GI, VillageSiegeUpgrades::FRanks Ranks)
{
    using namespace VillageSiegeUpgrades;
    FSmartTurretWeaponStats Out;
    if (!IsMountableFirearm(Item.Definition)) return Out;

    FGunsmithStats GunStats;
    FGunsmithParts Parts;
    if (const auto* Gunsmith = GI ? GI->GetSubsystem<UGunsmithSystem>() : nullptr)
    {
        Parts = Gunsmith->Installed(Item);
        GunStats = Gunsmith->CalculateItem(Item, Parts);
    }
    else
    {
        GunStats.Damage = ColdSteelInventory::Number(Item, TEXT("damage"), 30.);
        GunStats.Interval = ColdSteelInventory::Number(Item, TEXT("fire_interval"), 0.12);
        GunStats.Reload = ColdSteelInventory::Number(Item, TEXT("reload_time"), 2.4);
        GunStats.EmptyReload = ColdSteelInventory::Number(Item, TEXT("empty_reload_time"), GunStats.Reload);
        GunStats.Capacity = FMath::Max(1, FMath::RoundToInt(ColdSteelInventory::Number(Item, TEXT("mag_size"), 30.)));
        GunStats.Range = ColdSteelInventory::Number(Item, TEXT("effective_range"), 85.);
        GunStats.Speed = ColdSteelInventory::Number(Item, TEXT("bullet_speed"), 350.);
        GunStats.Spread = ColdSteelInventory::Number(Item, TEXT("spread_mult"), 2.);
    }

    const int32 RDamage = Rank(Ranks, Index(SmartTurret, TurretDamage));
    const int32 RFeed = Rank(Ranks, Index(SmartTurret, TurretFeed));
    const int32 ROptics = Rank(Ranks, Index(SmartTurret, TurretOptics));
    const int32 RWeak = Rank(Ranks, Index(SmartTurret, TurretWeakpoint));
    const int32 RMag = Rank(Ranks, Index(SmartTurret, TurretMagExpand));
    const int32 RPierce = Rank(Ranks, Index(SmartTurret, TurretPierce));

    const double DmgScale = TurretDamageMultiplier(RDamage);
    const double ReloadScale = TurretReloadScale(RFeed);
    const double RateScale = TurretFireRateScale(RFeed);
    const double SpreadScale = TurretSpreadScale(ROptics);

    // Pass Model=nullptr so player personal skills never bleed into garrison turret damage/handling.
    const double ItemPanelDmg = ColdSteelWeaponStats::DamageParts(Item, nullptr, GunStats.Damage).Total();
    Out.bValid = true;
    Out.bSuppressed = HasEquippedSuppressor(Item.Definition, Parts);
    Out.bShotgun = IsShotgunDefinition(Item.Definition);
    Out.bTubeShotgun = IsTubeShotgunDefinition(Item.Definition);
    Out.PelletCount = Out.bShotgun ? Super90WeaponAssets::PelletCount : 1;
    Out.BaseCapacity = FMath::Max(1, GunStats.Capacity);
    Out.ExpandedCapacity = TurretExpandedCapacity(Out.BaseCapacity, RMag);
    Out.BonusPierce = TurretBonusPierce(RPierce);
    Out.PerShotDamage = static_cast<float>(FMath::Max(1.0, ItemPanelDmg * DmgScale));
    Out.FireInterval = static_cast<float>(FMath::Max(0.04, GunStats.Interval / FMath::Max(0.1, RateScale)));
    Out.RPM = 60.f / FMath::Max(0.04f, Out.FireInterval);
    Out.ReloadTime = static_cast<float>(FMath::Max(0.35, GunStats.Reload * ReloadScale));
    Out.EmptyReloadTime = static_cast<float>(FMath::Max(0.35, FMath::Max(GunStats.Reload, GunStats.EmptyReload) * ReloadScale));
    Out.EffectiveScanRangeCm = static_cast<float>(TurretRangeCm(ROptics));
    Out.WeaponEffectiveRangeCm = static_cast<float>(FMath::Max(Out.EffectiveScanRangeCm, GunStats.Range * 100.));
    Out.BulletSpeedCm = static_cast<float>(FMath::Max(9000., GunStats.Speed * 100.));
    Out.SpreadDeg = static_cast<float>(FMath::Max(0.05, (Out.bShotgun ? Super90WeaponAssets::PelletConeDegrees : FMath::Clamp(GunStats.Spread * 0.35, 0.05, 1.35)) * SpreadScale));
    Out.WeakpointChance = static_cast<float>(TurretWeakpointChance(RWeak));
    Out.CritDamageMultiplier = static_cast<float>(FMath::Max(1.2, 1.5 + GunStats.FirearmCriticalDamageBonus));

    const double MagCycleShotTime = Out.ExpandedCapacity * Out.FireInterval;
    const double SustainedFireSec = MagCycleShotTime + Out.EmptyReloadTime;
    const double ExpectedCritFactor = 1.0 + Out.WeakpointChance * (Out.CritDamageMultiplier - 1.0);
    Out.EstimatedDPS = static_cast<float>((Out.PerShotDamage * Out.PelletCount * Out.ExpandedCapacity * ExpectedCritFactor) / FMath::Max(0.1, SustainedFireSec));
    return Out;
}

AVillageSmartTurret::AVillageSmartTurret()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = 0.016f;
    RepairSoulCost = 140;
    MaximumHealth = 820.f;
    Health = 820.f;

    InteractHull = CreateDefaultSubobject<UBoxComponent>(TEXT("InteractHull"));
    InteractHull->SetupAttachment(Masonry);
    InteractHull->SetRelativeLocation(FVector(0., 0., 122.));
    InteractHull->SetBoxExtent(FVector(46., 44., 48.));
    InteractHull->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    InteractHull->SetCollisionResponseToAllChannels(ECR_Ignore);
    InteractHull->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    InteractHull->SetCanEverAffectNavigation(false);
    InteractHull->SetGenerateOverlapEvents(false);

    Ballistics = CreateDefaultSubobject<UFPSBallisticsComponent>(TEXT("TurretBallistics"));
    WeaponFX = CreateDefaultSubobject<UFPSWeaponFXComponent>(TEXT("TurretWeaponFX"));
}

void AVillageSmartTurret::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AVillageSmartTurret, MountedWeapon);
    DOREPLIFETIME(AVillageSmartTurret, CurrentAmmo);
    DOREPLIFETIME(AVillageSmartTurret, MaxAmmo);
    DOREPLIFETIME(AVillageSmartTurret, bReloading);
    DOREPLIFETIME(AVillageSmartTurret, ReloadEndServerTime);
    DOREPLIFETIME(AVillageSmartTurret, ReplicatedReloadDuration);
    DOREPLIFETIME(AVillageSmartTurret, TargetYawDeg);
    DOREPLIFETIME(AVillageSmartTurret, TargetPitchDeg);
    DOREPLIFETIME(AVillageSmartTurret, OpticState);
}

double AVillageSmartTurret::CurrentServerTime() const
{
    const UWorld* W = GetWorld();
    if (!W) return 0.;
    if (const AGameStateBase* GS = W->GetGameState())
    {
        return GS->GetServerWorldTimeSeconds();
    }
    return W->GetTimeSeconds();
}

void AVillageSmartTurret::UpdateTickCadence()
{
    const bool bShouldFastTick =
        (GetHealth() > 0.f && HasMountedWeapon())
        || FMath::Abs(CurrentYawDeg) > 0.5f
        || FMath::Abs(CurrentPitchDeg) > 0.5f
        || SlideRecoilOffset > 0.01f;
    const float Desired = bShouldFastTick ? 0.016f : 0.25f;
    if (!FMath::IsNearlyEqual(GetActorTickInterval(), Desired, 0.005f))
    {
        SetActorTickInterval(Desired);
    }
}

FString AVillageSmartTurret::ComputeWeaponVisualKey(const FColdSteelItem& Item)
{
    if (Item.Definition.IsEmpty()) return {};
    return Item.InstanceId + TEXT("|") + Item.Definition + TEXT("|") + Item.Data;
}

void AVillageSmartTurret::BeginPlay()
{
    Super::BeginPlay();
    if (WeaponFX) WeaponFX->InitializeWorldTracers();
    EnsureVisualAssembly();
    if (HasAuthority() && !bRestoredFromSave && WorldId.IsValid() && PlacedId.IsValid())
    {
        bRestoredFromSave = true;
        FColdSteelItem Saved;
        if (auto* State = GetWorld()->GetSubsystem<UVillageDefenseState>(); State && State->LoadTurretWeapon(WorldId, PlacedId, Saved))
        {
            if (IsMountableFirearm(Saved.Definition))
            {
                MountedWeapon = MoveTemp(Saved);
                const FSmartTurretWeaponStats Stats = GetCurrentWeaponStats();
                MaxAmmo = FMath::Max(1, Stats.ExpandedCapacity);
                CurrentAmmo = FMath::Clamp(MountedWeapon.Magazine > 0 ? MountedWeapon.Magazine : MaxAmmo, 0, MaxAmmo);
                if (CurrentAmmo <= 0) StartReload(Stats, true);
                OnRep_MountedWeapon();
            }
        }
    }
    UpdateTickCadence();
    SetActorTickEnabled(true);
}

void AVillageSmartTurret::EndPlay(const EEndPlayReason::Type Reason)
{
    if (HasAuthority() && Reason == EEndPlayReason::Destroyed && HasMountedWeapon())
    {
        EjectWeaponSafely(nullptr);
    }
    ClearMountedGunVisual();
    Super::EndPlay(Reason);
}

void AVillageSmartTurret::OnRep_Setup()
{
    Super::OnRep_Setup();
    EnsureVisualAssembly();
    OnRep_MountedWeapon();
}

void AVillageSmartTurret::ApplyHealth()
{
    Super::ApplyHealth();
    const bool Alive = GetHealth() > 0.f;
    if (InteractHull)
    {
        InteractHull->SetCollisionResponseToChannel(ECC_Visibility, Alive ? ECR_Block : ECR_Ignore);
    }
    if (YawMesh) YawMesh->SetVisibility(Alive, true);
    if (MountedGunMesh) MountedGunMesh->SetVisibility(Alive && HasMountedWeapon(), true);
    UpdateTickCadence();
}

void AVillageSmartTurret::EnsureVisualAssembly()
{
    if (GetNetMode() == NM_DedicatedServer || YawMesh) return;
    YawMesh = MakeTurretPart(this, Masonry, TEXT("SmartTurretYaw"), MeshAsset(TEXT("Yaw")), FVector(0., 0., TurretYawAttachZCm));
    CradleMesh = MakeTurretPart(this, YawMesh, TEXT("SmartTurretCradle"), MeshAsset(TEXT("Cradle")), FVector(0., 0., TurretCradleInYawZCm));
    SlideMesh = MakeTurretPart(this, CradleMesh, TEXT("SmartTurretSlide"), MeshAsset(TEXT("Slide")), FVector::ZeroVector);

    WeaponAttach = NewObject<USceneComponent>(this, TEXT("WeaponAttach"));
    AddInstanceComponent(WeaponAttach);
    WeaponAttach->SetupAttachment(SlideMesh);
    WeaponAttach->SetRelativeLocation(FVector(0., 0., 2.5));
    WeaponAttach->RegisterComponent();

    MountedGunMesh = NewObject<UPoseableMeshComponent>(this, TEXT("MountedGunMesh"));
    AddInstanceComponent(MountedGunMesh);
    MountedGunMesh->SetupAttachment(WeaponAttach);
    MountedGunMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    MountedGunMesh->SetGenerateOverlapEvents(false);
    MountedGunMesh->SetCanEverAffectNavigation(false);
    MountedGunMesh->SetVisibility(false);
    MountedGunMesh->RegisterComponent();

    ApplyHealth();
    ApplyOpticVisualState(0.f);
}

void AVillageSmartTurret::ClearMountedGunVisual()
{
    bHasMuzzleInWeapon = false;
    CachedMuzzleInWeapon = FTransform::Identity;
    if (MuzzleMarkerPart.IsValid())
    {
        MuzzleMarkerPart->DestroyComponent();
        MuzzleMarkerPart = nullptr;
    }
    if (!MountedGunMesh) return;
    TArray<USceneComponent*> AttachedChildren;
    MountedGunMesh->GetChildrenComponents(true, AttachedChildren);
    for (USceneComponent* Child : AttachedChildren)
        if (Child) Child->DestroyComponent();
    MountedGunMesh->SetSkinnedAssetAndUpdate(nullptr);
    MountedGunMesh->SetRelativeTransform(FTransform::Identity);
    MountedGunMesh->SetVisibility(false);
}

void AVillageSmartTurret::RebuildMountedGunVisual()
{
    EnsureVisualAssembly();
    if (!MountedGunMesh || GetNetMode() == NM_DedicatedServer) return;
    ClearMountedGunVisual();
    if (!HasMountedWeapon()) return;

    auto* GI = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
    if (!GI) return;

    FTransform NativeMuzzle = FTransform::Identity;
    if (!AColdSteelPickup::AssembleWorldGun(MountedWeapon, *GI, *MountedGunMesh, nullptr, &NativeMuzzle))
    {
        return;
    }

    // Align assembled world gun purely in component space (+X barrel forward, +Z top rail up, centered inside U-clamp).
    MountedGunMesh->SetRelativeTransform(FTransform::Identity);
    const bool bHasFront = MountedGunMesh->DoesSocketExist(TEXT("WPN_FrontSight"));
    const bool bHasRear = MountedGunMesh->DoesSocketExist(TEXT("WPN_RearSight"));
    const bool bHasMag = MountedGunMesh->DoesSocketExist(TEXT("WPN_SOCKET_Magazine"));
    const FVector FrontLoc = bHasFront ? MountedGunMesh->GetSocketTransform(TEXT("WPN_FrontSight"), RTS_Component).GetLocation() : FVector::ZeroVector;
    const FVector RearLoc = bHasRear ? MountedGunMesh->GetSocketTransform(TEXT("WPN_RearSight"), RTS_Component).GetLocation() : FVector::ZeroVector;
    const FVector MagLoc = bHasMag ? MountedGunMesh->GetSocketTransform(TEXT("WPN_SOCKET_Magazine"), RTS_Component).GetLocation() : FVector::ZeroVector;

    FVector Barrel = (bHasFront && bHasRear) ? (FrontLoc - RearLoc).GetSafeNormal() : FVector::ZeroVector;
    if (Barrel.IsNearlyZero())
        Barrel = NativeMuzzle.GetRotation().GetForwardVector().GetSafeNormal();
    if (Barrel.IsNearlyZero())
        Barrel = FVector::ForwardVector;

    FVector Up = (bHasRear && bHasMag) ? (RearLoc - MagLoc).GetSafeNormal() : FVector::ZeroVector;
    if (Up.IsNearlyZero() || FMath::Abs(FVector::DotProduct(Barrel, Up)) > 0.98)
        Up = NativeMuzzle.GetRotation().GetUpVector().GetSafeNormal();
    if (Up.IsNearlyZero() || FMath::Abs(FVector::DotProduct(Barrel, Up)) > 0.98)
        Up = (FMath::Abs(FVector::DotProduct(Barrel, FVector::UpVector)) < 0.98) ? FVector::UpVector : FVector::RightVector;

    const FQuat Align = FRotationMatrix::MakeFromXZ(Barrel, Up).ToQuat().Inverse();
    // Center around magazine/receiver so magazines drop cleanly into the open magwell bay and top optics clear the U-fork.
    const FVector Anchor = bHasMag ? MagLoc : (bHasRear ? (RearLoc - FVector(0., 0., 12.)) : FVector::ZeroVector);
    const FVector RotatedAnchor = Align.RotateVector(Anchor);
    const FVector Offset = FVector(0., -RotatedAnchor.Y, -RotatedAnchor.Z - 4.0);
    const FTransform RelPose(Align, Offset);
    MountedGunMesh->SetRelativeTransform(RelPose);

    CachedMuzzleInWeapon = NativeMuzzle * RelPose;
    const FVector MuzzleLoc = CachedMuzzleInWeapon.GetLocation();
    if (!CachedMuzzleInWeapon.IsValid() || MuzzleLoc.X <= 5. || MuzzleLoc.Size() > 140.)
    {
        CachedMuzzleInWeapon = FTransform(FQuat::Identity, FVector(64., 0., 2.5));
    }
    bHasMuzzleInWeapon = true;
    MountedGunMesh->SetVisibility(GetHealth() > 0.f, true);

    if (WeaponFX)
    {
        const FSmartTurretWeaponStats Stats = ComputeWeaponStats(MountedWeapon, GI, CurrentAllRanks());
        WeaponFX->InitializeWorldTracers();
        WeaponFX->SetWorldGunType(FName(*MountedWeapon.Definition), false, false, FTransform::Identity);
        WeaponFX->SetWorldGunSuppressed(Stats.bSuppressed);
    }
}

void AVillageSmartTurret::OnRep_MountedWeapon()
{
    const FString NewKey = ComputeWeaponVisualKey(MountedWeapon);
    if (NewKey != LastBuiltVisualKey)
    {
        LastBuiltVisualKey = NewKey;
        RebuildMountedGunVisual();
        CachedFireSoundKey.Reset();
        CachedFireSound = nullptr;
        bWeaponStatsCached = false;
    }
    ApplyOpticVisualState(0.f);
    UpdateTickCadence();
}

VillageSiegeUpgrades::FRanks AVillageSmartTurret::CurrentAllRanks() const
{
    if (CachedVillageWorld.IsValid())
    {
        return CachedVillageWorld->GetAllSiegeRanks();
    }
    if (const UWorld* W = GetWorld())
    {
        for (TActorIterator<ATemperateHillsWorld> It(W); It; ++It)
        {
            CachedVillageWorld = *It;
            return It->GetAllSiegeRanks();
        }
    }
    return {};
}

FSmartTurretWeaponStats AVillageSmartTurret::GetCurrentWeaponStats() const
{
    const FString Key = ComputeWeaponVisualKey(MountedWeapon);
    const VillageSiegeUpgrades::FRanks Ranks = CurrentAllRanks();
    if (bWeaponStatsCached && CachedStatsWeaponId == Key
        && CachedStatsRanks.Low == Ranks.Low && CachedStatsRanks.High == Ranks.High)
    {
        return CachedWeaponStats;
    }
    auto* GI = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
    CachedWeaponStats = ComputeWeaponStats(MountedWeapon, GI, Ranks);
    CachedStatsWeaponId = Key;
    CachedStatsRanks = Ranks;
    bWeaponStatsCached = true;
    return CachedWeaponStats;
}

float AVillageSmartTurret::GetReloadRemainingSeconds() const
{
    if (!bReloading) return 0.f;
    return FMath::Max(0.f, float(ReloadEndServerTime - CurrentServerTime()));
}

float AVillageSmartTurret::GetReloadProgressFraction() const
{
    if (!bReloading || ReplicatedReloadDuration <= 0.01f) return 1.f;
    return FMath::Clamp(1.f - (GetReloadRemainingSeconds() / ReplicatedReloadDuration), 0.f, 1.f);
}

void AVillageSmartTurret::ApplyOpticVisualState(float DeltaSeconds)
{
    if (!CradleMesh) return;
    const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : -1.;
    uint8 Desired = (GetHealth() <= 0.f || !HasMountedWeapon()) ? uint8(EOpticState::Idle)
        : (bReloading ? uint8(EOpticState::Reloading)
        : ((Now >= 0. && Now < FireFlashUntil) ? uint8(EOpticState::Firing) : OpticState));
    if (Desired != LastAppliedOpticState)
    {
        LastAppliedOpticState = Desired;
        CradleMesh->SetCustomPrimitiveDataFloat(0, float(Desired));
        CradleMesh->SetCustomPrimitiveDataFloat(1, 1.0f);
    }

    if (SlideRecoilOffset > 0.f && DeltaSeconds > 0.f)
    {
        SlideRecoilOffset = FMath::Max(0.f, SlideRecoilOffset - DeltaSeconds * 28.f);
    }
    if (SlideMesh) SlideMesh->SetRelativeLocation(FVector(-SlideRecoilOffset, 0.f, 0.f));
}

void AVillageSmartTurret::StepTurretOrientation(float DeltaSeconds, float DesiredYaw, float DesiredPitch)
{
    const float SafeDelta = FMath::Max(0.f, DeltaSeconds);
    const float YawSpeed = HasMountedWeapon() ? TurretYawSpeedDegPerSec : TurretIdleReturnSpeedDegPerSec;
    const float YawStep = YawSpeed * SafeDelta;
    const float PitchStep = TurretPitchSpeedDegPerSec * SafeDelta;
    const float ClampedDesiredPitch = FMath::Clamp(DesiredPitch, TurretMinPitchDeg, TurretMaxPitchDeg);

    CurrentYawDeg = FRotator::NormalizeAxis(
        CurrentYawDeg + FMath::Clamp(FMath::FindDeltaAngleDegrees(CurrentYawDeg, DesiredYaw), -YawStep, YawStep));
    CurrentPitchDeg = FMath::Clamp(
        CurrentPitchDeg + FMath::Clamp(ClampedDesiredPitch - CurrentPitchDeg, -PitchStep, PitchStep),
        TurretMinPitchDeg, TurretMaxPitchDeg);

    if (GetNetMode() != NM_DedicatedServer && GetHealth() > 0.f)
    {
        if (YawMesh) YawMesh->SetRelativeRotation(FRotator(0.f, CurrentYawDeg, 0.f));
        if (CradleMesh) CradleMesh->SetRelativeRotation(FRotator(CurrentPitchDeg, 0.f, 0.f));
    }
}

void AVillageSmartTurret::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.;

    if (HasAuthority())
    {
        TickAuthorityCombat(DeltaSeconds, Now);
        if (GetNetMode() != NM_DedicatedServer && GetHealth() > 0.f)
        {
            ApplyOpticVisualState(DeltaSeconds);
        }
        UpdateTickCadence();
        return;
    }

    if (GetNetMode() != NM_DedicatedServer && GetHealth() > 0.f)
    {
        const float DesiredPitch = bReloading ? TurretReloadTiltDeg : TargetPitchDeg;
        StepTurretOrientation(DeltaSeconds, TargetYawDeg, DesiredPitch);
        ApplyOpticVisualState(DeltaSeconds);
        UpdateTickCadence();
    }
}

void AVillageSmartTurret::TickAuthorityCombat(float DeltaSeconds, double Now)
{
    if (GetHealth() <= 0.f || !HasMountedWeapon())
    {
        CurrentTarget = nullptr;
        bReloading = false;
        ReloadEndServerTime = 0.;
        bCurrentShotWeakpoint = false;
        OpticState = uint8(EOpticState::Idle);
        StepTurretOrientation(DeltaSeconds, 0.f, 0.f);
        return;
    }

    const FSmartTurretWeaponStats Stats = GetCurrentWeaponStats();
    MaxAmmo = FMath::Max(1, Stats.ExpandedCapacity);
    if (CurrentAmmo > MaxAmmo) CurrentAmmo = MaxAmmo;

    if (bReloading)
    {
        OpticState = uint8(EOpticState::Reloading);
        TargetPitchDeg = TurretReloadTiltDeg;
        StepTurretOrientation(DeltaSeconds, TargetYawDeg, TargetPitchDeg);
        if (CurrentServerTime() >= ReloadEndServerTime)
        {
            FinishOrStepReload(Stats, Now);
        }
        else if (Stats.bTubeShotgun && CurrentAmmo >= 1)
        {
            // Faithful old gamedev mechanic: tube shotguns interrupt progressive reload if a close threat rushes within 22m.
            AcquireTarget(Stats, Now);
            if (CurrentTarget.IsValid())
            {
                const double Dist = FVector::Distance(CurrentTarget->GetActorLocation(), GetActorLocation());
                if (Dist <= TurretTubeInterruptRangeCm)
                {
                    bReloading = false;
                    ReloadEndServerTime = 0.;
                    OpticState = uint8(EOpticState::Tracking);
                    ForceNetUpdate();
                }
            }
        }
        return;
    }

    if (CurrentAmmo <= 0)
    {
        StartReload(Stats, true);
        StepTurretOrientation(DeltaSeconds, TargetYawDeg, TargetPitchDeg);
        return;
    }

    APawn* PrevTarget = CurrentTarget.Get();
    if (Now >= NextScanTime)
    {
        const double Stagger = (SectionId % 8) * 0.012;
        NextScanTime = Now + TurretScanIntervalSec + Stagger * 0.1;
        AcquireTarget(Stats, Now);
    }

    APawn* Target = CurrentTarget.Get();
    if (!Target || !AVillageSiegeEngine::IsThreatUnit(Target, this))
    {
        CurrentTarget = nullptr;
        bCurrentShotWeakpoint = false;
        OpticState = (Now < FireFlashUntil) ? uint8(EOpticState::Firing) : uint8(EOpticState::Idle);
        StepTurretOrientation(DeltaSeconds, TargetYawDeg, 0.f);
        return;
    }

    if (Target != PrevTarget)
    {
        bCurrentShotWeakpoint = Stats.WeakpointChance > 0.f && FMath::FRand() < Stats.WeakpointChance;
        NextLosCheckTime = 0.;
    }

    const FVector Pivot = GetActorTransform().TransformPosition(FVector(0., 0., TurretPivotZCm));
    const double MaxRange = Stats.EffectiveScanRangeCm;
    if (FVector::DistSquared(Pivot, Target->GetActorLocation()) > FMath::Square(MaxRange * 1.05))
    {
        CurrentTarget = nullptr;
        bCurrentShotWeakpoint = false;
        OpticState = uint8(EOpticState::Idle);
        StepTurretOrientation(DeltaSeconds, TargetYawDeg, 0.f);
        return;
    }

    const FVector BaseAim = SelectTargetAimPoint(Target, bCurrentShotWeakpoint);
    const double RawDist = FVector::Distance(Pivot, BaseAim);
    const double TravelTime = FMath::Clamp(RawDist / FMath::Max(6000.f, Stats.BulletSpeedCm), 0., 0.35);
    const FVector TargetVel = Target->GetVelocity().GetClampedToMaxSize(800.);
    FVector AimPoint = BaseAim + TargetVel * TravelTime;

    const FVector PreLocalDir = GetActorTransform().InverseTransformVectorNoScale((AimPoint - Pivot).GetSafeNormal());
    const FRotator PreLocalRot = PreLocalDir.Rotation();
    const float PreYaw = FRotator::NormalizeAxis(PreLocalRot.Yaw);
    const float PrePitch = FMath::Clamp(PreLocalRot.Pitch, TurretMinPitchDeg, TurretMaxPitchDeg);
    const float PreYawErr = FMath::Abs(FMath::FindDeltaAngleDegrees(CurrentYawDeg, PreYaw));
    const float PrePitchErr = FMath::Abs(PrePitch - CurrentPitchDeg);
    const bool bWillFireThisTick = (FMath::Sqrt(PreYawErr * PreYawErr + PrePitchErr * PrePitchErr) <= TurretFireToleranceDeg) && (Now >= NextFireTime);

    if (bWillFireThisTick || Now >= NextLosCheckTime)
    {
        NextLosCheckTime = Now + 0.10;
        if (!HasLineOfSightToTarget(Pivot, AimPoint, Target))
        {
            if (!TargetVel.IsNearlyZero() && HasLineOfSightToTarget(Pivot, BaseAim, Target))
            {
                AimPoint = BaseAim;
            }
            else
            {
                CurrentTarget = nullptr;
                bCurrentShotWeakpoint = false;
                OpticState = uint8(EOpticState::Idle);
                StepTurretOrientation(DeltaSeconds, TargetYawDeg, 0.f);
                return;
            }
        }
    }

    const FVector LocalDir = GetActorTransform().InverseTransformVectorNoScale((AimPoint - Pivot).GetSafeNormal());
    const FRotator LocalRot = LocalDir.Rotation();
    TargetYawDeg = FRotator::NormalizeAxis(LocalRot.Yaw);
    TargetPitchDeg = FMath::Clamp(LocalRot.Pitch, TurretMinPitchDeg, TurretMaxPitchDeg);

    // Step authoritative yaw/pitch and update cradle/weapon world transforms BEFORE FireRound resolves muzzle.
    StepTurretOrientation(DeltaSeconds, TargetYawDeg, TargetPitchDeg);

    const float YawErr = FMath::Abs(FMath::FindDeltaAngleDegrees(CurrentYawDeg, TargetYawDeg));
    const float PitchErr = FMath::Abs(TargetPitchDeg - CurrentPitchDeg);
    const bool bAimed = FMath::Sqrt(YawErr * YawErr + PitchErr * PitchErr) <= TurretFireToleranceDeg;

    OpticState = (Now < FireFlashUntil) ? uint8(EOpticState::Firing) : uint8(EOpticState::Tracking);
    if (bAimed && Now >= NextFireTime)
    {
        FireRound(Stats, AimPoint, Now);
        bCurrentShotWeakpoint = Stats.WeakpointChance > 0.f && FMath::FRand() < Stats.WeakpointChance;
    }
}

void AVillageSmartTurret::AcquireTarget(const FSmartTurretWeaponStats& Stats, double Now)
{
    const FVector Pivot = GetActorTransform().TransformPosition(FVector(0., 0., TurretPivotZCm));
    const double MaxRange = Stats.EffectiveScanRangeCm;
    const double MaxRangeSq = FMath::Square(MaxRange);

    APawn* Kept = CurrentTarget.Get();
    double KeptDistSq = DBL_MAX;
    if (Kept && AVillageSiegeEngine::IsThreatUnit(Kept, this))
    {
        KeptDistSq = FVector::DistSquared(Pivot, Kept->GetActorLocation());
        if (KeptDistSq > MaxRangeSq || !HasLineOfSightToTarget(Pivot, SelectTargetAimPoint(Kept, false), Kept))
        {
            Kept = nullptr;
            KeptDistSq = DBL_MAX;
        }
    }
    else
    {
        Kept = nullptr;
    }

    APawn* Best = Kept;
    double SwitchThresholdSq = Kept ? KeptDistSq * FMath::Square(TurretHysteresisRatio) : MaxRangeSq;

    for (const TWeakObjectPtr<APawn>& Candidate : AVillageSiegeEngine::CachedThreatPawns(GetWorld()))
    {
        APawn* Unit = Candidate.Get();
        if (!Unit || Unit == Kept || !AVillageSiegeEngine::IsThreatUnit(Unit, this)) continue;
        const double D2 = FVector::DistSquared(Pivot, Unit->GetActorLocation());
        if (D2 >= SwitchThresholdSq) continue;
        if (!HasLineOfSightToTarget(Pivot, SelectTargetAimPoint(Unit, false), Unit)) continue;
        SwitchThresholdSq = D2;
        Best = Unit;
    }
    CurrentTarget = Best;
}

bool AVillageSmartTurret::HasLineOfSightToTarget(const FVector& Origin, const FVector& AimPoint, const AActor* Target) const
{
    if (!GetWorld()) return false;
    FFPSAttackQuery Query(SCENE_QUERY_STAT(SmartTurretLOS), true, this);
    if (AActor* Carrier = GetAttachParentActor()) Query.AddIgnoredActor(Carrier);
    FHitResult Hit;
    if (!RangedAttackQuery::LineTraceSingle(GetWorld(), this, Hit, Origin, AimPoint, ECC_Visibility, Query))
        return true;
    AActor* HitActor = Hit.GetActor();
    if (HitActor == Target) return true;
    // Do not drop target lock just because another enemy steps between turret and target.
    if (AVillageSiegeEngine::IsThreatUnit(HitActor, const_cast<AVillageSmartTurret*>(this))) return true;
    return false;
}

FVector AVillageSmartTurret::SelectTargetAimPoint(APawn* Target, bool bWeakpointLock) const
{
    if (!Target) return GetActorTransform().TransformPosition(FVector(100., 0., TurretPivotZCm));

    const USkeletalMeshComponent* Mesh = nullptr;
    if (const auto* Char = Cast<ACharacter>(Target))
    {
        Mesh = Char->GetMesh();
    }
    if (!Mesh)
    {
        Mesh = Target->FindComponentByClass<USkeletalMeshComponent>();
    }

    if (Mesh)
    {
        UPhysicsAsset* Phys = Mesh->GetPhysicsAsset();
        if (CachedAimTarget.Get() != Target)
        {
            CachedAimTarget = Target;
            CachedHeadBone = NAME_None;
            CachedTorsoBone = NAME_None;
            if (Phys)
            {
                if (const auto* HitVol = Cast<UHumanoidHitVolumeData>(Phys->GetAssetUserDataOfClass(UHumanoidHitVolumeData::StaticClass()));
                    HitVol && HitVol->HeadBone != NAME_None && Mesh->GetBoneIndex(HitVol->HeadBone) != INDEX_NONE)
                {
                    CachedHeadBone = HitVol->HeadBone;
                }
                if (CachedHeadBone == NAME_None)
                {
                    for (const USkeletalBodySetup* Setup : Phys->SkeletalBodySetups)
                    {
                        if (!Setup || Mesh->GetBoneIndex(Setup->BoneName) == INDEX_NONE) continue;
                        const FString Lower = Setup->BoneName.ToString().ToLower();
                        if (Lower.Contains(TEXT("head")) || Lower.Contains(TEXT("cranium")))
                        {
                            CachedHeadBone = Setup->BoneName;
                            break;
                        }
                    }
                }
                if (!Phys->SkeletalBodySetups.IsEmpty())
                {
                    int32 BestPriority = -1;
                    TArray<FName, TInlineAllocator<16>> ValidBones;
                    TArray<FVector, TInlineAllocator<16>> ValidCenters;
                    FVector CentroidSum = FVector::ZeroVector;
                    for (const USkeletalBodySetup* Setup : Phys->SkeletalBodySetups)
                    {
                        FVector Center = FVector::ZeroVector;
                        if (!ResolvePhysicsBodyWorldCenter(Mesh, Setup, Center)) continue;
                        const int32 Priority = ScoreTorsoBodyPriority(Setup->BoneName.ToString().ToLower());
                        if (Priority > BestPriority)
                        {
                            BestPriority = Priority;
                            CachedTorsoBone = Setup->BoneName;
                        }
                        ValidBones.Add(Setup->BoneName);
                        ValidCenters.Add(Center);
                        CentroidSum += Center;
                    }
                    if (BestPriority < 2 && !ValidCenters.IsEmpty())
                    {
                        const FVector Centroid = CentroidSum / double(ValidCenters.Num());
                        double ClosestSq = FVector::DistSquared(ValidCenters[0], Centroid);
                        CachedTorsoBone = ValidBones[0];
                        for (int32 Idx = 1; Idx < ValidCenters.Num(); ++Idx)
                        {
                            const double DistSq = FVector::DistSquared(ValidCenters[Idx], Centroid);
                            if (DistSq < ClosestSq)
                            {
                                ClosestSq = DistSq;
                                CachedTorsoBone = ValidBones[Idx];
                            }
                        }
                    }
                }
            }
            if (CachedHeadBone == NAME_None)
            {
                for (const TCHAR* HeadName : {TEXT("head"), TEXT("Head"), TEXT("cranium")})
                {
                    const FName Bone(HeadName);
                    if (Mesh->GetBoneIndex(Bone) != INDEX_NONE) { CachedHeadBone = Bone; break; }
                }
            }
            if (CachedTorsoBone == NAME_None)
            {
                for (const TCHAR* TorsoName : {TEXT("spine_02"), TEXT("spine_03"), TEXT("Spine2"), TEXT("Spine1"), TEXT("chest"), TEXT("pelvis")})
                {
                    const FName Bone(TorsoName);
                    if (Mesh->GetBoneIndex(Bone) != INDEX_NONE) { CachedTorsoBone = Bone; break; }
                }
            }
        }

        const FName DesiredBone = (bWeakpointLock && CachedHeadBone != NAME_None) ? CachedHeadBone : CachedTorsoBone;
        if (DesiredBone != NAME_None)
        {
            if (Phys)
            {
                for (const USkeletalBodySetup* Setup : Phys->SkeletalBodySetups)
                {
                    FVector Center = FVector::ZeroVector;
                    if (Setup && Setup->BoneName == DesiredBone && ResolvePhysicsBodyWorldCenter(Mesh, Setup, Center))
                        return Center;
                }
            }
            if (Mesh->GetBoneIndex(DesiredBone) != INDEX_NONE)
                return Mesh->GetSocketLocation(DesiredBone);
        }
        if (const USkeletalMesh* Asset = Mesh->GetSkeletalMeshAsset())
        {
            const FBox Box = Asset->GetBounds().GetBox().TransformBy(Mesh->GetComponentTransform());
            if (Box.IsValid) return Box.GetCenter();
        }
    }

    return Target->GetActorLocation();
}

FTransform AVillageSmartTurret::ResolveMuzzleWorldTransform() const
{
    const FVector Pivot = GetActorTransform().TransformPosition(FVector(0., 0., TurretPivotZCm));
    if (WeaponAttach && bHasMuzzleInWeapon)
    {
        const FTransform Muzzle = CachedMuzzleInWeapon * WeaponAttach->GetComponentTransform();
        if (FVector::DistSquared(Pivot, Muzzle.GetLocation()) <= FMath::Square(150.))
        {
            return Muzzle;
        }
    }
    const FTransform PivotXform(
        GetActorQuat() * FRotator(CurrentPitchDeg, CurrentYawDeg, 0.).Quaternion(),
        Pivot);
    return FTransform(PivotXform.GetRotation(), PivotXform.TransformPosition(FVector(64., 0., 2.5)));
}

void AVillageSmartTurret::StartReload(const FSmartTurretWeaponStats& Stats, bool bEmpty)
{
    bReloading = true;
    if (Stats.bTubeShotgun)
    {
        const double Step = FMath::Max(0.28, Super90WeaponAssets::LoopStep * (Stats.ReloadTime / FMath::Max(0.5f, float(Super90WeaponAssets::SingleReload))));
        ReloadDurationSec = Step;
    }
    else
    {
        ReloadDurationSec = bEmpty ? Stats.EmptyReloadTime : Stats.ReloadTime;
    }
    ReplicatedReloadDuration = float(FMath::Max(0.1, ReloadDurationSec));
    ReloadEndServerTime = CurrentServerTime() + ReloadDurationSec;
    OpticState = uint8(EOpticState::Reloading);
    ForceNetUpdate();
}

void AVillageSmartTurret::FinishOrStepReload(const FSmartTurretWeaponStats& Stats, double Now)
{
    if (Stats.bTubeShotgun)
    {
        CurrentAmmo = FMath::Min(MaxAmmo, CurrentAmmo + 1);
        if (CurrentAmmo < MaxAmmo)
        {
            StartReload(Stats, false);
            return;
        }
    }
    else
    {
        CurrentAmmo = MaxAmmo;
    }
    bReloading = false;
    ReloadEndServerTime = 0.;
    OpticState = uint8(EOpticState::Tracking);
    NextFireTime = FMath::Max(NextFireTime, Now + 0.04);
    ForceNetUpdate();
}

void AVillageSmartTurret::FireRound(const FSmartTurretWeaponStats& Stats, const FVector& AimPoint, double Now)
{
    if (!Ballistics || CurrentAmmo <= 0) return;

    CurrentAmmo = FMath::Max(0, CurrentAmmo - 1);
    NextFireTime = Now + Stats.FireInterval;
    FireFlashUntil = Now + 0.08;
    OpticState = uint8(EOpticState::Firing);
    ++FireSequence;

    const FVector Pivot = GetActorTransform().TransformPosition(FVector(0., 0., TurretPivotZCm));
    FVector Start = ResolveMuzzleWorldTransform().GetLocation();
    const FVector FallbackDir = (AimPoint - Pivot).GetSafeNormal(UE_SMALL_NUMBER, GetActorForwardVector());
    if (UWorld* World = GetWorld())
    {
        FFPSAttackQuery MuzzleCheck(SCENE_QUERY_STAT(SmartTurretMuzzleClear), true, this);
        if (AActor* Carrier = GetAttachParentActor()) MuzzleCheck.AddIgnoredActor(Carrier);
        FHitResult Block;
        if (RangedAttackQuery::LineTraceSingle(World, this, Block, Pivot, Start, ECC_Visibility, MuzzleCheck)
            && !AVillageSiegeEngine::IsThreatUnit(Block.GetActor(), this))
        {
            Start = Pivot + FallbackDir * 22.;
        }
    }

    const FVector AimDir = (AimPoint - Start).GetSafeNormal(UE_SMALL_NUMBER, FallbackDir);
    const float SpreadRad = FMath::DegreesToRadians(Stats.SpreadDeg);
    const int32 Pellets = FMath::Max(1, Stats.PelletCount);

    for (int32 P = 0; P < Pellets; ++P)
    {
        const FVector ShotDir = (SpreadRad > KINDA_SMALL_NUMBER) ? FMath::VRandCone(AimDir, SpreadRad) : AimDir;
        Ballistics->Launch(
            Start,
            ShotDir,
            Stats.BulletSpeedCm,
            Stats.EffectiveScanRangeCm * 1.15f,
            Stats.PerShotDamage,
            WeaponFX,
            nullptr,
            Stats.WeaponEffectiveRangeCm,
            &MountedWeapon,
            false,
            false,
            FireSequence,
            1,
            Stats.BonusPierce,
            Stats.CritDamageMultiplier);
    }

    MulticastShotFX(Start, AimDir, Stats.bSuppressed, uint8(FMath::Min(255, Pellets)));

    if (CurrentAmmo <= 0)
    {
        StartReload(Stats, true);
    }
}

void AVillageSmartTurret::MulticastShotFX_Implementation(FVector_NetQuantize MuzzlePos, FVector_NetQuantizeNormal AimDir, bool bSuppressed, uint8 FiredPellets)
{
    if (GetNetMode() == NM_DedicatedServer || GetHealth() <= 0.f || MountedWeapon.Definition.IsEmpty()) return;
    SlideRecoilOffset = TurretMaxRecoilSlideCm;
    FireFlashUntil = GetWorld() ? GetWorld()->GetTimeSeconds() + 0.08 : -1.;
    LastAppliedOpticState = 0;

    const FString SoundKey = FString::Printf(TEXT("%s_%d"), *MountedWeapon.Definition, bSuppressed ? 1 : 0);
    if (SoundKey != CachedFireSoundKey || !IsValid(CachedFireSound))
    {
        CachedFireSoundKey = SoundKey;
        CachedFireSound = ResolveWeaponFireSound(MountedWeapon.Definition, bSuppressed);
        if (WeaponFX)
        {
            WeaponFX->SetWorldGunType(FName(*MountedWeapon.Definition), false, false, FTransform::Identity);
            WeaponFX->SetWorldGunSuppressed(bSuppressed);
        }
    }

    if (WeaponFX)
    {
        const FTransform ShotXform(AimDir.Rotation(), MuzzlePos);
        WeaponFX->OnShotAtMuzzle(false, ShotXform, 1.f, 0.f);
        if (!HasAuthority())
        {
            const FVector Dir = FVector(AimDir).GetSafeNormal();
            const float TraceLen = FMath::Min(GetCurrentWeaponStats().EffectiveScanRangeCm, 5500.f);
            FVector TracerEnd = FVector(MuzzlePos) + Dir * TraceLen;
            if (UWorld* World = GetWorld())
            {
                FFPSAttackQuery Q(SCENE_QUERY_STAT(SmartTurretClientTracer), false, this);
                if (AActor* Carrier = GetAttachParentActor()) Q.AddIgnoredActor(Carrier);
                FHitResult Hit;
                if (World->LineTraceSingleByChannel(Hit, FVector(MuzzlePos), TracerEnd, ECC_Visibility, Q))
                {
                    TracerEnd = Hit.ImpactPoint;
                }
            }
            WeaponFX->OnTracerSegment(FVector(MuzzlePos), TracerEnd, false);
        }
    }
    if (IsValid(CachedFireSound))
    {
        UGameplayStatics::PlaySoundAtLocation(this, CachedFireSound, MuzzlePos, 0.85f, 1.f);
    }
}

float AVillageSmartTurret::TakeDamage(float Amount, const FDamageEvent& Event, AController* InstigatorPawn, AActor* Causer)
{
    const float OldHealth = Health;
    const float Dealt = Super::TakeDamage(Amount, Event, InstigatorPawn, Causer);
    if (HasAuthority() && OldHealth > 0.f && Health <= 0.f && HasMountedWeapon())
    {
        EjectWeaponSafely(nullptr);
    }
    return Dealt;
}

bool AVillageSmartTurret::ReturnWeaponToInventory(APawn* Recipient, const FColdSteelItem& Item, bool bAllowWarehouseFallback)
{
    if (!HasAuthority() || Item.Definition.IsEmpty()) return false;
    APawn* TargetPawn = Recipient ? Recipient : MountedOwnerPawn.Get();
    if (!TargetPawn && MountedOwnerState.IsValid())
    {
        TargetPawn = MountedOwnerState->GetPawn();
    }
    UColdSteelStatusModel* Model = TargetPawn ? ColdSteelAuthority::ForPawn(TargetPawn) : nullptr;
    if (!Model && MountedOwnerState.IsValid())
    {
        if (const APlayerController* OwnerPC = MountedOwnerState->GetPlayerController(); OwnerPC && OwnerPC->IsLocalController())
        {
            if (UGameInstance* GI = GetGameInstance()) Model = GI->GetSubsystem<UColdSteelStatusModel>();
        }
        else
        {
            Model = MountedOwnerState->GetShadowModel();
        }
    }
    if (!Model)
    {
        Model = ColdSteelAuthority::Model(this);
    }
    if (!Model) return false;

    FColdSteelProfile Profile = Model->Snapshot();
    const int32 PrevBagSize = Profile.Items.Num();
    if (InsertIntoBagOrCompartment(Profile.Items, Item))
    {
        const FString Key = FString::Printf(TEXT("TurretReturn_%s_%s"), *PlacedId.ToString(EGuidFormats::Digits), *Item.InstanceId);
        return Model->CommitCampfireState(MoveTemp(Profile), Key);
    }
    if (bAllowWarehouseFallback && Profile.Items.Num() == PrevBagSize)
    {
        const int32 WarehouseCap = ColdSteelWarehouse::CellsPerPage * FMath::Max(1, Profile.WarehousePages);
        if (ColdSteelWarehouse::Insert(Profile.Items, Item, WarehouseCap))
        {
            const FString Key = FString::Printf(TEXT("TurretWarehouse_%s_%s"), *PlacedId.ToString(EGuidFormats::Digits), *Item.InstanceId);
            return Model->CommitCampfireState(MoveTemp(Profile), Key);
        }
    }
    return false;
}

void AVillageSmartTurret::SpawnDroppedWeapon(const FColdSteelItem& Item)
{
    if (!HasAuthority() || !GetWorld() || Item.Definition.IsEmpty()) return;
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    const FVector DropLoc = GetActorLocation() + FVector(0., 0., 105.);
    if (auto* Drop = GetWorld()->SpawnActor<AColdSteelPickup>(DropLoc, GetActorRotation(), Spawn))
    {
        FColdSteelItem WorldCopy = Item;
        WorldCopy.Place = 2;
        WorldCopy.Cell = 0;
        WorldCopy.Container.Reset();
        WorldCopy.Position = DropLoc;
        Drop->InitializeSharedItem(WorldCopy);
    }
}

void AVillageSmartTurret::PersistWeaponState()
{
    if (!HasAuthority() || !GetWorld() || !WorldId.IsValid() || !PlacedId.IsValid()) return;
    if (auto* State = GetWorld()->GetSubsystem<UVillageDefenseState>())
    {
        if (HasMountedWeapon())
        {
            FColdSteelItem ToSave = MountedWeapon;
            ToSave.Magazine = FMath::Max(0, CurrentAmmo);
            State->SaveTurretWeapon(WorldId, PlacedId, ToSave);
        }
        else
        {
            State->ClearTurretWeapon(WorldId, PlacedId);
        }
    }
}

void AVillageSmartTurret::EjectWeaponSafely(APawn* PreferredOwner)
{
    if (!HasAuthority() || !HasMountedWeapon()) return;
    FColdSteelItem Ejected = MountedWeapon;
    Ejected.Magazine = FMath::Max(0, CurrentAmmo);

    if (!ReturnWeaponToInventory(PreferredOwner, Ejected, true))
    {
        SpawnDroppedWeapon(Ejected);
    }

    MountedWeapon = FColdSteelItem{};
    MountedOwnerPawn.Reset();
    MountedOwnerState.Reset();
    CurrentAmmo = 0;
    MaxAmmo = 0;
    bReloading = false;
    ReloadEndServerTime = 0.;
    CurrentTarget = nullptr;
    OpticState = uint8(EOpticState::Idle);
    PersistWeaponState();
    OnRep_MountedWeapon();
    ForceNetUpdate();
}

bool AVillageSmartTurret::ServerMountFromPlayer(APawn* Player, const FString& ItemInstanceId, FString& OutMessage)
{
    if (!HasAuthority() || !IsValid(Player))
    {
        OutMessage = TEXT("无权修改炮塔武器。");
        return false;
    }
    if (GetHealth() <= 0.f)
    {
        OutMessage = TEXT("智能机枪塔已损毁，请先按 E 修复。");
        return false;
    }
    if (FVector::DistSquared(Player->GetActorLocation(), GetActorLocation()) > FMath::Square(420.))
    {
        OutMessage = TEXT("请靠近智能机枪塔再进行武器装配。");
        return false;
    }
    UColdSteelStatusModel* Model = ColdSteelAuthority::ForPawn(Player);
    if (!Model)
    {
        OutMessage = TEXT("玩家背包尚未就绪。");
        return false;
    }

    Model->SyncRuntime();
    FColdSteelProfile Profile = Model->Snapshot();
    const int32 FoundIdx = Profile.Items.IndexOfByPredicate([&ItemInstanceId](const FColdSteelItem& E)
    {
        return E.InstanceId == ItemInstanceId && (E.Place == 0 || E.Place == ColdSteelInventory::ColdSteelCompartment::Place);
    });
    if (FoundIdx == INDEX_NONE)
    {
        OutMessage = TEXT("背包中未找到该枪械。");
        return false;
    }
    const FColdSteelItem Candidate = Profile.Items[FoundIdx];
    if (!IsMountableFirearm(Candidate.Definition))
    {
        OutMessage = TEXT("智能机枪塔仅支持挂载主战长枪（步枪 / 轻机枪 / 霰弹 / 狙击，不含手枪）。");
        return false;
    }

    FColdSteelItem Returning = MountedWeapon;
    const bool bSwapping = !Returning.Definition.IsEmpty();
    if (bSwapping) Returning.Magazine = FMath::Max(0, CurrentAmmo);

    Profile.Items.RemoveAt(FoundIdx);
    if (bSwapping)
    {
        if (!InsertIntoBagOrCompartment(Profile.Items, Returning))
        {
            OutMessage = TEXT("背包空间不足，无法替换卸下当前枪械。");
            return false;
        }
    }

    const FString CommitKey = FString::Printf(TEXT("TurretMount_%s_%s"), *PlacedId.ToString(EGuidFormats::Digits), *Candidate.InstanceId);
    if (!Model->CommitCampfireState(MoveTemp(Profile), CommitKey))
    {
        OutMessage = Model->ResultMessage().IsEmpty() ? TEXT("背包事务提交失败。") : Model->ResultMessage();
        return false;
    }

    MountedWeapon = Candidate;
    MountedWeapon.Place = 2;
    MountedWeapon.Container.Reset();
    MountedOwnerPawn = Player;
    MountedOwnerState = Player->GetPlayerState<AColdSteelPlayerState>();
    const FSmartTurretWeaponStats Stats = GetCurrentWeaponStats();
    MaxAmmo = FMath::Max(1, Stats.ExpandedCapacity);
    CurrentAmmo = FMath::Clamp(Candidate.Magazine > 0 ? Candidate.Magazine : MaxAmmo, 1, MaxAmmo);
    bReloading = false;
    ReloadEndServerTime = 0.;
    CurrentTarget = nullptr;
    NextScanTime = 0.;
    NextLosCheckTime = 0.;
    NextFireTime = 0.;
    OpticState = uint8(EOpticState::Tracking);

    PersistWeaponState();
    OnRep_MountedWeapon();
    ForceNetUpdate();

    const FString GunName = ColdSteelInventory::Text(MountedWeapon, TEXT("name"));
    OutMessage = bSwapping
        ? FString::Printf(TEXT("已替换为「%s」，原枪械已退回背包。"), *GunName)
        : FString::Printf(TEXT("已挂载「%s」，智能索敌系统就绪。"), *GunName);
    return true;
}

bool AVillageSmartTurret::ServerUnmountToPlayer(APawn* Player, FString& OutMessage)
{
    if (!HasAuthority() || !IsValid(Player))
    {
        OutMessage = TEXT("无权卸下炮塔武器。");
        return false;
    }
    if (!HasMountedWeapon())
    {
        OutMessage = TEXT("当前炮塔尚未挂载枪械。");
        return false;
    }
    if (FVector::DistSquared(Player->GetActorLocation(), GetActorLocation()) > FMath::Square(420.))
    {
        OutMessage = TEXT("请靠近智能机枪塔再卸下枪械。");
        return false;
    }

    FColdSteelItem Returning = MountedWeapon;
    Returning.Magazine = FMath::Max(0, CurrentAmmo);
    if (!ReturnWeaponToInventory(Player, Returning, false))
    {
        OutMessage = TEXT("背包空间不足，请清理后再卸下枪械。");
        return false;
    }

    const FString GunName = ColdSteelInventory::Text(Returning, TEXT("name"));
    MountedWeapon = FColdSteelItem{};
    MountedOwnerPawn.Reset();
    MountedOwnerState.Reset();
    CurrentAmmo = 0;
    MaxAmmo = 0;
    bReloading = false;
    ReloadEndServerTime = 0.;
    CurrentTarget = nullptr;
    OpticState = uint8(EOpticState::Idle);

    PersistWeaponState();
    OnRep_MountedWeapon();
    ForceNetUpdate();

    OutMessage = FString::Printf(TEXT("已卸下「%s」并放回背包。"), *GunName);
    return true;
}
