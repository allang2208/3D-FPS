#include "VillageHerbalist.h"
#include "../NPC/VillageResidentDetail.h"
#include "../UI/ResidentHighlightSubsystem.h"

#include "HerbalistRoamAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"

namespace
{
const FSoftObjectPath HerbalistMesh(TEXT("/Game/Characters/VillageHerbalist/HeadR3/SK_VillageHerbalist_HeadR3.SK_VillageHerbalist_HeadR3"));
const FSoftObjectPath HerbalistIdle(TEXT("/Game/Characters/VillageHerbalist/A_VillageHerbalist_Idle.A_VillageHerbalist_Idle"));
const FSoftObjectPath HerbalistWalk(TEXT("/Game/Characters/VillageHerbalist/A_VillageHerbalist_Walk.A_VillageHerbalist_Walk"));

struct FHerbalistShopStop
{
    FVector FloorPoint;
    float Facing;
};

// Ground-floor centimetres in author_shop03's frame. The service counter occupies
// x=97..153, y=-267..-67. Its staff passage opens to the north. The return stair
// lies west of x=-90. These stops keep both the door and the stairs clear.
const FHerbalistShopStop HerbalistStops[] = {
    {{205., -88., 0.}, 180.f},   // counter service position used by the workshop
    {{213., -211., 0.}, 0.f},    // dispensary shelf
    {{207., 26., 0.}, 90.f},     // open end of the staff passage
    {{93., 51., 0.}, 90.f},      // work aisle
    {{54., 136., 0.}, 68.f},     // in front of the potion bench
    {{19., -79., 0.}, 0.f},      // customer side of the counter
    {{17., -223., 0.}, -90.f},   // view of the hanging herbs
};
constexpr float HerbalistSpeed = 60.f;
constexpr float HerbalistRampSeconds = .22f;
// The installed 50-frame gait advances 100 cm per left-to-left footfall.
constexpr float HerbalistStrideCm = 100.f;

// Integrate the two short, constant-acceleration ramps. The middle of a walk
// stays at its authored pace irrespective of leg length or frame rate.
double HerbalistTravel(double Elapsed, double Length, double& Duration)
{
    Duration = 0.;
    if (Length <= UE_SMALL_NUMBER) return 0.;
    const double Acceleration = HerbalistSpeed / HerbalistRampSeconds;
    const double Ramp = FMath::Min(double(HerbalistRampSeconds), FMath::Sqrt(Length / Acceleration));
    const double PeakSpeed = Acceleration * Ramp;
    Duration = Length / PeakSpeed + Ramp;
    if (Elapsed <= 0.) return 0.;
    if (Elapsed >= Duration) return Length;
    if (Elapsed < Ramp) return .5 * Acceleration * Elapsed * Elapsed;
    const double Remaining = Duration - Elapsed;
    if (Remaining < Ramp) return Length - .5 * Acceleration * Remaining * Remaining;
    return PeakSpeed * (Elapsed - .5 * Ramp);
}
}

AVillageHerbalist::AVillageHerbalist()
{
    bReplicates = true;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    SetCanBeDamaged(false);
    Tags.Append({TEXT("NPC"), TEXT("Friendly"), TEXT("VillageHerbalist")});

    auto* Feet = CreateDefaultSubobject<USceneComponent>(TEXT("StandingPoint"));
    SetRootComponent(Feet);

    Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("StandingCapsule"));
    Capsule->SetupAttachment(Feet);
    Capsule->InitCapsuleSize(28.f, 84.f);
    Capsule->SetRelativeLocation(FVector(0., 0., 84.));
    Capsule->SetCollisionObjectType(ECC_WorldDynamic);
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Capsule->SetCollisionResponseToAllChannels(ECR_Ignore);
    Capsule->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetGenerateOverlapEvents(false);
    Capsule->SetCanEverAffectNavigation(false);

    Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("HerbalistBody"));
    Body->SetupAttachment(Feet);
    Body->SetRelativeRotation(FRotator(0., FResidentConversationFacing::RestYaw, 0.));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetGenerateOverlapEvents(false);
    Body->SetCanEverAffectNavigation(false);
    Body->AddTickPrerequisiteActor(this);
}

