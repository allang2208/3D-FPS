#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelAmmoWheel.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerInput.h"
#include "InputCoreTypes.h"

namespace
{
    /**
     * Turn/LookUp 收到的是经过轴灵敏度缩放后的鼠标轴值。DefaultInput.ini 里
     * MouseX/MouseY 的 Sensitivity 是 0.07，所以 1 个屏幕像素只产生 0.07 轴值；
     * 轮盘按像素定义手感，必须在输入层还原。灵敏度从玩家输入配置读取而不是写死，
     * 改轴配置之后轮盘不必跟着改；读不到时才退回引擎默认 0.07。
     */
    float MouseAxisToScreenPixels(const APlayerController* PC)
    {
        FInputAxisProperties Properties;
        const float Sensitivity = (PC && PC->PlayerInput &&
            PC->PlayerInput->GetAxisProperties(EKeys::MouseX, Properties) &&
            Properties.Sensitivity > KINDA_SMALL_NUMBER) ? Properties.Sensitivity : 0.07f;
        return 1.f / Sensitivity;
    }
}

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
        if(AmmoWheel)
        {
            // 双持手枪：左右两个圆盘同时弹出（左副手、右主手），复用步枪那套圆盘；
            // 两盘共用一根自由指针，鼠标移到哪个盘里就改哪只手的弹种，不需要再点键选手。
            if(IsDualWieldingPistols())AmmoWheel->OpenForDualPistols(DualPistols->Hand(0).Item.InstanceId,DualPistols->Hand(1).Item.InstanceId);
            else AmmoWheel->OpenForWeapon(AmmoSelectionWeapon);
            AmmoWheel->AddToViewport(45);
            // 两把枪都取不到物品时没有盘可画，直接当作取消。
            if(!AmmoWheel->HasDiscs())CancelAmmoSelection();
        }
        else CancelAmmoSelection();
    }
}
void AFPSGAMECharacter::MoveAmmoPointer(FVector2D Delta)
{
    // 轴值 → 屏幕像素；轮盘内部再按 fps.AmmoWheel.PixelsPerRadius 换算成半径比例。
    // MouseY 的 Scale=-1 已体现在传入值里，这里只换算单位，不翻转方向。
    if(AmmoWheel)AmmoWheel->MovePointer(Delta*MouseAxisToScreenPixels(Cast<APlayerController>(Controller)));
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
