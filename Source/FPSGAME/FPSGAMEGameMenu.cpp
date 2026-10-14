#include "FPSGAMEPlayerController.h"
#include "FPSGAMECharacter.h"
#include "UI/ColdSteelGameMenuWidget.h"
#include "UI/ColdSteelHUDWidget.h"
#include "UI/ColdSteelWoodworkingWidget.h"
#include "UI/TransitLoadingSubsystem.h"
#include "UI/WeatherControlWidget.h"
#include "Building/VoxelBuildComponent.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/AudioComponent.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"

bool AFPSGAMEPlayerController::IsGameMenuOpen() const
{
    return GameMenu && GameMenu->IsMenuOpen();
}

bool AFPSGAMEPlayerController::CanOpenGameMenu() const
{
    if (!IsLocalController() || !GetPawn() || IsGameMenuOpen()) return false;
    const auto* Loading = GetGameInstance() ? GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>() : nullptr;
    if (Loading && Loading->OwnsPlayerCursor()) return false;
    // Existing drawers, drags and stations keep their own close/back semantics.
    return !WoodworkingPanel && !ExpeditionPanel && !GunsmithPanel && !EnhancementPanel
        && (!WeatherPanel || !WeatherPanel->IsPanelOpen())
        && (!VoxelBuilder || !VoxelBuilder->IsPanelOpen())
        && (!ColdSteelHUD || (!ColdSteelHUD->IsInventoryOpen() && !ColdSteelHUD->IsQuickDragging()
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

void AFPSGAMEPlayerController::CloseGameMenu()
{
    if (!IsGameMenuOpen()) return;
    GameMenu->HideMenu();
    GameMenu->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    if (bGameMenuOwnsPause) { SetPause(false); bGameMenuOwnsPause = false; }
    if (bGameMenuOwnsInput)
    {
        SetIgnoreMoveInput(false);
        SetIgnoreLookInput(false);
        bGameMenuOwnsInput = false;
    }
    if (PlayerInput) PlayerInput->FlushPressedKeys();
    const auto* Loading = GetGameInstance() ? GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>() : nullptr;
    if (!Loading || !Loading->OwnsPlayerCursor())
    {
        bShowMouseCursor = false;
        SetInputMode(FInputModeGameOnly());
        UWidgetBlueprintLibrary::SetFocusToGameViewport();
    }
}

void AFPSGAMEPlayerController::SetHubMusicUserVolume(float Volume)
{
    if (HubMusic) HubMusic->SetVolumeMultiplier(.6f * FMath::Clamp(Volume, 0.f, 1.f));
}
