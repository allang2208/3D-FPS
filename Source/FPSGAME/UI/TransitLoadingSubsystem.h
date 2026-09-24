#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "TransitLoadingSubsystem.generated.h"

struct FStreamableHandle;
struct FTransitLoadingView;
class UGameViewportClient;
class APlayerController;
class ACharacter;
class FGameResourcePreparation;
struct FStartupLoadingView;

/** Owns the transition UI across map teardown and the destination's preparation phase. */
UCLASS()
class FPSGAME_API UTransitLoadingSubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual bool IsTickable() const override;
    virtual bool IsTickableWhenPaused() const override { return true; }
    virtual UWorld* GetTickableGameObjectWorld() const override { return GetWorld(); }

    void BeginTransition(const FString& Map, FSimpleDelegate OnCancel = FSimpleDelegate());
    void UpdatePreparation(const FText& Status, float Progress);
    void BeginDungeonPreparation();
    void CompletePreparation();
    void FailPreparation(const FText& Reason);
    void CancelTransition();
    void RetainBiomeResources(const TArray<TSharedPtr<FStreamableHandle>>& Handles);
    void ShowStartupMenu(APlayerController* Controller);
    bool IsCompletePreloadSelected() const { return bCompletePreload; }

private:
    void BeforeMap(const FString& Map);
    void AfterMap(UWorld* World);
    void AttachOverlay();
    void RemoveOverlay();
    TSharedPtr<FTransitLoadingView> View;
    TSharedPtr<SWidget> Overlay;
    TWeakObjectPtr<UGameViewportClient> AttachedViewport;
    TWeakObjectPtr<APlayerController> CursorController;
    TArray<TSharedPtr<FStreamableHandle>> BiomeHandles;
    FSimpleDelegate CancelAction;
    FDelegateHandle PreMapHandle;
    FDelegateHandle PostMapHandle;
    double StartedAt = 0;
    double FinishedAt = 0;
    bool bMapLoading = false;
    bool bDestinationLoaded = false;
    bool bDungeon=false;
    bool bHills = false;
    bool bPreviousIgnoreInput = false;
    bool bPreviousCursor = false;
    void ChooseLoadingMode(bool Complete);
    void RemoveStartupMenu();
    void ApplyLoadingBudget();
    void RestoreLoadingBudget();
    void FinishPreparation();
    void HoldPreparedPlayer();
    void ReleasePreparedPlayer();
    void RetryResources();
    TSharedPtr<FStartupLoadingView> StartupView;
    TSharedPtr<SWidget> StartupOverlay;
    TWeakObjectPtr<UGameViewportClient> StartupViewport;
    TWeakObjectPtr<APlayerController> StartupController;
    TWeakObjectPtr<ACharacter> PreparedPlayer;
    TSharedPtr<FGameResourcePreparation> ResourcePreparation;
    bool bStartupChosen = false;
    bool bCompletePreload = false;
    bool bStartupPausedWorld = false;
    bool bStartupPreviousIgnore = false;
    bool bStartupPreviousCursor = false;
    bool bScenePrepared = false;
    bool bPreparationFailed = false;
    bool bPlayerPreviouslyDamageable = true;
    bool bPlayerMovementTicked = false;
    bool bBudgetApplied = false;
    int32 OriginalPoolSize = -1;
    int32 AppliedPoolSize = -1;
};
