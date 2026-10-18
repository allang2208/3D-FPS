#include "FPSGAMECharacter.h"
#include "Weapons/RuneSwordComponent.h"
#include "Weapons/Bow/BowWeaponComponent.h"
#include "Weapons/Bow/BowArmsMeshComponent.h"
#include "Weapons/Staff/StaffWeaponComponent.h"
#include "Weapons/Spellbook/SpellbookComponent.h"
#include "Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Items/FPSPotionUseComponent.h"
#include "Production/ProductionToolComponent.h"

bool AFPSGAMECharacter::CanBeginConsumableUse() const
{
    if(IsResolvingActionInterrupt() || IsTraversing() || IsCastBlockingLeftHandAction() || IsSpellGestureBlocking())return false;
    if(const auto* Use=FindComponentByClass<UFPSPotionUseComponent>();Use&&Use->IsReturningBow())return false;
    if(HasOffhandPistol() && DualPistols->LeftBusy())return false;
    // Only the equipped family owns this gate. The inactive firearm clock/ADS
    // and a menu-hidden staff must not lock a sword, tool or empty hand.
    if(RuneSword && RuneSword->IsEquipped())return RuneSword->CanReleaseSupportHand();
    if(const auto* Tool=FindComponentByClass<UProductionToolComponent>();Tool && Tool->IsEquipped())return !Tool->IsBusy();
    if(Bow && Bow->IsEquipped())
    {
        if(Bow->CastTransfer()>0.f)return false; // complete the previous hand's recovery first
        switch(Bow->GetStage())
        {
        case EBowStage::Stowed: case EBowStage::Ready: case EBowStage::DrawEntry:
        case EBowStage::Drawing: case EBowStage::Holding: case EBowStage::LetDown:return true;
        default:return false; // equip, nock, release/recovery and melee keep their clock
        }
    }
    if(Staff && Staff->IsEquipped())return !Staff->IsBusy();
    if(HasOffhandPistol())return true; // the offhand controller owns both pistol clocks
    return !bInventoryWeaponReady || WeaponState==EAKMWeaponState::Idle || WeaponState==EAKMWeaponState::Inspecting;
}

void AFPSGAMECharacter::PrepareForConsumableUse()
{
    InterruptWeaponInspection();
    if(Spellbook)Spellbook->CancelFocus();
    // Clearing intent is essential: holding RMB must not reacquire ADS next tick.
    bAimHeld=false;SetAimingState(false);
    if(RuneSword && RuneSword->IsEquipped() && (RuneSword->IsBusy() || RuneSword->IsInspecting()))
        RuneSword->CancelAction(); // eligibility admitted only guard/return/inspect
    if(Bow && Bow->IsEquipped()&&!Bow->BeginCastHandoff())Bow->CancelAction(); // shared support transfer; retain the nocked arrow
}

USkeletalMeshComponent* AFPSGAMECharacter::ConsumableHands() const
{
    if(HasOffhandSpellbook())return Spellbook->ArmsMesh();
    if(HasOffhandPistol())return DualPistols->Hand(1).Mesh.Get();
    if(RuneSword && RuneSword->IsEquipped())return RuneSword->ArmsMesh();
    if(const auto* Tool=FindComponentByClass<UProductionToolComponent>();Tool && Tool->IsEquipped())return Tool->ArmsMesh();
    if(Bow && Bow->IsEquipped())return Bow->ArmsMesh();
    if(Staff && Staff->IsEquipped())return Staff->ArmsMesh();
    if(UnarmedIdle && UnarmedIdle->IsEquipped())return UnarmedIdle->ArmsMesh();
    return bInventoryWeaponReady ? AKMViewmodel.Get() : nullptr;
}