void AVillageHerbalist::BeginPlay()
{
    Super::BeginPlay();
    UResidentHighlightSubsystem::RegisterShopkeeper(*this);
    if (HasAuthority())
    {
        // The workshop spawns the standing point facing the counter. Store its
        // immutable shop frame independently of the mobile actor and camera.
        const FQuat ShopRotation = GetActorQuat() * FRotator(0., -HerbalistStops[0].Facing, 0.).Quaternion();
        ShopFrame = FTransform(ShopRotation, FRepMovement::RebaseOntoZeroOrigin(GetActorLocation(), this), GetActorScale3D());
        ShopFrame.AddToTranslation(-ShopFrame.TransformVector(HerbalistStops[0].FloorPoint));
        PublishLeg(GetActorLocation(), GetActorRotation().Yaw);
        WaitAtStop(FMath::FRandRange(4.f, 8.f));
    }
    else if (bHaveRoamLeg)
    {
        SetActorTickEnabled(true);
    }
    if (GetNetMode() != NM_DedicatedServer)
    {
        UVillageResidentDetail::Attach(*this, 
            TArray<FSoftObjectPath>{HerbalistMesh, HerbalistIdle, HerbalistWalk},
            FStreamableDelegate::CreateUObject(this, &AVillageHerbalist::ApplyAppearance), {Body.Get()}, FSimpleDelegate::CreateWeakLambda(this, [this] { IdleClip = nullptr; WalkClip = nullptr; }));
    }
}

void AVillageHerbalist::ApplyAppearance()
{
    auto* Mesh = Cast<USkeletalMesh>(HerbalistMesh.ResolveObject());
    IdleClip = Cast<UAnimSequence>(HerbalistIdle.ResolveObject());
    WalkClip = Cast<UAnimSequence>(HerbalistWalk.ResolveObject());
    if (!Mesh || !IdleClip)
    {
        UE_LOG(LogTemp, Error, TEXT("Village herbalist appearance missing (mesh=%d idle=%d)."), Mesh != nullptr, IdleClip != nullptr);
        return;
    }
    Body->SetSkeletalMeshAsset(Mesh);
    StartConversationIdle();
}

double AVillageHerbalist::ServerNow() const
{
    const auto* State = GetWorld()->GetGameState();
    return State ? State->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}

void AVillageHerbalist::StartConversationIdle()
{
    const double Length = IdleClip->GetPlayLength();
    ConversationFacing.StartIdle(*Body, *IdleClip, Length > 0. ? FMath::Fmod(ServerNow(), Length) : 0.);
}

void AVillageHerbalist::SetLocalConversation(APlayerController* Player)
{
    if (Player && !Player->IsLocalController()) return;
    LocalTalker = Player;
    ConversationFacing.SetLocalPlayer(Player);
    if (Player) SetActorTickEnabled(true);
}

void AVillageHerbalist::SetConversationParticipant(APlayerController* Player, bool bTalking)
{
    if (!HasAuthority() || !Player) return;
    if (bTalking)
    {
        Talkers.Add(Player);
        PublishLeg(GetActorLocation(), GetActorRotation().Yaw);
        WaitAtStop(1.f);
    }
    else if (Talkers.Remove(Player) && Talkers.IsEmpty())
    {
        WaitAtStop(FMath::FRandRange(3.f, 6.f));
    }
}

bool AVillageHerbalist::CanWalkBetween(const FVector& From, const FVector& To) const
{
    const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    const float Radius = Capsule->GetScaledCapsuleRadius();
    const FVector Center(0., 0., HalfHeight);
    // Leave 3 cm beneath the probe for the repaired planks. The visible feet
    // and the interaction capsule retain their original floor-level placement.
    const FCollisionShape Shape = FCollisionShape::MakeCapsule(Radius, FMath::Max(Radius, HalfHeight - 3.f));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HerbalistWalk), false, this);
    Query.bFindInitialOverlaps = true;
    const UWorld* World = GetWorld();
    return !World->SweepTestByChannel(From + Center, To + Center, FQuat::Identity, ECC_Pawn, Shape, Query)
        && !World->SweepTestByObjectType(From + Center, To + Center, FQuat::Identity,
            FCollisionObjectQueryParams(ECC_Pawn), Shape, Query);
}

