#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "WeatherControlWidget.h"
#include "Engine/GameInstance.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Misc/ConfigCacheIni.h"

namespace
{
FString GunsmithNavigationSection(const UColdSteelStatusModel& Profile)
{
    return TEXT("FPSGAME.Gunsmith.Navigation.")+Profile.ProfileSlot();
}
}

bool AFPSGAMEPlayerController::OpenGunsmith(const FString& Instance)
{
    CloseExpedition();
    if(EnhancementPanel)CloseEnhancement();
    if(GunsmithPanel)return false;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const FString Id=Instance.IsEmpty()?(P->Equipped()?P->Equipped()->InstanceId:TEXT("")):Instance;
    if(!G->Begin(Id))return false;
    UWidgetBlueprintLibrary::CancelDragDrop();
    if(WeatherPanel&&WeatherPanel->IsPanelOpen())WeatherPanel->SetPanelOpen(false);
    if(ColdSteelHUD){ColdSteelHUD->HideItemTooltip(true);if(ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();}
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->SuspendWeaponForMenu();
    GunsmithPanel=CreateWidget<UM4GunsmithWidget>(this);
    // RebuildWidget resolves a missing or unavailable category to the first
    // available row. Navigation belongs to this profile and inventory instance.
    GConfig->GetString(*GunsmithNavigationSection(*P),*Id,GunsmithPanel->SelectedCategory,GGameUserSettingsIni);
    GunsmithPanel->AddToViewport(60);
    SetIgnoreMoveInput(true);SetIgnoreLookInput(true);bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(GunsmithPanel->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);SetInputMode(Mode);
    GunsmithPanel->SetKeyboardFocus();return true;
}
void AFPSGAMEPlayerController::CloseGunsmith()
{
    if(!GunsmithPanel)return;
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    // Capture before widget teardown and Close() clear the active instance.
    // This stores only the viewed category; unapplied part drafts remain transient.
    if(!G->Instance().IsEmpty()&&GunsmithPanel->IsCategoryAvailable(GunsmithPanel->SelectedCategory))
    {
        GConfig->SetString(*GunsmithNavigationSection(*P),*G->Instance(),*GunsmithPanel->SelectedCategory,GGameUserSettingsIni);
        GConfig->Flush(false,GGameUserSettingsIni);
    }
    GunsmithPanel->SetAimPreview(false);GunsmithPanel->RemoveFromParent();GunsmithPanel=nullptr;
    G->Close();
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->ApplyColdSteelProfile(GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
    SetIgnoreMoveInput(false);SetIgnoreLookInput(false);bShowMouseCursor=false;SetInputMode(FInputModeGameOnly());
}
