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
{
    auto* Pawn=Cast<ACharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||IsDead()||MaximumDistanceCM<=0.f)return;
    AdvanceToughnessBar();
    FMonsterCoreStats Stats;
    const bool bOrdinary=MonsterCoreStats::Get(Pawn,Stats)
        &&(Stats.Rank==EMonsterRank::Normal||Stats.Rank==EMonsterRank::Minor);
    if(!bOrdinary&&!IsToughnessBroken())return;
    const float Clearance=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()+20.f;
    FormationPullDistance=FMath::Min(MaximumDistanceCM,FMath::Max(0.f,
        float(FVector::Dist2D(Destination,Pawn->GetActorLocation()))-Clearance));
    if(FormationPullDistance<=0.f)return;
    FormationPullCenter=Destination;FormationPullAge=0.f;
    MeleePushDistance=ParryPushDistance=0.f;
    if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    Pawn->ForceNetUpdate();
}

void UMonsterCombatComponent::TickFormationPull(float Delta)
{
    if(FormationPullDistance<=0.f||Delta<=0.f)return;
    auto* Pawn=Cast<ACharacter>(GetOwner());
    auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    if(!Move||!Move->UpdatedComponent){FormationPullDistance=0.f;return;}
    constexpr float Duration=.4f;
    const float Before=FormationPullAge/Duration;
    FormationPullAge=FMath::Min(Duration,FormationPullAge+Delta);
    const float After=FormationPullAge/Duration;
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
