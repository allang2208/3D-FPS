#include "LumberMillWorkerActor.h"
#include "LumberMillTimberWagon.h"
#include "VillagePresentationView.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"

namespace LumberWorkerAssets
{
    const TCHAR* BodySK = TEXT("/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Body.SK_Smith_Body");
    const TCHAR* CoveredMat = TEXT("/Game/Characters/VillageBlacksmithNPC20261118/BodyOutfit/Materials/M_Smith_Covered.M_Smith_Covered");
    const TCHAR* HatSK = TEXT("/Game/Characters/ModularOutfit20260924/WorkwearSet20261024/Hat/SK_FieldHat.SK_FieldHat");

    // 3 visually distinct complete head + workwear sets verified on disk, all sharing SKM_Jason_body_Skeleton.
    // (SK_Smith_Body provides bare arms/neck/feet base; Workwear provides full shirt/trousers/boots; Head provides full face/hair.)
    const TCHAR* RoleHeads[3] = {
        TEXT("/Game/Characters/VillageMasterArtisan/SK_MasterArtisan_Head.SK_MasterArtisan_Head"),
        TEXT("/Game/Characters/VillageCarpenterNPC/Head/SK_Carpenter_Head.SK_Carpenter_Head"),
        TEXT("/Game/Characters/VillageGunsmith/SK_Gunsmith_Head.SK_Gunsmith_Head"),
    };
    const TCHAR* RoleWorkwear[3] = {
        TEXT("/Game/Characters/VillageCarpenterNPC/Outfit/SK_Carpenter_Workwear.SK_Carpenter_Workwear"),
        TEXT("/Game/Characters/VillageMasterArtisan/SK_MasterArtisan_Workwear.SK_MasterArtisan_Workwear"),
        TEXT("/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit.SK_Smith_Outfit"),
    };
    // Resident artisan heads carry complete sculpted hair/beards; omit player FieldHat to avoid hair-crown clipping.
    const bool RoleUsesHat[3] = { false, false, false };

    const TCHAR* IdleAnim = TEXT("/Game/Characters/VillageBlacksmithNPC20261118/Animations/A_Smith_StandingBreath.A_Smith_StandingBreath");
    const TCHAR* WalkAnim = TEXT("/Game/Characters/JasonPlayer20261003/Animations/J_MF_Unarmed_Walk_Fwd.J_MF_Unarmed_Walk_Fwd");
    const TCHAR* ChopTreeAnim = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_ChopTree_Loop.A_LJ_ChopTree_Loop");
    const TCHAR* SplitLogAnim = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_SplitLog_Loop.A_LJ_SplitLog_Loop");
    const TCHAR* SawLogAnim = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_SawLog_Loop.A_LJ_SawLog_Loop");
    const TCHAR* CarryLogAnim = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_CarryLog_Walk.A_LJ_CarryLog_Walk");
    const TCHAR* DriveWagonAnim = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_DriveWagon_Idle.A_LJ_DriveWagon_Idle");
    const TCHAR* SitTavernAnim = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_SitTavern_Relaxed.A_LJ_SitTavern_Relaxed");

    const TCHAR* BattleAxeSM = TEXT("/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe.SM_BattleAxe");
    const TCHAR* CrosscutSawSM = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Arch/SM_LM_TwoManCrosscutSaw.SM_LM_TwoManCrosscutSaw");
    const TCHAR* CarriedLogSM = TEXT("/Game/Items/HarvestTimber/SM_PoplarLog_Solid_A.SM_PoplarLog_Solid_A");
    const TCHAR* SplitHalfLSM = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_SplitLog_HalfL.SM_LM_SplitLog_HalfL");
    const TCHAR* SplitHalfRSM = TEXT("/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/SM_LM_SplitLog_HalfR.SM_LM_SplitLog_HalfR");
    const TCHAR* WoodChipVfx = TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Wood.P_Destruction_Wood");
    const TCHAR* ChopSfx = TEXT("/Game/EasyBuildingSystem/Audio/Sounds/Interactions/Chopping/SC_Hatchet_Hit.SC_Hatchet_Hit");

    constexpr float MaxDrawDistCm = 16000.f;
}

ALumberMillWorker::ALumberMillWorker()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    bAlwaysRelevant = true;
    SetReplicateMovement(true);
    SetCanBeDamaged(false);
    SetNetUpdateFrequency(6.f);

    Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
    Capsule->InitCapsuleSize(30.f, 88.f);
    Capsule->SetCollisionObjectType(ECC_WorldDynamic);
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Capsule->SetCollisionResponseToAllChannels(ECR_Ignore);
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetCanEverAffectNavigation(false);
    Capsule->SetGenerateOverlapEvents(false);
    SetRootComponent(Capsule);

    BodyMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("BodyMesh"));
    BodyMesh->SetupAttachment(Capsule);
    BodyMesh->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -88.f), FRotator(0.f, -90.f, 0.f));
    BodyMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BodyMesh->SetGenerateOverlapEvents(false);
    BodyMesh->SetReceivesDecals(false);
    BodyMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    BodyMesh->bEnableUpdateRateOptimizations = true;
    BodyMesh->LDMaxDrawDistance = LumberWorkerAssets::MaxDrawDistCm;

    auto MakeFollower = [&](const TCHAR* Name)
    {
        auto* Comp = CreateDefaultSubobject<USkeletalMeshComponent>(Name);
        Comp->SetupAttachment(BodyMesh);
        Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Comp->SetGenerateOverlapEvents(false);
        Comp->SetReceivesDecals(false);
        Comp->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
        Comp->bEnableUpdateRateOptimizations = true;
        Comp->LDMaxDrawDistance = LumberWorkerAssets::MaxDrawDistCm;
        return Comp;
    };

    HeadMesh = MakeFollower(TEXT("HeadMesh"));
    WorkwearMesh = MakeFollower(TEXT("WorkwearMesh"));

    HatMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("HatMesh"));
    HatMesh->SetupAttachment(BodyMesh, TEXT("head"));
    // Exact Jason head-socket fit from Content/ColdSteelData/player_body.json.
    HatMesh->SetRelativeLocationAndRotation(FVector(12.021f, -0.225f, 0.107f), FRotator(-86.685f, 117.067f, -122.624f));
    HatMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HatMesh->SetGenerateOverlapEvents(false);
    HatMesh->SetReceivesDecals(false);
    HatMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    HatMesh->bEnableUpdateRateOptimizations = true;
    HatMesh->LDMaxDrawDistance = LumberWorkerAssets::MaxDrawDistCm;
    HatMesh->SetVisibility(false);

    ToolMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ToolMesh"));
    ToolMesh->SetupAttachment(BodyMesh);
    ToolMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    ToolMesh->SetGenerateOverlapEvents(false);
    ToolMesh->SetCanEverAffectNavigation(false);
    ToolMesh->SetReceivesDecals(false);
    ToolMesh->LDMaxDrawDistance = LumberWorkerAssets::MaxDrawDistCm;
    ToolMesh->SetVisibility(false);
}

