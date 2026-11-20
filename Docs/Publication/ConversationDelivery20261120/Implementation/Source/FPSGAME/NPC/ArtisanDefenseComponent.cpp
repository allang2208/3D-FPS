#include "ArtisanDefenseComponent.h"
#include "ArtisanDefenseArrow.h"
#include "SmithHammerTiming.h"
#include "VillageArtisanMerchant.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationData.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"

namespace ArtisanPatrol
{
    constexpr float SmithAlert = 1500.f, CarpenterAlert = 2100.f;
    constexpr float SmithLeash = 2200.f, CarpenterLeash = 2500.f;
    constexpr float HammerReach = 120.f, BowReach = 1750.f;
    constexpr float SmithReachInset = 12.f;
    const FSoftObjectPath HammerSwingSound(TEXT("/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing.S_Warhammer_NormalSwing"));
    const FSoftObjectPath HammerImpactSound(TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick"));
    constexpr float BowDraw = 1.4f, BowRelease = .3f;
    constexpr double WatchDuration = 4.0, ScanInterval = .48;

    FVector AimPoint(const AActor& Actor)
    {
        const auto* Root = Cast<UPrimitiveComponent>(Actor.GetRootComponent());
        return Root ? Root->Bounds.Origin + FVector(0, 0, Root->Bounds.BoxExtent.Z * .20) : Actor.GetActorLocation();
    }
    float Radius(const AActor& Actor)
    {
        const auto* Capsule = Cast<UCapsuleComponent>(Actor.GetRootComponent());
        return Capsule ? Capsule->GetScaledCapsuleRadius() : 28.f;
    }
    FVector GroundOffset(const AActor& Actor)
    {
        const auto* Capsule = Cast<UCapsuleComponent>(Actor.GetRootComponent());
        return FVector(0, 0, Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 91.f);
    }
    float AimHammerPitch(const AActor& Guard, const AActor& Target, bool bClose)
    {
        const auto* Root = Cast<UPrimitiveComponent>(Target.GetRootComponent());
        if (!Root) return 0.f;
        const auto& Contact = SmithHammerTiming::HeadKeys(bClose)[3];
        const float Scale = FMath::Max(.01f, float(FMath::Abs(Guard.GetActorScale3D().Z)));
        const double Feet = Guard.GetActorLocation().Z - GroundOffset(Guard).Z;
        const double Mid = (Root->Bounds.Origin.Z - Feet) / Scale;
        const double Half = Root->Bounds.BoxExtent.Z / Scale;
        const double Band = Half - FMath::Min(16., .2 * Half);
        const double Height = FMath::Clamp(Contact.Head.Z, Mid - Band, Mid + Band);
        const FVector Arm = Contact.Head - Contact.Spine;
        const FVector Forward = FVector::CrossProduct(SmithHammerTiming::AimAxis(bClose), FVector::UpVector);
        const double Reach = FVector::DotProduct(Arm, Forward);
        const double Span = FMath::Sqrt(Reach * Reach + Arm.Z * Arm.Z);
        const double Tilt = FMath::Atan2(Arm.Z, Reach) - FMath::Asin(FMath::Clamp((Height - Contact.Spine.Z) / Span, -1., 1.));
        return FMath::Clamp(float(FMath::RadiansToDegrees(Tilt)), -16.f, 42.f);
    }
    bool InHearingRange(const FVector& A, const FVector& B)
    {
        return FMath::Abs(A.Z - B.Z) < 160.f && FVector::DistSquared2D(A, B) <= FMath::Square(475.f);
    }
    bool InWeaponReach(bool bBow, const AActor& Guard, const AActor& Other, float Inset = 0.f)
    {
        const FVector Here = Guard.GetActorLocation();
        if (bBow) return FVector::DistSquared2D(Here, Other.GetActorLocation()) <= FMath::Square(BowReach);
        const float Scale = FMath::Abs(Guard.GetActorScale3D().X);
        const auto* Root = Cast<UPrimitiveComponent>(Other.GetRootComponent());
        const double Feet = Here.Z - GroundOffset(Guard).Z;
        if (Root && (Root->Bounds.Origin.Z + Root->Bounds.BoxExtent.Z < Feet + 16.f * Scale ||
            Root->Bounds.Origin.Z - Root->Bounds.BoxExtent.Z > Feet + 205.f * Scale)) return false;
        return FVector::DistSquared2D(Here, Other.GetActorLocation()) <= FMath::Square((HammerReach - Inset) * Scale + Radius(Other));
    }

    // Probe above the step height so ordinary stairs can still be climbed by CharacterMovement.
    FVector SmithClearHeading(const ACharacter& Character, const FVector& Desired, float Travel, const FVector& Previous)
    {
        const auto* Capsule = Character.GetCapsuleComponent();
        const auto* Move = Character.GetCharacterMovement();
        const float StepHeight = Move->MaxStepHeight;
        const FVector Center = Capsule->GetComponentLocation() + FVector(0, 0, StepHeight * .5f);
        const float Radius = FMath::Max(1.f, Capsule->GetScaledCapsuleRadius() - 2.f);
        const FCollisionShape Shape = FCollisionShape::MakeCapsule(Radius, FMath::Max(Radius, Capsule->GetScaledCapsuleHalfHeight() - StepHeight * .5f - 2.f));
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(SmithWalkClearance), false, &Character);
        const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
        UWorld* World = Character.GetWorld();
        auto IsClear = [&](const FVector& Heading, FHitResult& Hit)
        {
            return !World->SweepSingleByChannel(Hit, Center, Center + Heading * Travel, FQuat::Identity,
                Capsule->GetCollisionObjectType(), Shape, Query, Response) || Move->IsWalkable(Hit);
        };

        FHitResult Hit;
        if (IsClear(Desired, Hit)) return Desired;
        const FVector Side = FVector::CrossProduct(FVector::UpVector, Desired);
        const double PreviousSide = FVector::DotProduct(Side, Previous);
        const double PreferredSide = FMath::Abs(PreviousSide) > .3 ? PreviousSide : FVector::DotProduct(Side, Hit.ImpactNormal);
        const float FirstAngle = PreferredSide < 0. ? -60.f : 60.f;
        for (const float Angle : {FirstAngle, -FirstAngle})
        {
            const FVector Candidate = Desired.RotateAngleAxis(Angle, FVector::UpVector);
            if (!IsClear(Candidate, Hit)) continue;
            const FVector Feet = Character.GetNavAgentLocation() + Candidate * Travel;
            if (World->LineTraceSingleByChannel(Hit, Feet + FVector(0, 0, StepHeight + 6.f),
                Feet - FVector(0, 0, StepHeight + 12.f), Capsule->GetCollisionObjectType(), Query, Response) &&
                Move->IsWalkable(Hit)) return Candidate;
        }
        return FVector::ZeroVector;
    }
}

