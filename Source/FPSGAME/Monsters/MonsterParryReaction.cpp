#include "MonsterCombatComponent.h"
#include "M10Mawcrawler.h"
#include "HangingBellM09.h"
#include "MonsterObstacleCollision.h"
#include "MonsterAIController.h"
#include "NurseZombie.h"
#include "HumanoidKnockdownComponent.h"
#include "HandBrainMonster.h"
#include "FleshHandMonster.h"
#include "PoisonMaggotMonster.h"
#include "HundredEyedSlagMonster.h"
#include "WolfMonster.h"
#include "GameFramework/CharacterMovementComponent.h"

void UMonsterCombatComponent::ReceiveParry(APawn* Defender,float Seconds,float KnockbackCM)
{
    if(!GetOwner()->HasAuthority() || IsDead() || GetOwner()->ActorHasTag(TEXT("ParryImmune")))return;
    const FVector Before=GetOwner()->GetActorLocation();
    const auto* Nurse=Cast<ANurseZombie>(GetOwner());
    if(IsKnockedDown())return;
    const float AttackTime=Nurse?Nurse->StateTime:-1.f;
    // Set reaction context before InterruptAttack starts each monster's pose.
    bParryReaction=true;
    ParryPushDirection=IsValid(Defender)?(GetOwner()->GetActorLocation()-Defender->GetActorLocation()).GetSafeNormal2D():FVector::ZeroVector;
    if(ParryPushDirection.IsNearlyZero())ParryPushDirection=-GetOwner()->GetActorForwardVector().GetSafeNormal2D();
    ParryPushDistance=0.f;ParryPushAge=0.f;
    const float Remaining=IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f;
    RegisterExplicitStun(Seconds);
    Seconds=FMath::Max(StunSecondsRemaining(),Remaining);Toughness=0.f;SinceHit=0.f;
    if(auto* M09=Cast<AHangingBellM09>(GetOwner()))M09->InterruptAttack(Seconds);
    else if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->InterruptAttack(Seconds);
    else if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->InterruptAttack(Seconds);
    else if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->InterruptAttack(Seconds);
    else if(auto* W=Cast<AWolfMonster>(GetOwner()))W->InterruptAttack(Seconds);
    else if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->InterruptAttack(Seconds);
    else if(auto* N=Cast<ANurseZombie>(GetOwner()))N->InterruptAttack(Seconds);
    else if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->InterruptAttack(Seconds);
    if(auto* Pawn=Cast<ACharacter>(GetOwner()))
    {
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Defender);}
    }
    if(KnockbackCM>0.f&&!GetOwner()->ActorHasTag(TEXT("KnockbackImmune")))
    {
        // Spend part of the same distance now; waiting for a later component
        // tick makes the defender react before the attacker visibly moves.
        const float ImmediateDistance=KnockbackCM*.2f;
        if(MoveParryPush(ImmediateDistance))ParryPushDistance=KnockbackCM-ImmediateDistance;
    }
    UE_LOG(LogTemp,Display,TEXT("MONSTER_PARRY target=%s attack_time=%.3f controlled=%d initial_push_cm=%.2f remaining_push_cm=%.2f"),
        *GetOwner()->GetName(),AttackTime,IsControlled(),FVector::Dist2D(Before,GetOwner()->GetActorLocation()),ParryPushDistance);
}
void UMonsterCombatComponent::TickParryPush(float Delta)
{
    if(ParryPushDistance<=0.f)return;
    constexpr float Duration=.16f;
    const float Before=ParryPushAge/Duration;
    ParryPushAge=FMath::Min(Duration,ParryPushAge+Delta);
    const float After=ParryPushAge/Duration;
    const float Travel=ParryPushDistance*(FMath::Square(1.f-Before)-FMath::Square(1.f-After));
    if(!MoveParryPush(Travel) || ParryPushAge>=Duration)ParryPushDistance=0.f;
}
bool UMonsterCombatComponent::MoveParryPush(float Distance)
{
    auto* Pawn=Cast<ACharacter>(GetOwner());
    auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    if(!Move || !Move->UpdatedComponent)return false;
    FHitResult Hit;
    const FVector Delta=ParryPushDirection*Distance;
    const float Fraction=MonsterObstacleCollision::LimitPush(Pawn,Delta);
    Move->SafeMoveUpdatedComponent(Delta*Fraction,Pawn->GetActorQuat(),true,Hit);
    Move->bForceNextFloorCheck=true;
    return Fraction>=1.f && !Hit.bBlockingHit;
}