void ALumberMillWorker::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ALumberMillWorker, WorkerRole);
    DOREPLIFETIME(ALumberMillWorker, ReplicatedAnimState);
    DOREPLIFETIME(ALumberMillWorker, ReplicatedTool);
    DOREPLIFETIME(ALumberMillWorker, ReplicatedMoveSpeed);
    DOREPLIFETIME(ALumberMillWorker, bRestingIndoors);
    DOREPLIFETIME(ALumberMillWorker, ImpactPoint);
    DOREPLIFETIME(ALumberMillWorker, MountedWagon);
}

void ALumberMillWorker::BeginPlay()
{
    Super::BeginPlay();
    ApplyAppearanceAndAnims();
    ApplyToolAndVisibility();
    UpdateRayTracingVisibility(true);
}

void ALumberMillWorker::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (ALumberMillTimberWagon* OldWagon = TickPrereqWagon.Get())
    {
        RemoveTickPrerequisiteActor(OldWagon);
    }
    TickPrereqWagon.Reset();
    RestoreCompoundWorkPropOverride();
    Super::EndPlay(EndPlayReason);
}

void ALumberMillWorker::InitializeRole(ELumberWorkerRole InRole)
{
    if (!HasAuthority()) return;
    WorkerRole = static_cast<uint8>(InRole);
    ActionRateScale = (WorkerRole == 0) ? 1.0f : (0.98f + 0.04f * float(WorkerRole));
    ApplyAppearanceAndAnims();
    ApplyToolAndVisibility();
    ForceNetUpdate();
}

void ALumberMillWorker::SetServerPresentation(ELumberjackAnimState InAnim, ELumberWorkerTool InTool,
    float InSpeedCmPerSec, bool bInRestingIndoors, const FVector& InImpactPoint, ALumberMillTimberWagon* InMountedWagon)
{
    if (!HasAuthority()) return;
    const uint8 NextAnim = static_cast<uint8>(InAnim);
    const uint8 NextTool = static_cast<uint8>(InTool);
    const bool bMajorChange =
        (ReplicatedAnimState != NextAnim) ||
        (ReplicatedTool != NextTool) ||
        (bRestingIndoors != bInRestingIndoors) ||
        (MountedWagon.Get() != InMountedWagon);

    ReplicatedAnimState = NextAnim;
    ReplicatedTool = NextTool;
    ReplicatedMoveSpeed = InSpeedCmPerSec;
    bRestingIndoors = bInRestingIndoors;
    ImpactPoint = InImpactPoint;
    MountedWagon = InMountedWagon;

    // Crisp 10 Hz movement replication only while walking freely; drop to 2 Hz when stationary/mounted/resting to save bandwidth!
    const float DesiredNetHz = (!bInRestingIndoors && !InMountedWagon && InSpeedCmPerSec > 5.f) ? 10.f : 2.f;
    if (!FMath::IsNearlyEqual(GetNetUpdateFrequency(), DesiredNetHz, 0.1f))
    {
        SetNetUpdateFrequency(DesiredNetHz);
    }

    if (bMajorChange)
    {
        ApplyToolAndVisibility();
        ForceNetUpdate();
    }
}

void ALumberMillWorker::OnRep_ReplicatedMovement()
{
    if (HasAuthority())
    {
        Super::OnRep_ReplicatedMovement();
        return;
    }
    // When driving the wagon, UpdateMountedSeatTransform() locks us 0.0 mm onto the client's local DriverSeatAnchor every frame;
    // ignore server transform snaps so the driver never jitters backward/forward against the smoothly moving client wagon!
    if (MountedWagon.IsValid())
    {
        bHasClientRepTarget = false;
        return;
    }
    const FRepMovement& Rep = GetReplicatedMovement();
    ClientRepTargetLoc = Rep.Location;
    ClientRepTargetRot = Rep.Rotation;
    if (!bHasClientRepTarget || bRestingIndoors || FVector::DistSquared(GetActorLocation(), ClientRepTargetLoc) > FMath::Square(450.0))
    {
        SetActorLocationAndRotation(ClientRepTargetLoc, ClientRepTargetRot);
        bHasClientRepTarget = true;
    }
}

void ALumberMillWorker::OnRep_WorkerRole()
{
    ActionRateScale = (WorkerRole == 0) ? 1.0f : (0.98f + 0.04f * float(WorkerRole));
    ApplyAppearanceAndAnims();
    ApplyToolAndVisibility();
}

void ALumberMillWorker::OnRep_WorkState()
{
    ApplyToolAndVisibility();
}

