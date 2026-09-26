#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SceneTestPortal.generated.h"

class UTextRenderComponent;
struct FStreamableHandle;

    /** Travel actor for the hills hub door and authored dungeon return doors. */
UCLASS()
class FPSGAME_API ASceneTestPortal : public AActor
{
    GENERATED_BODY()
public:
    ASceneTestPortal();
    void Configure(const FString& Map, const FString& Label, const FString& Options = FString(), FColor Color = FColor::Cyan);
    bool IsWithinInteractionRange(const APawn* Pawn) const;
    /** 0 = wait for pawn, 1 = installed or already present, 2 = skip this map. */
    static int32 InstallHillsLink(UWorld* World);
    /** Two-way link between the main hub and the Clearwater water test level. */
    static int32 InstallWaterLink(UWorld* World);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void UsePortal();
    void CancelLoading();
    void FinishLoading();
    void OpenDestination();
    UPROPERTY() TObjectPtr<UTextRenderComponent> Sign;
    UPROPERTY() FString Destination;
    UPROPERTY() FString DestinationOptions;
    FString DestinationLabel;
    TSharedPtr<FStreamableHandle> PreloadHandle;
    FTimerHandle DungeonTravelTimer;
    bool bTravelling = false;
};
