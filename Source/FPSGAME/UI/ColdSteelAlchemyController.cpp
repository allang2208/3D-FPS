#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Building/AlchemySystem.h"
#include "ColdSteelAlchemyWidget.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "WeatherControlWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"

bool AFPSGAMEPlayerController::OpenAlchemy(AActor* Station)
{
    if(!IsLocalController()||!GetWorld()||!GetPawn()||IsMoveInputIgnored()||IsLookInputIgnored()
        ||AlchemyPanel||WoodworkingPanel||GunsmithPanel||EnhancementPanel||ExpeditionPanel
        ||(ColdSteelHUD&&(ColdSteelHUD->IsWorldForging()||ColdSteelHUD->IsGunAssembly())))return false;
    if(!ColdSteelWorldInteraction::IsAlchemyBench(Station)||ColdSteelWorldInteraction::TraceTarget(this)!=Station)return false;
    bAlchemyReturnToCursor=IsCursorOnlyInteraction();UWidgetBlueprintLibrary::CancelDragDrop();
    if(WeatherPanel&&WeatherPanel->IsPanelOpen())WeatherPanel->SetPanelOpen(false);
    if(VoxelBuilder&&VoxelBuilder->IsPanelOpen())VoxelBuilder->ClosePanel();
    if(ColdSteelHUD){ColdSteelHUD->CancelQuickDrag();ColdSteelHUD->HideItemTooltip(true);if(ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();}
    AlchemyPanel=CreateWidget<UColdSteelAlchemyWidget>(this);
    if(!AlchemyPanel||!AlchemyPanel->Configure(Station)){if(AlchemyPanel)AlchemyPanel->EndSession();AlchemyPanel=nullptr;bAlchemyReturnToCursor=false;return false;}
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn())){C->SuspendWeaponForMenu();if(auto* Movement=C->GetCharacterMovement())Movement->StopMovementImmediately();}
    AlchemyPanel->SetVisibility(ESlateVisibility::SelfHitTestInvisible);AlchemyPanel->AddToViewport(60);
    if(ColdSteelHUD)ColdSteelHUD->SetAlchemyManagement(true);
    FlushPressedKeys();SetIgnoreMoveInput(true);SetIgnoreLookInput(true);bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(AlchemyPanel->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);SetInputMode(Mode);
    AlchemyPanel->SetKeyboardFocus();return true;
}
bool AFPSGAMEPlayerController::IsAlchemyPanelUnderLocation(FVector2D ScreenPosition) const
{return AlchemyPanel&&AlchemyPanel->ContainsManagement(ScreenPosition);}
void AFPSGAMEPlayerController::CloseAlchemy()
{
    if(!AlchemyPanel)return;
    if(auto* System=GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>();System&&(System->Pending()||System->Active())){AlchemyPanel->RequestClose();return;}
    auto* Closing=AlchemyPanel.Get();AlchemyPanel=nullptr;Closing->EndSession();Closing->RemoveFromParent();
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->ApplyColdSteelProfile(GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
    FlushPressedKeys();SetIgnoreMoveInput(false);SetIgnoreLookInput(false);bShowMouseCursor=bAlchemyReturnToCursor;
    if(bAlchemyReturnToCursor){FInputModeGameAndUI Mode;Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);Mode.SetHideCursorDuringCapture(false);SetInputMode(Mode);}
    else SetInputMode(FInputModeGameOnly());bAlchemyReturnToCursor=false;
}
void UColdSteelHUDWidget::SetAlchemyManagement(bool Open)
{
    if(bAlchemyManagement==Open&&bInventoryOpen==Open)return;
    if(Open){HideForgingInstantly();HideWorkbenchInstantly();HideSmeltingInstantly();CloseWarehouse();CloseShop();SetInventoryTab(false);}
    bAlchemyManagement=Open;TGuardValue<bool> Guard(bAlchemyInventoryTransition,true);SetInventoryOpen(Open);
}
