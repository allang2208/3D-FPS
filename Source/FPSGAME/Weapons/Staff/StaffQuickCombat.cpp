#include "StaffWeaponComponent.h"
#include "StaffArmsMeshComponent.h"
#include "StaffQuickCombatPose.h"
#include "../../FPSGAMECharacter.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../PistolDualWieldComponent.h"
#include "Components/StaticMeshComponent.h"

bool UStaffWeaponComponent::IsQuickCombatActive()const
{
    const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr;
    return Quick&&Quick->IsOccupyingLeftHand()
        &&(Quick->GetStyle()==EQuickCombatStyle::StaffPunch||Quick->GetStyle()==EQuickCombatStyle::StaffOffhandPistol);
}

bool UStaffWeaponComponent::BeginQuickCombat()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!IsEquipped()||IsEquipping()||!Pawn||!Pawn->CanStartQuickCombatPriority()
        ||Pawn->HasOffhandSpellbook()
        ||!Staff||!Staff->IsVisible()||!Arms||!Arms->IsVisible())return false;
    if(Pawn->HasOffhandPistol())
    {
        auto* Dual=Pawn->FindComponentByClass<UPistolDualWieldComponent>();
        return Dual&&Dual->IsOffhandOnly()&&Dual->BeginQuickCombat();
    }
    auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    if(!Quick)return false;
    // Capture the live free arm before priority interruption changes its gait.
    StaffQuickCombatPose::CaptureEntry(*Arms,Quick->GetActionSerial()+1u);
    Pawn->InterruptActionsForPriority(false);
    Pawn->ExitSprintForWeapon();
    Quick->ConfigureForStaffPunch();
    return Quick->BeginAction();
}

bool UStaffWeaponComponent::GetQuickCombatStrikeProbe(FVector& Origin,float /*ContactTime*/)
{
    const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr;
    if(!IsEquipped()||!IsQuickCombatActive()||!Quick||Quick->GetStyle()!=EQuickCombatStyle::StaffPunch
        ||!Arms||Arms->GetBoneIndex(TEXT("middle_01_l"))==INDEX_NONE)return false;
    // The shared action clock is already held at the exact contact before this call.
    Arms->TickAnimation(0.f,false);
    Arms->RefreshBoneTransforms();
    Origin=Arms->GetSocketLocation(TEXT("middle_01_l"));
    return true;
}
