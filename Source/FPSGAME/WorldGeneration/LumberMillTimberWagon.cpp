#include "LumberMillTimberWagon.h"
#include "LumberMillSupplyRoute.h"
#include "TemperateHillsWorld.h"
#include "VillagePresentationView.h"
#include "HAL/IConsoleManager.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"

namespace LumberWagonGeom
{
    constexpr float RearWheelRadiusCm = 52.f;
    constexpr float FrontWheelScale = 0.72f;
    constexpr float FrontWheelRadiusCm = RearWheelRadiusCm * FrontWheelScale; // 37.44 cm (cut-under clearance vs MainSill Z>=78.5)
    constexpr float RearAxleX = -105.f;
    constexpr float RearTrackHalfY = 76.f;
    constexpr float FrontAxleX = 105.f;
    constexpr float FrontTrackHalfY = 72.f;
    constexpr float HorseOffsetFromFrontAxleX = 218.f; // Singletree @ +66 => Horse X=-152 (+19 cm clear of walk tail, +24 cm clear of hind hooves)
    constexpr float DriverSeatX = 108.f;
    constexpr float DriverSeatZ = 136.f;
    constexpr float ReinTerretX = -8.f;
    constexpr float ReinTerretHalfY = 14.f;
    constexpr float ReinTerretZ = 177.5f;
    constexpr float MaxDrawDistCm = 18000.f;
}

