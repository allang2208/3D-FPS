#include "MonsterCombatComponent.h"
#include "M10Mawcrawler.h"
#include "MonsterObstacleCollision.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MonsterAIController.h"
#include "WolfMonster.h"
#include "PoisonMaggotMonster.h"
#include "HundredEyedSlagMonster.h"
#include "NurseZombie.h"
#include "HumanoidKnockdownComponent.h"
#include "HandBrainMonster.h"
#include "FleshHandMonster.h"
#include "FleshHandKnockdownComponent.h"

void UMonsterCombatComponent::ReceiveMeleeKnockback(APawn* Attacker,float DistanceCM)
{
    if(!GetOwner()->HasAuthority()||IsDead()||DistanceCM<=0||GetOwner()->ActorHasTag(TEXT("KnockbackImmune")))return;
    if(IsKnockedDown())return;
    // Called once after both damage components settle. No added stun or parry.
    MeleePushDirection=IsValid(Attacker)?(GetOwner()->GetActorLocation()-Attacker->GetActorLocation()).GetSafeNormal2D():-GetOwner()->GetActorForwardVector().GetSafeNormal2D();
    MeleePushDistance=0;MeleePushAge=0;
    if(MoveMeleePush(DistanceCM*.2f))MeleePushDistance=DistanceCM*.8f;
}

void UMonsterCombatComponent::ReceiveStun(APawn* Attacker,float Seconds,float KnockbackCM)
{
    // Explicit skill stun, independent of toughness stagger and its duration.
    if(!GetOwner()->HasAuthority()||IsDead())return;
    if(Seconds<=0.f){ReceiveMeleeKnockback(Attacker,KnockbackCM);return;}
    if(auto* F=Cast<AFleshHandMonster>(GetOwner());F&&F->Knockdown&&F->Knockdown->IsControlling())
    { RegisterExplicitStun(Seconds);F->Knockdown->ExtendControl(Seconds);return; }
    if(auto* N=Cast<ANurseZombie>(GetOwner());N && N->Knockdown && N->Knockdown->IsControlling())
    { N->Knockdown->ExtendControl(Seconds);return; }
    if(auto* Pawn=Cast<ACharacter>(GetOwner()))
    {
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    }
    const float Remaining=IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f;
    RegisterExplicitStun(Seconds);
    Seconds=FMath::Max(StunSecondsRemaining(),Remaining);
    bParryReaction=false;Toughness=0.f;SinceHit=0.f;
    if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->InterruptAttack(Seconds);
    else if(auto* S=Cast<AHundredEyedSlagMonster>(GetOwner()))S->InterruptAttack(Seconds);
    else if(auto* F=Cast<AFleshHandMonster>(GetOwner()))F->InterruptAttack(Seconds);
    else if(auto* W=Cast<AWolfMonster>(GetOwner()))W->InterruptAttack(Seconds);
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
    const FVector Delta=MeleePushDirection*Distance;
    const float Fraction=MonsterObstacleCollision::LimitPush(Pawn,Delta);
    FHitResult Hit;Move->SafeMoveUpdatedComponent(Delta*Fraction,Pawn->GetActorQuat(),true,Hit);
    Move->bForceNextFloorCheck=true;return Fraction>=1.f && !Hit.bBlockingHit;
}

bool UMonsterCombatComponent::ReceiveKnockdown(APawn* Attacker,FVector LaunchVelocity,float DownSeconds)
{
    if(!GetOwner()->HasAuthority() || IsDead())return false;
    bool Launched=false;
    if(auto* F=Cast<AFleshHandMonster>(GetOwner()))Launched=F->Knockdown&&F->Knockdown->Launch(Attacker,LaunchVelocity,DownSeconds);
    else if(auto* N=Cast<ANurseZombie>(GetOwner()))Launched=N->Knockdown&&N->Knockdown->Launch(Attacker,LaunchVelocity,DownSeconds);
    if(!Launched)return false;
    ClearHumanoidStun();
    ParryPushDistance=MeleePushDistance=0.f;
    ReactionTime=ReactionDuration=0.f;ExplicitStunUntil=0.0;bParryReaction=false;bStunned=false;Toughness=0.f;
    return true;
}
