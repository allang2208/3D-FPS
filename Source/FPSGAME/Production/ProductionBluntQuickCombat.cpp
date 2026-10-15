#include "ProductionToolComponent.h"
#include "ProductionToolMeshComponent.h"
#include "WarhammerQuickCombatMotion.h"
#include "WarhammerQuickCombatMarker.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "Animation/AnimSequence.h"

bool UProductionToolComponent::IsQuickCombatActive() const
{
    const auto* Quick=Character.IsValid()?Character->QuickCombatPistol.Get():nullptr;
    return IsWarhammerEquipped()&&Quick&&Quick->GetStyle()==EQuickCombatStyle::Warhammer
        &&Quick->IsOccupyingLeftHand();
}

bool UProductionToolComponent::BeginQuickCombat()
{
    auto* Pawn=Character.Get();
    auto* Quick=Pawn?Pawn->QuickCombatPistol.Get():nullptr;
    if(!IsWarhammerEquipped()||!Pawn||!Quick||!CanUse()||!HasReadyPresentation()
        ||!Motions.FindRef(TEXT("QuickCombat"))||!Pawn->CanStartQuickCombatPriority())return false;
    Pawn->InterruptActionsForPriority(false);
    Pawn->ExitSprintForWeapon();
    Quick->ConfigureForWarhammer();
    if(!Quick->BeginAction())return false;
    SprintBlend=0.f;
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    SampleMotion(TEXT("QuickCombat"),0.f);
    return true;
}

bool UProductionToolComponent::GetQuickCombatStrikeProbe(FVector& Origin,float PoseSeconds)
{
    if(!IsQuickCombatActive()||!Viewmodel||!Viewmodel->DoesSocketExist(TEXT("WPN_root")))return false;
    // The shared action clock is at the exact contact, even across a hitch.
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    SampleMotion(TEXT("QuickCombat"),PoseSeconds);
    Origin=Viewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(WarhammerQuickCombat::StrikeLocal);
    return true;
}
