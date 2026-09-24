#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Building/VoxelBuildComponent.h"
#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelWorldInteraction.h"
#include "WeatherControlWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"

bool AFPSGAMEPlayerController::OpenExpedition()
{
    if (ExpeditionPanel || !IsLocalController()) return false;
    if (!ColdSteelWorldInteraction::IsExpeditionAltar(ColdSteelWorldInteraction::TraceTarget(this))) return false;
    CloseGunsmith();
    CloseEnhancement();
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) WeatherPanel->SetPanelOpen(false);
    if (VoxelBuilder && VoxelBuilder->IsPanelOpen()) VoxelBuilder->ClosePanel();

    auto* Panel = CreateWidget<UColdSteelExpeditionWidget>(this);
    if (!Panel) return false;
    bExpeditionReturnToInventory = ColdSteelHUD && ColdSteelHUD->IsInventoryOpen();
    bExpeditionReturnToCursor = bShowMouseCursor && !bExpeditionReturnToInventory;
    UWidgetBlueprintLibrary::CancelDragDrop();
    if (ColdSteelHUD)
    {
        ColdSteelHUD->CancelQuickDrag();
        ColdSteelHUD->HideItemTooltip(true);
        if (bExpeditionReturnToInventory) ColdSteelHUD->ToggleInventory();
        ColdSteelHUD->SetExternalDrawerOpen(true);
    }
    if (auto* PawnCharacter = Cast<AFPSGAMECharacter>(GetPawn())) PawnCharacter->SuspendWeaponForMenu();

    // One presentation card for the UE project's existing underground-facility art direction.
    // No legacy dungeon records, inferred eligibility, travel, reward table or costs are imported.
    FColdSteelExpeditionDestination Facility;
    Facility.Id = TEXT("industrial_facility");
    Facility.Name = TEXT("地下设施");
    Facility.Category = TEXT("地牢 / 地下探索");
    Facility.Description = TEXT("深入废弃的地下设施。工业通道连接遗迹与异常区域，封闭空间中仍有未知的威胁等待揭晓。");
    Facility.BlockReason = TEXT("当前目的地暂未开放出征");
    TArray<FColdSteelExpeditionDestination> Entries;
    Entries.Add(MoveTemp(Facility));
    Panel->SetDestinations(MoveTemp(Entries));
    ExpeditionPanel = Panel;
    Panel->AddToPlayerScreen(60);
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(Panel->TakeWidget());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
    Panel->SetKeyboardFocus();
    return true;
}

void AFPSGAMEPlayerController::CloseExpedition()
{
    if (!ExpeditionPanel) return;
    ExpeditionPanel->RemoveFromParent();
    ExpeditionPanel = nullptr;
    if (ColdSteelHUD) ColdSteelHUD->SetExternalDrawerOpen(false);
    // Release only the input locks added by OpenExpedition; do not reset other owners' counters.
    SetIgnoreMoveInput(false);
    SetIgnoreLookInput(false);
    bShowMouseCursor = bExpeditionReturnToCursor;
    if (bExpeditionReturnToCursor)
    {
        FInputModeGameAndUI Mode;
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        Mode.SetHideCursorDuringCapture(false);
        SetInputMode(Mode);
    }
    else SetInputMode(FInputModeGameOnly());
    if (bExpeditionReturnToInventory && ColdSteelHUD && !ColdSteelHUD->IsInventoryOpen()) ColdSteelHUD->ToggleInventory();
    bExpeditionReturnToInventory = false;
    bExpeditionReturnToCursor = false;
}
