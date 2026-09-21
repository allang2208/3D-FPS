#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelAmmoWheel.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"

void AFPSGAMECharacter::ReloadInputPressed()
{
    if(bReloadInputHeld||IsAmmoWheelOpen())return;
    const auto* PC=Cast<APlayerController>(Controller);
    if(!PC||PC->bShowMouseCursor||AFPSGAMEPlayerController::BlocksOngoingActions(PC))return;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Gun=Model?Model->Equipped():nullptr;
    const auto* Off=Model&&IsDualWieldingPistols()?Model->Equipped(Gun&&Gun->Cell==6?8:11):nullptr;
    if(!Gun||!bInventoryWeaponReady)return;
    if(Model->CompatibleAmmo(*Gun).Num()<=1&&(!Off||Model->CompatibleAmmo(*Off).Num()<=1)){ReloadPressed();return;}
    if(IsWeaponBusy()||IsCastBlockingLeftHandAction()||IsTraversing())return;
    bReloadInputHeld=true;ReloadInputStarted=GetWorld()->GetTimeSeconds();AmmoSelectionWeapon=Gun->InstanceId;
}
void AFPSGAMECharacter::UpdateAmmoSelection()
{
    if(!IsChoosingAmmo())return;
    const auto* PC=Cast<APlayerController>(Controller);
    const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const bool Focused=!FSlateApplication::IsInitialized()||FSlateApplication::Get().IsActive();
    if(!PC||PC->bShowMouseCursor||AFPSGAMEPlayerController::BlocksOngoingActions(PC)||!Focused||
        (Health&&Health->IsDead())||IsTraversing()||IsWeaponBusy()||IsCastBlockingLeftHandAction()||
        !Model||!Model->Equipped()||Model->Equipped()->InstanceId!=AmmoSelectionWeapon)
    {CancelAmmoSelection();return;}
    if(bReloadInputHeld&&!AmmoWheel&&GetWorld()->GetTimeSeconds()-ReloadInputStarted>=.30)
    {
        FireReleased();AimReleased();if(DualPistols)DualPistols->CancelInputs();
        AmmoWheel=CreateWidget<UColdSteelAmmoWheel>(Cast<APlayerController>(Controller));
        if(AmmoWheel){AmmoWheel->OpenForWeapon(AmmoSelectionWeapon,IsDualWieldingPistols()?0:-1);AmmoWheel->AddToViewport(45);}
        else CancelAmmoSelection();
    }
}
void AFPSGAMECharacter::MoveAmmoPointer(FVector2D Delta)
{if(AmmoWheel)AmmoWheel->MovePointer(Delta);}
void AFPSGAMECharacter::SelectAmmoWheelHand(int32 Hand)
{
    if(!AmmoWheel||!IsDualWieldingPistols()||Hand<0||Hand>1)return;
    AmmoWheel->OpenForWeapon(DualPistols->Hand(Hand).Item.InstanceId,Hand);
}
void AFPSGAMECharacter::ReloadInputReleased()
{
    if(AmmoWheel)
    {
        const FString Id=AmmoWheel->WeaponId(),Target=AmmoWheel->SelectedAmmo();
        CancelAmmoSelection();if(!Target.IsEmpty())StartAmmoSwitch(Id,Target);
        return;
    }
    if(bReloadInputHeld){CancelAmmoSelection();ReloadPressed();}
}
void AFPSGAMECharacter::CancelAmmoSelection()
{
    bReloadInputHeld=false;AmmoSelectionWeapon.Reset();LookInput=FVector2D::ZeroVector;
    if(AmmoWheel){AmmoWheel->RemoveFromParent();AmmoWheel=nullptr;}
}
bool AFPSGAMECharacter::StartAmmoSwitch(const FString& WeaponId,const FString& Target)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* PC=Cast<APlayerController>(Controller);
    if(!bInventoryWeaponReady||!Model||!Model->CanSwitchAmmo(WeaponId,Target)||!PC||
        AFPSGAMEPlayerController::BlocksOngoingActions(PC)||IsWeaponBusy()||IsCastBlockingLeftHandAction()||IsTraversing())return false;
    if(IsDualWieldingPistols())return DualPistols->SwitchAmmo(WeaponId,Target);
    if(ActiveInventoryWeapon!=WeaponId)return false;
    PendingAmmoType=Target;PendingAmmoWeapon=WeaponId;
    FireReleased();ReloadPressed();
    if(!IsReloading()){PendingAmmoType.Reset();PendingAmmoWeapon.Reset();return false;}
    return true;
}
