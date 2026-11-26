#include "MonsterCombatComponent.h"
#include "MonsterCoreStats.h"
#include "MonsterObstacleCollision.h"
#include "MonsterAIController.h"
#include "HumanoidKnockdownComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

void UMonsterCombatComponent::ReceiveFormationPull(APawn* Attacker,const FVector& Destination,float MaximumDistanceCM)
{StartFormationPull(Attacker,Destination,MaximumDistanceCM,false);}

bool UMonsterCombatComponent::ReceiveFalconDraw(APawn* Attacker,const FVector& Destination)
{return StartFormationPull(Attacker,Destination,80.f,true);}

bool UMonsterCombatComponent::StartFormationPull(APawn* Attacker,const FVector& Destination,float MaximumDistanceCM,bool bFalcon)
{
    auto* Pawn=Cast<ACharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||IsDead()||MaximumDistanceCM<=0.f)return false;
    AdvanceToughnessBar();
    FMonsterCoreStats Stats;
    const bool bOrdinary=MonsterCoreStats::Get(Pawn,Stats)
        &&(Stats.Rank==EMonsterRank::Normal||Stats.Rank==EMonsterRank::Minor);
    if(!bOrdinary&&!IsToughnessBroken())return false;
    // Lead with the species' hit reaction; even a victim already at the stopping distance flinches.
    if(bFalcon)ApplyToughnessReaction(.16f);
    const float Clearance=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()+20.f;
    FormationPullDistance=FMath::Min(MaximumDistanceCM,FMath::Max(0.f,
        float(FVector::Dist2D(Destination,Pawn->GetActorLocation()))-Clearance));
    if(FormationPullDistance<=0.f)return true;
    FormationPullCenter=Destination;FormationPullAge=0.f;
    FormationPullSeconds=bFalcon?.16f:.4f;
    FormationPullWindup=bFalcon?.025f:0.f;
    MeleePushDistance=ParryPushDistance=0.f;
    if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    Pawn->ForceNetUpdate();
    return true;
}

void UMonsterCombatComponent::ShowFalconTug(FVector TowardPlayer,FVector HitPoint)
{
    auto* Character=Cast<ACharacter>(GetOwner());
    auto* Mesh=Character?Character->GetMesh():nullptr;
    if(!Mesh||!Mesh->GetAttachParent()||Mesh->IsSimulatingPhysics()||IsKnockedDown())return;
    if(FalconLeanAge>=0.f)TickFalconLean(1.f);
    const FVector Axis=FVector::CrossProduct(FVector::UpVector,TowardPlayer.GetSafeNormal2D());
    FalconLeanAxis=Mesh->GetAttachParent()->GetComponentTransform().InverseTransformVectorNoScale(Axis).GetSafeNormal();
    FalconLeanSide=FMath::Clamp(float(FVector::DotProduct(HitPoint-Character->GetActorLocation(),Axis)/25.),-1.f,1.f);
    FalconLeanBase=FalconLeanLast=Mesh->GetRelativeRotation().Quaternion();
    FalconLeanAge=0.f;
}

void UMonsterCombatComponent::TickFalconLean(float Delta)
{
    auto* Character=Cast<ACharacter>(GetOwner());
    auto* Mesh=Character?Character->GetMesh():nullptr;
    FalconLeanAge+=Delta;
    if(!Mesh||!Mesh->GetAttachParent()||Mesh->IsSimulatingPhysics()){FalconLeanAge=-1.f;return;}
    const FQuat Current=Mesh->GetRelativeRotation().Quaternion();
    // Network smoothing or a species animation may have supplied a fresh base since our last tick.
    if(!Current.Equals(FalconLeanLast,.00001f))FalconLeanBase=Current;
    if(FalconLeanAge>=.16f||IsDead()||IsKnockedDown())
    {Mesh->SetRelativeRotation(FalconLeanBase);FalconLeanAge=-1.f;return;}
    const float Weight=FMath::SmoothStep(0.f,.035f,FalconLeanAge)*(1.f-FMath::SmoothStep(.05f,.16f,FalconLeanAge));
    FalconLeanLast=FQuat(FalconLeanAxis,FMath::DegreesToRadians(5.f*Weight))*
        FQuat(FVector::UpVector,FMath::DegreesToRadians(2.5f*FalconLeanSide*Weight))*FalconLeanBase;
    Mesh->SetRelativeRotation(FalconLeanLast);
}

void UMonsterCombatComponent::TickFormationPull(float Delta)
{
    if(FormationPullDistance<=0.f||Delta<=0.f)return;
    auto* Pawn=Cast<ACharacter>(GetOwner());
    auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    if(!Move||!Move->UpdatedComponent){FormationPullDistance=0.f;return;}
    const float Duration=FormationPullSeconds;
    const float MotionSeconds=Duration-FormationPullWindup;
    const float Before=FMath::Max(0.f,FormationPullAge-FormationPullWindup)/MotionSeconds;
    FormationPullAge=FMath::Min(Duration,FormationPullAge+Delta);
    const float After=FMath::Max(0.f,FormationPullAge-FormationPullWindup)/MotionSeconds;
    if(After<=0.f)return;
    const FVector Offset=FormationPullCenter-Pawn->GetActorLocation();
    const float Clearance=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()+20.f;
    const float Remaining=FMath::Max(0.f,float(Offset.Size2D())-Clearance);
    const float Travel=FMath::Min(Remaining,FormationPullDistance*(FMath::Square(1-Before)-FMath::Square(1-After)));
    const FVector Motion=Offset.GetSafeNormal2D()*Travel;
    const float Fraction=MonsterObstacleCollision::LimitPush(Pawn,Motion);
    // Keep the uppercut's vertical launch/knockdown clock. Pull owns only XY,
    // and subsequent blade knockback cannot replace its independent movement.
    MeleePushDistance=ParryPushDistance=0.f;
    Move->Velocity.X=Move->Velocity.Y=0.;
    Pawn->ConsumeMovementInputVector();
    auto* Mesh=Pawn->GetMesh();
    const bool bDetached=Mesh&&!Mesh->IsAttachedTo(Pawn->GetRootComponent());
    const FVector Previous=Pawn->GetActorLocation();
    FHitResult Hit;
    Move->SafeMoveUpdatedComponent(Motion*Fraction,Pawn->GetActorQuat(),true,Hit);
    const FVector Applied=Pawn->GetActorLocation()-Previous;
    // Knocked-down humanoids keep a detached physical/frozen mesh. Move that
    // body with the swept root so its next pelvis update cannot undo the pull.
    if(bDetached)Mesh->AddWorldOffset(Applied,false,nullptr,ETeleportType::TeleportPhysics);
    if(auto* Knockdown=Pawn->FindComponentByClass<UHumanoidKnockdownComponent>())
        Knockdown->OffsetRecoverySupport(Applied);
    Move->bForceNextFloorCheck=true;
    if(Fraction<1.f||Hit.bBlockingHit||Remaining<=Travel+UE_KINDA_SMALL_NUMBER||FormationPullAge>=Duration)
        FormationPullDistance=0.f;
}
