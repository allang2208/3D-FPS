#include "FPSGAMECharacter.h"
#include "Items/FPSPotionUseComponent.h"
#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelStatusModel.h"
#include "Skills/FPSFireballComponent.h"
#include "Skills/FPSQuickCombatComponent.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Weapons/WeaponBipodDeploymentComponent.h"
#include "Weapons/RuneSwordComponent.h"
#include "Weapons/Bow/BowWeaponComponent.h"
#include "Weapons/Staff/StaffWeaponComponent.h"
#include "Weapons/RuneOrbBladesComponent.h"
#include "Production/ProductionToolComponent.h"
#include "Movement/FPSTraversalComponent.h"
#include "Movement/FPSDoorPushComponent.h"
#include "Movement/FPSCharacterMovementComponent.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

void AFPSGAMECharacter::InterruptWeaponInspection()
{
    if(WeaponState!=EAKMWeaponState::Inspecting)return;
    // FinishWeaponAction advances the shot deadline to the original clip end.
    // An interrupted inspect must release its pose and input gate immediately.
    StopMechanicalAudio();
    WeaponState=EAKMWeaponState::Idle;
    WeaponStateElapsed=WeaponStateDuration=ActionElapsed=ActionDuration=0.f;
    ActiveActionAnimation=nullptr;
    ActionStartPosition=0.f;ActionPlayRate=1.f;
    M4ActionFramingAlpha=0.f;
    if(GunplayAnimation)
    {
        GunplayAnimation->ActionClip=nullptr;
        GunplayAnimation->ActionTime=GunplayAnimation->ActionAlpha=0.f;
    }
    SetAimingState(bAimHeld);
    ResumeWeaponPose();
}

bool AFPSGAMECharacter::IsSwitchingWeapon() const
{
    if(WeaponState==EAKMWeaponState::Equipping)return true;
    if(HasOffhandPistol() && DualPistols->IsEquipping())return true;
    if(RuneSword && RuneSword->IsEquipped() && RuneSword->IsEquipping())return true;
    if(Bow && Bow->IsEquipped() && Bow->GetStage()==EBowStage::Equip)return true;
    if(Staff && Staff->IsEquipping())return true;
    const auto* Tool=FindComponentByClass<UProductionToolComponent>();
    return Tool && Tool->IsEquipped() && Tool->IsEquipping();
}

bool AFPSGAMECharacter::CanStartQuickCombatPriority() const
{
    if(IsDoorPushActive() || IsSwitchingWeapon() || bResolvingActionInterrupt || !IsLocallyControlled())return false;
    if(AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(GetController())))return false;
    if(const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();Health && Health->IsDead())return false;
    if(QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand())return false;
    if(RuneSword && RuneSword->IsQuickCombatActive())return false;
    return bInventoryWeaponReady || HasOffhandSpellbook() || (RuneSword && RuneSword->IsEquipped()) || (Bow && Bow->IsEquipped()) || (Staff && Staff->IsEquipped());
}

void AFPSGAMECharacter::InterruptActionsForPriority(bool bWeaponSwitch)
{
    if(bResolvingActionInterrupt)return;
    if(BipodDeployment)BipodDeployment->Release(true);
    auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    // A successful equipment transaction has already published the NEW item.
    // Never sync the outgoing gun's counters into that newly equipped instance.
    if(Profile && !bWeaponSwitch)Profile->SyncRuntime();
    {
        TGuardValue<bool> Resolving(bResolvingActionInterrupt,true);
        if(DoorPush)DoorPush->Cancel();
        if(auto* Potion=FindComponentByClass<UFPSPotionUseComponent>())Potion->Cancel();
        if(auto* Magic=FindComponentByClass<UFPSFireballComponent>())Magic->InterruptForPriority();
        if(QuickCombatPistol)QuickCombatPistol->Cancel();
        // Cancel the draw before FireReleased: priority interrupts never loose an arrow.
        if(Bow && Bow->IsEquipped())Bow->CancelAction();
        if(Staff && Staff->IsEquipped())Staff->CancelAction();
        if(RuneSword && (RuneSword->IsBusy() || RuneSword->IsInspecting()))RuneSword->CancelAction();
        if(bWeaponSwitch && RuneOrbBlades)RuneOrbBlades->EndOrbit();
        if(auto* Tool=FindComponentByClass<UProductionToolComponent>())Tool->CancelUse();
        if(Traversal && IsTraversing())Traversal->Cancel();
        if(auto* Movement=Cast<UFPSCharacterMovementComponent>(GetCharacterMovement()))Movement->CancelDodge();
        if(bIsSliding)StopSlide(false);
        InterruptReload();
        if(HasOffhandPistol())DualPistols->InterruptActions();
        CancelAmmoSelection();
        FireReleased();AimReleased();
        bReloadAfterCasting=bRevolverReloadAfterFire=bPistolShotPending=false;
        bPendingEmptyReload=bReloadAmmoCommitted=bReloadCycleOnly=false;
        ReloadResumeElapsed=0.f;
        PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
        StopMechanicalAudio();
        WeaponState=EAKMWeaponState::Idle;
        WeaponStateElapsed=WeaponStateDuration=ActionElapsed=ActionDuration=0.f;
        ActiveActionAnimation=nullptr;M4ActionFramingAlpha=0.f;
        if(GunplayAnimation)GunplayAnimation->ActionAlpha=0.f;
    }
    // Refund/cooldown transactions deliberately defer nested presentation refresh.
    // Equipment changes are refreshed by their caller after all cancellations.
    if(Profile && !bWeaponSwitch)ApplyColdSteelProfile(Profile);
}