void ALumberMillWorker::ApplyAppearanceAndAnims()
{
    const uint8 ClampedRole = FMath::Clamp<uint8>(WorkerRole, 0, 2);
    if (bAppearanceApplied && AppliedRole == ClampedRole) return;

    USkeletalMesh* BodySK = LoadObject<USkeletalMesh>(nullptr, LumberWorkerAssets::BodySK);
    USkeletalMesh* HeadSK = LoadObject<USkeletalMesh>(nullptr, LumberWorkerAssets::RoleHeads[ClampedRole]);
    USkeletalMesh* WearSK = LoadObject<USkeletalMesh>(nullptr, LumberWorkerAssets::RoleWorkwear[ClampedRole]);
    USkeletalMesh* HatSK = LumberWorkerAssets::RoleUsesHat[ClampedRole]
        ? LoadObject<USkeletalMesh>(nullptr, LumberWorkerAssets::HatSK) : nullptr;

    if (!BodySK)
    {
        UE_LOG(LogTemp, Error, TEXT("LUMBER_WORKER role=%u missing BodySK: %s"), ClampedRole, LumberWorkerAssets::BodySK);
        return;
    }
    BodyMesh->SetSkeletalMeshAsset(BodySK);
    // R59/R60 Armpit/Torso Masking: hide SK_Smith_Body slots 100% covered by the long-sleeve work shirts
    // on ALL 3 worker roles (Slot 0 = DefaultSleeves, Slot 3 = SkinTorso Z=[100.1..140] — Role 1 V-neck throat is
    // covered by HeadMesh + MasterArtisan Flax collar Z=[139.9..152.1], so Slot 3 is completely hidden under the shirt!).
    if (UMaterialInterface* Covered = LoadObject<UMaterialInterface>(nullptr, LumberWorkerAssets::CoveredMat))
    {
        BodyMesh->SetMaterial(0, Covered);
        BodyMesh->SetMaterial(3, Covered);
    }
    if (HeadSK)
    {
        HeadMesh->SetSkeletalMeshAsset(HeadSK);
        HeadMesh->SetLeaderPoseComponent(BodyMesh);
        HeadMesh->SetComponentTickEnabled(false);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("LUMBER_WORKER role=%u missing HeadSK: %s"), ClampedRole, LumberWorkerAssets::RoleHeads[ClampedRole]);
    }
    if (WearSK)
    {
        WorkwearMesh->SetSkeletalMeshAsset(WearSK);
        WorkwearMesh->SetLeaderPoseComponent(BodyMesh);
        WorkwearMesh->SetComponentTickEnabled(false);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("LUMBER_WORKER role=%u missing WorkwearSK: %s"), ClampedRole, LumberWorkerAssets::RoleWorkwear[ClampedRole]);
    }
    if (HatSK)
    {
        HatMesh->SetSkeletalMeshAsset(HatSK);
        HatMesh->AttachToComponent(BodyMesh, FAttachmentTransformRules::KeepRelativeTransform, TEXT("head"));
        HatMesh->SetRelativeLocationAndRotation(FVector(12.021f, -0.225f, 0.107f), FRotator(-86.685f, 117.067f, -122.624f));
        HatMesh->SetVisibility(!bRestingIndoors);
    }
    else
    {
        HatMesh->SetVisibility(false);
    }

    BodyMesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    BodyMesh->SetAnimInstanceClass(ULumberjackAnimInstance::StaticClass());
    if (auto* Anim = Cast<ULumberjackAnimInstance>(BodyMesh->GetAnimInstance()))
    {
        Anim->IdleClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::IdleAnim);
        Anim->WalkClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::WalkAnim);
        Anim->ChopTreeClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::ChopTreeAnim);
        Anim->SplitLogClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::SplitLogAnim);
        Anim->SawLogClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::SawLogAnim);
        Anim->CarryLogWalkClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::CarryLogAnim);
        Anim->DriveWagonClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::DriveWagonAnim);
        Anim->SitTavernClip = LoadObject<UAnimSequence>(nullptr, LumberWorkerAssets::SitTavernAnim);
    }

    AxeMeshAsset = LoadObject<UStaticMesh>(nullptr, LumberWorkerAssets::BattleAxeSM);
    SawMeshAsset = LoadObject<UStaticMesh>(nullptr, LumberWorkerAssets::CrosscutSawSM);
    LogMeshAsset = LoadObject<UStaticMesh>(nullptr, LumberWorkerAssets::CarriedLogSM);
    SplitHalfLMeshAsset = LoadObject<UStaticMesh>(nullptr, LumberWorkerAssets::SplitHalfLSM);
    SplitHalfRMeshAsset = LoadObject<UStaticMesh>(nullptr, LumberWorkerAssets::SplitHalfRSM);
    WoodChipVfx = LoadObject<UParticleSystem>(nullptr, LumberWorkerAssets::WoodChipVfx);
    ChopSfx = LoadObject<USoundBase>(nullptr, LumberWorkerAssets::ChopSfx);

    bAppearanceApplied = true;
    AppliedRole = ClampedRole;
}

