#include "MonsterCombatComponent.h"
#include "VortexCofferM25.h"
#include "M10Mawcrawler.h"
#include "SpiralPillarM14.h"
#include "HangingBellM09.h"
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
    { RegisterExplicitStun(Seconds);N->Knockdown->ExtendControl(Seconds);return; }
    if(auto* Pawn=Cast<ACharacter>(GetOwner()))
    {
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    }
    const float Remaining=IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f;
    RegisterExplicitStun(Seconds);
    Seconds=FMath::Max(StunSecondsRemaining(),Remaining);
    bParryReaction=false;
    if(!UsesToughnessBar()){Toughness=0.f;SinceHit=0.f;PublishToughnessState();}
    if(auto* M25=Cast<AVortexCofferM25>(GetOwner()))M25->InterruptAttack(Seconds);
    else if(auto* M14=Cast<ASpiralPillarM14>(GetOwner()))M14->InterruptAttack(Seconds);
    else if(auto* M09=Cast<AHangingBellM09>(GetOwner()))M09->InterruptAttack(Seconds);
    else if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->InterruptAttack(Seconds);
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

bool UMonsterCombatComponent::ReceiveForcedLaunch(APawn* Attacker,FVector LaunchVelocity,float ControlSeconds)
{
    auto* Pawn=Cast<ACharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||IsDead())return false;
    if(!CanReceiveLaunchOrKnockdown())return false;
    const float Hold=FMath::Max(ControlSeconds,StunSecondsRemaining());
    bool Launched=false;
    if(auto* F=Cast<AFleshHandMonster>(Pawn))Launched=F->Knockdown&&F->Knockdown->Launch(Attacker,LaunchVelocity,Hold,true);
    else if(auto* N=Cast<ANurseZombie>(Pawn))Launched=N->Knockdown&&N->Knockdown->Launch(Attacker,LaunchVelocity,Hold,true);
    ParryPushDistance=MeleePushDistance=0.f;
    if(Launched)
    {
        ClearHumanoidStun();
        ToughnessReactionUntil=0.;
        ReactionTime=ReactionDuration=0.f;bParryReaction=false;
        // Physical control does not erase a previously applied explicit stun.
        return true;
    }
    auto* Move=Pawn->GetCharacterMovement();
    if(!Move)return false;
    if(auto* AI=Cast<AMonsterAIController>(Pawn->GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    const float Remaining=IsControlled()?FMath::Max(0.f,ReactionDuration-ReactionTime):0.f;
    const float Duration=FMath::Max(Hold,Remaining);
    if(auto* M14=Cast<ASpiralPillarM14>(Pawn))M14->InterruptAttack(Duration);
    else if(auto* M09=Cast<AHangingBellM09>(Pawn))M09->InterruptAttack(Duration);
    else if(auto* M10=Cast<AM10Mawcrawler>(Pawn))M10->InterruptAttack(Duration);
    else if(auto* S=Cast<AHundredEyedSlagMonster>(Pawn))S->InterruptAttack(Duration);
    else if(auto* F=Cast<AFleshHandMonster>(Pawn))F->InterruptAttack(Duration);
    else if(auto* W=Cast<AWolfMonster>(Pawn))W->InterruptAttack(Duration);
    else if(auto* M=Cast<APoisonMaggotMonster>(Pawn))M->InterruptAttack(Duration);
    else if(auto* N=Cast<ANurseZombie>(Pawn))N->InterruptAttack(Duration);
    else if(auto* H=Cast<AHandBrainMonster>(Pawn))H->InterruptAttack(Duration);
    // Suspended monsters have no gravity: bound their impulse in time instead
    // of changing their ceiling locomotion or leaving them drifting forever.
    if(Move->GravityScale<=SMALL_NUMBER)
    {
        if(SuspendedLaunchRemaining<=0.f)SuspendedMovementMode=Move->MovementMode;
        SuspendedLaunchRemaining=ControlSeconds;
    }
    Move->StopMovementImmediately();Move->ClearAccumulatedForces();
    Move->SetMovementMode(MOVE_Falling);Pawn->LaunchCharacter(LaunchVelocity,true,true);
    return true;
}

void UMonsterCombatComponent::TickForcedLaunch(float Delta)
{
    if(SuspendedLaunchRemaining<=0.f)return;
    SuspendedLaunchRemaining=FMath::Max(0.f,SuspendedLaunchRemaining-Delta);
    if(SuspendedLaunchRemaining>0.f)return;
    if(auto* Pawn=Cast<ACharacter>(GetOwner()))
        if(auto* Move=Pawn->GetCharacterMovement())
        {
            Move->StopMovementImmediately();Move->ClearAccumulatedForces();
            Move->SetMovementMode(static_cast<EMovementMode>(SuspendedMovementMode));
        }
}

bool UMonsterCombatComponent::ReceiveKnockdown(APawn* Attacker,FVector LaunchVelocity,float DownSeconds)
{
    if(!GetOwner()->HasAuthority() || IsDead())return false;
    if(!CanReceiveLaunchOrKnockdown())return false;
    DownSeconds=FMath::Max(DownSeconds,StunSecondsRemaining());
    if(auto* M14=Cast<ASpiralPillarM14>(GetOwner())){M14->InterruptAttack(FMath::Max(.7f,DownSeconds));return true;}
    if(auto* M09=Cast<AHangingBellM09>(GetOwner())){M09->InterruptAttack(FMath::Max(.7f,DownSeconds));return true;}
    bool Launched=false;
    if(auto* F=Cast<AFleshHandMonster>(GetOwner()))Launched=F->Knockdown&&F->Knockdown->Launch(Attacker,LaunchVelocity,DownSeconds);
    else if(auto* N=Cast<ANurseZombie>(GetOwner()))Launched=N->Knockdown&&N->Knockdown->Launch(Attacker,LaunchVelocity,DownSeconds);
    if(!Launched)return false;
    ClearHumanoidStun();
    ParryPushDistance=MeleePushDistance=0.f;
    ReactionTime=ReactionDuration=0.f;ToughnessReactionUntil=0.;bParryReaction=false;
    bStunned=StunSecondsRemaining()>0.f;
    if(!UsesToughnessBar()){Toughness=0.f;PublishToughnessState();}
    return true;
}