void AVillageHerbalist::ChooseNextStop()
{
    for (auto It = Talkers.CreateIterator(); It; ++It)
        if (!It->IsValid() || !It->Get()->GetPawn()) It.RemoveCurrent();
    if (!Talkers.IsEmpty())
    {
        WaitAtStop(1.f);
        return;
    }

    const FVector Here = GetActorLocation();
    TArray<int32, TInlineAllocator<UE_ARRAY_COUNT(HerbalistStops)>> Options;
    for (int32 I = 0; I < UE_ARRAY_COUNT(HerbalistStops); ++I) Options.Add(I);
    for (int32 I = Options.Num() - 1; I > 0; --I) Options.Swap(I, FMath::RandRange(0, I));
    // When alternatives are clear, leave the previous destination for another visit.
    const int32 PreviousOption = Options.Find(PreviousStop);
    if (PreviousOption != INDEX_NONE) Options.Swap(PreviousOption, Options.Num() - 1);

    for (int32 Stop : Options)
    {
        const FVector Point = FRepMovement::RebaseOntoLocalOrigin(ShopFrame.TransformPosition(HerbalistStops[Stop].FloorPoint), this);
        const double Distance = FVector::Dist2D(Here, Point);
        // A conversation can interrupt a leg just after setting out. Keep the
        // short way back to that stop available when a player blocks the aisle.
        if (Distance < 3. || Distance > 238. || !CanWalkBetween(Here, Point)) continue;
        TargetStop = Stop;
        PublishLeg(Point, (Point - Here).Rotation().Yaw);
        return;
    }
    // A player may occupy the narrow passage. Try other lines again after they move.
    WaitAtStop(FMath::FRandRange(1.3f, 2.7f));
}

void AVillageHerbalist::WaitAtStop(float Delay)
{
    TargetStop = INDEX_NONE;
    GetWorldTimerManager().SetTimer(NextStopTimer, this, &AVillageHerbalist::ChooseNextStop, Delay);
}

void AVillageHerbalist::PublishLeg(const FVector& Target, float TargetYaw)
{
    RoamLeg.Start = FRepMovement::RebaseOntoZeroOrigin(GetActorLocation(), this);
    RoamLeg.End = FRepMovement::RebaseOntoZeroOrigin(Target, this);
    RoamLeg.StartYaw = GetActorRotation().Yaw;
    RoamLeg.EndYaw = TargetYaw;
    RoamLeg.ServerTime = ServerNow();
    bHaveRoamLeg = true;
    SetActorTickEnabled(true);
    ForceNetUpdate();
}

void AVillageHerbalist::OnRep_RoamLeg()
{
    bHaveRoamLeg = true;
    SetActorTickEnabled(true);
}

void AVillageHerbalist::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AVillageHerbalist, RoamLeg);
}

