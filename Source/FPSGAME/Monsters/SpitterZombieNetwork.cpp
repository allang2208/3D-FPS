#include "SpitterZombie.h"
#include "HumanoidKnockdownComponent.h"
#include "Net/UnrealNetwork.h"

void ASpitterZombie::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ASpitterZombie,SelectedMovementIndex);
    DOREPLIFETIME(ASpitterZombie,NetworkAttack);
}

void ASpitterZombie::OnRep_MovementChoice()
{
    ApplyMovementChoice();
    if (HasActorBegunPlay() && State==ENurseState::Chase && !(Knockdown && Knockdown->IsControlling()))
        StartStateAnimation(SelectedMovementClip,true);
}

void ASpitterZombie::ApplyNetworkAttack()
{
    if (!NetworkAttack.Variant.Clip) return;
    SelectedAttackIndex=NetworkAttack.Index;
    AttackClip=NetworkAttack.Variant.Clip;
    ContactTime=NetworkAttack.Variant.ContactTime;
    ContactEnd=NetworkAttack.Variant.ContactEnd;
    RecoveryTime=NetworkAttack.Variant.RecoveryTime;
}

void ASpitterZombie::OnRep_AttackChoice()
{
    ApplyNetworkAttack();
    if (HasActorBegunPlay() && State==ENurseState::Attack && !(Knockdown && Knockdown->IsControlling()))
    {
        StartStateAnimation(AttackClip,false);
        SetAttackAnimationTime(0.f);
    }
}