void ALumberMillWorker::ApplyToolAndVisibility()
{
    const bool bVisible = !bRestingIndoors;
    SetActorHiddenInGame(!bVisible);
    Capsule->SetCollisionEnabled(bVisible ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
    BodyMesh->SetVisibility(bVisible);
    HeadMesh->SetVisibility(bVisible);
    WorkwearMesh->SetVisibility(bVisible);
    const uint8 ClampedRole = FMath::Clamp<uint8>(WorkerRole, 0, 2);
    HatMesh->SetVisibility(bVisible && LumberWorkerAssets::RoleUsesHat[ClampedRole]);

    const ELumberWorkerTool Tool = static_cast<ELumberWorkerTool>(ReplicatedTool);
    UStaticMesh* DesiredTool = nullptr;
    if (bVisible)
    {
        if (Tool == ELumberWorkerTool::BattleAxe) DesiredTool = AxeMeshAsset;
        else if (Tool == ELumberWorkerTool::CrosscutSaw) DesiredTool = SawMeshAsset;
        else if (Tool == ELumberWorkerTool::CarriedLog) DesiredTool = LogMeshAsset;
    }

    if (DesiredTool)
    {
        if (ToolMesh->GetStaticMesh() != DesiredTool)
        {
            ToolMesh->SetStaticMesh(DesiredTool);
        }
        ToolMesh->SetVisibility(true);
    }
    else
    {
        ToolMesh->SetVisibility(false);
    }
}

void ALumberMillWorker::UpdateRayTracingVisibility(bool bForce)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    UWorld* World = GetWorld();
    if (!World) return;
    const double Now = World->GetTimeSeconds();
    if (!bForce && Now < NextWorkerRTCheckAt) return;
    NextWorkerRTCheckAt = Now + 0.5;

    static const auto* RTDistCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Hills.ResidentRayTracingDistCm"));
    const float LimitCm = RTDistCVar ? RTDistCVar->GetFloat() : 1800.f;
    bool bWantRT = !bRestingIndoors;
    if (bWantRT && LimitCm > 0.f)
    {
        bool bHasView = false;
        const double Dist = VillagePresentationView::Distance(*World, GetActorLocation(), 0., &bHasView);
        const double Cutoff = bWorkerRTVisible ? (double(LimitCm) + 300.) : double(LimitCm);
        bWantRT = bHasView && Dist <= Cutoff;
    }
    if (bForce || bWantRT != bWorkerRTVisible)
    {
        bWorkerRTVisible = bWantRT;
        for (USkeletalMeshComponent* Comp : { BodyMesh.Get(), HeadMesh.Get(), WorkwearMesh.Get(), HatMesh.Get() })
            if (Comp) Comp->SetVisibleInRayTracing(bWantRT);
    }
}

void ALumberMillWorker::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bAppearanceApplied)
    {
        ApplyAppearanceAndAnims();
    }
    UpdateRayTracingVisibility(false);

    UpdateCompoundWorkPropOverride();
    TickSplitLogSimulation(FMath::Clamp(DeltaSeconds, 0.f, 0.1f));

    if (bRestingIndoors) return;

    UpdateMountedSeatTransform();

    if (!HasAuthority() && !MountedWagon.IsValid() && bHasClientRepTarget)
    {
        const float InterpDt = FMath::Clamp(DeltaSeconds, 0.f, 0.25f);
        const FVector SmoothLoc = FMath::VInterpTo(GetActorLocation(), ClientRepTargetLoc, InterpDt, 10.f);
        const FRotator SmoothRot = FMath::RInterpTo(GetActorRotation(), ClientRepTargetRot, InterpDt, 12.f);
        SetActorLocationAndRotation(SmoothLoc, SmoothRot);
    }

    if (auto* Anim = Cast<ULumberjackAnimInstance>(BodyMesh->GetAnimInstance()))
    {
        Anim->SetAnimInputs(static_cast<ELumberjackAnimState>(ReplicatedAnimState), ReplicatedMoveSpeed, ActionRateScale);
    }

    if (GetNetMode() != NM_DedicatedServer)
    {
        UpdateDynamicToolTransform();
    }
    TickWorkImpactFeedback();
}

void ALumberMillWorker::UpdateMountedSeatTransform()
{
    ALumberMillTimberWagon* Wagon = MountedWagon.Get();
    if (TickPrereqWagon.Get() != Wagon)
    {
        if (ALumberMillTimberWagon* OldWagon = TickPrereqWagon.Get())
        {
            RemoveTickPrerequisiteActor(OldWagon);
        }
        if (IsValid(Wagon))
        {
            AddTickPrerequisiteActor(Wagon);
        }
        TickPrereqWagon = Wagon;
    }
    if (!IsValid(Wagon) || !Wagon->GetDriverSeatAnchor()) return;

    // A_Rest_Bench_Idle pelvis center is measured at Z=61.5 cm above mesh root (buttocks contact ~Z=51.0 cm).
    // Capsule root is 88 cm above mesh feet -> Capsule Z = SeatTop + (88 - 51) = +37 cm seats buttocks flush on plank bench!
    const FTransform SeatTf = Wagon->GetDriverSeatAnchor()->GetComponentTransform();
    const FVector WorldPos = SeatTf.TransformPosition(FVector(-6.0, 0.0, 37.0));
    SetActorLocationAndRotation(WorldPos, SeatTf.Rotator());
    // Refresh reins immediately after updating seated driver pose to guarantee 0.0 mm hand-to-rein lag!
    Wagon->RefreshDynamicReins();
}

FVector ALumberMillWorker::ComputePalmGripCenter(FName HandBone, FName MiddleBone, FName IndexBone, FName PinkyBone, bool bIsRight) const
{
    const FVector Hand = BodyMesh->GetSocketLocation(HandBone);
    if (!BodyMesh->DoesSocketExist(MiddleBone)) return Hand;
    const FVector Mid1 = BodyMesh->GetSocketLocation(MiddleBone);
    const FVector Fingers = (Mid1 - Hand).GetSafeNormal();
    if (Fingers.IsNearlyZero()) return Hand;

    // R59: Well-conditioned inward palm normal via index_01 x pinky_01 (dot=+0.99 with finger curl),
    // blended 50/50 with the actual enclosed curled-fist ring centroid (middle_01/02/03 + thumb_02).
    // Exact 1:1 mirror of RigSession::measure_fist_cavity() in author_lumber_ops_r52.py!
    FVector PalmInward = FVector::ZeroVector;
    if (BodyMesh->DoesSocketExist(IndexBone) && BodyMesh->DoesSocketExist(PinkyBone))
    {
        const FVector VIdx = BodyMesh->GetSocketLocation(IndexBone) - Hand;
        const FVector VPnk = BodyMesh->GetSocketLocation(PinkyBone) - Hand;
        const FVector RawN = bIsRight ? FVector::CrossProduct(VPnk, VIdx) : FVector::CrossProduct(VIdx, VPnk);
        PalmInward = FVector::VectorPlaneProject(RawN, Fingers).GetSafeNormal();
    }
    const FVector Analytic = Hand + Fingers * 6.5 + PalmInward * 3.0;

    const FName Mid2Bone = bIsRight ? TEXT("middle_02_r") : TEXT("middle_02_l");
    const FName Mid3Bone = bIsRight ? TEXT("middle_03_r") : TEXT("middle_03_l");
    const FName Thumb2Bone = bIsRight ? TEXT("thumb_02_r") : TEXT("thumb_02_l");
    if (BodyMesh->DoesSocketExist(Mid2Bone) && BodyMesh->DoesSocketExist(Mid3Bone) && BodyMesh->DoesSocketExist(Thumb2Bone))
    {
        const FVector PalmPad = Mid1 * 0.55 + Hand * 0.45;
        const FVector RingCenter = PalmPad * 0.30
            + BodyMesh->GetSocketLocation(Mid2Bone) * 0.25
            + BodyMesh->GetSocketLocation(Mid3Bone) * 0.25
            + BodyMesh->GetSocketLocation(Thumb2Bone) * 0.20;
        return FMath::Lerp(Analytic, RingCenter, 0.50);
    }
    return Analytic;
}