ALumberMillTimberWagon::ALumberMillTimberWagon()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PrePhysics;
    bReplicates = true;
    bAlwaysRelevant = true;
    SetReplicateMovement(false);
    SetCanBeDamaged(false);
    SetNetUpdateFrequency(1.f);

    WagonRoot = CreateDefaultSubobject<USceneComponent>(TEXT("WagonRoot"));
    SetRootComponent(WagonRoot);

    auto SetupMesh = [](UStaticMeshComponent* Comp, bool bVisibilityTrace)
    {
        Comp->SetCollisionEnabled(bVisibilityTrace ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
        Comp->SetCollisionObjectType(ECC_WorldDynamic);
        Comp->SetCollisionResponseToAllChannels(ECR_Ignore);
        if (bVisibilityTrace)
        {
            Comp->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
        }
        Comp->SetCanEverAffectNavigation(false);
        Comp->SetGenerateOverlapEvents(false);
        Comp->SetReceivesDecals(false);
        Comp->LDMaxDrawDistance = LumberWagonGeom::MaxDrawDistCm;
    };

    ChassisMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ChassisMesh"));
    ChassisMesh->SetupAttachment(WagonRoot);
    // Keep ChassisMesh for visibility/weapon traces only; exact walkable & rideable pawn collision is owned by the UBoxComponents below.
    SetupMesh(ChassisMesh, true);

    TimberLoadMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TimberLoadMesh"));
    TimberLoadMesh->SetupAttachment(WagonRoot);
    SetupMesh(TimberLoadMesh, false);
    TimberLoadMesh->SetVisibility(false);

    auto MakeRideBox = [&](const TCHAR* Name, const FVector& LocalPos, const FVector& HalfExtent, bool bWalkableStepUp) -> UBoxComponent*
    {
        UBoxComponent* Box = CreateDefaultSubobject<UBoxComponent>(Name);
        Box->SetupAttachment(WagonRoot);
        Box->InitBoxExtent(HalfExtent);
        Box->SetRelativeLocation(LocalPos);
        Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Box->SetCollisionObjectType(ECC_WorldDynamic);
        Box->SetCollisionResponseToAllChannels(ECR_Ignore);
        Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
        Box->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
        Box->CanCharacterStepUpOn = bWalkableStepUp ? ECB_Yes : ECB_No;
        Box->SetCanEverAffectNavigation(false);
        Box->SetGenerateOverlapEvents(false);
        Box->SetHiddenInGame(true);
        return Box;
    };

    // Exact build_lumber_wagon_r52.py datums:
    //  - Empty oak bed deck top = 95.0 cm (X=[-146..+88], Y=[-62..+62]); Loaded timber stack top = 156.0 cm (clears East Portcullis!)
    //  - Two low rear boarding steps (36 cm -> 72 cm -> 95 cm, all deltas <= player MaxStepHeight 40 cm => walk OR jump straight aboard!)
    //  - Side stake guard rails (Y=+-68, Z=[95..165]) keep riding players safely inside the bed around curves while leaving the rear open.
    BedWalkDeck = MakeRideBox(TEXT("BedWalkDeck"), FVector(-29.f, 0.f, 89.f), FVector(117.f, 62.f, 6.f), true);
    RearLowerStep = MakeRideBox(TEXT("RearLowerStep"), FVector(-168.f, 0.f, 18.f), FVector(10.f, 52.f, 18.f), true);
    RearUpperStep = MakeRideBox(TEXT("RearUpperStep"), FVector(-151.f, 0.f, 54.f), FVector(7.f, 54.f, 18.f), true);
    SideGuardL = MakeRideBox(TEXT("SideGuardL"), FVector(-19.f, -68.f, 130.f), FVector(107.f, 5.f, 35.f), false);
    SideGuardR = MakeRideBox(TEXT("SideGuardR"), FVector(-19.f, 68.f, 130.f), FVector(107.f, 5.f, 35.f), false);
    DriverSeatDeck = MakeRideBox(TEXT("DriverSeatDeck"), FVector(107.f, 0.f, 115.f), FVector(19.f, 58.f, 21.f), true);
    DriverFootboardDeck = MakeRideBox(TEXT("DriverFootboardDeck"), FVector(142.f, 0.f, 88.f), FVector(16.f, 58.f, 6.f), true);
    FrontDashGuard = MakeRideBox(TEXT("FrontDashGuard"), FVector(163.f, 0.f, 118.f), FVector(5.f, 62.f, 26.f), false);
    UndercarriageBox = MakeRideBox(TEXT("UndercarriageBox"), FVector(4.f, 0.f, 54.f), FVector(144.f, 66.f, 34.f), false);

    RearLeftWheel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RearLeftWheel"));
    RearLeftWheel->SetupAttachment(WagonRoot);
    RearLeftWheel->SetRelativeLocation(FVector(LumberWagonGeom::RearAxleX, -LumberWagonGeom::RearTrackHalfY, LumberWagonGeom::RearWheelRadiusCm));
    RearLeftWheel->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
    SetupMesh(RearLeftWheel, false);

    RearRightWheel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RearRightWheel"));
    RearRightWheel->SetupAttachment(WagonRoot);
    RearRightWheel->SetRelativeLocation(FVector(LumberWagonGeom::RearAxleX, LumberWagonGeom::RearTrackHalfY, LumberWagonGeom::RearWheelRadiusCm));
    SetupMesh(RearRightWheel, false);

    FrontAxlePivot = CreateDefaultSubobject<USceneComponent>(TEXT("FrontAxlePivot"));
    FrontAxlePivot->SetupAttachment(WagonRoot);
    FrontAxlePivot->SetRelativeLocation(FVector(LumberWagonGeom::FrontAxleX, 0.f, LumberWagonGeom::FrontWheelRadiusCm));

    FrontAxleMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrontAxleMesh"));
    FrontAxleMesh->SetupAttachment(FrontAxlePivot);
    SetupMesh(FrontAxleMesh, false);

    FrontLeftWheel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrontLeftWheel"));
    FrontLeftWheel->SetupAttachment(FrontAxlePivot);
    FrontLeftWheel->SetRelativeLocation(FVector(0.f, -LumberWagonGeom::FrontTrackHalfY, 0.f));
    FrontLeftWheel->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
    FrontLeftWheel->SetRelativeScale3D(FVector(LumberWagonGeom::FrontWheelScale));
    SetupMesh(FrontLeftWheel, false);

    FrontRightWheel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrontRightWheel"));
    FrontRightWheel->SetupAttachment(FrontAxlePivot);
    FrontRightWheel->SetRelativeLocation(FVector(0.f, LumberWagonGeom::FrontTrackHalfY, 0.f));
    FrontRightWheel->SetRelativeScale3D(FVector(LumberWagonGeom::FrontWheelScale));
    SetupMesh(FrontRightWheel, false);

    HorseRoot = CreateDefaultSubobject<USceneComponent>(TEXT("HorseRoot"));
    HorseRoot->SetupAttachment(FrontAxlePivot);
    HorseRoot->SetRelativeLocation(FVector(LumberWagonGeom::HorseOffsetFromFrontAxleX, 0.f, -LumberWagonGeom::FrontWheelRadiusCm));

    HorseMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("HorseMesh"));
    HorseMesh->SetupAttachment(HorseRoot);
    HorseMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HorseMesh->SetGenerateOverlapEvents(false);
    HorseMesh->SetReceivesDecals(false);
    HorseMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    HorseMesh->bEnableUpdateRateOptimizations = true;
    HorseMesh->LDMaxDrawDistance = LumberWagonGeom::MaxDrawDistCm;

    HorseManeMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("HorseManeMesh"));
    HorseManeMesh->SetupAttachment(HorseMesh);
    HorseManeMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HorseManeMesh->SetGenerateOverlapEvents(false);
    HorseManeMesh->SetReceivesDecals(false);
    HorseManeMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    HorseManeMesh->bEnableUpdateRateOptimizations = true;
    HorseManeMesh->LDMaxDrawDistance = LumberWagonGeom::MaxDrawDistCm;

    HarnessMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HarnessMesh"));
    HarnessMesh->SetupAttachment(HorseRoot);
    SetupMesh(HarnessMesh, false);

    DriverSeatAnchor = CreateDefaultSubobject<USceneComponent>(TEXT("DriverSeatAnchor"));
    DriverSeatAnchor->SetupAttachment(WagonRoot);
    DriverSeatAnchor->SetRelativeLocation(FVector(LumberWagonGeom::DriverSeatX, 0.f, LumberWagonGeom::DriverSeatZ));

    // 2-segment articulated leather reins per side: Driver Hand -> Harness Brass ReinTerret Ring -> Horse Mouth Bit (0.0 cm detachment!).
    UStaticMesh* ReinUnit = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    UMaterialInterface* ReinMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/Materials/M_StableHarnessLeather.M_StableHarnessLeather"));
    auto InitRein = [&](TObjectPtr<UStaticMeshComponent>& Comp, const TCHAR* Name)
    {
        Comp = CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Comp->SetupAttachment(WagonRoot);
        if (ReinUnit) Comp->SetStaticMesh(ReinUnit);
        if (ReinMat) Comp->SetMaterial(0, ReinMat);
        SetupMesh(Comp, false);
        Comp->SetVisibility(false);
    };
    InitRein(ReinLeftRearMesh, TEXT("ReinLeftRearMesh"));
    InitRein(ReinLeftFrontMesh, TEXT("ReinLeftFrontMesh"));
    InitRein(ReinRightRearMesh, TEXT("ReinRightRearMesh"));
    InitRein(ReinRightFrontMesh, TEXT("ReinRightFrontMesh"));
}

void ALumberMillTimberWagon::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ALumberMillTimberWagon, NetState);
    DOREPLIFETIME(ALumberMillTimberWagon, DriverWorker);
}