UArtisanDefenseComponent::UArtisanDefenseComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = .36f;
}

bool UArtisanDefenseComponent::IsBow() const
{
    const auto* Merchant = Cast<AVillageArtisanMerchant>(GetOwner());
    return Merchant && Merchant->IsCarpenterMerchant();
}

bool UArtisanDefenseComponent::IsAlerted() const
{
    return State == EArtisanGuardState::Watching || State == EArtisanGuardState::Ready || State == EArtisanGuardState::Approach ||
        State == EArtisanGuardState::Attack || State == EArtisanGuardState::Release;
}

void UArtisanDefenseComponent::BeginPlay()
{
    Super::BeginPlay();
    if (GetOwner()->HasAuthority())
    {
        Station = GetOwner()->GetActorLocation();
        StationRotation = GetOwner()->GetActorRotation();
        GetOwner()->SetReplicateMovement(true);
        if (auto* Character = Cast<ACharacter>(GetOwner()))
            Character->GetCharacterMovement()->bRunPhysicsWithNoController = true;
        if (AttackDamage <= 0.f) AttackDamage = IsBow() ? 69.f : 49.5f;
        UNavigationSystemV1::RegisterNavigationInvoker(*GetOwner(), 3300.f, 4200.f);
        bNavigationInvokerRegistered = true;
    }
    if (GetNetMode() != NM_DedicatedServer)
    {
        WarmPresentation();
        if (!IsBow())
        {
            HammerAttenuation = NewObject<USoundAttenuation>(this);
            HammerAttenuation->Attenuation.bSpatialize = true;
            HammerAttenuation->Attenuation.bAttenuate = true;
            HammerAttenuation->Attenuation.AttenuationShapeExtents = FVector(80.f);
            HammerAttenuation->Attenuation.FalloffDistance = 1600.f;
            HammerAudioAssets = UAssetManager::GetStreamableManager().RequestAsyncLoad(
                TArray<FSoftObjectPath>{ArtisanPatrol::HammerSwingSound, ArtisanPatrol::HammerImpactSound});
        }
    }
    OnRep_State();
}

void UArtisanDefenseComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (bNavigationInvokerRegistered) UNavigationSystemV1::UnregisterNavigationInvoker(*GetOwner());
    PresentationAssets.Reset();
    HammerAudioAssets.Reset();
    Super::EndPlay(Reason);
}

void UArtisanDefenseComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UArtisanDefenseComponent, State);
    DOREPLIFETIME(UArtisanDefenseComponent, StateStartedAt);
    DOREPLIFETIME(UArtisanDefenseComponent, HammerPitch);
    DOREPLIFETIME(UArtisanDefenseComponent, bCloseHammer);
}

