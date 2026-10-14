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
    const FString& DestinationMap() const {return Destination;}
    const FString& TravelOptions() const {return DestinationOptions;}
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UFUNCTION() void OnRep_Destination();
    bool IsWithinInteractionRange(const APawn* Pawn) const;
    /** 0 = wait for pawn, 1 = installed or already present, 2 = skip this map. */
    static int32 InstallHillsLink(UWorld* World);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void UsePortal();
    void CancelLoading();
    void FinishLoading();
    void OpenDestination();
    UPROPERTY() TObjectPtr<UTextRenderComponent> Sign;
    UPROPERTY(ReplicatedUsing=OnRep_Destination) FString Destination;
    UPROPERTY(Replicated) FString DestinationOptions;
    UPROPERTY(ReplicatedUsing=OnRep_Destination) FString DestinationLabel;
    TSharedPtr<FStreamableHandle> PreloadHandle;
    FTimerHandle DungeonTravelTimer;
    bool bTravelling = false;
};
