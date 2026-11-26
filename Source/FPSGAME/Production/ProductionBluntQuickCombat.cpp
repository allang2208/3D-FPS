#include "ProductionToolComponent.h"
#include "ProductionToolMeshComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
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
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||Item->InstanceId!=EquippedId||!PojunGrip::UsesHammerMotion(*Item)||PojunGrip::Installed(*Item)!=bPojunGrip)return false;
    if(IsPojunChainOccupied()||IsThunderHammerAway()||ThunderCatchAge>=0.f||!IsWarhammerEquipped()||!Pawn||!Quick||!CanUse()||!HasReadyPresentation()
        ||!Motions.FindRef(TEXT("QuickCombat"))||!Pawn->CanStartQuickCombatPriority())return false;
    Pawn->InterruptActionsForPriority(false);
    Pawn->ExitSprintForWeapon();
    Quick->ConfigureForWarhammer(bConicalSeat);
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
    if(bPojunGrip&&!PojunStrikeLocal.IsSet())return false;
    const FVector Local=PojunStrikeLocal.Get(bConicalSeat?ConicalStrikeLocal:WarhammerQuickCombat::StrikeLocal);
    Origin=Viewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(Local);
    return true;
}
