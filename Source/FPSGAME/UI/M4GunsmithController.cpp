#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "WeatherControlWidget.h"
#include "Engine/GameInstance.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
bool AFPSGAMEPlayerController::OpenGunsmith(const FString& Instance)
{
    if(GunsmithPanel)return false;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const FString Id=Instance.IsEmpty()?(P->Equipped()?P->Equipped()->InstanceId:TEXT("")):Instance;
    if(!G->Begin(Id))return false;
    UWidgetBlueprintLibrary::CancelDragDrop();
    if(WeatherPanel&&WeatherPanel->IsPanelOpen())WeatherPanel->SetPanelOpen(false);
    if(ColdSteelHUD){ColdSteelHUD->HideItemTooltip(true);if(ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();}
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->SuspendWeaponForMenu();
    GunsmithPanel=CreateWidget<UM4GunsmithWidget>(this);GunsmithPanel->AddToViewport(60);
    SetIgnoreMoveInput(true);SetIgnoreLookInput(true);bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(GunsmithPanel->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);SetInputMode(Mode);
    GunsmithPanel->SetKeyboardFocus();return true;
}
void AFPSGAMEPlayerController::CloseGunsmith()
{
    if(!GunsmithPanel)return;
    GunsmithPanel->SetAimPreview(false);GunsmithPanel->RemoveFromParent();GunsmithPanel=nullptr;
    GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Close();
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->ApplyColdSteelProfile(GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
    SetIgnoreMoveInput(false);SetIgnoreLookInput(false);bShowMouseCursor=false;SetInputMode(FInputModeGameOnly());
}
