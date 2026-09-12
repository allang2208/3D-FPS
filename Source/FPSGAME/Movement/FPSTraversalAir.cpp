#include "FPSTraversalComponent.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"

void UFPSTraversalComponent::SetJumpHeld(bool bHeld)
{
    if (bHeld && !bJumpHeld) bJumpRequestConsumed=bTraversing;
    bJumpHeld=bHeld;
}

void UFPSTraversalComponent::TryAirCatch()
{
    if (!bJumpHeld || bJumpRequestConsumed) return;
    auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    if (!C || !C->Controller || C->Controller->IsMoveInputIgnored())
    { bJumpHeld=false; return; }
    if (!C->GetCharacterMovement()->IsFalling() || C->bIsCrouched || C->bIsSliding || C->IsWeaponBusy()) return;
    // Failed air probes leave gravity and jump untouched. Cheap wall rays gate
    // the support/path checks; no scanning on the ground or after key release.
    TryStart(true,false);
}