void AVillageHerbalist::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bHaveRoamLeg) return;
    const FVector Start = FRepMovement::RebaseOntoLocalOrigin(RoamLeg.Start, this);
    const FVector End = FRepMovement::RebaseOntoLocalOrigin(RoamLeg.End, this);
    const FVector Path = End - Start;
    const double Length = Path.Size();
    if (!HasAuthority() && LocalTalker.IsValid() && Length > .15)
    {
        // Owner-reliable dialogue acceptance can arrive before the resident's
        // stopped leg. Immediately stop showing that superseded walk.
        UpdateGait(DeltaSeconds, 0.f);
        return;
    }
    const double Elapsed = FMath::Max(0., ServerNow() - RoamLeg.ServerTime);
    const float Turn = FMath::FindDeltaAngleDegrees(RoamLeg.StartYaw, RoamLeg.EndYaw);
    const double TurnTime = FMath::Abs(Turn) / 225.;
    const double TurnAlpha = TurnTime > UE_SMALL_NUMBER ? FMath::Clamp(Elapsed / TurnTime, 0., 1.) : 1.;
    const float Yaw = RoamLeg.StartYaw + Turn * FMath::SmoothStep(0., 1., TurnAlpha);
    double WalkTime;
    const double Travel = HerbalistTravel(Elapsed - TurnTime, Length, WalkTime);
    const FVector Sample = Start + Path.GetSafeNormal() * Travel;
    const FVector Before = GetActorLocation();
    // The server publishes a stop when a pawn or fixture blocks the walk. A
    // client's interpolated pawns must not veto convergence to that stop.
    const FVector Next = HasAuthority() ? Sample : FMath::VInterpConstantTo(Before, Sample, DeltaSeconds, 2.f * HerbalistSpeed);
    const bool bAdvancing = !Before.Equals(Next, .015f);
    const bool bBlocked = HasAuthority() && bAdvancing && !CanWalkBetween(Before, Next);
    SetActorLocationAndRotation(bBlocked ? Before : Next, FRotator(0., Yaw, 0.));
    if (GetNetMode() != NM_DedicatedServer)
        UpdateGait(DeltaSeconds, FVector::Dist2D(Before, GetActorLocation()));

    const bool bArrived = Elapsed >= TurnTime + WalkTime && GetActorLocation().Equals(End, .15f);
    if (HasAuthority() && TargetStop != INDEX_NONE && (bBlocked || bArrived))
    {
        float RestYaw = GetActorRotation().Yaw;
        if (bArrived) RestYaw = ShopFrame.Rotator().Yaw + HerbalistStops[TargetStop].Facing;
        PreviousStop = TargetStop;
        PublishLeg(GetActorLocation(), RestYaw);
        WaitAtStop(bBlocked ? FMath::FRandRange(1.3f, 2.7f) : FMath::FRandRange(5.f, 13.f));
    }
    else if (bArrived && WalkWeight <= 0.f)
    {
        SetActorTickEnabled(false);
    }
}

void AVillageHerbalist::UpdateGait(float DeltaSeconds, float Distance)
{
    if (!IdleClip || !WalkClip) return;
    const float Speed = DeltaSeconds > UE_SMALL_NUMBER ? Distance / DeltaSeconds : 0.f;
    const float Desired = LocalTalker.IsValid() ? 0.f : FMath::Clamp(Speed / HerbalistSpeed, 0.f, 1.f);
    WalkWeight = FMath::FInterpConstantTo(WalkWeight, Desired, DeltaSeconds, 7.f);
    WalkPhase = FMath::Fmod(WalkPhase + Distance / HerbalistStrideCm, 1.f);
    auto* Anim = Cast<UHerbalistRoamAnimInstance>(Body->GetAnimInstance());
    if (LocalTalker.IsValid())
    {
        if (Anim && WalkWeight <= 0.f) StartConversationIdle();
    }
    else if (!Anim && (!RoamLeg.Start.Equals(RoamLeg.End, .15f) || WalkWeight > 0.f))
    {
        const double Length = IdleClip->GetPlayLength();
        Body->AnimationData.SavedPosition = Length > 0. ? FMath::Fmod(ServerNow(), Length) : 0.;
        Body->SetAnimInstanceClass(UHerbalistRoamAnimInstance::StaticClass());
        Anim = Cast<UHerbalistRoamAnimInstance>(Body->GetAnimInstance());
        if (Anim) Anim->Walk = WalkClip;
    }
    if (Anim && Anim == Body->GetAnimInstance())
    {
        Anim->WalkWeight = WalkWeight;
        Anim->WalkSeconds = WalkPhase * WalkClip->GetPlayLength();
        if (!LocalTalker.IsValid())
        {
            const FRotator Rest(0., FResidentConversationFacing::RestYaw, 0.);
            Body->SetRelativeRotation(FMath::RInterpConstantTo(Body->GetRelativeRotation(), Rest, DeltaSeconds, 420.f));
        }
    }
}

void AVillageHerbalist::EndPlay(EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(NextStopTimer);
    Super::EndPlay(Reason);
}
