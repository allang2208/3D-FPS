#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "WeatherControlWidget.h"
#include "Engine/GameInstance.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
bool AFPSGAMEPlayerController::OpenEnhancement(const FString& Id)
{
    if(EnhancementPanel)return false;if(GunsmithPanel)CloseGunsmith();
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    FString Selected=Id;if(Selected.IsEmpty()&&P->Equipped())Selected=P->Equipped()->InstanceId;
    UWidgetBlueprintLibrary::CancelDragDrop();bEnhancementReturnToInventory=ColdSteelHUD&&ColdSteelHUD->IsInventoryOpen();
    if(WeatherPanel&&WeatherPanel->IsPanelOpen())WeatherPanel->SetPanelOpen(false);
    if(ColdSteelHUD){ColdSteelHUD->HideItemTooltip(true);if(ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();}
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->SuspendWeaponForMenu();
    EnhancementPanel=CreateWidget<UColdSteelEnhancementWidget>(this);EnhancementPanel->SelectItem(Selected);EnhancementPanel->AddToViewport(60);
    SetIgnoreMoveInput(true);SetIgnoreLookInput(true);bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(EnhancementPanel->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);SetInputMode(Mode);EnhancementPanel->SetKeyboardFocus();return true;
}
void AFPSGAMEPlayerController::CloseEnhancement()
{
    if(!EnhancementPanel)return;EnhancementPanel->RemoveFromParent();EnhancementPanel=nullptr;
    SetIgnoreMoveInput(false);SetIgnoreLookInput(false);bShowMouseCursor=false;SetInputMode(FInputModeGameOnly());
    if(bEnhancementReturnToInventory&&ColdSteelHUD&&!ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();bEnhancementReturnToInventory=false;
}
