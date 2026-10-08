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
    // The isolated organ has its own measured chain and fixed proximal collar.
    // Reserve distal length for the coil instead of stretching shared skin.
    if(Victim->GetCapsuleComponent()->GetScaledCapsuleRadius()>60.f)return false;
    // Keep the whip eligible at close range as well. Tying its minimum range
    // to the bite left only a narrow ring in which it could ever be selected.
    return Delta.Size2D()<=TentacleRange&&FMath::Abs(Delta.Z)<180.f&&
        FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,Delta.Rotation().Yaw))<=60.f&&HasSight(Victim);
}
bool ABoundCongregate::BeginTentacle(APawn* Pawn)
{
    auto* Victim=Cast<ACharacter>(Pawn);if(!HasAuthority()||!CanTentacle(Victim))return false;
    Target=Victim;AttackYaw=GetActorRotation().Yaw;NextTentacle=Clock()+TentacleCooldown;
    NetState.TentacleAim=Victim->GetActorLocation();NetState.TentacleRadius=BoundTentacle::Radius(Victim);
    NetState.CapturedTarget=nullptr;NetState.ReleasedWrap=0.f;TentacleBlockedSeconds=0.f;
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
    SetActorRotation(FRotator(0,AttackYaw,0));
    const float T=float(StateElapsed());
    if(NetState.State==EBoundCongregateState::TentacleWindup)
    {
        if(!BoundTentacle::Available(Cast<ACharacter>(Target.Get()))||!HasSight(Target.Get())){EndTentacle(true);return;}
        if(T>=TentacleWindupSeconds)
        {
            // Commit the aim once. The release can be sidestepped or dodged.
            NetState.TentacleAim=Target->GetActorLocation();
            bTentacleFinalPoseRequested=false;
            PreviousTentacleTip=GetMesh()->GetSocketLocation(TEXT("attack_tentacle_56"));SetState(EBoundCongregateState::TentacleStrike);
        }
    }
    else if(NetState.State==EBoundCongregateState::TentacleStrike)
    {
        const FVector Tip=GetMesh()->GetSocketLocation(TEXT("attack_tentacle_56"));
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CongregateTentacle),false,this);FHitResult Hit;
        if(GetWorld()->SweepSingleByChannel(Hit,PreviousTentacleTip,Tip,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(16.f),Query))
        {
            if(auto* Victim=Cast<ACharacter>(Hit.GetActor());Victim&&Victim==Target.Get())TentacleHit(Victim,Hit);
            if(NetState.State==EBoundCongregateState::TentacleStrike){EndTentacle(true);return;}
        }
        PreviousTentacleTip=Tip;
        // Mesh evaluation follows this actor. Request the terminal pose once,
        // sweep it on the next tick, then cut to recovery without a fixed hold.
        if(NetState.State==EBoundCongregateState::TentacleStrike&&T>=TentacleStrikeSeconds)
        {
            if(bTentacleFinalPoseRequested)EndTentacle(true);
            else bTentacleFinalPoseRequested=true;
        }
    }
    else if(NetState.State==EBoundCongregateState::TentacleWrap||NetState.State==EBoundCongregateState::TentacleDrag)
    {
        auto* Victim=NetState.CapturedTarget.Get();
        const auto* Capture=Victim?Victim->FindComponentByClass<UBoundCongregateCaptureComponent>():nullptr;
        if(!BoundTentacle::Available(Victim)||!Capture||!Capture->IsHeldBy(this)||!HasSight(Victim)||
            FVector::DistSquared(Victim->GetActorLocation(),GetActorLocation())>FMath::Square(TentacleRange+100.f))
        {EndTentacle(true);return;}
        const FVector Tip=GetMesh()->GetSocketLocation(TEXT("attack_tentacle_56"));
        // Contact cannot persist while the visible organ is out of reach.
        if(T>.25f&&FVector::DistSquared(Tip,Victim->GetActorLocation())>FMath::Square(125.f)){EndTentacle(true);return;}
        if(NetState.State==EBoundCongregateState::TentacleWrap)
        {if(T>=TentacleWrapSeconds)SetState(EBoundCongregateState::TentacleDrag);return;}
        if(T>=TentacleHoldSeconds){EndTentacle(true);return;}
        const bool WantsPull=CapturePullVelocity(Victim).SizeSquared2D()>100.f;
        TentacleBlockedSeconds=WantsPull&&FVector::DistSquared2D(Victim->GetActorLocation(),LastCapturedPosition)<FMath::Square(Dt*5.f)?TentacleBlockedSeconds+Dt:0.f;
        LastCapturedPosition=Victim->GetActorLocation();
        if(TentacleBlockedSeconds>.55f){EndTentacle(true);return;}
        if(Clock()>=NextSqueeze)
        {
            NextSqueeze=Clock()+FMath::Max(.1f,TentacleDamageInterval);
            // Physical continuous damage, distinct from the initial blockable hit.
            UGameplayStatics::ApplyDamage(Victim,TentacleTickDamage,GetController(),this,UDamageType::StaticClass());
        }
    }
    else if(NetState.State==EBoundCongregateState::TentacleRecover&&T>=TentacleRecoverSeconds)
    {NetState.ReleasedWrap=0.f;SetState(EBoundCongregateState::Idle);}
}
void ABoundCongregate::EndTentacle(bool bRecover)
{
    if(!HasAuthority())return;
    const bool WasTentacle=TentacleActive();
    const float Elapsed=float(StateElapsed());
    NetState.ReleasedWeight=NetState.State==EBoundCongregateState::TentacleWindup?FMath::SmoothStep(0.f,TentacleWindupSeconds,Elapsed):1.f;
    NetState.ReleasedStrike=NetState.State==EBoundCongregateState::TentacleWindup?0.f:
        NetState.State==EBoundCongregateState::TentacleStrike?BoundCongregateTentacleTiming::Release(Elapsed,TentacleStrikeSeconds).Phase:1.f;
    NetState.ReleasedWrap=NetState.State==EBoundCongregateState::TentacleDrag?1.f:
        NetState.State==EBoundCongregateState::TentacleWrap?FMath::SmoothStep(0.f,TentacleWrapSeconds,Elapsed):0.f;
    if(auto* Victim=NetState.CapturedTarget.Get())
    {
        NetState.TentacleAim=Victim->GetActorLocation();
        if(auto* Capture=Victim->FindComponentByClass<UBoundCongregateCaptureComponent>())Capture->Release(this);
    }
    NetState.CapturedTarget=nullptr;
    if(WasTentacle)
    {
        NextAttack=FMath::Max(NextAttack,Clock()+TentacleRecoverSeconds+.25f);
        if(bRecover)SetState(EBoundCongregateState::TentacleRecover);
    }
}
void ABoundCongregate::CancelTentacle(){if(HasAuthority()&&TentacleActive()&&NetState.State!=EBoundCongregateState::TentacleRecover)EndTentacle(true);}
void ABoundCongregate::EndPlay(const EEndPlayReason::Type Reason){EndTentacle(false);Super::EndPlay(Reason);}
