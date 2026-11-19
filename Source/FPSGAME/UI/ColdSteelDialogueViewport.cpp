#include "ColdSteelDialogueViewport.h"

#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/SlateUser.h"
#include "Slate/SGameLayerManager.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SViewport.h"

bool UColdSteelDialogueViewport::Show(UUserWidget* Screen)
{
    if (!IsValid(Screen))
        return false;
    if (DialogueLayer)
        return ActiveScreen.Get() == Screen;

    UWorld* World = Screen->GetWorld();
    UGameViewportClient* Client = World ? World->GetGameViewport() : nullptr;
    if (!Client || !Client->GetGameLayerManager())
        return false;

    TSharedPtr<SViewport> Scene = Client->GetGameViewportWidget();
    TSharedRef<SWidget> Layers = Client->GetGameLayerManager()->AsWidget();
    if (!Scene)
        return false;

    TSharedPtr<SOverlay> Overlay;
    if (Scene->GetContent() == Layers)
    {
        // Standalone normally mounts the game layer manager directly on the viewport.
        Overlay = SNew(SOverlay);
        Scene->SetContent(Overlay);
        Overlay->AddSlot(0)[Layers];
        bCreatedHost = true;
    }
    else
    {
        // An embedded viewport already has an overlay that also belongs to the editor.
        TSharedPtr<SWidget> Content = Scene->GetContent();
        if (!Content || Content != Layers->GetParentWidget()
            || Content->GetWidgetClass().GetWidgetType() != SOverlay::StaticWidgetClass().GetWidgetType())
            return false;
        Overlay = StaticCastSharedPtr<SOverlay>(Content);
    }

    Viewport = Scene;
    GameLayers = Layers;
    Host = Overlay;
    ActiveScreen = Screen;
    PreviousVisibility = Layers->GetVisibility();

    // Match the game's resolution-based UI scale outside SGameLayerManager.
    TWeakObjectPtr<UGameViewportClient> WeakClient = Client;
    DialogueLayer = SNew(SDPIScaler)
        .DPIScale_Lambda([WeakClient, WeakScene = Viewport]()
        {
            const TSharedPtr<SViewport> LocalScene = WeakScene.Pin();
            if (const UGameViewportClient* LocalClient = WeakClient.Get(); LocalClient && LocalScene)
            {
                const float PlatformScale = LocalScene->GetTickSpaceGeometry().GetAccumulatedLayoutTransform().GetScale();
                return UWidgetLayoutLibrary::GetViewportScale(LocalClient) / FMath::Max(PlatformScale, UE_SMALL_NUMBER);
            }
            return 1.f;
        })
        [Screen->TakeWidget()];
    Overlay->AddSlot()[DialogueLayer.ToSharedRef()];
    Layers->SetVisibility(EVisibility::Collapsed);
    if (APlayerController* PC = Screen->GetOwningPlayer())
    {
        SceneHUD = PC->GetHUD();
        if (AHUD* HUD = SceneHUD.Get())
        {
            bPreviousShowHUD = HUD->bShowHUD;
            HUD->bShowHUD = false;
        }
    }
    if (ULocalPlayer* Player = Screen->GetOwningLocalPlayer())
    {
        if (TSharedPtr<FSlateUser> User = Player->GetSlateUser())
        {
            User->CloseTooltip();
            User->ReleaseAllCapture();
        }
    }
    return true;
}

void UColdSteelDialogueViewport::Hide(const UUserWidget* Screen)
{
    if (Screen && ActiveScreen.Get() == Screen)
        ReleaseLayer();
}

void UColdSteelDialogueViewport::ReleaseLayer()
{
    TSharedPtr<SOverlay> Overlay = Host.Pin();
    TSharedPtr<SWidget> Layers = GameLayers.Pin();
    if (Overlay && DialogueLayer)
        Overlay->RemoveSlot(DialogueLayer.ToSharedRef());
    if (Layers)
        Layers->SetVisibility(PreviousVisibility);
    if (AHUD* HUD = SceneHUD.Get())
        HUD->bShowHUD = bPreviousShowHUD;
    SceneHUD.Reset();

    // Travel or PIE teardown may have detached/rebound the viewport in the meantime.
    if (bCreatedHost && Overlay && Layers && Layers->GetParentWidget() == Overlay
        && Overlay->GetNumWidgets() == 1)
    {
        if (TSharedPtr<SViewport> Scene = Viewport.Pin(); Scene && Scene->GetContent() == Overlay)
        {
            Overlay->RemoveSlot(Layers.ToSharedRef());
            Scene->SetContent(Layers);
        }
    }
    ActiveScreen.Reset();
    DialogueLayer.Reset();
    Host.Reset();
    GameLayers.Reset();
    Viewport.Reset();
    bCreatedHost = false;
}

void UColdSteelDialogueViewport::Deinitialize()
{
    ReleaseLayer();
    Super::Deinitialize();
}