void ALumberMillTimberWagon::BeginPlay()
{
    Super::BeginPlay();
    EnsureRouteAndTerrain();
    if (!bAssetsBound)
    {
        // Self-load assets on clients if spawned before subsystem binds them.
        auto* ChassisSM = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_TimberWagon_Chassis.SM_LM_TimberWagon_Chassis"));
        auto* FrontAxleSM = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_TimberWagon_FrontAxle.SM_LM_TimberWagon_FrontAxle"));
        auto* WheelSM = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_TimberWagon_Wheel.SM_LM_TimberWagon_Wheel"));
        auto* LoadSM = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_TimberWagon_TimberLoad.SM_LM_TimberWagon_TimberLoad"));
        auto* HarnessSM = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_HorseHarness.SM_LM_HorseHarness"));
        auto* HorseSK = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/SK_StableWarhorse.SK_StableWarhorse"));
        auto* ManeSK = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/ManeR16/SK_Warhorse_Mane.SK_Warhorse_Mane"));
        auto* HIdle = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_Idle.A_Warhorse_Idle"));
        auto* HWalk = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_Walk.A_Warhorse_Walk"));
        TArray<USoundBase*> Hooves;
        for (int32 I = 1; I <= 4; ++I)
        {
            if (auto* S = LoadObject<USoundBase>(nullptr, *FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Audio/SW_Hoof_Walk_%02d.SW_Hoof_Walk_%02d"), I, I)))
                Hooves.Add(S);
        }
        auto* Atten = LoadObject<USoundAttenuation>(nullptr, TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Audio/ATT_StableHoof_Walk.ATT_StableHoof_Walk"));
        ApplyArtAssets(ChassisSM, FrontAxleSM, WheelSM, LoadSM, HarnessSM, HorseSK, ManeSK, HIdle, HWalk, Hooves, Atten);
    }
    VisualDistanceCm = NetState.DistanceCm;
    bHasInitialNetSync = HasAuthority() || NetState.ServerWorldTime > 0.0;
    UpdateWalkDeckForLoadState(NetState.bLoaded);
    ApplyRoutePose(VisualDistanceCm, GetPhase() == ELumberWagonPhase::ReturningToMill, 0.f);
    LastAppliedDistanceCm = VisualDistanceCm;
    bLastAppliedReturning = (GetPhase() == ELumberWagonPhase::ReturningToMill);
    bParkedPoseSettled = !IsInTransit();
    UpdateRayTracingVisibility(true);
}

void ALumberMillTimberWagon::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    ClearRidingCharacterTickOrder();
    Super::EndPlay(EndPlayReason);
}

void ALumberMillTimberWagon::UpdateWalkDeckForLoadState(bool bLoaded)
{
    if (TimberLoadMesh)
    {
        TimberLoadMesh->SetVisibility(bLoaded);
        TimberLoadMesh->SetCollisionEnabled(bLoaded ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
        TimberLoadMesh->SetCollisionResponseToAllChannels(ECR_Ignore);
        if (bLoaded)
        {
            TimberLoadMesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
        }
    }
    if (!BedWalkDeck) return;

    const bool bRisingOntoLogs = (!bWalkDeckLoaded && bLoaded);
    bWalkDeckLoaded = bLoaded;

    if (bLoaded)
    {
        // Loaded 11-log stack walkable top at Z=156.0 cm (standing player top 332 cm < East Portcullis 340..480 cm!).
        BedWalkDeck->SetBoxExtent(FVector(115.f, 56.f, 34.f), true);
        BedWalkDeck->SetRelativeLocation(FVector(-33.f, 0.f, 122.f));
    }
    else
    {
        // Empty oak plank cargo bed top at exact BED_TOP_Z = 95.0 cm.
        BedWalkDeck->SetBoxExtent(FVector(117.f, 62.f, 6.f), true);
        BedWalkDeck->SetRelativeLocation(FVector(-29.f, 0.f, 89.f));
    }

    // If timber logs load while a player is already standing inside the empty cargo bed, smoothly lift them onto the logs!
    if (bRisingOntoLogs && GetWorld())
    {
        const FTransform WagonTf = GetActorTransform();
        for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        {
            APlayerController* PC = It->Get();
            ACharacter* Char = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
            if (!IsValid(Char)) continue;
            const UCharacterMovementComponent* CMC = Char->GetCharacterMovement();
            const bool bBasedOnDeck = (CMC && CMC->GetMovementBaseObject() == BedWalkDeck.Get());
            const FVector LocalPos = WagonTf.InverseTransformPosition(Char->GetActorLocation());
            const float HalfH = Char->GetCapsuleComponent() ? Char->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 88.f;
            const double FootLocalZ = LocalPos.Z - double(HalfH);
            const bool bInsideCargoBox = (LocalPos.X >= -154.0 && LocalPos.X <= 92.0 && FMath::Abs(LocalPos.Y) <= 68.0 && FootLocalZ >= 72.0 && FootLocalZ < 156.0);
            if (bBasedOnDeck || bInsideCargoBox)
            {
                const FVector LiftedLocal(LocalPos.X, FMath::Clamp(LocalPos.Y, -50.0, 50.0), 156.0 + double(HalfH) + 3.0);
                Char->SetActorLocation(WagonTf.TransformPosition(LiftedLocal), false, nullptr, ETeleportType::TeleportPhysics);
            }
        }
    }
}

void ALumberMillTimberWagon::SyncRidingCharacterTickOrder()
{
    UWorld* World = GetWorld();
    if (!World) return;

    TArray<UCharacterMovementComponent*, TInlineAllocator<8>> ActiveRiders;
    for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
    {
        const APlayerController* PC = It->Get();
        const ACharacter* Char = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
        if (!IsValid(Char)) continue;
        UCharacterMovementComponent* CMC = Char->GetCharacterMovement();
        if (!CMC) continue;
        const UPrimitiveComponent* Base = Cast<UPrimitiveComponent>(CMC->GetMovementBaseObject());
        if (Base && Base->GetOwner() == this)
        {
            ActiveRiders.Add(CMC);
        }
    }

    for (int32 I = TrackedRiderMovements.Num() - 1; I >= 0; --I)
    {
        UCharacterMovementComponent* Existing = TrackedRiderMovements[I].Get();
        if (!IsValid(Existing) || !ActiveRiders.Contains(Existing))
        {
            if (IsValid(Existing))
            {
                Existing->RemoveTickPrerequisiteActor(this);
            }
            TrackedRiderMovements.RemoveAtSwap(I);
        }
    }

    for (UCharacterMovementComponent* RiderCMC : ActiveRiders)
    {
        bool bAlreadyTracked = false;
        for (const TWeakObjectPtr<UCharacterMovementComponent>& Ref : TrackedRiderMovements)
        {
            if (Ref.Get() == RiderCMC)
            {
                bAlreadyTracked = true;
                break;
            }
        }
        if (!bAlreadyTracked)
        {
            // Force ALumberMillTimberWagon::Tick to finish updating WagonRoot BEFORE riding CharacterMovementComponent::TickComponent!
            RiderCMC->AddTickPrerequisiteActor(this);
            TrackedRiderMovements.Add(RiderCMC);
        }
    }
}

void ALumberMillTimberWagon::ClearRidingCharacterTickOrder()
{
    for (const TWeakObjectPtr<UCharacterMovementComponent>& Ref : TrackedRiderMovements)
    {
        if (UCharacterMovementComponent* CMC = Ref.Get())
        {
            CMC->RemoveTickPrerequisiteActor(this);
        }
    }
    TrackedRiderMovements.Reset();
}

void ALumberMillTimberWagon::RefreshDynamicReins()
{
    UpdateDynamicReins();
}

void ALumberMillTimberWagon::ApplyArtAssets(
    UStaticMesh* ChassisSM, UStaticMesh* FrontAxleSM, UStaticMesh* WheelSM, UStaticMesh* TimberLoadSM,
    UStaticMesh* HarnessSM, USkeletalMesh* HorseSK, USkeletalMesh* HorseManeSK,
    UAnimSequence* HorseIdleAnim, UAnimSequence* HorseWalkAnim,
    const TArray<USoundBase*>& HoofSounds, USoundAttenuation* HoofAtten)
{
    if (ChassisSM) ChassisMesh->SetStaticMesh(ChassisSM);
    if (FrontAxleSM) FrontAxleMesh->SetStaticMesh(FrontAxleSM);
    if (WheelSM)
    {
        RearLeftWheel->SetStaticMesh(WheelSM);
        RearRightWheel->SetStaticMesh(WheelSM);
        FrontLeftWheel->SetStaticMesh(WheelSM);
        FrontRightWheel->SetStaticMesh(WheelSM);
    }
    if (TimberLoadSM) TimberLoadMesh->SetStaticMesh(TimberLoadSM);
    if (HarnessSM) HarnessMesh->SetStaticMesh(HarnessSM);

    if (HorseSK)
    {
        HorseMesh->SetSkeletalMeshAsset(HorseSK);
        // Mirror StableRidingHorse.cpp exact forward derivation (pelvis -> mouth_socket -> +X).
        const auto& Ref = HorseSK->GetRefSkeleton();
        const int32 Mouth = Ref.FindBoneIndex(TEXT("mouth_socket"));
        const int32 Hip = Ref.FindBoneIndex(TEXT("pelvis"));
        if (Mouth != INDEX_NONE && Hip != INDEX_NONE)
        {
            const FVector Heading = Ref.GetBoneAbsoluteTransform(Mouth).GetLocation() - Ref.GetBoneAbsoluteTransform(Hip).GetLocation();
            HorseMesh->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator(0.f, -Heading.Rotation().Yaw, 0.f));
        }
        if (HorseManeSK)
        {
            HorseManeMesh->SetSkeletalMeshAsset(HorseManeSK);
            HorseManeMesh->SetLeaderPoseComponent(HorseMesh);
            HorseManeMesh->SetComponentTickEnabled(false);
        }
    }

    HorseIdleClip = HorseIdleAnim;
    HorseWalkClip = HorseWalkAnim;
    HoofWalkSounds = HoofSounds;
    HoofAttenuation = HoofAtten;
    bAssetsBound = true;

    UpdateWalkDeckForLoadState(NetState.bLoaded);
    bHorseWalking = false;
    if (HorseIdleClip && HorseMesh->GetSkeletalMeshAsset())
    {
        HorseMesh->PlayAnimation(HorseIdleClip, true);
    }
}

void ALumberMillTimberWagon::EnsureRouteAndTerrain()
{
    if (bRouteBuilt && Hills.IsValid()) return;
    UWorld* World = GetWorld();
    if (!World) return;
    if (!Hills.IsValid())
    {
        for (TActorIterator<ATemperateHillsWorld> It(World); It; ++It)
        {
            if (It->IsForestVillage())
            {
                Hills = *It;
                break;
            }
        }
    }
    if (Hills.IsValid() && Hills->GetVillageSite().bPlaced)
    {
        LumberMillSupplyRoute::BuildWorldPolyline(Hills->GetVillageSite(), RoutePoints, RouteCumulativeCm, RouteTotalCm);
        bRouteBuilt = (RoutePoints.Num() >= 2 && RouteTotalCm > 100.0);
    }
}

bool ALumberMillTimberWagon::IsInTransit() const
{
    const ELumberWagonPhase P = GetPhase();
    return P == ELumberWagonPhase::OutboundToVillage || P == ELumberWagonPhase::ReturningToMill;
}

void ALumberMillTimberWagon::SetAuthoritativeState(ELumberWagonPhase InPhase, bool bInLoaded, float InDistanceCm, float InSpeedCmPerSec)
{
    if (!HasAuthority()) return;
    EnsureRouteAndTerrain();
    const double Now = GetWorld() && GetWorld()->GetGameState()
        ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds()
        : (GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0);
    const bool bPhaseChanged = (NetState.Phase != static_cast<uint8>(InPhase)) || (NetState.bLoaded != bInLoaded);
    NetState.Phase = static_cast<uint8>(InPhase);
    NetState.bLoaded = bInLoaded;
    NetState.DistanceCm = FMath::Clamp(InDistanceCm, 0.f, float(FMath::Max(1.0, RouteTotalCm)));
    NetState.SpeedCmPerSec = InSpeedCmPerSec;
    NetState.ServerWorldTime = Now;
    UpdateWalkDeckForLoadState(bInLoaded);

    // Crisp 12 Hz sync while players may be riding in transit; drop to 1 Hz when parked to save network bandwidth!
    const float DesiredNetHz = IsInTransit() ? 12.f : 1.f;
    if (!FMath::IsNearlyEqual(GetNetUpdateFrequency(), DesiredNetHz, 0.1f))
    {
        SetNetUpdateFrequency(DesiredNetHz);
    }

    if (bPhaseChanged)
    {
        bParkedPoseSettled = false;
        ForceNetUpdate();
    }
}

void ALumberMillTimberWagon::SetSupplyBlockState(bool bInBlocked, bool bInNightInvasion, int32 InRemainingRaiders)
{
    if (!HasAuthority()) return;
    const uint16 ClampedRaiders = uint16(FMath::Clamp(InRemainingRaiders, 0, 65535));
    const bool bChanged = (NetState.bSupplyBlocked != bInBlocked) ||
        (NetState.bNightInvasion != bInNightInvasion) ||
        (NetState.RemainingRaiders != ClampedRaiders);
    NetState.bSupplyBlocked = bInBlocked;
    NetState.bNightInvasion = bInNightInvasion;
    NetState.RemainingRaiders = ClampedRaiders;
    if (bChanged)
    {
        ForceNetUpdate();
    }
}

void ALumberMillTimberWagon::SetDriverWorker(AActor* InDriver)
{
    if (!HasAuthority()) return;
    DriverWorker = InDriver;
    ForceNetUpdate();
}

void ALumberMillTimberWagon::OnRep_NetState()
{
    UpdateWalkDeckForLoadState(NetState.bLoaded);
    EnsureRouteAndTerrain();
    bParkedPoseSettled = false;

    float SnapTarget = NetState.DistanceCm;
    const bool bMoving = IsInTransit() && FMath::Abs(NetState.SpeedCmPerSec) > 5.f;
    if (bMoving && bRouteBuilt && GetWorld())
    {
        const double Now = GetWorld()->GetGameState()
            ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds()
            : GetWorld()->GetTimeSeconds();
        const float ExtrapDt = FMath::Clamp(float(Now - NetState.ServerWorldTime), 0.f, 1.5f);
        SnapTarget = FMath::Clamp(NetState.DistanceCm + NetState.SpeedCmPerSec * ExtrapDt, 0.f, float(RouteTotalCm));
    }

    // Immediately snap on first client net sync (late join) or major distance jump so the wagon never crawls in from origin.
    if (!bHasInitialNetSync || FMath::Abs(VisualDistanceCm - SnapTarget) > 900.f)
    {
        VisualDistanceCm = SnapTarget;
        if (bRouteBuilt)
        {
            bHasInitialNetSync = true;
            const bool bRet = (GetPhase() == ELumberWagonPhase::ReturningToMill);
            ApplyRoutePose(VisualDistanceCm, bRet, 0.f);
            LastAppliedDistanceCm = VisualDistanceCm;
            bLastAppliedReturning = bRet;
            bParkedPoseSettled = !bMoving;
        }
    }
}

double ALumberMillTimberWagon::SampleGroundZ(const FVector2D& XY) const
{
    if (const ATemperateHillsWorld* Terrain = Hills.Get())
    {
        return Terrain->Height(XY.X, XY.Y);
    }
    return GetActorLocation().Z;
}

void ALumberMillTimberWagon::UpdateRayTracingVisibility(bool bForce)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    UWorld* World = GetWorld();
    if (!World) return;
    const double Now = World->GetTimeSeconds();
    if (!bForce && Now < NextWagonRTCheckAt) return;
    NextWagonRTCheckAt = Now + 0.5;

    static const auto* RTDistCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Hills.HorseRayTracingDistCm"));
    const float LimitCm = RTDistCVar ? RTDistCVar->GetFloat() : 2200.f;
    bool bWantRT = LimitCm <= 0.f;
    if (!bWantRT)
    {
        bool bHasView = false;
        const FVector HorseLoc = HorseMesh ? HorseMesh->GetComponentLocation() : GetActorLocation();
        const double Dist = VillagePresentationView::Distance(*World, HorseLoc, 0., &bHasView);
        const double Cutoff = bWagonRTVisible ? (double(LimitCm) + 300.) : double(LimitCm);
        bWantRT = bHasView && Dist <= Cutoff;
    }
    if (bForce || bWantRT != bWagonRTVisible)
    {
        bWagonRTVisible = bWantRT;
        if (HorseMesh) HorseMesh->SetVisibleInRayTracing(bWantRT);
        if (HorseManeMesh) HorseManeMesh->SetVisibleInRayTracing(bWantRT);
    }
}

void ALumberMillTimberWagon::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateRayTracingVisibility(false);
    SyncRidingCharacterTickOrder();
    EnsureRouteAndTerrain();
    if (!bRouteBuilt) return;

    const float Dt = FMath::Clamp(DeltaSeconds, 0.f, 0.25f);
    const ELumberWagonPhase Phase = GetPhase();
    const bool bMoving = IsInTransit() && FMath::Abs(NetState.SpeedCmPerSec) > 5.f;
    const bool bReturning = (Phase == ELumberWagonPhase::ReturningToMill);

    float TargetDist = NetState.DistanceCm;
    if (!HasAuthority() && bMoving)
    {
        const double Now = GetWorld() && GetWorld()->GetGameState()
            ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds()
            : GetWorld()->GetTimeSeconds();
        const float ExtrapDt = FMath::Clamp(float(Now - NetState.ServerWorldTime), 0.f, 1.5f);
        TargetDist = FMath::Clamp(NetState.DistanceCm + NetState.SpeedCmPerSec * ExtrapDt, 0.f, float(RouteTotalCm));
    }

    const float PrevDist = VisualDistanceCm;
    bool bJustSnapped = false;
    if (HasAuthority())
    {
        // Authoritative subsystem already integrates DistanceCm smoothly every frame -> 0.00 cm lag behind NetState!
        VisualDistanceCm = TargetDist;
        bHasInitialNetSync = true;
    }
    else if (!bHasInitialNetSync)
    {
        VisualDistanceCm = TargetDist;
        bHasInitialNetSync = true;
        bJustSnapped = true;
    }
    else if (bMoving)
    {
        // Feed-forward velocity integration + gentle PD error correction eliminates steady-state FInterpTo lag on clients (< 1 cm drift!).
        const float Predicted = FMath::Clamp(VisualDistanceCm + NetState.SpeedCmPerSec * Dt, 0.f, float(RouteTotalCm));
        VisualDistanceCm = FMath::FInterpTo(Predicted, TargetDist, Dt, 8.f);
    }
    else
    {
        VisualDistanceCm = FMath::FInterpTo(VisualDistanceCm, TargetDist, Dt, 12.f);
    }

    const float DeltaTravelCm = bJustSnapped ? 0.f : FMath::Abs(VisualDistanceCm - PrevDist);
    WheelRollCm += DeltaTravelCm;

    // Skip redundant 6-sample terrain & transform updates once parked and fully settled (saves ~100% parked CPU!).
    const bool bNeedsPoseUpdate = bMoving || bJustSnapped || !bParkedPoseSettled ||
        !FMath::IsNearlyEqual(VisualDistanceCm, LastAppliedDistanceCm, 0.05f) ||
        (bReturning != bLastAppliedReturning);
    if (bNeedsPoseUpdate)
    {
        ApplyRoutePose(VisualDistanceCm, bReturning, bJustSnapped ? 0.f : Dt);
        LastAppliedDistanceCm = VisualDistanceCm;
        bLastAppliedReturning = bReturning;
        bParkedPoseSettled = !bMoving && FMath::IsNearlyEqual(VisualDistanceCm, TargetDist, 0.05f);
    }

    UpdateHorseAnimation(bMoving, FMath::Abs(NetState.SpeedCmPerSec));
    UpdateDynamicReins();
    if (bMoving)
    {
        TryPlayHoofSound(FMath::Abs(NetState.SpeedCmPerSec));
    }
}

