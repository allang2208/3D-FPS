#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"

void UFPSPlayerBodyComponent::RecordAcceptedHit(AActor* Attacker,float Damage,float MaxHealth)
{
    if(!GetOwner()->HasAuthority()||Damage<=0.f)return;
    FVector Direction=Attacker?(GetOwner()->GetActorLocation()-Attacker->GetActorLocation()).GetSafeNormal2D():FVector::ZeroVector;
    if(Direction.IsNearlyZero())Direction=-GetOwner()->GetActorForwardVector();
    ++Reactions.HitSerial;Reactions.HitAt=ServerClock();Reactions.HitDirection=Direction;
    Reactions.HitStrength=FMath::Clamp(.3f+Damage/FMath::Max(1.f,MaxHealth)*2.f,.3f,1.f);
    GetOwner()->ForceNetUpdate();
}

void UFPSPlayerBodyComponent::RecordKnockback(const FVector& Direction,float Distance,float Duration)
{
    if(!GetOwner()->HasAuthority()||Distance<=.1f||Direction.ContainsNaN())return;
    ++Reactions.PushSerial;Reactions.PushAt=ServerClock();
    Reactions.PushDirection=Direction.GetSafeNormal2D();
    Reactions.PushSeconds=FMath::Clamp(Duration+.32f,.4f,1.25f);
    Reactions.PushStrength=FMath::Clamp(Distance/120.f,.25f,1.f);
    GetOwner()->ForceNetUpdate();
}

void UFPSPlayerBodyComponent::UpdateReactions()
{
    if(!GetOwner()->HasAuthority())return;
    const float Now=ServerClock();
    if(Now>=ReactionComponentRefresh)
    {
        ReactionComponentRefresh=Now+.25f;
        ReactionStatus=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
        ReactionGuard=GetOwner()->FindComponentByClass<UPlayerGuardBreakComponent>();
    }
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    const bool Stunned=!(Health&&Health->IsDead())&&
        ((ReactionStatus.IsValid()&&ReactionStatus->IsStunned())||(ReactionGuard.IsValid()&&ReactionGuard->IsActive()));
    if(Stunned!=Reactions.bStunned)
    {
        Reactions.bStunned=Stunned;if(Stunned)Reactions.StunAt=Now;
        GetOwner()->ForceNetUpdate();
    }
}