void UArtisanDefenseComponent::SetDowned(bool bDowned)
{
    if (!GetOwner()->HasAuthority()) return;
    if (bDowned)
    {
        Threat.Reset();
        UnreachableThreats.Reset();
        ClearRoute();
        ChangeState(EArtisanGuardState::Downed);
    }
    else if (State == EArtisanGuardState::Downed)
    {
        const double Now = GetWorld()->GetTimeSeconds();
        if (AcquireNearbyThreat(Now)) return;
        StartReturning(Now);
        RestoreStation(Now, 0.f);
    }
}

void UArtisanDefenseComponent::ChangeState(EArtisanGuardState NewState)
{
    if (State == NewState) return;
    const bool bSmith = !IsBow();
    if (bSmith && NewState == EArtisanGuardState::Approach)
    {
        ProgressSample = GetOwner()->GetActorLocation();
        ProgressAt = GetWorld()->GetTimeSeconds();
        Detour = 0;
    }
    NextSmithProbe = 0.;
    if (NewState != EArtisanGuardState::Approach && NewState != EArtisanGuardState::Returning)
        if (auto* Character = Cast<ACharacter>(GetOwner()))
        {
            Character->ConsumeMovementInputVector();
            // Let ground braking complete the last stride before he plants for a swing.
            if (!bSmith || NewState == EArtisanGuardState::Downed || NewState == EArtisanGuardState::AtWork)
                Character->GetCharacterMovement()->StopMovementImmediately();
        }
    StateStartedAt = GetWorld()->GetTimeSeconds();
    State = NewState;
    OnRep_State();
    GetOwner()->ForceNetUpdate();
}

void UArtisanDefenseComponent::OnRep_State()
{
    const bool bRest = IsAtWork() || State == EArtisanGuardState::Downed;
    SetComponentTickEnabled(!bRest || (IsAtWork() && GetOwner()->HasAuthority()));
    SetComponentTickInterval(bRest ? .36f : 0.f);
    RefreshPresentation();
    if (IsAtWork() && HasBegunPlay()) OnResumeWork.Broadcast();
}

void UArtisanDefenseComponent::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(Dt, Type, TickFunction);
    if (GetOwner()->HasAuthority()) StepGuard(Dt, GetWorld()->GetTimeSeconds());
    if (GetNetMode() != NM_DedicatedServer && !IsAtWork() && State != EArtisanGuardState::Downed) UpdateGrip();
}

bool UArtisanDefenseComponent::CanSee(AActor* Other) const
{
    if (!Other) return false;
    const FVector Eye = GetOwner()->GetActorLocation() + FVector(0, 0, 48);
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(ArtisanSight), false, GetOwner());
    return !RangedAttackQuery::LineTraceSingle(GetWorld(), GetOwner(), Hit, Eye, ArtisanPatrol::AimPoint(*Other), ECC_Visibility, Query)
        || Hit.GetActor() == Other;
}

bool UArtisanDefenseComponent::AcquireNearbyThreat(double Now)
{
    NextScan = Now + ArtisanPatrol::ScanInterval;
    const bool bBow = IsBow();
    const float Radius = bBow ? ArtisanPatrol::CarpenterAlert : ArtisanPatrol::SmithAlert;
    const float Leash = bBow ? ArtisanPatrol::CarpenterLeash : ArtisanPatrol::SmithLeash;
    const FVector Here = GetOwner()->GetActorLocation();
    if (FVector::DistSquared2D(Station, Here) > FMath::Square(Leash)) return false;
    for (auto It = UnreachableThreats.CreateIterator(); It; ++It)
    {
        const AActor* Blocked = It.Key().Get();
        if (!Blocked || (Now >= It.Value().RetryAfter && (IsAtWork() ||
            FVector::DistSquared(Blocked->GetActorLocation(), It.Value().Location) >= FMath::Square(150.f))))
            It.RemoveCurrent();
    }
    TArray<FOverlapResult> Nearby;
    FCollisionObjectQueryParams Types(ECC_Pawn);
    GetWorld()->OverlapMultiByObjectType(Nearby, Here, FQuat::Identity, Types, FCollisionShape::MakeSphere(Radius),
        FCollisionQueryParams(SCENE_QUERY_STAT(ArtisanWatch), false, GetOwner()));
    AActor* Best = nullptr;
    double BestDistance = Radius * Radius;
    TSet<const AActor*> Considered;
    for (const FOverlapResult& Overlap : Nearby)
    {
        AActor* Other = Overlap.GetActor();
        if (!Other || Considered.Contains(Other)) continue;
        Considered.Add(Other);
        const FVector Location = Other->GetActorLocation();
        const double Distance = FVector::DistSquared(Location, Here);
        if (Distance > BestDistance || FVector::DistSquared2D(Station, Location) > FMath::Square(Leash) ||
            !UFPSMeleeLightningComponent::IsEnemy(Other, GetOwner())) continue;
        // A failed chase must not repeatedly cancel the walk home. Re-engage a
        // stationary blocked target if it can now be attacked from this spot.
        if (const FUnreachableThreat* Blocked = UnreachableThreats.Find(Other))
        {
            if (Now < Blocked->RetryAfter || !ArtisanPatrol::InWeaponReach(bBow, *GetOwner(), *Other) || !CanSee(Other)) continue;
        }
        else if (!ArtisanPatrol::InHearingRange(Here, Location) && !CanSee(Other)) continue;
        Best = Other;
        BestDistance = Distance;
    }
    if (!Best) return false;
    UnreachableThreats.Remove(Best);
    SetTarget(Best);
    return true;
}