void ALumberMillWorker::UpdateDynamicToolTransform()
{
    if (!ToolMesh || !ToolMesh->IsVisible() || !BodyMesh || !BodyMesh->GetSkeletalMeshAsset()) return;

    const ELumberWorkerTool Tool = static_cast<ELumberWorkerTool>(ReplicatedTool);
    if (Tool == ELumberWorkerTool::BattleAxe)
    {
        // LumberMillOps-R60: EXACT rigid hand_r socket attachment measured on SM_BattleAxe's REAL curved wooden/leather handle
        // (lower leather grip_l Z=-27.5cm X=-4.88cm, upper ash grip_r Z=-7.5cm X=-3.61cm, scale 1.00; 0.000mm slip/drift!).
        // Both A_LJ_SplitLog_Loop and A_LJ_ChopTree_Loop share this identical rigid hand_r contract & FitShaft finger wrap.
        const FTransform HandRWorld = BodyMesh->GetSocketTransform(TEXT("hand_r"), RTS_World);
        static const FTransform AxeInHandR(
            FQuat(-0.294757, 0.138579, 0.892663, -0.311555).GetNormalized(),
            FVector(-13.4449, 2.2296, 4.4388),
            FVector(1.0));
        ToolMesh->SetWorldTransform(AxeInHandR * HandRWorld);
    }
    else if (Tool == ELumberWorkerTool::CrosscutSaw)
    {
        // Measured SM_LM_TwoManCrosscutSaw: vertical oak handle CS_Handle_-1 at X=-83.0 cm, Z=[+14.5..+44.5] (mid +27.5); teeth Z=-2.6 cm.
        // Scale 0.90 => handle midpoint at local (-74.7 cm, 0, +24.75 cm); lock 0.0 mm dead-center inside BOTH curled palms!
        const FVector GripR = ComputePalmGripCenter(TEXT("hand_r"), TEXT("middle_01_r"), TEXT("index_01_r"), TEXT("pinky_01_r"), true);
        const FVector GripL = ComputePalmGripCenter(TEXT("hand_l"), TEXT("middle_01_l"), TEXT("index_01_l"), TEXT("pinky_01_l"), false);
        const FVector HandleMid = 0.5 * (GripR + GripL);
        FVector BladeFwd = ImpactPoint.IsNearlyZero() ? GetActorForwardVector() : (FVector(ImpactPoint) - HandleMid);
        BladeFwd.Z = 0.0;
        BladeFwd = BladeFwd.GetSafeNormal();
        if (BladeFwd.IsNearlyZero()) BladeFwd = GetActorForwardVector();
        const FQuat SawRot = FRotationMatrix::MakeFromXZ(BladeFwd, FVector::UpVector).ToQuat();
        const FVector SawCenter = HandleMid + BladeFwd * 74.7 - FVector(0.0, 0.0, 24.75);
        ToolMesh->SetWorldLocationAndRotation(SawCenter, SawRot);
        ToolMesh->SetWorldScale3D(FVector(0.90f));
    }
    else if (Tool == ELumberWorkerTool::CarriedLog)
    {
        // Measured SM_PoplarLog_Solid_A bounds: X=[-40..+40] (length 80 cm), Y/Z=[-15.3..+15.3] (radius 15.3 cm).
        // Scaled (1.20, 0.56, 0.56) -> 96 cm long x 8.55 cm radius realistic sawn timber log.
        // Rest cleanly ON TOP of outer right shoulder (zero overlap with neck/head/chest!), tilted +7 deg nose-up forward!
        const FVector ShoulderR = BodyMesh->GetSocketLocation(TEXT("upperarm_r"));
        const FVector HandR = BodyMesh->GetSocketLocation(TEXT("hand_r"));
        const FVector ActorFwd = GetActorForwardVector();
        const FVector ActorRight = GetActorRightVector();
        const FVector ActorUp = FVector::UpVector;

        // Outer-top deltoid seat: +9.0 cm outward right, +11.5 cm above upperarm_r joint -> >= 10 cm clear of head/neck!
        const FVector SeatCenter = ShoulderR + ActorRight * 9.0 + ActorUp * 11.5 + ActorFwd * 5.0;
        // Subtle pitch follow from right hand bob while strictly keeping log parallel to walking direction (never angling into head!)
        const double HandRelZ = FMath::Clamp((HandR.Z - SeatCenter.Z) * 0.25, -4.0, 6.0);
        const FVector LogDir = (ActorFwd * 40.0 + ActorUp * (5.5 + HandRelZ)).GetSafeNormal();
        const FQuat LogRot = FRotationMatrix::MakeFromXZ(LogDir, ActorUp).ToQuat();
        ToolMesh->SetWorldLocationAndRotation(SeatCenter, LogRot);
        ToolMesh->SetWorldScale3D(FVector(1.20f, 0.56f, 0.56f));
    }
}

