#include "KukriWeaponComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Movement/FPSCharacterMovementComponent.h"

void UKukriWeaponComponent::FinishNetworkAttack(bool Cancelled)
{
    const uint32 Serial=Shot.KukriAttackSerial;
    if(!Serial)return;
    Shot.KukriAttackSerial=OffhandShot.KukriAttackSerial=0;
    if(auto* P=Pawn())
    {
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(P->GetCharacterMovement()))Move->CancelKukriAttackMove(Serial);
        if(auto* PS=P->GetPlayerState<AColdSteelPlayerState>())PS->FinishKukriAttack(Serial,Cancelled);
    }
}

void UKukriWeaponComponent::RejectNetworkAttack(uint32 Serial)
{
    if(Serial&&Shot.KukriAttackSerial==Serial)CancelAction();
    if(auto* P=Pawn())
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(P->GetCharacterMovement()))Move->CancelKukriAttackMove(Serial);
}