void UArtisanDefenseComponent::SetTarget(AActor* NewTarget)
{
    Threat = NewTarget;
    LastSeen = NewTarget->GetActorLocation();
    NextSight = 0;
    LastSeenAt = LastThreatProgress = ProgressAt = GetWorld()->GetTimeSeconds();
    BestThreatDistance = FVector::Dist2D(LastSeen, GetOwner()->GetActorLocation());
    ProgressSample = GetOwner()->GetActorLocation();
    Detour = 0;
    ClearRoute();
    ChangeState(EArtisanGuardState::Ready);
}

void UArtisanDefenseComponent::StartWatching(double Now)
{
    if (AcquireNearbyThreat(Now)) return;
    Threat.Reset();
    ClearRoute();
    ChangeState(EArtisanGuardState::Watching);
}

void UArtisanDefenseComponent::StartReturning(double Now)
{
    Threat.Reset();
    bWaitingBesideStation = false;
    ClearRoute();
    ProgressSample = GetOwner()->GetActorLocation();
    BestReturnDistance = FVector::Dist(ProgressSample, Station);
    LastReturnProgress = ProgressAt = Now;
    Detour = 0;
    ChangeState(EArtisanGuardState::Returning);
}

void UArtisanDefenseComponent::StepGuard(float Dt, double Now)
{
    if (State == EArtisanGuardState::Downed) return;
    if (IsAtWork() || State == EArtisanGuardState::Watching || State == EArtisanGuardState::Returning)
    {
        const bool bWatchExpired = State == EArtisanGuardState::Watching && Now >= StateStartedAt + ArtisanPatrol::WatchDuration;
        const bool bScan = bWatchExpired || Now >= NextScan;
        if (bScan && AcquireNearbyThreat(Now)) return;
        if (State == EArtisanGuardState::Returning) RestoreStation(Now, Dt);
        else if (bWatchExpired || (bScan && IsAtWork() && bWaitingBesideStation && CanStandAt(Station))) StartReturning(Now);
        return;
    }
    AActor* Other = Threat.Get();
    const FVector Here = GetOwner()->GetActorLocation();
    const bool bBow = IsBow();
    if (!bBow && State == EArtisanGuardState::Attack)
    {
        StepHammerSwing(Other, Dt, Now);
        return;
    }
    const float Leash = bBow ? ArtisanPatrol::CarpenterLeash : ArtisanPatrol::SmithLeash;
    if (!UFPSMeleeLightningComponent::IsEnemy(Other, GetOwner()) ||
        FVector::Dist2D(Station, Other->GetActorLocation()) > Leash || FVector::Dist2D(Station, Here) > Leash)
    {
        StartWatching(Now);
        return;
    }
    if (Now >= NextSight)
    {
        NextSight = Now + .16;
        bLastVisible = CanSee(Other);
    }
    const bool bSees = bLastVisible;
    if (bSees || ArtisanPatrol::InHearingRange(Here, Other->GetActorLocation()))
    {
        LastSeen = Other->GetActorLocation();
        LastSeenAt = Now;
    }
    const double Distance = FVector::Dist2D(Here, LastSeen);
    const bool bInReach = ArtisanPatrol::InWeaponReach(bBow, *GetOwner(), *Other);
    if (Distance < BestThreatDistance - 45. || (bSees && bInReach))
    {
        LastThreatProgress = Now;
        BestThreatDistance = Distance;
    }
    if (Now - LastSeenAt > 3.5 || Now - LastThreatProgress > 10.)
    {
        UnreachableThreats.Add(Other, FUnreachableThreat{Other->GetActorLocation(), Now + 5.});
        StartWatching(Now);
        return;
    }
    if (State == EArtisanGuardState::Attack || State == EArtisanGuardState::Release)
    {
        const double Age = Now - AttackStarted;
        TurnToward(LastSeen - Here, Dt);
        if (!bStruck && Age >= ArtisanPatrol::BowDraw)
        {
            bStruck = true;
            if (bSees && bInReach) ShootArrow(Other);
            ChangeState(EArtisanGuardState::Release);
        }
        if (Age >= ArtisanPatrol::BowDraw + ArtisanPatrol::BowRelease)
            ChangeState(EArtisanGuardState::Ready);
        return;
    }
    const bool bClosing = !bBow && State == EArtisanGuardState::Approach && Now - ProgressAt < .75;
    if (bInReach && bSees && (!bClosing || ArtisanPatrol::InWeaponReach(false, *GetOwner(), *Other, ArtisanPatrol::SmithReachInset)))
    {
        ClearRoute();
        const float Scale = FMath::Abs(GetOwner()->GetActorScale3D().X);
        const bool bUseClose = !bBow && Distance - ArtisanPatrol::Radius(*Other) <= (bCloseHammer ? 82.f : 76.f) * Scale;
        const FVector Stance = (LastSeen - Here).RotateAngleAxis(bUseClose ? SmithHammerTiming::CloseStanceYaw : 0.f, FVector::UpVector);
        TurnToward(Stance, Dt);
        ChangeState(EArtisanGuardState::Ready);
        const double Facing = FVector::DotProduct(GetOwner()->GetActorForwardVector(), Stance.GetSafeNormal2D());
        const bool bFeetSet = bBow || GetOwner()->GetVelocity().SizeSquared2D() < FMath::Square(26.f);
        if (bFeetSet && Now >= NextAttack && (Facing >= (bBow ? .9 : .992) || Distance < 10.))
        {
            AttackStarted = Now;
            if (!bBow)
            {
                bCloseHammer = bUseClose;
                HammerPitch = ArtisanPatrol::AimHammerPitch(*GetOwner(), *Other, bUseClose);
                HammerTraceTime = SmithHammerTiming::FirstHeadTime;
            }
            NextAttack = Now + (bBow ? 2.45 : SmithHammerTiming::AttackInterval);
            bPlayedHammerSwing = false;
            bStruck = false;
            ChangeState(EArtisanGuardState::Attack);
        }
        return;
    }
    ChangeState(EArtisanGuardState::Approach);
    const FVector Away = (Here - LastSeen).GetSafeNormal2D();
    const float Angle = Detour == 0 ? 0.f : (Detour % 2 ? 1.f : -1.f) * (40.f + (Detour % 3) * 25.f);
    const float Offset = bBow ? (bSees ? 1250.f : 190.f) :
        ArtisanPatrol::Radius(*Other) + (ArtisanPatrol::HammerReach - ArtisanPatrol::SmithReachInset) * FMath::Abs(GetOwner()->GetActorScale3D().X) - 18.f;
    const FVector Goal = LastSeen - ArtisanPatrol::GroundOffset(*Other) + ArtisanPatrol::GroundOffset(*GetOwner()) +
        Away.RotateAngleAxis(Angle, FVector::UpVector) * Offset;
    MoveToward(Goal, Dt, Now);
}