void ALumberMillWorker::RestoreCompoundWorkPropOverride()
{
    if (UStaticMeshComponent* AxeComp = HiddenStumpAxe.Get())
    {
        AxeComp->SetVisibility(true);
        AxeComp->SetHiddenInGame(false);
    }
    HiddenStumpAxe.Reset();

    if (UInstancedStaticMeshComponent* SawHism = HiddenSawHism.Get())
    {
        if (HiddenSawInstanceIndex != INDEX_NONE && HiddenSawInstanceIndex < SawHism->GetInstanceCount())
        {
            SawHism->UpdateInstanceTransform(HiddenSawInstanceIndex, HiddenSawOriginalTransform, true, true, true);
        }
    }
    HiddenSawHism.Reset();
    HiddenSawInstanceIndex = INDEX_NONE;
}

void ALumberMillWorker::UpdateCompoundWorkPropOverride()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    UWorld* World = GetWorld();
    if (!World) return;

    const ELumberjackAnimState State = static_cast<ELumberjackAnimState>(ReplicatedAnimState);
    const bool bWantHideStumpAxe = !bRestingIndoors && State == ELumberjackAnimState::SplitLog && !ImpactPoint.IsNearlyZero();
    const bool bWantHideSawbuckSaw = !bRestingIndoors && State == ELumberjackAnimState::SawLog && !ImpactPoint.IsNearlyZero();

    if (!bWantHideStumpAxe && HiddenStumpAxe.IsValid())
    {
        if (UStaticMeshComponent* AxeComp = HiddenStumpAxe.Get())
        {
            AxeComp->SetVisibility(true);
            AxeComp->SetHiddenInGame(false);
        }
        HiddenStumpAxe.Reset();
    }

    if (!bWantHideSawbuckSaw && HiddenSawHism.IsValid())
    {
        if (UInstancedStaticMeshComponent* SawHism = HiddenSawHism.Get())
        {
            if (HiddenSawInstanceIndex != INDEX_NONE && HiddenSawInstanceIndex < SawHism->GetInstanceCount())
            {
                SawHism->UpdateInstanceTransform(HiddenSawInstanceIndex, HiddenSawOriginalTransform, true, true, true);
            }
        }
        HiddenSawHism.Reset();
        HiddenSawInstanceIndex = INDEX_NONE;
    }

    if ((!bWantHideStumpAxe || HiddenStumpAxe.IsValid()) && (!bWantHideSawbuckSaw || HiddenSawHism.IsValid()))
    {
        return;
    }

    AActor* Compound = CachedCompoundActor.Get();
    if (!IsValid(Compound))
    {
        const double Now = World->GetTimeSeconds();
        if (Now < NextCompoundLookupAt) return;
        NextCompoundLookupAt = Now + 1.0;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (It->ActorHasTag(TEXT("LumberMill.R49")))
            {
                Compound = *It;
                CachedCompoundActor = Compound;
                break;
            }
        }
    }
    if (!IsValid(Compound)) return;

    const FVector Target = FVector(ImpactPoint);
    if (bWantHideStumpAxe && !HiddenStumpAxe.IsValid())
    {
        UStaticMeshComponent* BestAxe = nullptr;
        double BestDSq = FMath::Square(150.0);
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Compound);
        for (UStaticMeshComponent* Comp : Meshes)
        {
            if (!IsValid(Comp) || Cast<UInstancedStaticMeshComponent>(Comp)) continue;
            const UStaticMesh* SM = Comp->GetStaticMesh();
            if (!SM || !SM->GetName().Contains(TEXT("BattleAxe"))) continue;
            const double DSq = FVector::DistSquared2D(Comp->GetComponentLocation(), Target);
            if (DSq < BestDSq)
            {
                BestDSq = DSq;
                BestAxe = Comp;
            }
        }
        if (BestAxe)
        {
            BestAxe->SetVisibility(false);
            BestAxe->SetHiddenInGame(true);
            HiddenStumpAxe = BestAxe;
        }
    }

    if (bWantHideSawbuckSaw && !HiddenSawHism.IsValid())
    {
        UInstancedStaticMeshComponent* BestHism = nullptr;
        int32 BestIdx = INDEX_NONE;
        FTransform BestTf = FTransform::Identity;
        double BestDSq = FMath::Square(150.0);
        TInlineComponentArray<UInstancedStaticMeshComponent*> Hisms(Compound);
        for (UInstancedStaticMeshComponent* Hism : Hisms)
        {
            if (!IsValid(Hism) || !Hism->IsVisible()) continue;
            const UStaticMesh* SM = Hism->GetStaticMesh();
            if (!SM || !SM->GetName().Contains(TEXT("TwoManCrosscutSaw"))) continue;
            const int32 Count = Hism->GetInstanceCount();
            for (int32 Idx = 0; Idx < Count; ++Idx)
            {
                FTransform Tf;
                if (!Hism->GetInstanceTransform(Idx, Tf, true)) continue;
                if (Tf.GetScale3D().GetMin() < 0.1) continue;
                const double DSq = FVector::DistSquared2D(Tf.GetLocation(), Target);
                if (DSq < BestDSq)
                {
                    BestDSq = DSq;
                    BestHism = Hism;
                    BestIdx = Idx;
                    BestTf = Tf;
                }
            }
        }
        if (BestHism && BestIdx != INDEX_NONE)
        {
            HiddenSawHism = BestHism;
            HiddenSawInstanceIndex = BestIdx;
            HiddenSawOriginalTransform = BestTf;
            const FTransform HiddenTf(FQuat::Identity, BestTf.GetLocation() - FVector(0.0, 0.0, 400.0), FVector::ZeroVector);
            BestHism->UpdateInstanceTransform(BestIdx, HiddenTf, true, true, true);
        }
    }
}