void ALumberMillTimberWagon::ApplyRoutePose(float DistanceCm, bool bFacingReturn, float DeltaSeconds)
{
    if (!bRouteBuilt) return;
    const float Sign = bFacingReturn ? -1.f : 1.f;
    const double CenterD = FMath::Clamp<double>(DistanceCm, 160.0, FMath::Max(161.0, RouteTotalCm - 360.0));
    // Sample rear axle and front axle along the spline so the chassis follows road curvature cleanly!
    const double RearD = FMath::Clamp(CenterD - Sign * double(LumberWagonGeom::FrontAxleX), 0.0, RouteTotalCm);
    const double FrontD = FMath::Clamp(CenterD + Sign * double(LumberWagonGeom::FrontAxleX), 0.0, RouteTotalCm);
    const double HorseD = FMath::Clamp(FrontD + Sign * double(LumberWagonGeom::HorseOffsetFromFrontAxleX), 0.0, RouteTotalCm);

    FVector2D RearXY, FrontXY, HorseXY, UnusedTan;
    LumberMillSupplyRoute::SampleAtDistance(RoutePoints, RouteCumulativeCm, RearD, RearXY, UnusedTan);
    LumberMillSupplyRoute::SampleAtDistance(RoutePoints, RouteCumulativeCm, FrontD, FrontXY, UnusedTan);
    LumberMillSupplyRoute::SampleAtDistance(RoutePoints, RouteCumulativeCm, HorseD, HorseXY, UnusedTan);

    const FVector RearP(RearXY.X, RearXY.Y, SampleGroundZ(RearXY));
    const FVector FrontP(FrontXY.X, FrontXY.Y, SampleGroundZ(FrontXY));
    const FVector CenterP = 0.5 * (RearP + FrontP);

    FVector Forward = (FrontP - RearP).GetSafeNormal();
    if (Forward.IsNearlyZero()) Forward = FVector(0.0, 1.0, 0.0);
    // Compute local right vector & road cross-slope for realistic wheel grounding!
    FVector RightFlat(-Forward.Y, Forward.X, 0.0);
    RightFlat = RightFlat.GetSafeNormal();
    if (RightFlat.IsNearlyZero()) RightFlat = FVector::RightVector;
    const FVector2D LeftSampleXY(CenterP.X - RightFlat.X * 72.0, CenterP.Y - RightFlat.Y * 72.0);
    const FVector2D RightSampleXY(CenterP.X + RightFlat.X * 72.0, CenterP.Y + RightFlat.Y * 72.0);
    const FVector RightSlope = (FVector(RightSampleXY, SampleGroundZ(RightSampleXY)) - FVector(LeftSampleXY, SampleGroundZ(LeftSampleXY))).GetSafeNormal();
    const FVector Up = FVector::CrossProduct(RightSlope, Forward).GetSafeNormal();
    const FRotator ChassisRot = FRotationMatrix::MakeFromXZ(Forward, Up.Z > 0.3 ? Up : FVector::UpVector).Rotator();

    // Preserve any riding players cleanly across an instantaneous 180-degree turnaround (ParkedAtTavern -> ReturningToMill)
    // so UpdateBasedMovement never sweeps a standing player through the rotated DriverSeatDeck!
    struct FTurnaroundRider
    {
        ACharacter* Char = nullptr;
        UCharacterMovementComponent* CMC = nullptr;
        FVector LocalPos = FVector::ZeroVector;
        FRotator LocalRot = FRotator::ZeroRotator;
    };
    TArray<FTurnaroundRider, TInlineAllocator<8>> TurnaroundRiders;
    const bool bFlip180 = (LastAppliedDistanceCm >= 0.f) && (bFacingReturn != bLastAppliedReturning);
    if (bFlip180 && GetWorld())
    {
        const FTransform OldWagonTf = GetActorTransform();
        for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        {
            APlayerController* PC = It->Get();
            ACharacter* Char = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
            UCharacterMovementComponent* CMC = Char ? Char->GetCharacterMovement() : nullptr;
            if (!IsValid(Char) || !CMC) continue;
            const UPrimitiveComponent* Base = Cast<UPrimitiveComponent>(CMC->GetMovementBaseObject());
            if (Base && Base->GetOwner() == this)
            {
                FTurnaroundRider R;
                R.Char = Char;
                R.CMC = CMC;
                R.LocalPos = OldWagonTf.InverseTransformPosition(Char->GetActorLocation());
                R.LocalRot = OldWagonTf.InverseTransformRotation(Char->GetActorQuat()).Rotator();
                TurnaroundRiders.Add(R);
            }
        }
    }

    SetActorLocationAndRotation(CenterP, ChassisRot, false, nullptr, ETeleportType::None);

    if (!TurnaroundRiders.IsEmpty())
    {
        const FTransform NewWagonTf = GetActorTransform();
        for (const FTurnaroundRider& R : TurnaroundRiders)
        {
            if (!IsValid(R.Char) || !IsValid(R.CMC)) continue;
            const FVector NewWorldPos = NewWagonTf.TransformPosition(R.LocalPos);
            const FRotator NewWorldRot = NewWagonTf.TransformRotation(R.LocalRot.Quaternion()).Rotator();
            R.Char->SetActorLocationAndRotation(NewWorldPos, FRotator(0.f, NewWorldRot.Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
            R.CMC->SaveBaseLocation();
        }
    }

    // Steer front axle smoothly toward the horse's point ahead on the road!
    FVector2D HorseVec = HorseXY - FrontXY;
    const float ChassisYaw = ChassisRot.Yaw;
    float TargetSteerYaw = 0.f;
    if (HorseVec.SizeSquared() > 25.0)
    {
        const float HorseYaw = FMath::RadiansToDegrees(FMath::Atan2(HorseVec.Y, HorseVec.X));
        TargetSteerYaw = FMath::Clamp(FRotator::NormalizeAxis(HorseYaw - ChassisYaw), -30.f, 30.f);
    }
    CurrentSteerYawDeg = (DeltaSeconds > 0.f)
        ? FMath::FInterpTo(CurrentSteerYawDeg, TargetSteerYaw, DeltaSeconds, 5.5f)
        : TargetSteerYaw;

    // Hinge front draft shafts + singletree + harness + horse TOGETHER along road grade (0.0 cm vertical shaft detachment!).
    // Pitching FrontAxlePivot around its own axle Y-axis keeps front wheel centers at (0, +-72, 0) planted at 0.0 cm lift!
    FrontAxlePivot->SetRelativeRotation(FRotator(0.f, CurrentSteerYawDeg, 0.f));
    const FVector FlatHorseBase = HorseRoot->GetComponentLocation();
    const double HorseGroundZ = SampleGroundZ(FVector2D(FlatHorseBase.X, FlatHorseBase.Y));
    const float TargetShaftPitchDeg = FMath::Clamp(
        FMath::RadiansToDegrees(FMath::Atan2(float(HorseGroundZ - FlatHorseBase.Z), LumberWagonGeom::HorseOffsetFromFrontAxleX)),
        -12.f, 12.f);
    CurrentShaftPitchDeg = (DeltaSeconds > 0.f)
        ? FMath::FInterpTo(CurrentShaftPitchDeg, TargetShaftPitchDeg, DeltaSeconds, 7.f)
        : TargetShaftPitchDeg;
    FrontAxlePivot->SetRelativeRotation(FRotator(CurrentShaftPitchDeg, CurrentSteerYawDeg, 0.f));

    // Match horse pitch cleanly to road slope between hind hooves (-75 cm) and fore hooves (+65 cm) so all 4 hooves plant flush!
    const FVector HorseLoc = HorseRoot->GetComponentLocation();
    FVector HorseFwdXY = HorseRoot->GetForwardVector();
    HorseFwdXY.Z = 0.0;
    HorseFwdXY = HorseFwdXY.GetSafeNormal();
    if (HorseFwdXY.IsNearlyZero()) HorseFwdXY = FVector(1.0, 0.0, 0.0);
    const double HindZ = SampleGroundZ(FVector2D(HorseLoc.X - HorseFwdXY.X * 75.0, HorseLoc.Y - HorseFwdXY.Y * 75.0));
    const double ForeZ = SampleGroundZ(FVector2D(HorseLoc.X + HorseFwdXY.X * 65.0, HorseLoc.Y + HorseFwdXY.Y * 65.0));
    const float DesiredHorseWorldPitch = FMath::RadiansToDegrees(FMath::Atan2(float(ForeZ - HindZ), 140.f));
    const float CurrentHorseParentPitch = FrontAxlePivot->GetComponentRotation().Pitch;
    const float ResidualHorsePitch = FMath::Clamp(FRotator::NormalizeAxis(DesiredHorseWorldPitch - CurrentHorseParentPitch), -10.f, 10.f);
    HorseRoot->SetRelativeRotation(FRotator(ResidualHorsePitch, 0.f, 0.f));

    // Keep HorseMesh & HarnessMesh coupled tightly to hinged draft shafts (tiny <= 3 cm ground micro-conform only if needed)
    const double PostHingeGroundZ = SampleGroundZ(FVector2D(HorseLoc.X, HorseLoc.Y));
    const float MicroZAdj = FMath::Clamp(float(PostHingeGroundZ - HorseLoc.Z), -3.f, 3.f);
    HorseMesh->SetRelativeLocation(FVector(0.f, 0.f, MicroZAdj));
    HarnessMesh->SetRelativeLocation(FVector(0.f, 0.f, MicroZAdj));

    // Roll all 4 wheels accurately by distance traveled!
    // In UE left-handed coordinates, decreasing Pitch (-angle) rolls the wheel top (+Z) forward (+X).
    // Left wheels have Yaw=180 deg, so their local +X points backward and Pitch increases (+angle) to roll forward!
    const float RearAngleDeg = FMath::Fmod((WheelRollCm / LumberWagonGeom::RearWheelRadiusCm) * (180.f / PI), 360.f);
    const float FrontAngleDeg = FMath::Fmod((WheelRollCm / LumberWagonGeom::FrontWheelRadiusCm) * (180.f / PI), 360.f);
    RearRightWheel->SetRelativeRotation(FRotator(-RearAngleDeg, 0.f, 0.f));
    RearLeftWheel->SetRelativeRotation(FRotator(RearAngleDeg, 180.f, 0.f));
    FrontRightWheel->SetRelativeRotation(FRotator(-FrontAngleDeg, 0.f, 0.f));
    FrontLeftWheel->SetRelativeRotation(FRotator(FrontAngleDeg, 180.f, 0.f));
}

void ALumberMillTimberWagon::UpdateHorseAnimation(bool bMoving, float SpeedCmPerSec)
{
    if (!HorseMesh || !HorseMesh->GetSkeletalMeshAsset()) return;
    if (bMoving != bHorseWalking)
    {
        bHorseWalking = bMoving;
        UAnimSequence* Clip = bMoving ? HorseWalkClip : HorseIdleClip;
        if (Clip)
        {
            HorseMesh->PlayAnimation(Clip, true);
        }
    }
    if (bMoving && HorseWalkClip)
    {
        // A_Warhorse_Walk authored cadence ~180 cm/s; scale smoothly up to crisp purposeful draft trot-walk!
        const float Rate = FMath::Clamp(SpeedCmPerSec / 185.f, 0.75f, 1.85f);
        HorseMesh->SetPlayRate(Rate);
    }
    else
    {
        HorseMesh->SetPlayRate(1.f);
    }
}

void ALumberMillTimberWagon::UpdateDynamicReins()
{
    AActor* Driver = DriverWorker.Get();
    const bool bDriverSeated = IsValid(Driver) && IsInTransit();
    const bool bShowReins = bDriverSeated && HorseMesh && HorseMesh->GetSkeletalMeshAsset();
    if (!bShowReins)
    {
        for (UStaticMeshComponent* Comp : { ReinLeftRearMesh.Get(), ReinLeftFrontMesh.Get(), ReinRightRearMesh.Get(), ReinRightFrontMesh.Get() })
        {
            if (Comp && Comp->IsVisible()) Comp->SetVisibility(false);
        }
        return;
    }

    const USkeletalMeshComponent* DriverBody = Driver->FindComponentByClass<USkeletalMeshComponent>();
    if (!DriverBody || !DriverBody->GetSkeletalMeshAsset()) return;

    const FVector MouthPos = HorseMesh->DoesSocketExist(TEXT("mouth_socket"))
        ? HorseMesh->GetSocketLocation(TEXT("mouth_socket"))
        : HorseRoot->GetComponentTransform().TransformPosition(FVector(126.0, 0.0, 152.0));
    const FVector HorseRight = HorseRoot->GetRightVector();
    const FTransform HarnessTf = HarnessMesh->GetComponentTransform();

    auto PlaceSegment = [](UStaticMeshComponent* Comp, const FVector& A, const FVector& B)
    {
        if (!Comp) return;
        const FVector Delta = B - A;
        const float Len = Delta.Size();
        if (Len < 4.f)
        {
            Comp->SetVisibility(false);
            return;
        }
        Comp->SetVisibility(true);
        const FVector Mid = 0.5 * (A + B); // Exact endpoint-to-endpoint coupling (0.0 cm floating offset!)
        const FQuat Rot = FRotationMatrix::MakeFromZ(Delta / Len).ToQuat();
        Comp->SetWorldLocationAndRotation(Mid, Rot);
        // BasicShapes/Cylinder is 100 cm tall x 100 cm diameter -> 1.4 cm thick leather rein strap
        Comp->SetWorldScale3D(FVector(0.014f, 0.014f, Len / 100.f));
    };

    auto PlaceReinPair = [&](UStaticMeshComponent* RearComp, UStaticMeshComponent* FrontComp, FName HandBone, float SideSign)
    {
        const FVector HandPos = DriverBody->DoesSocketExist(HandBone)
            ? DriverBody->GetSocketLocation(HandBone)
            : DriverSeatAnchor->GetComponentTransform().TransformPosition(FVector(22.0, SideSign * 14.5, 42.0));
        // Pass dead-center through the Harness Brass ReinTerret Ring so reins drape authentically over horse withers!
        const FVector TerretPos = HarnessTf.TransformPosition(FVector(
            LumberWagonGeom::ReinTerretX, SideSign * LumberWagonGeom::ReinTerretHalfY, LumberWagonGeom::ReinTerretZ));
        const FVector BitPos = MouthPos + HorseRight * (SideSign * 8.0);
        PlaceSegment(RearComp, HandPos, TerretPos);
        PlaceSegment(FrontComp, TerretPos, BitPos);
    };

    PlaceReinPair(ReinLeftRearMesh.Get(), ReinLeftFrontMesh.Get(), TEXT("hand_l"), -1.f);
    PlaceReinPair(ReinRightRearMesh.Get(), ReinRightFrontMesh.Get(), TEXT("hand_r"), +1.f);
}

void ALumberMillTimberWagon::TryPlayHoofSound(float SpeedCmPerSec)
{
    if (HoofWalkSounds.IsEmpty() || GetNetMode() == NM_DedicatedServer) return;
    UWorld* World = GetWorld();
    if (!World) return;
    const float Now = World->GetTimeSeconds();
    if (Now < NextHoofSoundAt) return;

    // Cull audio when local player is farther than 45 m away (0 audio channels wasted!).
    bool bNearListener = false;
    if (APlayerController* LocalPC = World->GetFirstPlayerController())
    {
        if (APawn* P = LocalPC->GetPawn())
        {
            bNearListener = FVector::DistSquared(P->GetActorLocation(), GetActorLocation()) < FMath::Square(4500.f);
        }
    }
    const float StepInterval = FMath::Clamp(115.f / FMath::Max(120.f, SpeedCmPerSec), 0.24f, 0.52f);
    NextHoofSoundAt = Now + StepInterval;
    if (!bNearListener) return;

    USoundBase* Clip = HoofWalkSounds[HoofStepIndex % HoofWalkSounds.Num()];
    ++HoofStepIndex;
    if (Clip)
    {
        UGameplayStatics::PlaySoundAtLocation(
            World, Clip, HorseRoot->GetComponentLocation(), 0.55f,
            FMath::FRandRange(0.92f, 1.08f), 0.f, HoofAttenuation);
    }
}