void UArtisanDefenseComponent::TurnToward(const FVector& Direction, float Dt)
{
    if (Direction.SizeSquared2D() < UE_SMALL_NUMBER) return;
    const float Current = GetOwner()->GetActorRotation().Yaw;
    const float Target = Direction.Rotation().Yaw;
    float Speed = 360.f;
    if (!IsBow())
    {
        const float Limit = State == EArtisanGuardState::Attack ? 115.f : State == EArtisanGuardState::Returning ? 205.f : 260.f;
        Speed = FMath::Clamp(FMath::Abs(FMath::FindDeltaAngleDegrees(Current, Target)) * 7.f, 20.f, Limit);
    }
    const float Next = FMath::FixedTurn(Current, Target, Speed * Dt);
    GetOwner()->SetActorRotation(FRotator(0.f, Next, 0.f));
}

void UArtisanDefenseComponent::StepHammerSwing(AActor* Target, float Dt, double Now)
{
    const double Age = Now - AttackStarted;
    const FVector Here = GetOwner()->GetActorLocation();
    const bool bTrackTarget = UFPSMeleeLightningComponent::IsEnemy(Target, GetOwner())
        && FVector::DistSquared2D(Station, Target->GetActorLocation()) <= FMath::Square(ArtisanPatrol::SmithLeash)
        && FVector::DistSquared2D(Station, Here) <= FMath::Square(ArtisanPatrol::SmithLeash);
    if (bTrackTarget && Age < SmithHammerTiming::Swing)
        TurnToward((Target->GetActorLocation() - Here).RotateAngleAxis(
            bCloseHammer ? SmithHammerTiming::CloseStanceYaw : 0.f, FVector::UpVector), Dt);
    if (!bPlayedHammerSwing && Age >= SmithHammerTiming::Swing)
    {
        bPlayedHammerSwing = true;
        if (Age < SmithHammerTiming::Contact)
            MulticastHammerSound(false, Here + GetOwner()->GetActorForwardVector() * 50.f);
    }
    if (!bStruck && HammerTraceTime < SmithHammerTiming::LastHeadTime)
    {
        const float Time = FMath::Min(SmithHammerTiming::LastHeadTime, SmithHammerTiming::SampleClip(
            float(Age), SmithHammerTiming::AuthoredContact, SmithHammerTiming::ClipLengthSeconds(bCloseHammer)));
        if (Time > HammerTraceTime)
        {
            bStruck = SweepHammer(HammerTraceTime, Time);
            HammerTraceTime = Time;
        }
    }
    // A killing blow or a missed target still carries the head past contact.
    // Re-enter the existing search/watch path only when the swing is over.
    if (Age >= SmithHammerTiming::End)
    {
        if (bTrackTarget && UFPSMeleeLightningComponent::IsEnemy(Target, GetOwner()))
            ChangeState(EArtisanGuardState::Ready);
        else
            StartWatching(Now);
    }
}

