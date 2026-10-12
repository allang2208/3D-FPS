#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonThemeEncounter.generated.h"

class UDungeonRunSubsystem;
class AAuthoredDungeonGenerator;
class ADungeonRoomGate;
struct FDungeonRunDoor;

/** One combat area spans several rooms. Room spawners own kills; this owns exit gates. */
UCLASS(NotBlueprintable, Transient)
class FPSGAME_API ADungeonThemeEncounter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonThemeEncounter();
    bool Configure(UDungeonRunSubsystem* InRun, AAuthoredDungeonGenerator* InGenerator,
        const TArray<int32>& InRooms, const TArray<FDungeonRunDoor>& Exits);
    bool HasStarted() const { return bStarted; }
    APawn* PlayerInArea() const;
    bool ContainsLocation(const FVector& Location) const;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    void UpdateEncounter();
    UFUNCTION() void DungeonDestroyed(AActor* Actor);
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    TArray<int32> Rooms;
    UPROPERTY(Transient) TArray<TObjectPtr<ADungeonRoomGate>> Gates;
    FTimerHandle EncounterTimer;
    float OpenFraction = 1.f;
    bool bStarted = false, bCleared = false;
};
