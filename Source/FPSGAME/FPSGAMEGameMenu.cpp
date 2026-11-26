#include "FPSGAMEPlayerController.h"
#include "FPSGAMECharacter.h"
#include "NPC/ChapelDialogueComponent.h"
#include "UI/ColdSteelGameMenuWidget.h"
#include "UI/ColdSteelHUDWidget.h"
#include "UI/StatusEffectsHUD.h"
#include "UI/ColdSteelWoodworkingWidget.h"
#include "UI/ColdSteelAlchemyWidget.h"
#include "UI/TransitLoadingSubsystem.h"
#include "UI/WeatherControlWidget.h"
#include "Building/VoxelBuildComponent.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/AudioComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"
#include "Widgets/SViewport.h"

bool AFPSGAMEPlayerController::IsGameMenuOpen() const
{
    return GameMenu && GameMenu->IsMenuOpen();
}

const FColdSteelMapMarkers* AFPSGAMEPlayerController::GetMapMarkers() const
{
    return GameMenu ? GameMenu->GetMapMarkers() : nullptr;
}

bool AFPSGAMEPlayerController::CanOpenGameMenu() const
{
    if (!IsLocalController() || !GetPawn() || IsGameMenuOpen() || (ChapelDialogue && ChapelDialogue->IsOpen())) return false;
    const auto* Loading = GetGameInstance() ? GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>() : nullptr;
    if (Loading && Loading->OwnsPlayerCursor()) return false;
    // Existing drawers, drags and stations keep their own close/back semantics.
    return !AlchemyPanel && !WoodworkingPanel && !ExpeditionPanel && !GunsmithPanel && !EnhancementPanel
        && (!WeatherPanel || !WeatherPanel->IsPanelOpen())
        && (!VoxelBuilder || !VoxelBuilder->IsPanelOpen())
        && (!ColdSteelHUD || (!ColdSteelHUD->IsInventoryOpen() && !ColdSteelHUD->IsExternalDrawerOpen() && !ColdSteelHUD->IsQuickDragging()
            && !ColdSteelHUD->IsWorldForging() && !ColdSteelHUD->IsGunAssembly()))
        && !UWidgetBlueprintLibrary::IsDragDropping();
}

void AFPSGAMEPlayerController::OpenGameMenu()
{
    if (!GameMenu || !CanOpenGameMenu()) return;
    if (auto* ControlledCharacter = Cast<AFPSGAMECharacter>(GetPawn())) ControlledCharacter->SuspendWeaponForMenu();
    if (ColdSteelHUD) ColdSteelHUD->HideItemTooltip(true);
    if (PlayerInput) PlayerInput->FlushPressedKeys();
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    bGameMenuOwnsInput = true;
    // A listen server must not pause everybody when its host opens a local menu.
    bGameMenuOwnsPause = GetNetMode() == NM_Standalone && !UGameplayStatics::IsGamePaused(this) && SetPause(true);
    GameMenu->SetVisibility(ESlateVisibility::Visible); // Also works when the scope hid the other HUDs.
    GameMenu->ShowMenu();
    bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(GameMenu->TakeWidget());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
    GameMenu->SetUserFocus(this);
}

void AFPSGAMEPlayerController::OpenWorldMap()
{
    if (!GameMenu || !CanOpenGameMenu() || IsMoveInputIgnored() || IsLookInputIgnored()) return;
    auto* MapCharacter=Cast<AFPSGAMECharacter>(GetPawn());
    if (!MapCharacter || MapCharacter->IsChoosingAmmo()) return;
    bMapReturnToCursor=IsCursorOnlyInteraction();
    if (bShowMouseCursor && !bMapReturnToCursor) return;
    MapCharacter->PrepareForPanelInput();
    if (ColdSteelHUD) ColdSteelHUD->HideItemTooltip(true);
    GameMenu->SetVisibility(ESlateVisibility::Visible);
    GameMenu->TakeWidget();
    GameMenu->ShowWorldMap();
    if (!GameMenu->IsWorldMapOpen()) return;
    if (auto* StatusHUD=GetWorld()->GetSubsystem<UStatusEffectsHUDSubsystem>()) StatusHUD->SetWorldMapOpen(true);
    if (ColdSteelHUD) ColdSteelHUD->SetWorldMapOpen(true);
    // Retire held weapon inputs as before, without releasing the movement keys.
    if (PlayerInput)
    {
        PlayerInput->FlushPressedActionBindingKeys(TEXT("Fire"));
        PlayerInput->FlushPressedActionBindingKeys(TEXT("Aim"));
        PlayerInput->FlushPressedActionBindingKeys(TEXT("Reload"));
    }
    bGameMenuOwnsInput=true;
    SetIgnoreLookInput(true);
    bShowMouseCursor=true;
    FInputModeGameAndUI Mode;
    if (auto* Viewport=GetWorld()->GetGameViewport()) Mode.SetWidgetToFocus(Viewport->GetGameViewportWidget());
    Mode.SetHideCursorDuringCapture(false);
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
}

void AFPSGAMEPlayerController::CloseGameMenu()
{
    if (!IsGameMenuOpen()) return;
    const bool bWasMap=GameMenu->IsWorldMapOpen();
    const bool bRestoreCursor=bWasMap && bMapReturnToCursor;
    bMapReturnToCursor=false;
    GameMenu->HideMenu();
    if (bWasMap)
    {
        if (auto* StatusHUD=GetWorld()->GetSubsystem<UStatusEffectsHUDSubsystem>()) StatusHUD->SetWorldMapOpen(false);
        if (ColdSteelHUD) ColdSteelHUD->SetWorldMapOpen(false);
    }
    GameMenu->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    if (bGameMenuOwnsPause) { SetPause(false); bGameMenuOwnsPause = false; }
    if (bGameMenuOwnsInput)
    {
        if (!bWasMap) SetIgnoreMoveInput(false);
        SetIgnoreLookInput(false);
        bGameMenuOwnsInput = false;
    }
    if (!bWasMap && PlayerInput) PlayerInput->FlushPressedKeys();
    const auto* Loading = GetGameInstance() ? GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>() : nullptr;
    if (!Loading || !Loading->OwnsPlayerCursor())
    {
        bShowMouseCursor = bRestoreCursor;
        if (bRestoreCursor)
        {
            FInputModeGameAndUI Mode;
            Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            Mode.SetHideCursorDuringCapture(false);
            SetInputMode(Mode);
        }
        else SetInputMode(FInputModeGameOnly());
        UWidgetBlueprintLibrary::SetFocusToGameViewport();
    }
}

void AFPSGAMEPlayerController::SetHubMusicUserVolume(float Volume)
{
    HubMusicUserVolume=FMath::Clamp(Volume,0.f,1.f);
    if (HubMusic) HubMusic->SetVolumeMultiplier(.6f*HubMusicUserVolume);
}