void UArtisanDefenseComponent::MulticastHammerSound_Implementation(bool bImpact, FVector_NetQuantize Location)
{
    if (GetNetMode() == NM_DedicatedServer || !HammerAttenuation) return;
    const FSoftObjectPath& Path = bImpact ? ArtisanPatrol::HammerImpactSound : ArtisanPatrol::HammerSwingSound;
    if (auto* Sound = Cast<USoundBase>(Path.ResolveObject()))
        UGameplayStatics::PlaySoundAtLocation(this, Sound, Location, bImpact ? .8f : .65f, 1.f, 0.f, HammerAttenuation);
}

void UArtisanDefenseComponent::ShootArrow(AActor* Other)
{
    const FVector Eye = GetOwner()->GetActorLocation() + FVector(0, 0, 40);
    const FVector Aim = ArtisanPatrol::AimPoint(*Other);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ArtisanContact), false, GetOwner());
    FHitResult Hit;
    APawn* Pawn = Cast<APawn>(GetOwner());
    const FVector Start = Eye + GetOwner()->GetActorForwardVector() * 34.f;
    if (RangedAttackQuery::LineTraceSingle(GetWorld(), GetOwner(), Hit, Eye, Start, ECC_Visibility, Query) && Hit.GetActor() != Other) return;
    const float Travel = FVector::Dist(Start, Aim) / 9800.f;
    const FVector Direction = (Aim + Other->GetVelocity() * Travel + FVector(0, 0, 260.f * Travel * Travel) - Start).GetSafeNormal();
    FActorSpawnParameters Spawn;
    Spawn.Owner = GetOwner();
    Spawn.Instigator = Pawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (auto* Arrow = GetWorld()->SpawnActor<AArtisanDefenseArrow>(Start, Direction.Rotation(), Spawn))
        Arrow->Launch(Direction, AttackDamage);
}

bool UArtisanDefenseComponent::SweepHammer(float FromTime, float ToTime)
{
    using namespace SmithHammerTiming;
    const AActor* Guard = GetOwner();
    FTransform Frame = Guard->GetActorTransform();
    Frame.AddToTranslation(-ArtisanPatrol::GroundOffset(*Guard));
    const FQuat Tilt(AimAxis(bCloseHammer), FMath::DegreesToRadians(HammerPitch));
    const auto Keys = HeadKeys(bCloseHammer);
    auto Head = [&](const FHeadKey& Key)
    {
        return Frame.TransformPosition(Key.Spine + Tilt.RotateVector(Key.Head - Key.Spine));
    };
    const FCollisionShape Shape = FCollisionShape::MakeSphere(HeadRadius * Frame.GetMaximumAxisScale());
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SmithHammerContact), false, Guard);
    for (int32 I = 0; I + 1 < Keys.Num(); ++I)
    {
        const float KeyStart = (10 + I) / 60.f, KeyEnd = (11 + I) / 60.f;
        if (KeyStart >= ToTime || KeyEnd <= FromTime) continue;
        const FVector A = Head(Keys[I]), B = Head(Keys[I + 1]);
        const FVector From = FMath::Lerp(A, B, FMath::Max(0.f, (FromTime - KeyStart) / (KeyEnd - KeyStart)));
        const FVector To = FMath::Lerp(A, B, FMath::Min(1.f, (ToTime - KeyStart) / (KeyEnd - KeyStart)));
        FHitResult Hit;
        if (!GetWorld()->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_Visibility, Shape, Query)) continue;
        if (UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(), GetOwner()))
        {
            // The head may already be on the far side of thin cover at the first sample.
            FHitResult Cover;
            const FVector Chest = Frame.TransformPosition(FVector(0, 0, 110));
            if (GetWorld()->LineTraceSingleByChannel(Cover, Chest, Hit.ImpactPoint, ECC_Visibility, Query)
                && Cover.GetActor() != Hit.GetActor()) return true;
            const MonsterToughness::FScopedForm Form(EMonsterAttackForm::Blunt);
            const auto* Pawn = Cast<APawn>(Guard);
            const float Damage = UGameplayStatics::ApplyPointDamage(Hit.GetActor(), AttackDamage, (B - A).GetSafeNormal(),
                Hit, Pawn ? Pawn->GetController() : nullptr, GetOwner(), UBluntToughnessDamage::StaticClass());
            if (Damage > 0.f) MulticastHammerSound(true, Hit.ImpactPoint);
        }
        return true;
    }
    return false;
}

