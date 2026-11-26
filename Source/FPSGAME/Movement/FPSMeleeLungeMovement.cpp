#include "FPSCharacterMovementComponent.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Engine/ScopedMovementUpdate.h"
#include "GameFramework/Character.h"
#include "GameFramework/Controller.h"

bool UFPSCharacterMovementComponent::BeginMeleeDashMomentum(const FVector& IncomingVelocity,uint32 HammerAttackId)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(CharacterOwner))return false;
    if(!CharacterOwner || !UpdatedComponent || (!CharacterOwner->HasAuthority()&&!CharacterOwner->IsLocallyControlled()) ||
        (!IsMovingOnGround() && !IsFalling()) || IncomingVelocity.ContainsNaN() ||
        IncomingVelocity.SizeSquared2D()<=1.f)return false;
    Velocity.X=IncomingVelocity.X;
    Velocity.Y=IncomingVelocity.Y;
    bMeleeDashMomentum=true;
    if(CharacterOwner->GetLocalRole()==ROLE_AutonomousProxy&&!CharacterOwner->bClientUpdating)
    {
        BeginMeleeLungeRequest(EFPSMeleeMove::AirMomentum,IncomingVelocity.GetSafeNormal2D(),HammerAttackId);
        MeleeRequest.Momentum=FVector(IncomingVelocity.X,IncomingVelocity.Y,0.f);bPendingMeleeMomentum=true;
    }
    UpdateComponentVelocity();
    return true;
}

void UFPSCharacterMovementComponent::CalcVelocity(float DeltaTime,float Friction,bool bFluid,float BrakingDeceleration)
{
    if(IsBipodMovementLocked()&&IsMovingOnGround())
    {bMeleeDashMomentum=false;Velocity=FVector::ZeroVector;Acceleration=FVector::ZeroVector;return;}
    if(bMeleeDashMomentum)
    {
        const auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);
        const auto* Status=CharacterOwner?CharacterOwner->FindComponentByClass<UCombatStatusFormula>():nullptr;
        const bool bInputResumed=Player && !Player->IsMeleeSkillMovementLocked() && !Acceleration.IsNearlyZero();
        if(!Player || IsDodging() || (!IsMovingOnGround() && !IsFalling()) ||
            (Player->Controller && AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Player->Controller))) ||
            (Status && Status->BlocksMovement()) || bInputResumed)
        {
            bMeleeDashMomentum=false;
        }
        else
        {
            if(!HasValidData() || HasAnimRootMotion() || DeltaTime<MIN_TICK_TIME)return;
            // Brake the real, collision-constrained velocity. Never restore a
            // cached speed after hitting a wall, or add the fixed one-metre step.
            // Native walking/falling still owns capsule sweeps and gravity.
            constexpr float AirDeceleration=300.f;
            constexpr float GroundDeceleration=1800.f;
            const double VerticalSpeed=Velocity.Z;
            Velocity.Z=0.;
            ApplyVelocityBraking(DeltaTime,0.f,IsFalling()?AirDeceleration:GroundDeceleration);
            Velocity.Z=VerticalSpeed;
            if(Velocity.SizeSquared2D()<=1.f)bMeleeDashMomentum=false;
            return;
        }
    }
    Super::CalcVelocity(DeltaTime,Friction,bFluid,BrakingDeceleration);
}

void UFPSCharacterMovementComponent::StopMovementImmediately()
{
    bMeleeDashMomentum=false;
    Super::StopMovementImmediately();
}

FVector UFPSCharacterMovementComponent::ApplyMeleeLungeStep(const FVector& Direction,float DistanceCM)
{
    if(!CharacterOwner || !UpdatedComponent || (!CharacterOwner->HasAuthority()&&!CharacterOwner->IsLocallyControlled()) ||
        !IsMovingOnGround() || IsDodging() || !CurrentFloor.IsWalkableFloor() || DistanceCM<=0.f)
        return FVector::ZeroVector;
    const auto* Controller=CharacterOwner->GetController();
    if(!Controller || AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Controller)))return FVector::ZeroVector;

    const FVector Start=UpdatedComponent->GetComponentLocation();
    const FVector Forward=Direction.GetSafeNormal2D();
    float Remaining=DistanceCM;
    // A metre-long stride can span a ledge during one slow frame. Check ground
    // support in short swept steps, retaining accepted movement up to the edge.
    while(Remaining>UE_SMALL_NUMBER)
    {
        const float StepDistance=FMath::Min(Remaining,5.f);
        const FVector StepStart=UpdatedComponent->GetComponentLocation();
        const FVector Delta=ComputeGroundMovementDelta(Forward*StepDistance,
            CurrentFloor.HitResult,CurrentFloor.bLineTrace);
        FFindFloorResult Floor;
        FindFloor(StepStart+Delta,Floor,false);
        if(!Floor.IsWalkableFloor() || Floor.GetDistanceToFloor()>MaxStepHeight+MAX_FLOOR_DIST)break;

        FScopedMovementUpdate Movement(UpdatedComponent,EScopedUpdate::DeferredUpdates);
        FHitResult Hit;
        SafeMoveUpdatedComponent(Delta,UpdatedComponent->GetComponentQuat(),true,Hit);
        FindFloor(UpdatedComponent->GetComponentLocation(),Floor,false);
        if(!Floor.IsWalkableFloor() || Floor.GetDistanceToFloor()>MaxStepHeight+MAX_FLOOR_DIST)
        {
            Movement.RevertMove();
            break;
        }
        CurrentFloor=Floor;bForceNextFloorCheck=true;
        Remaining-=StepDistance;
        const float Travel=FVector::DotProduct(UpdatedComponent->GetComponentLocation()-StepStart,Forward);
        if(Hit.bBlockingHit || Travel+.01f<StepDistance)break;
    }
    return UpdatedComponent->GetComponentLocation()-Start;
}

