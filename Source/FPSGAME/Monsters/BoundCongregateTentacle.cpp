#include "BoundCongregate.h"
#include "BoundCongregateCaptureComponent.h"
#include "BoundCongregateTentacleTiming.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace BoundTentacle
{
bool Available(ACharacter* Victim)
{
    if(!IsValid(Victim)||Victim->IsActorBeingDestroyed())return false;
    const auto* H=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* S=Victim->FindComponentByClass<UCombatStatusFormula>();
    return !(H&&(H->IsDead()||H->IsInvulnerable()))&&!(S&&S->IsImmune());
}
float Radius(const ACharacter* Victim){return FMath::Clamp(Victim->GetCapsuleComponent()->GetScaledCapsuleRadius()+6.f,32.f,66.f);}
}
bool ABoundCongregate::CanTentacle(APawn* Pawn) const
{
    auto* Victim=Cast<ACharacter>(Pawn);
    if(!BoundTentacle::Available(Victim)||Busy()||Clock()<NextTentacle||UBoundCongregateCaptureComponent::IsCaptured(Victim))return false;
    if(!GetMesh()->DoesSocketExist(TEXT("attack_tentacle_00"))||!GetMesh()->DoesSocketExist(TEXT("attack_tentacle_56")))return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    // V29 extends only the isolated distal flesh; the shared collar stays fixed.
    if(Victim->GetCapsuleComponent()->GetScaledCapsuleRadius()>60.f)return false;
    // Keep the whip eligible at close range as well. Tying its minimum range
    // to the bite left only a narrow ring in which it could ever be selected.
    return Delta.Size()<=TentacleRange&&FMath::Abs(Delta.Z)<180.f&&
        FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,Delta.Rotation().Yaw))<=60.f&&HasSight(Victim);
}
float ABoundCongregate::TentacleReleaseDuration() const
{
    // Keep the accepted close-range snap. A full 30 m release gets a readable
    // 180 ms burst, still much faster than the 620 ms muscular preparation.
    const float Distance=FVector::Distance(NetState.TentacleAim,GetActorLocation());
    return TentacleStrikeSeconds+.09f*FMath::SmoothStep(400.f,3000.f,Distance);
}
bool ABoundCongregate::BeginTentacle(APawn* Pawn)
{
    auto* Victim=Cast<ACharacter>(Pawn);if(!HasAuthority()||!CanTentacle(Victim))return false;
    Target=Victim;AttackYaw=GetActorRotation().Yaw;NextTentacle=Clock()+TentacleCooldown;
    NetState.TentacleAim=Victim->GetActorLocation();NetState.TentacleRadius=BoundTentacle::Radius(Victim);
    NetState.CapturedTarget=nullptr;NetState.ReleasedWrap=0.f;NetState.TentacleRecoveryStartedAt=-1.;TentacleBlockedSeconds=0.f;
    TentacleHealth=TentacleMaxHealth;
    PreviousTentacleTip=GetMesh()->GetSocketLocation(TEXT("attack_tentacle_56"));
    SetState(EBoundCongregateState::TentacleWindup);
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
bool ABoundCongregate::IsDragging(const ACharacter* Victim) const
{return NetState.State==EBoundCongregateState::TentacleDrag&&NetState.CapturedTarget==Victim;}
FVector ABoundCongregate::CapturePullVelocity(const ACharacter* Victim) const
{
    if(!Victim||!IsDragging(Victim))return FVector::ZeroVector;
    const FVector Toward=GetActorLocation()-Victim->GetActorLocation();
    const float Stop=GetCapsuleComponent()->GetScaledCapsuleRadius()+Victim->GetCapsuleComponent()->GetScaledCapsuleRadius()+12.f;
    const float Remaining=FMath::Max(0.f,float(Toward.Size2D())-Stop);
    const float Ramp=FMath::SmoothStep(0.f,.4f,float(StateElapsed()));
    return Toward.GetSafeNormal2D()*FMath::Min(TentaclePullSpeed*Ramp,Remaining*4.f);
}
void ABoundCongregate::TentacleHit(ACharacter* Victim,const FHitResult& Hit)
{
    if(!BoundTentacle::Available(Victim)||!HasSight(Victim))return;
    auto* Capture=UBoundCongregateCaptureComponent::GetOrAdd(Victim);
    if(!Capture||!Capture->Capture(this))return;
    NetState.CapturedTarget=Victim;NetState.TentacleAim=Victim->GetActorLocation();
    NetState.TentacleRadius=BoundTentacle::Radius(Victim);LastCapturedPosition=Victim->GetActorLocation();
    NextSqueeze=Clock()+TentacleWrapSeconds+TentacleDamageInterval;
    SetState(EBoundCongregateState::TentacleWrap);
    UGameplayStatics::ApplyPointDamage(Victim,TentacleImpactDamage,GetActorForwardVector(),Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
}
void ABoundCongregate::TickTentacle(float Dt)
{
    if(NetState.CapturedTarget)
        AttackYaw=FMath::FixedTurn(AttackYaw,(NetState.CapturedTarget->GetActorLocation()-GetActorLocation()).Rotation().Yaw,
            GetCharacterMovement()->RotationRate.Yaw*Dt);
    SetActorRotation(FRotator(0,AttackYaw,0));
    const float T=float(StateElapsed());
    if(NetState.State==EBoundCongregateState::TentacleWindup)
    {
        if(!BoundTentacle::Available(Cast<ACharacter>(Target.Get()))||!HasSight(Target.Get())){EndTentacle(true);return;}
        if(T>=TentacleWindupSeconds)
        {
            // Commit the aim once. The release can be sidestepped or dodged.
            NetState.TentacleAim=GetActorLocation()+(Target->GetActorLocation()-GetActorLocation()).GetClampedToMaxSize(TentacleRange);
            bTentacleFinalPoseRequested=false;
            PreviousTentacleTip=GetMesh()->GetSocketLocation(TEXT("attack_tentacle_56"));SetState(EBoundCongregateState::TentacleStrike);
        }
    }
    else if(NetState.State==EBoundCongregateState::TentacleStrike)
    {
        const FVector Tip=GetMesh()->GetSocketLocation(TEXT("attack_tentacle_56"));
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CongregateTentacle),false,this);FHitResult Hit;
        const auto Shape=FCollisionShape::MakeSphere(BoundCongregateTentacleTiming::ContactRadius);
        bool bContact=GetWorld()->SweepSingleByChannel(Hit,PreviousTentacleTip,Tip,FQuat::Identity,ECC_Pawn,Shape,Query);
        // Include the visible terminal shaft as well as the moving tip. The
        // faster throw keeps its continuous temporal sweep and cover blocking.
        for(int32 I=48;I<56&&!bContact;++I)
            bContact=GetWorld()->SweepSingleByChannel(Hit,
                GetMesh()->GetSocketLocation(FName(FString::Printf(TEXT("attack_tentacle_%02d"),I))),
                GetMesh()->GetSocketLocation(FName(FString::Printf(TEXT("attack_tentacle_%02d"),I+1))),
                FQuat::Identity,ECC_Pawn,Shape,Query);
        if(bContact)
        {
            if(auto* Victim=Cast<ACharacter>(Hit.GetActor());Victim&&Victim==Target.Get()&&
                FVector::DistSquared(Victim->GetActorLocation(),GetActorLocation())<=FMath::Square(TentacleRange))TentacleHit(Victim,Hit);
            if(NetState.State==EBoundCongregateState::TentacleStrike){EndTentacle(true);return;}
        }
        PreviousTentacleTip=Tip;
        // Mesh evaluation follows this actor. Request the terminal pose once,
        // sweep it on the next tick, then cut to recovery without a fixed hold.
        if(NetState.State==EBoundCongregateState::TentacleStrike&&T>=TentacleReleaseDuration())
        {
            if(bTentacleFinalPoseRequested)EndTentacle(true);
            else bTentacleFinalPoseRequested=true;
        }
    }
    else if(NetState.State==EBoundCongregateState::TentacleWrap||NetState.State==EBoundCongregateState::TentacleDrag)
    {
        auto* Victim=NetState.CapturedTarget.Get();
        const auto* Capture=Victim?Victim->FindComponentByClass<UBoundCongregateCaptureComponent>():nullptr;
        const auto* VictimHealth=Victim?Victim->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(!IsValid(Victim)||Victim->IsActorBeingDestroyed()||(VictimHealth&&VictimHealth->IsDead())||!Capture||!Capture->IsHeldBy(this))
        {EndTentacle(true);return;}
        const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
        // Capture is persistent: cover, elapsed time and blocked swept motion
        // pause the pull rather than granting an automatic escape.
        if(Delta.Size2D()<=BiteTriggerRange&&FMath::Abs(Delta.Z)<180.f&&HasSight(Victim)&&BiteClip)
        {BeginCapturedBite(Victim);return;}
        if(NetState.State==EBoundCongregateState::TentacleWrap)
        {if(T>=TentacleWrapSeconds)SetState(EBoundCongregateState::TentacleDrag);return;}
        if(Clock()>=NextSqueeze)
        {
            NextSqueeze=Clock()+FMath::Max(.1f,TentacleDamageInterval);
            // Physical continuous damage, distinct from the initial blockable hit.
            UGameplayStatics::ApplyDamage(Victim,TentacleTickDamage,GetController(),this,UDamageType::StaticClass());
        }
    }
    else if(NetState.State==EBoundCongregateState::TentacleRecover&&TentacleRecoveryElapsed()>=TentacleRecoverSeconds)
    {NetState.ReleasedWrap=0.f;SetState(EBoundCongregateState::Idle);}
}
void ABoundCongregate::BeginCapturedBite(ACharacter* Victim)
{
    // The combo bypasses the ordinary attack chooser/cooldown. Release the
    // player's restraint now; the bite still has its normal visible windup.
    EndTentacle(false);
    NetState.ReleasedWrap=FMath::Max(.001f,NetState.ReleasedWrap);
    Target=Victim;AttackYaw=(Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw;
    bContactConsumed=false;NextBite=Clock()+BiteCooldown;AttackChoice=1;
    SetState(EBoundCongregateState::Bite);
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
}
void ABoundCongregate::EndTentacle(bool bRecover)
{
    if(!HasAuthority())return;
    const bool WasTentacle=TentacleActive();
    const float Elapsed=float(StateElapsed());
    NetState.ReleasedWeight=NetState.State==EBoundCongregateState::TentacleWindup?FMath::SmoothStep(0.f,TentacleWindupSeconds,Elapsed):1.f;
    NetState.ReleasedStrike=NetState.State==EBoundCongregateState::TentacleWindup?0.f:
        NetState.State==EBoundCongregateState::TentacleStrike?BoundCongregateTentacleTiming::Release(Elapsed,TentacleReleaseDuration()).Phase:1.f;
    NetState.ReleasedWrap=NetState.State==EBoundCongregateState::TentacleWrap?FMath::SmoothStep(0.f,TentacleWrapSeconds,Elapsed):
        NetState.CapturedTarget?1.f:0.f;
    if(auto* Victim=NetState.CapturedTarget.Get())
    {
        NetState.TentacleAim=Victim->GetActorLocation();
        if(auto* Capture=Victim->FindComponentByClass<UBoundCongregateCaptureComponent>())Capture->Release(this);
    }
    NetState.CapturedTarget=nullptr;
    if(WasTentacle)
    {
        // Recovery keeps its own replicated clock when a hit reaction or bite
        // owns the body state. Escaping during a stagger must not snap the coil.
        NetState.TentacleRecoveryStartedAt=Clock();
        NextAttack=FMath::Max(NextAttack,Clock()+TentacleRecoverSeconds+.25f);
        if(bRecover)SetState(EBoundCongregateState::TentacleRecover);
    }
}
void ABoundCongregate::CancelTentacle()
{
    if(!HasAuthority()||!TentacleActive()||TentacleRecovering())return;
    const bool KeepReaction=Controlled();
    EndTentacle(!KeepReaction);
    if(KeepReaction){UpdateTentacleHitShapeState();ForceNetUpdate();}
}
void ABoundCongregate::EndPlay(const EEndPlayReason::Type Reason)
{
    EndTentacle(false);
    if(TentaclePoseHandle.IsValid())GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(TentaclePoseHandle);
    TentaclePoseHandle.Reset();
    Super::EndPlay(Reason);
}
