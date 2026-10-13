#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelWoodworkingWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "WeatherControlWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

bool AFPSGAMEPlayerController::OpenWoodworking(AActor* Station,bool PracticeOnly)
{
    if(PracticeOnly)return false;
    if(!IsLocalController()||!GetWorld()||!GetPawn()||IsMoveInputIgnored()||IsLookInputIgnored()
        ||WoodworkingPanel||GunsmithPanel||EnhancementPanel||ExpeditionPanel
        ||(ColdSteelHUD&&(ColdSteelHUD->IsWorldForging()||ColdSteelHUD->IsGunAssembly())))return false;
    if(!PracticeOnly)
    {
        if(!ColdSteelWorldInteraction::IsWoodworkingBench(Station)||ColdSteelWorldInteraction::TraceTarget(this)!=Station)return false;
        const auto* Piece=Cast<AVoxelBuildPrefabActor>(Station);
        const auto* BuildWorld=Cast<AVoxelBuildWorld>(Piece->GetOwner());
        if(!BuildWorld||!BuildWorld->HasPrefabAt(Piece->AnchorCell()))return false;
    }
    bWoodworkingReturnToCursor=IsCursorOnlyInteraction();
    UWidgetBlueprintLibrary::CancelDragDrop();
    if(WeatherPanel&&WeatherPanel->IsPanelOpen())WeatherPanel->SetPanelOpen(false);
    if(VoxelBuilder&&VoxelBuilder->IsPanelOpen())VoxelBuilder->ClosePanel();
    if(ColdSteelHUD){ColdSteelHUD->CancelQuickDrag();ColdSteelHUD->HideItemTooltip(true);if(ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();}
    if(auto* PlayerCharacter=Cast<AFPSGAMECharacter>(GetPawn()))PlayerCharacter->SuspendWeaponForMenu();
    WoodworkingPanel=CreateWidget<UColdSteelWoodworkingWidget>(this);
    if(!WoodworkingPanel)return false;
    if(!WoodworkingPanel->Configure(Station,PracticeOnly))
    {
        WoodworkingPanel=nullptr;
        if(auto* PlayerCharacter=Cast<AFPSGAMECharacter>(GetPawn()))PlayerCharacter->ApplyColdSteelProfile(GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
        bWoodworkingReturnToCursor=false;return false;
    }
    if(auto* PlayerCharacter=Cast<AFPSGAMECharacter>(GetPawn()))if(auto* Movement=PlayerCharacter->GetCharacterMovement())Movement->StopMovementImmediately();
    WoodworkingPanel->SetVisibility(ESlateVisibility::SelfHitTestInvisible);WoodworkingPanel->AddToViewport(60);
    if(ColdSteelHUD)ColdSteelHUD->SetWoodworkingManagement(true);
    FlushPressedKeys();SetIgnoreMoveInput(true);SetIgnoreLookInput(true);bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(WoodworkingPanel->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);SetInputMode(Mode);
    WoodworkingPanel->SetKeyboardFocus();return true;
}
void AFPSGAMEPlayerController::CloseWoodworking()
{
    if(!WoodworkingPanel)return;
    if(WoodworkingPanel->BeginAnimatedClose())return;
    auto* Closing=WoodworkingPanel.Get();WoodworkingPanel=nullptr;Closing->EndSession();Closing->RemoveFromParent();
    if(auto* PlayerCharacter=Cast<AFPSGAMECharacter>(GetPawn()))PlayerCharacter->ApplyColdSteelProfile(GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
    FlushPressedKeys();SetIgnoreMoveInput(false);SetIgnoreLookInput(false);bShowMouseCursor=bWoodworkingReturnToCursor;
    if(bWoodworkingReturnToCursor)
    {
        FInputModeGameAndUI Mode;Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);Mode.SetHideCursorDuringCapture(false);SetInputMode(Mode);
    }
    else SetInputMode(FInputModeGameOnly());
    bWoodworkingReturnToCursor=false;
}

void UColdSteelHUDWidget::SetWoodworkingManagement(bool Open)
{
    if(bWoodworkingManagement==Open&&bInventoryOpen==Open)return;
    if(Open){HideForgingInstantly();HideWorkbenchInstantly();HideSmeltingInstantly();CloseWarehouse();CloseShop();SetInventoryTab(false);}
    bWoodworkingManagement=Open;
    // The woodworking controller owns input until the whole two-stage session closes.
    TGuardValue<bool> Guard(bWoodworkingInventoryTransition,true);SetInventoryOpen(Open);
}
void UColdSteelHUDWidget::SetWoodworkingDrawerOpen(bool Open)
{
    // Keep the paired layout until the whole woodworking drawer has slid away.
    TGuardValue<bool> Guard(bWoodworkingInventoryTransition,true);SetInventoryOpen(Open);
}
