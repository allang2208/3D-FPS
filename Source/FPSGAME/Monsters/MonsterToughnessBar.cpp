#include "MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

double UMonsterCombatComponent::ToughnessClock() const
{
    if(const auto* World=GetWorld())
        return World->GetGameState()?World->GetGameState()->GetServerWorldTimeSeconds():World->GetTimeSeconds();
    return 0.;
}

void UMonsterCombatComponent::ConfigureToughnessBar(const FMonsterToughnessBarTuning& Tuning)
{
    ToughnessBarTuning=Tuning;
    ToughnessThreshold=Tuning.Maximum;
    if(Tuning.Maximum>0.f)ToughnessBreakSeconds=Tuning.InitialStaggerSeconds;
    ToughnessState.Phase=Tuning.Maximum>0.f?EMonsterToughnessPhase::Guarded:EMonsterToughnessPhase::Legacy;
    ResetToughnessOnReturnHome();
}

bool UMonsterCombatComponent::CanReceiveLaunchOrKnockdown()
{
    if(GetOwner()->HasAuthority())AdvanceToughnessBar();
    return ToughnessThreshold<=0.f||IsToughnessBroken();
}

void UMonsterCombatComponent::ResetToughnessOnReturnHome()
{
    if(!GetOwner()->HasAuthority())return;
    Toughness=0.f;LastToughnessDamage=0.f;SinceHit=100.f;
    if(UsesToughnessBar())ToughnessState.Phase=EMonsterToughnessPhase::Guarded;
    ToughnessState.PhaseEndsAt=0.;ToughnessState.PhaseDuration=0.f;
    LastToughnessHitAt=LastToughnessUpdateAt=ToughnessClock();
    LastBrokenReactionAt=-100.;ToughnessReactionUntil=0.;
    PublishToughnessState();GetOwner()->ForceNetUpdate();
}

void UMonsterCombatComponent::PublishToughnessState()
{
    ToughnessState.Accumulated=Toughness;
    ToughnessState.Maximum=ToughnessThreshold;
    ToughnessState.BreakCount=Breaks;
}

void UMonsterCombatComponent::OnRep_ToughnessState()
{
    Toughness=ToughnessState.Accumulated;
    ToughnessThreshold=ToughnessState.Maximum;
    Breaks=ToughnessState.BreakCount;
}

float UMonsterCombatComponent::ToughnessPhaseSecondsRemaining() const
{
    return float(FMath::Max(0.,ToughnessState.PhaseEndsAt-ToughnessClock()));
}

float UMonsterCombatComponent::DisplayToughness() const
{
    if(!UsesToughnessBar())return Toughness;
    if(IsToughnessBroken())return 0.f;
    if(ToughnessState.Phase==EMonsterToughnessPhase::Recovering)
        return ToughnessThreshold*FMath::Clamp(1.f-ToughnessPhaseSecondsRemaining()/FMath::Max(.01f,ToughnessState.PhaseDuration),0.f,1.f);
    return FMath::Clamp(ToughnessThreshold-Toughness,0.f,ToughnessThreshold);
}

void UMonsterCombatComponent::AdvanceToughnessBar()
{
    if(!UsesToughnessBar())return;
    const double Now=ToughnessClock();
    if(IsToughnessBroken()&&Now>=ToughnessState.PhaseEndsAt)
    {
        // Carry the exact deadline forward, including a frame that spans both phases.
        ToughnessState.Phase=EMonsterToughnessPhase::Recovering;
        ToughnessState.PhaseDuration=ToughnessBarTuning.RefillSeconds;
        ToughnessState.PhaseEndsAt+=ToughnessBarTuning.RefillSeconds;
        GetOwner()->ForceNetUpdate();
    }
    if(ToughnessState.Phase==EMonsterToughnessPhase::Recovering)
    {
        Toughness=ToughnessThreshold*FMath::Clamp(float((ToughnessState.PhaseEndsAt-Now)/ToughnessBarTuning.RefillSeconds),0.f,1.f);
        if(Now>=ToughnessState.PhaseEndsAt)
        {
            ToughnessState.Phase=EMonsterToughnessPhase::Guarded;
            ToughnessState.PhaseEndsAt=0.;ToughnessState.PhaseDuration=0.f;
            Toughness=0.f;LastToughnessHitAt=Now;
            GetOwner()->ForceNetUpdate();
        }
    }
    else if(ToughnessState.Phase==EMonsterToughnessPhase::Guarded&&Toughness>0.f)
    {
        const double From=FMath::Max(LastToughnessUpdateAt,LastToughnessHitAt+ToughnessBarTuning.RegenDelaySeconds);
        Toughness=FMath::Max(0.f,Toughness-float(FMath::Max(0.,Now-From))*ToughnessThreshold*ToughnessBarTuning.RegenFractionPerSecond);
    }
    LastToughnessUpdateAt=Now;
    PublishToughnessState();
    // Only end a reaction owned by poise. Stun/freeze/launch retain their own clocks.
    if(ToughnessReactionUntil>0.&&Now>=ToughnessReactionUntil)
    {
        ToughnessReactionUntil=0.;
        const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
        if(IsControlled()&&!IsKnockedDown()&&StunSecondsRemaining()<=0.f&&
            !(Status&&(Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned())))FinishReaction();
    }
}

void UMonsterCombatComponent::ReceiveToughnessBarHit(float Damage,EMonsterAttackForm Form)
{
    AdvanceToughnessBar();
    if(Damage<=0.f)return;
    LastAttackForm=Form;LastToughnessDamage=0.f;
    if(ToughnessState.Phase==EMonsterToughnessPhase::Recovering)return;
    const double Now=ToughnessClock();
    if(IsToughnessBroken())
    {
        // Pellets/simultaneous hits still deal damage, but do not repeatedly reset a pose.
        if(IsKnockedDown()||Now-LastBrokenReactionAt<ToughnessBarTuning.HitIntervalSeconds)return;
        const float Left=ToughnessPhaseSecondsRemaining();
        if(Left<=0.f)return;
        LastBrokenReactionAt=Now;
        const float Duration=FMath::Min(Left,FMath::Clamp(ToughnessBarTuning.HitStaggerSeconds*IncomingHitReactionMultiplier,.15f,.25f));
        ApplyToughnessReaction(Duration);
        return;
    }
    LastToughnessDamage=ToughnessDamageFor(Damage,Form)*IncomingToughnessDamageMultiplier;
    if(LastToughnessDamage<=0.f)return;
    LastToughnessHitAt=Now;
    Toughness=FMath::Min(ToughnessThreshold,Toughness+LastToughnessDamage);
    if(Toughness>=ToughnessThreshold)
    {
        ++Breaks;
        ToughnessState.Phase=EMonsterToughnessPhase::Broken;
        ToughnessState.PhaseDuration=ToughnessBarTuning.BrokenSeconds;
        ToughnessState.PhaseEndsAt=Now+ToughnessBarTuning.BrokenSeconds;
        LastBrokenReactionAt=Now;
        if(!IsKnockedDown())ApplyToughnessReaction(FMath::Min(ToughnessBarTuning.BrokenSeconds,ToughnessBreakSeconds*IncomingHitReactionMultiplier));
        GetOwner()->ForceNetUpdate();
    }
    PublishToughnessState();
}