void UArtisanDefenseComponent::ClearRoute()
{
    Route.Reset();
    RouteIndex = 0;
    NextPath = 0.;
}

bool UArtisanDefenseComponent::BuildRoute(const FVector& Goal)
{
    auto* Character = Cast<ACharacter>(GetOwner());
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if (!Character || !Nav) return false;
    const FVector Feet = Character->GetNavAgentLocation();
    const auto& Agent = Character->GetNavAgentPropertiesRef();
    const auto* Data = Nav->GetNavDataForProps(Agent, Feet);
    if (!Data) return false;
    const FVector GoalFeet = Goal - ArtisanPatrol::GroundOffset(*Character);
    FNavLocation Start, End;
    if (!Nav->ProjectPointToNavigation(Feet, Start, FVector(70,70,90), Data) ||
        !Nav->ProjectPointToNavigation(GoalFeet, End, FVector(90,90,100), Data)) return false;
    FPathFindingQuery Query(Character, *Data, Start.Location, End.Location, Data->GetDefaultQueryFilter());
    Query.SetAllowPartialPaths(false);
    const FPathFindingResult Result = Nav->FindPathSync(Agent, Query);
    if (!Result.IsSuccessful() || !Result.Path.IsValid() || Result.Path->IsPartial()) return false;
    Route.Reset();
    RouteIndex = 0;
    // Keep all corners. When squeezed by a pawn, alternate short steering offsets,
    // then return to the complete navmesh corridor on the next replan.
    for (const auto& Point : Result.Path->GetPathPoints()) Route.Add(Point.Location);
    return !Route.IsEmpty();
}

bool UArtisanDefenseComponent::MoveToward(const FVector& Goal, float Dt, double Now)
{
    auto* Character = Cast<ACharacter>(GetOwner());
    if (!Character) return false;
    const FVector Here = Character->GetActorLocation();
    const FVector Feet = Character->GetNavAgentLocation();
    const bool bBow = IsBow();
    if (FVector::DistSquared2D(Here, ProgressSample) > FMath::Square(38.f))
    {
        ProgressSample = Here;
        ProgressAt = Now;
    }
    if (Now - ProgressAt > 1.1)
    {
        ++Detour;
        ProgressAt = Now;
        ClearRoute();
    }
    if (Now >= NextPath && (RouteIndex >= Route.Num() || FVector::DistSquared2D(Goal, PreviousGoal) > FMath::Square(85.f)))
    {
        PreviousGoal = Goal;
        NextPath = Now + .55;
        Route.Reset();
        RouteIndex = 0;
        BuildRoute(Goal);
    }
    const double CornerRadius = bBow ? 40. : 17.;
    while (Route.IsValidIndex(RouteIndex) && FVector::Dist2D(Route[RouteIndex], Feet) <
            (RouteIndex + 1 == Route.Num() ? 7. : CornerRadius) && FMath::Abs(Route[RouteIndex].Z - Feet.Z) < 85.)
        ++RouteIndex;
    FVector Next = Goal - ArtisanPatrol::GroundOffset(*Character);
    if (Route.IsValidIndex(RouteIndex)) Next = Route[RouteIndex];
    else
    {
        // The work marker may lie just outside the inset navmesh, or its tile
        // may still be generating. Allow a short, grounded, swept walk only.
        if (FVector::Dist2D(Goal, Here) > 285. || FMath::Abs(Next.Z - Feet.Z) > 55.) return false;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(ArtisanLastMetres), false, Character);
        FHitResult Floor;
        const FVector Step = Feet + (Next - Feet).GetClampedToMaxSize(55.);
        if (!GetWorld()->LineTraceSingleByChannel(Floor, Step + FVector(0,0,42), Step - FVector(0,0,56), ECC_Visibility, Q)
            || !Character->GetCharacterMovement()->IsWalkable(Floor)) return false;
    }
    FVector Direction = (Next - Feet).GetSafeNormal2D();
    if (bBow && Detour && Now - ProgressAt < .4 && FVector::Dist2D(Here, Goal) > 90.)
        Direction = Direction.RotateAngleAxis(Detour % 2 ? 45.f : -45.f, FVector::UpVector);
    if (Direction.IsNearlyZero()) return false;
    auto* Move = Character->GetCharacterMovement();
    const bool bReturning = State == EArtisanGuardState::Returning;
    const float Remaining = FVector::Dist2D(Here, Goal);
    if (!bBow)
    {
        if (Now >= NextSmithProbe || FVector::DotProduct(Direction, SmithProbeHeading) < .94)
        {
            const float LookAhead = FMath::Min(float(FVector::Dist2D(Feet, Next)), 36.f + float(Move->Velocity.Size2D()) * .18f);
            SmithClearDirection = ArtisanPatrol::SmithClearHeading(*Character, Direction, LookAhead, SmithClearDirection);
            SmithProbeHeading = Direction;
            NextSmithProbe = Now + .12;
        }
        if (SmithClearDirection.IsNearlyZero()) return false;
        Direction = SmithClearDirection;
        TurnToward(Direction, Dt);
        const float Alignment = FMath::Clamp(float(FVector::DotProduct(Character->GetActorForwardVector(), Direction)), 0.f, 1.f);
        if (Alignment < .25f) return false;
        Move->MaxAcceleration = 720.f;
        Move->BrakingDecelerationWalking = 700.f;
        Move->MaxWalkSpeed = FMath::Clamp((Remaining - 5.f) * 2.3f, 30.f, bReturning ? 185.f : 270.f) * Alignment;
        if (Route.IsValidIndex(RouteIndex + 1) && FVector::DistSquared2D(Feet, Next) < FMath::Square(75.f))
        {
            const FVector Outgoing = (Route[RouteIndex + 1] - Next).GetSafeNormal2D();
            const float CornerSpeed = FMath::Lerp(95.f, Move->MaxWalkSpeed,
                FMath::Clamp(float(FVector::DotProduct(Direction, Outgoing)), 0.f, 1.f));
            Move->MaxWalkSpeed = FMath::Min(Move->MaxWalkSpeed, CornerSpeed);
        }
    }
    else
    {
        TurnToward(Direction, Dt);
        Move->MaxWalkSpeed = bReturning ? FMath::Clamp(Remaining * 2.f, 35.f, 220.f) : 280.f;
    }
    Character->AddMovementInput(Direction, 1.f, true);
    return true;
}