void ALumberMillWorker::EnsureSplitLogComponents()
{
    if (GetNetMode() == NM_DedicatedServer || BilletHalfL || !SplitHalfLMeshAsset || !SplitHalfRMeshAsset) return;
    auto MakeSplitMesh = [&](const TCHAR* Name, UStaticMesh* Asset) -> UStaticMeshComponent*
    {
        auto* Comp = NewObject<UStaticMeshComponent>(this, Name, RF_Transient);
        AddInstanceComponent(Comp);
        Comp->SetupAttachment(RootComponent);
        Comp->SetUsingAbsoluteLocation(true);
        Comp->SetUsingAbsoluteRotation(true);
        Comp->SetUsingAbsoluteScale(true);
        Comp->SetStaticMesh(Asset);
        Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Comp->SetGenerateOverlapEvents(false);
        Comp->SetCanEverAffectNavigation(false);
        Comp->SetReceivesDecals(false);
        Comp->SetCastShadow(true);
        Comp->LDMaxDrawDistance = 7000.f;
        Comp->SetVisibility(false);
        Comp->RegisterComponent();
        return Comp;
    };
    BilletHalfL = MakeSplitMesh(TEXT("StumpBilletHalfL"), SplitHalfLMeshAsset);
    BilletHalfR = MakeSplitMesh(TEXT("StumpBilletHalfR"), SplitHalfRMeshAsset);
    for (int32 I = 0; I < MaxSplitHalves; ++I)
    {
        const bool bRight = (I & 1) != 0;
        SplitPool[I].Comp = MakeSplitMesh(
            *FString::Printf(TEXT("FallingSplitHalf_%d"), I),
            bRight ? SplitHalfRMeshAsset.Get() : SplitHalfLMeshAsset.Get());
        SplitPool[I].bActive = false;
    }
}

void ALumberMillWorker::SpawnSplitLogHalves(const FVector& StumpTop, const FVector& CleaveRight, float BilletYawDeg)
{
    EnsureSplitLogComponents();
    if (!SplitPool[0].Comp) return;

    // Measure ground elevation around stump base once so split halves land cleanly on the woodchip earth!
    double BaseGroundZ = StumpTop.Z - 75.0;
    if (UWorld* World = GetWorld())
    {
        FHitResult Hit;
        const FVector ProbeStart = StumpTop + CleaveRight * 62.0 + FVector(0.0, 0.0, 20.0);
        const FVector ProbeEnd = ProbeStart - FVector(0.0, 0.0, 180.0);
        FCollisionQueryParams Params(SCENE_QUERY_STAT(SplitLogGround), false, this);
        if (World->LineTraceSingleByChannel(Hit, ProbeStart, ProbeEnd, ECC_WorldStatic, Params))
        {
            BaseGroundZ = Hit.ImpactPoint.Z;
        }
    }

    const FVector Fwd = GetActorForwardVector();
    const int32 PairBase = (NextSplitPair % (MaxSplitHalves / 2)) * 2;
    ++NextSplitPair;

    for (int32 Side = 0; Side < 2; ++Side)
    {
        FFallingSplitHalf& H = SplitPool[PairBase + Side];
        if (!H.Comp) continue;
        const double Sign = (Side == 0) ? -1.0 : 1.0;
        H.Pos = StumpTop + CleaveRight * (Sign * 3.5) + FVector(0.0, 0.0, 2.0);
        // Realistic axe-wedge kick: halves fly apart perpendicular to blade, clear stump rim & tumble down to earth!
        const double OutSpeed = FMath::FRandRange(108.0, 146.0);
        const double FwdKick = FMath::FRandRange(-26.0, 42.0);
        const double PopUp = FMath::FRandRange(72.0, 102.0);
        H.Vel = CleaveRight * (Sign * OutSpeed) + Fwd * FwdKick + FVector(0.0, 0.0, PopUp);
        H.Rot = FRotator(0.f, BilletYawDeg, 0.f);
        H.AngVel = FVector(
            float(FMath::FRandRange(-90.f, 90.f)),            // Pitch tumble
            float(FMath::FRandRange(-120.f, 120.f)),          // Yaw spin
            float(-Sign * FMath::FRandRange(240.f, 340.f)));  // Roll outward off stump!
        H.GroundZ = BaseGroundZ + 5.8;
        H.Age = 0.f;
        H.bActive = true;
        H.bGrounded = false;
        H.Comp->SetWorldLocationAndRotation(H.Pos, H.Rot);
        H.Comp->SetWorldScale3D(FVector(1.0f));
        H.Comp->SetVisibility(true);
    }
}

