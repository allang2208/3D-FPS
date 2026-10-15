#include "HeQueMonster.h"
#include "FPSCombatHealthComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"

namespace
{
    constexpr float CloseRange=600.f;
    bool InCloseBand(const AHeQueMonster* HeQue,const APawn* Target)
    {
        if(!IsValid(Target))return false;
        const FVector Delta=Target->GetNavAgentLocation()-HeQue->GetNavAgentLocation();
        return Delta.SizeSquared2D()<=FMath::Square(CloseRange)&&FMath::Abs(Delta.Z)<=100.f;
    }
}

APawn* AHeQueMonster::PreferredCombatTarget(APawn* Victim) const
{
    // Only an already engaged monster may switch to an exposed nearby player.
    // This does not acquire enemies through floors or rewrite perception memory.
    if(!IsValid(Victim)||Busy())return Victim;
    APawn* Nearest=nullptr;float Best=FMath::Square(CloseRange)+1.f;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        APawn* Candidate=It->Get()?It->Get()->GetPawn().Get():nullptr;
        if(!Candidate||!Candidate->IsPlayerControlled()||!InCloseBand(this,Candidate))continue;
        const auto* Vitals=Candidate->FindComponentByClass<UFPSCombatHealthComponent>();
        if(Vitals&&Vitals->IsDead())continue;
        const float Distance=FVector::DistSquared2D(GetActorLocation(),Candidate->GetActorLocation());
        if(Distance>=Best||!HasSweepSight(Candidate))continue;
        Nearest=Candidate;Best=Distance;
    }
    return Nearest?Nearest:Victim;
}

void AHeQueMonster::SetCombatTarget(APawn* Victim)
{
    CombatTarget=PreferredCombatTarget(Victim);
}

AHeQueMonster::EAttackChoice AHeQueMonster::ChooseAttack(APawn* Victim) const
{
    if(Busy()||SweepBlocked()||!IsValid(Victim))return EAttackChoice::None;
    if(InCloseBand(this,Victim))
    {
        // Rotate among ready close moves. A failed facing/ceiling/cooldown gate
        // never starts an unready kick or lets a ranged cast steal the windup.
        for(uint8 I=0;I<3;++I)
        {
            switch((NextCloseAttack+I)%3)
            {
            case 0:if(CanSweep(Victim))return EAttackChoice::Kick;break;
            case 1:if(CanClamp(Victim))return EAttackChoice::Clamp;break;
            case 2:if(CanJumpSlam(Victim))return EAttackChoice::Jump;break;
            }
        }
        return EAttackChoice::None;
    }
    const bool PsychicReady=CanPsychic(Victim),RiftReady=CanRift(Victim);
    if(PsychicReady&&(bPreferPsychicNext||!RiftReady))return EAttackChoice::Psychic;
    if(RiftReady)return EAttackChoice::Rift;
    return EAttackChoice::None;
}

bool AHeQueMonster::CanAttack(APawn* Victim) const
{
    return ChooseAttack(PreferredCombatTarget(Victim))!=EAttackChoice::None;
}

bool AHeQueMonster::StartAttack(APawn* Victim)
{
    if(!HasAuthority())return false;
    Victim=PreferredCombatTarget(Victim);
    switch(ChooseAttack(Victim))
    {
    case EAttackChoice::Kick:NextCloseAttack=1;return StartSweep(Victim);
    case EAttackChoice::Clamp:NextCloseAttack=2;return StartClamp(Victim);
    case EAttackChoice::Jump:NextCloseAttack=0;return StartJumpSlam(Victim);
    case EAttackChoice::Rift:bPreferPsychicNext=true;return StartRift(Victim);
    case EAttackChoice::Psychic:bPreferPsychicNext=false;return StartPsychic(Victim);
    default:return false;
    }
}