bool UArtisanDefenseComponent::CanStandAt(const FVector& Center) const
{
    const auto* Character = CastChecked<ACharacter>(GetOwner());
    const auto* Capsule = Character->GetCapsuleComponent();
    const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight() - 2.f);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(ArtisanStandClear), false, Character);
    return !GetWorld()->OverlapBlockingTestByChannel(Center + FVector(0,0,2), FQuat::Identity, Capsule->GetCollisionObjectType(),
        Shape, Query, FCollisionResponseParams(Capsule->GetCollisionResponseToChannels()));
}

void UArtisanDefenseComponent::RestoreStation(double Now, float Dt)
{
    auto* Character = Cast<ACharacter>(GetOwner());
    if (!Character) return;
    const FVector Here = Character->GetActorLocation();
    const double Distance = FVector::Dist(Here, Station);
    const bool bArrived = FVector::Dist2D(Here, Station) <= 8. && FMath::Abs(Here.Z - Station.Z) <= 12.;
    if (Distance + 22. < BestReturnDistance)
    {
        BestReturnDistance = Distance;
        LastReturnProgress = Now;
    }
    if (bArrived || Now - LastReturnProgress >= 12.)
    {
        // An indefinitely blocked corridor can recover to the actual recorded
        // work spot. An occupied stand waits until its capsule is free.
        bool bSettled = false;
        const bool bStandFree = CanStandAt(Station);
        const bool bCanWaitBeside = !bStandFree && Distance < 140. && Character->GetCharacterMovement()->IsMovingOnGround();
        if (!IsBow() && (bArrived || bCanWaitBeside))
        {
            Character->ConsumeMovementInputVector();
            TurnToward(StationRotation.Vector(), Dt);
            if (Character->GetVelocity().SizeSquared2D() > FMath::Square(15.f) ||
                FMath::Abs(FMath::FindDeltaAngleDegrees(float(Character->GetActorRotation().Yaw), float(StationRotation.Yaw))) > 3.f) return;
        }
        if (bStandFree) bSettled = Character->TeleportTo(Station, StationRotation, false, true);
        else if (bCanWaitBeside)
        {
            Character->SetActorRotation(StationRotation);
            bWaitingBesideStation = bSettled = true;
        }
        if (bSettled)
        {
            ClearRoute();
            ChangeState(EArtisanGuardState::AtWork);
            NextScan = Now + .65;
            return;
        }
        if (!bArrived) LastReturnProgress = Now - 10.;
    }
    MoveToward(Station, Dt, Now);
}
