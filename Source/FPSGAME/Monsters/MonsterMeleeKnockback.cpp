#include "MonsterCombatComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MonsterAIController.h"
#include "WolfMonster.h"
#include "PoisonMaggotMonster.h"
#include "NurseZombie.h"
#include "HandBrainMonster.h"

void UMonsterCombatComponent::ReceiveMeleeKnockback(APawn* Attacker,float DistanceCM)
{
    if(!GetOwner()->HasAuthority()||IsDead()||DistanceCM<=0||GetOwner()->ActorHasTag(TEXT("KnockbackImmune")))return;
    // Called once after both damage components settle. No added stun or parry.
    MeleePushDirection=IsValid(Attacker)?(GetOwner()->GetActorLocation()-Attacker->GetActorLocation()).GetSafeNormal2D():-GetOwner()->GetActorForwardVector().GetSafeNormal2D();
    MeleePushDistance=0;MeleePushAge=0;
    if(MoveMeleePush(DistanceCM*.2f))MeleePushDistance=DistanceCM*.8f;
}

void UMonsterCombatComponent::ReceiveStun(APawn* Attacker,float Seconds,float KnockbackCM)
{
    // Mirrors the parry reaction's stun flow (interrupt, movement stop, immediate
    // push) without the parry flag, so the stagger presentation stays the default.
    if(!GetOwner()->HasAuthority()||IsDead())return;
    if(auto* Pawn=Cast<ACharacter>(GetOwner()))
    {
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    }
    const float Remaining=IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f;
    Seconds=FMath::Max(Seconds,Remaining);
    bStunned=true;Poise=0.f;SinceHit=0.f;
    if(auto* W=Cast<AWolfMonster>(GetOwner()))W->InterruptAttack(Seconds);
    else if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->InterruptAttack(Seconds);
    else if(auto* N=Cast<ANurseZombie>(GetOwner()))N->InterruptAttack(Seconds);
    else if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->InterruptAttack(Seconds);
    if(KnockbackCM>0.f&&!GetOwner()->ActorHasTag(TEXT("KnockbackImmune")))
    {
        // Spend part of the same distance now so the shove lands inside the stun.
        MeleePushDirection=IsValid(Attacker)?(GetOwner()->GetActorLocation()-Attacker->GetActorLocation()).GetSafeNormal2D():-GetOwner()->GetActorForwardVector().GetSafeNormal2D();
        MeleePushDistance=0;MeleePushAge=0;
        if(MoveMeleePush(KnockbackCM*.2f))MeleePushDistance=KnockbackCM*.8f;
    }
    UE_LOG(LogTemp,Display,TEXT("QUICK_COMBAT_STUN target=%s seconds=%.2f knockback_cm=%.1f"),
        *GetOwner()->GetName(),Seconds,KnockbackCM);
}

void UMonsterCombatComponent::TickMeleePush(float Delta)
{
    if(MeleePushDistance<=0)return;
    constexpr float Duration=.16f;
    const float Before=MeleePushAge/Duration;
    MeleePushAge=FMath::Min(Duration,MeleePushAge+Delta);
    const float After=MeleePushAge/Duration;
    const float Travel=MeleePushDistance*(FMath::Square(1-Before)-FMath::Square(1-After));
    if(!MoveMeleePush(Travel)||MeleePushAge>=Duration)MeleePushDistance=0;
}

bool UMonsterCombatComponent::MoveMeleePush(float Distance)
{
    auto* Pawn=Cast<ACharacter>(GetOwner());auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    if(!Move||!Move->UpdatedComponent)return false;
    FHitResult Hit;Move->SafeMoveUpdatedComponent(MeleePushDirection*Distance,Pawn->GetActorQuat(),true,Hit);
    Move->bForceNextFloorCheck=true;return !Hit.bBlockingHit;
}
