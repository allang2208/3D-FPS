#pragma once

#include "CoreMinimal.h"
#include "Layout/Visibility.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelDialogueViewport.generated.h"

class SOverlay;
class SViewport;
class SWidget;
class UUserWidget;
class AHUD;

/** A conversation occupies its game viewport while the ordinary game UI stays mounted. */
UCLASS()
class FPSGAME_API UColdSteelDialogueViewport : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    bool Show(UUserWidget* Screen);
    void Hide(const UUserWidget* Screen);
    virtual void Deinitialize() override;

private:
    void ReleaseLayer();

    TWeakObjectPtr<UUserWidget> ActiveScreen;
    TWeakObjectPtr<AHUD> SceneHUD;
    bool bPreviousShowHUD = false;
    TWeakPtr<SViewport> Viewport;
    TWeakPtr<SWidget> GameLayers;
    TWeakPtr<SOverlay> Host;
    TSharedPtr<SWidget> DialogueLayer;
    EVisibility PreviousVisibility = EVisibility::SelfHitTestInvisible;
    bool bCreatedHost = false;
};