FVector UFPSCharacterMovementComponent::ApplyShadowStepDashStep(const FVector& Direction,float DistanceCM,bool bFinishDepenetrate)
{
    if(!CharacterOwner || !UpdatedComponent || (!CharacterOwner->HasAuthority()&&!CharacterOwner->IsLocallyControlled()) ||
        !IsMovingOnGround() || IsDodging() || !CurrentFloor.IsWalkableFloor())
        return FVector::ZeroVector;
    const auto* Controller=CharacterOwner->GetController();
    if(!Controller || AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Controller)))return FVector::ZeroVector;

    auto* Capsule=CharacterOwner->GetCapsuleComponent();
    const FVector Forward=Direction.GetSafeNormal2D();
    const FVector Start=UpdatedComponent->GetComponentLocation();
    TArray<AActor*,TInlineAllocator<16>> TempIgnored;
    if(Capsule && DistanceCM>0.f && !Forward.IsNearlyZero() && GetWorld())
    {
        const float HalfH=Capsule->GetScaledCapsuleHalfHeight();
        const float Rad=Capsule->GetScaledCapsuleRadius();
        const FVector Mid=Start+Forward*(DistanceCM*.5f);
        const FVector Extent(DistanceCM*.5f+Rad+80.f,DistanceCM*.5f+Rad+80.f,HalfH+80.f);
        TArray<FOverlapResult> Overlaps;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(ShadowStepPassThrough),false,CharacterOwner);
        if(GetWorld()->OverlapMultiByChannel(Overlaps,Mid,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeBox(Extent),Q))
        {
            for(const auto& O:Overlaps)
            {
                AActor* Other=O.GetActor();
                if(!IsValid(Other)||Other==CharacterOwner||!Cast<APawn>(Other))continue;
                FMonsterCoreStats Stats;
                // Stop cleanly before Lord/Boss capsules so the dash never clips into giant bosses.
                if(MonsterCoreStats::Get(Other,Stats)&&(Stats.Rank==EMonsterRank::Lord||Stats.Rank==EMonsterRank::Boss))continue;
                if(!Capsule->MoveIgnoreActors.Contains(Other))
                {
                    Capsule->IgnoreActorWhenMoving(Other,true);
                    TempIgnored.Add(Other);
                }
            }
        }
    }

    FVector Displaced=FVector::ZeroVector;
    if(DistanceCM>0.f && !Forward.IsNearlyZero())
    {
        Displaced=ApplyMeleeLungeStep(Forward,DistanceCM);
    }

    if(Capsule)
        for(AActor* Ignored:TempIgnored)
            if(IsValid(Ignored))Capsule->IgnoreActorWhenMoving(Ignored,false);

    // Safe post-dash depenetration: if the dash finishes overlapping any pawn capsule, nudge cleanly outside.
    if(bFinishDepenetrate && Capsule && GetWorld())
    {
        const float HalfH=Capsule->GetScaledCapsuleHalfHeight();
        const float Rad=Capsule->GetScaledCapsuleRadius();
        TArray<FOverlapResult> Overlaps;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(ShadowStepDepenetrate),false,CharacterOwner);
        if(GetWorld()->OverlapMultiByChannel(Overlaps,UpdatedComponent->GetComponentLocation(),FQuat::Identity,
            ECC_Pawn,FCollisionShape::MakeCapsule(Rad+4.f,HalfH),Q))
        {
            for(const auto& O:Overlaps)
            {
                const auto* OtherPawn=Cast<APawn>(O.GetActor());
                if(!IsValid(OtherPawn)||OtherPawn==CharacterOwner)continue;
                const FVector MyLoc=UpdatedComponent->GetComponentLocation();
                const FVector OtherLoc=OtherPawn->GetActorLocation();
                FVector Push=(MyLoc-OtherLoc).GetSafeNormal2D();
                if(Push.IsNearlyZero())Push=Forward.IsNearlyZero()?CharacterOwner->GetActorForwardVector().GetSafeNormal2D():Forward;
                float OtherRad=42.f;
                if(const auto* OtherCap=OtherPawn->FindComponentByClass<UCapsuleComponent>())OtherRad=OtherCap->GetScaledCapsuleRadius();
                const float Dist2D=FVector::Dist2D(MyLoc,OtherLoc);
                const float Need=FMath::Max(0.f,Rad+OtherRad+10.f-Dist2D);
                if(Need>1.f)
                {
                    const FVector Moved=ApplyMeleeLungeStep(Push,Need);
                    if(Moved.Size2D()<Need*.5f && !Forward.IsNearlyZero())ApplyMeleeLungeStep(-Forward,Need);
                }
            }
        }
    }
    return UpdatedComponent->GetComponentLocation()-Start;
}
