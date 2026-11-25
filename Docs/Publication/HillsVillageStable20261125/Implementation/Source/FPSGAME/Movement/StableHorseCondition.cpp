#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "Engine/DamageEvents.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "GameFramework/Controller.h"
#include "TimerManager.h"

float AStableRidingHorse::TakeDamage(float Amount,const FDamageEvent& Event,AController* Source,AActor* Causer)
{
    // Village mounts share the artisans' protection from friendly fire.
    const auto Hostile=[](const AActor* Actor)
    {
        return IsValid(Actor) && !Actor->ActorHasTag(TEXT("Friendly")) && !Actor->ActorHasTag(TEXT("Wildlife")) &&
            (Actor->ActorHasTag(TEXT("Enemy")) || Actor->FindComponentByClass<UMonsterCombatComponent>());
    };
    if(!HasAuthority()||Amount<=0.f||
       !(Hostile(Source?Source->GetPawn():nullptr)||Hostile(Causer)||Hostile(Causer?Causer->GetOwner():nullptr)))return 0.f;
    // A single physical hit on the mount uses the rider's normal armor/guard pipeline.
    // The accepted health event below is the only writer for both members of the pair.
    if(IsValid(Rider))return Rider->TakeDamage(Amount,Event,Source,Causer);
    if(Health<=0.f)return 0.f;
    return LoseHealth(Super::TakeDamage(Amount,Event,Source,Causer));
}

void AStableRidingHorse::ShareRiderHealthLoss(float AcceptedDamage)
{
    if(HasAuthority()&&Rider&&AcceptedDamage>0.f)LoseHealth(AcceptedDamage);
}

float AStableRidingHorse::LoseHealth(float Amount)
{
    const float Loss=FMath::Min(Health,Amount);
    if(Loss<=0.f)return 0.f;
    Health-=Loss;
    CacheKeeperCondition(Health<=0.f);
    ForceNetUpdate();
    if(Health<=0.f)
    {
        GetWorldTimerManager().ClearTimer(RestRecoveryTimer);
        if(Leader)SetLeader(nullptr);
        Drive(0.f,0.f,false);
        ConsumeMovementInputVector();
        return Loss;
    }
    ScheduleInjuryRecovery();
    return Loss;
}

void AStableRidingHorse::ApplyPotionHealth(float After)
{
    if(!HasAuthority()||IsRetreating())return;
    Health=FMath::Clamp(After,Health,MaxHealth);ForceNetUpdate();
}
void AStableRidingHorse::ScheduleInjuryRecovery()
{
    // A wounded horse can still recover while standing.
    GetWorldTimerManager().SetTimer(RestRecoveryTimer,FTimerDelegate::CreateWeakLambda(this,[this]()
    {
        if(InJump()||GetVelocity().SizeSquared2D()>64.f)return;
        Health=FMath::Min(MaxHealth,Health+MaxHealth*.025f*Traits.HealingScale());
        ForceNetUpdate();
        if(Health>=MaxHealth)GetWorldTimerManager().ClearTimer(RestRecoveryTimer);
    }),1.f,true,12.f);
}

void AStableRidingHorse::UpdateStamina(float Delta,bool Running)
{
    if(!InJump()&&!Running&&Stamina>=MaxStamina)return;
    // A running jump is billed once at the jump rate, through gathering, flight and landing.
    if(InJump()||Running)
    {
        Stamina=FMath::Max(0.f,Stamina-(InJump()?JumpDrainPerSecond:StaminaRates.SprintPerSecond)*Delta);
        RecoveryWait=StaminaRates.RecoveryDelay;
        if(Stamina<=0.f)bExhausted=true;
        return;
    }
    const float RecoverSeconds=FMath::Max(0.f,Delta-RecoveryWait);
    RecoveryWait=FMath::Max(0.f,RecoveryWait-Delta);
    Stamina=FMath::Min(MaxStamina,Stamina+StaminaRates.RecoveryPerSecond*Traits.RecoveryScale()*RecoverSeconds);
    if(bExhausted&&Stamina>=MaxStamina*StaminaRates.SprintRestartRatio)bExhausted=false;
}
