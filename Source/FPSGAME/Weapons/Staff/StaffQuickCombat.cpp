#include "StaffWeaponComponent.h"
#include "StaffOffhandMeleeComponent.h"
#include "StaffArmsMeshComponent.h"
#include "StaffQuickCombatPose.h"
#include "StaffGripPose.h"
#include "../WoodenTorchArmsComponent.h"
#include "../WoodenTorchComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../PistolDualWieldComponent.h"
#include "../Kukri/OffhandKukriComponent.h"
#include "Components/StaticMeshComponent.h"

bool UStaffWeaponComponent::IsQuickCombatActive()const
{
    if(const auto* Pair=GetOwner()?GetOwner()->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
        Pair&&Pair->IsActionPresentationActive())return true;
    const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr;
    return Quick&&Quick->IsOccupyingLeftHand()
        &&(Quick->GetStyle()==EQuickCombatStyle::StaffPunch||Quick->GetStyle()==EQuickCombatStyle::StaffOffhandPistol||
            Quick->GetStyle()==EQuickCombatStyle::TorchStrike);
}

bool UStaffWeaponComponent::BeginQuickCombat()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->CanStartQuickCombatPriority()||Pawn->HasOffhandSpellbook())return false;
    auto* Torch=Pawn->FindComponentByClass<UWoodenTorchComponent>();
    if(Torch&&Torch->UsesQuickAttack())
    {
        const int32 Side=Torch->QuickAttackHand();
        auto* Mesh=Side==TorchHand?Staff.Get():Torch->ReadyPairedOffhand();
        auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
        if(!Mesh||!Torch->HandForMotion(Side)||!Quick||Pawn->IsReloading()||Pawn->IsTraversing()||IsEquipping())return false;
        Pawn->InterruptActionsForPriority(false);
        Pawn->ExitSprintForWeapon();
        Quick->ConfigureForTorchStrike();
        if(!Quick->BeginAction())return false;
        QuickTorchMesh=Mesh;
        AttackEntry=Side==TorchHand?CarryPoseInCamera():FStaffCastPose();
        if(Side!=TorchHand)AttackEntry.Contact=StaffGripPose::RestContactInCamera();
        return true;
    }
    else if(!HasMeleeMoveset()||IsEquipping()||!Staff||!Staff->IsVisible()||!Arms||!Arms->IsVisible())return false;
    if(UStaffOffhandMeleeComponent::IsEquippedOn(Pawn))
    {
        auto* Knife=Pawn->FindComponentByClass<UOffhandKukriComponent>();
        return Knife&&Knife->BeginQuickCombat();
    }
    if(Pawn->HasOffhandPistol())
    {
        auto* Dual=Pawn->FindComponentByClass<UPistolDualWieldComponent>();
        return Dual&&Dual->IsOffhandOnly()&&Dual->BeginQuickCombat();
    }
    if(TorchHand!=INDEX_NONE||(Torch&&Torch->HoldsLeft()))return false;
    auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    if(!Quick)return false;
    // Capture the staff's empty hand before priority interruption changes its gait.
    StaffQuickCombatPose::CaptureEntry(*Arms,Quick->GetActionSerial()+1u);
    Pawn->InterruptActionsForPriority(false);
    Pawn->ExitSprintForWeapon();
    Quick->ConfigureForStaffPunch();
    return Quick->BeginAction();
}

bool UStaffWeaponComponent::GetQuickCombatStrikeProbe(FVector& Origin,float /*ContactTime*/)
{
    const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr;
    if(!HasMeleeMoveset()||!IsQuickCombatActive()||!Quick||Quick->GetStyle()!=EQuickCombatStyle::StaffPunch)return false;
    auto* StrikeHand=Arms.Get();
    const FName Contact=TEXT("middle_01_l");
    if(!StrikeHand||StrikeHand->GetBoneIndex(Contact)==INDEX_NONE)return false;
    // The shared action clock is already held at the exact contact before this call.
    StrikeHand->TickAnimation(0.f,false);
    StrikeHand->RefreshBoneTransforms();
    Origin=StrikeHand->GetSocketLocation(Contact);
    return true;
}

bool UStaffWeaponComponent::IsPairedTorchSwing() const
{
    return (Age>=0.f&&PairedTorchMesh.IsValid())||(QuickTorchMesh.IsValid()&&QuickTorchMesh.Get()!=Staff.Get());
}

bool UStaffWeaponComponent::GetTorchQuickContact(FVector& Grip,FVector& Head) const
{
    const auto* Mesh=QuickTorchMesh.Get();
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Mesh||!Pawn)return false;
    auto Contact=SamplePrimaryPose().Contact;
    if(TorchHand==1||IsPairedTorchSwing())Contact=UWoodenTorchArmsComponent::MirrorContact(Contact);
    // Reconstruct both sockets at the exact skill contact frame, before the render tick updates the prop.
    const FTransform WorldGrip=Contact*Pawn->GetMeleeAimTransform();
    const auto FlameInGrip=Mesh->GetSocketTransform(TEXT("Flame"),RTS_Component)
        .GetRelativeTransform(Mesh->GetSocketTransform(TEXT("Grip"),RTS_Component));
    Grip=WorldGrip.GetLocation();
    Head=WorldGrip.TransformPosition(FlameInGrip.GetLocation());
    return true;
}