void ALumberMillWorker::TickSplitLogSimulation(float DeltaSeconds)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    const ELumberjackAnimState State = static_cast<ELumberjackAnimState>(ReplicatedAnimState);
    const bool bSplitting = !bRestingIndoors && State == ELumberjackAnimState::SplitLog && !ImpactPoint.IsNearlyZero();

    if (bSplitting)
    {
        EnsureSplitLogComponents();
        if (BilletHalfL && BilletHalfR)
        {
            // Align local X=0 split plane parallel to axe swing (Worker Forward) -> BilletYaw = WorkerYaw + 90 deg!
            const float BilletYaw = FRotator::NormalizeAxis(GetActorRotation().Yaw + 90.f);
            const bool bShowIntact = !bBilletSplitThisCycle;
            BilletHalfL->SetVisibility(bShowIntact);
            BilletHalfR->SetVisibility(bShowIntact);
            if (bShowIntact)
            {
                const FVector TopPos = FVector(ImpactPoint);
                const FRotator BilletRot(0.f, BilletYaw, 0.f);
                BilletHalfL->SetWorldLocationAndRotation(TopPos, BilletRot);
                BilletHalfR->SetWorldLocationAndRotation(TopPos, BilletRot);
            }
        }
    }
    else
    {
        bBilletSplitThisCycle = false;
        if (BilletHalfL && BilletHalfL->IsVisible()) BilletHalfL->SetVisibility(false);
        if (BilletHalfR && BilletHalfR->IsVisible()) BilletHalfR->SetVisibility(false);
    }

    // Advance ballistic flight, soft ground bounce, and rest fade for freshly split firewood halves!
    for (int32 I = 0; I < MaxSplitHalves; ++I)
    {
        FFallingSplitHalf& H = SplitPool[I];
        if (!H.bActive || !H.Comp) continue;
        H.Age += DeltaSeconds;
        if (H.Age > 20.f)
        {
            H.bActive = false;
            H.Comp->SetVisibility(false);
            continue;
        }
        if (!H.bGrounded)
        {
            H.Vel.Z -= 980.0 * double(DeltaSeconds);
            H.Pos += H.Vel * double(DeltaSeconds);
            H.Rot.Pitch = FRotator::NormalizeAxis(H.Rot.Pitch + H.AngVel.X * DeltaSeconds);
            H.Rot.Yaw = FRotator::NormalizeAxis(H.Rot.Yaw + H.AngVel.Y * DeltaSeconds);
            H.Rot.Roll = FRotator::NormalizeAxis(H.Rot.Roll + H.AngVel.Z * DeltaSeconds);
            if (H.Pos.Z <= H.GroundZ)
            {
                H.Pos.Z = H.GroundZ;
                if (FMath::Abs(H.Vel.Z) > 95.0)
                {
                    H.Vel.Z = -H.Vel.Z * 0.24;
                    H.Vel.X *= 0.48;
                    H.Vel.Y *= 0.48;
                    H.AngVel *= 0.42;
                }
                else
                {
                    // Settle cleanly lying lengthwise on the woodchip ground!
                    H.Vel = FVector::ZeroVector;
                    H.AngVel = FVector::ZeroVector;
                    H.Rot.Pitch = FMath::Clamp(H.Rot.Pitch, -8.f, 8.f);
                    H.Rot.Roll = (H.Rot.Roll >= 0.f) ? 88.f : -88.f;
                    H.bGrounded = true;
                }
            }
            H.Comp->SetWorldLocationAndRotation(H.Pos, H.Rot);
        }
        else if (H.Age > 18.5f)
        {
            // Gently sink/shrink before recycling so old firewood never pops away abruptly
            const float Alpha = FMath::Clamp((20.f - H.Age) / 1.5f, 0.f, 1.f);
            H.Comp->SetWorldScale3D(FVector(Alpha));
        }
    }
}

void ALumberMillWorker::TickWorkImpactFeedback()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    const ELumberjackAnimState State = static_cast<ELumberjackAnimState>(ReplicatedAnimState);
    if (State != ELumberjackAnimState::ChopTree &&
        State != ELumberjackAnimState::SplitLog &&
        State != ELumberjackAnimState::SawLog)
    {
        PrevActionPhase = 0.f;
        return;
    }

    auto* Anim = Cast<ULumberjackAnimInstance>(BodyMesh->GetAnimInstance());
    if (!Anim) return;
    const float Phase = Anim->GetActiveNormalizedPhase();

    // Seat fresh upright billet on stump as worker recovers back to ready (u >= 0.84 or wrapped past 0)!
    if (State == ELumberjackAnimState::SplitLog && bBilletSplitThisCycle && (Phase >= 0.84f || Phase < PrevActionPhase))
    {
        bBilletSplitThisCycle = false;
    }

    auto Crossed = [&](float Trigger)
    {
        return (PrevActionPhase < Trigger && Phase >= Trigger);
    };

    bool bFire = false;
    bool bDoSplitBillet = false;
    float Volume = 0.42f;
    float Pitch = 1.0f;
    // Synced to exact R60 authored impact phases (author_lumber_ops_r60.py: ChopTree u=0.46, SplitLog frame 24/48 u=0.500)!
    if (State == ELumberjackAnimState::ChopTree && Crossed(0.46f))
    {
        bFire = true;
        Volume = 0.46f;
        Pitch = FMath::FRandRange(0.90f, 1.06f);
    }
    else if (State == ELumberjackAnimState::SplitLog && Crossed(0.50f))
    {
        bFire = true;
        bDoSplitBillet = true;
        Volume = 0.52f;
        Pitch = FMath::FRandRange(0.94f, 1.10f);
    }
    else if (State == ELumberjackAnimState::SawLog && (Crossed(0.25f) || Crossed(0.75f)))
    {
        bFire = true;
        Volume = 0.20f;
        Pitch = FMath::FRandRange(1.35f, 1.55f);
    }
    PrevActionPhase = Phase;
    if (!bFire) return;

    UWorld* World = GetWorld();
    if (!World) return;

    if (bDoSplitBillet && !ImpactPoint.IsNearlyZero())
    {
        bBilletSplitThisCycle = true;
        if (BilletHalfL) BilletHalfL->SetVisibility(false);
        if (BilletHalfR) BilletHalfR->SetVisibility(false);
        const float BilletYaw = FRotator::NormalizeAxis(GetActorRotation().Yaw + 90.f);
        SpawnSplitLogHalves(FVector(ImpactPoint), GetActorRightVector(), BilletYaw);
    }

    // Distance cull VFX/SFX outside 45 m so far-away workers cost zero particles/audio voices.
    if (APlayerController* LocalPC = World->GetFirstPlayerController())
    {
        if (APawn* P = LocalPC->GetPawn())
        {
            if (FVector::DistSquared(P->GetActorLocation(), GetActorLocation()) > FMath::Square(4500.f))
            {
                return;
            }
        }
    }

    FVector FxPos = ImpactPoint.IsNearlyZero()
        ? (GetActorLocation() + GetActorForwardVector() * 75.0)
        : FVector(ImpactPoint);
    if (bDoSplitBillet)
    {
        FxPos.Z += 18.0; // Burst woodchips right where the axe cleaves the upright firewood billet!
    }
    if (WoodChipVfx)
    {
        UGameplayStatics::SpawnEmitterAtLocation(
            World, WoodChipVfx, FTransform(FRotator::ZeroRotator, FxPos, FVector(0.55f)), true);
    }
    if (ChopSfx)
    {
        UGameplayStatics::PlaySoundAtLocation(World, ChopSfx, FxPos, Volume, Pitch);
    }
}
