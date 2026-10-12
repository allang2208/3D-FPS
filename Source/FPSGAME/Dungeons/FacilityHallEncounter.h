#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonRunSubsystem.h"
#include "FacilityHallEncounter.generated.h"

class ACharacter;
class AStaticMeshActor;

struct FFacilityHallSlot
{
    TWeakObjectPtr<ACharacter> Monster;
    int32 Member = 0;
    /** Four fixed first-wave additions: 0/1 ground floor, 2/3 upper floor. */
    int32 BellowPosition = INDEX_NONE;
    bool bDefeated = false;
};

struct FFacilityHallDoor
{
    FString Id;
    TWeakObjectPtr<AStaticMeshActor> Left, Right;
    FTransform ClosedLeft, ClosedRight;
    FVector FloorCenter = FVector::ZeroVector;
    FVector Inward = FVector::ForwardVector;
    float OpenAlpha = 0.f;
    bool bWantOpen = false;
    double NextSpawnAt = 0.;
};

/** Two staff waves plus four first-wave Bellow M-09 in one facility hall. */
UCLASS(NotBlueprintable, Transient)
class FPSGAME_API AFacilityHallEncounter : public AActor
{
    GENERATED_BODY()
public:
    AFacilityHallEncounter();
    static bool IsHall(const FString& Module);
    static bool IsDoorLeaf(const FString& Module, const FString& Mesh);
    static TArray<FString> MonsterClassPaths();
    static TArray<FString> PreparationAssetPaths();
    void Configure(UDungeonRunSubsystem* InRun, int32 InNode, AAuthoredDungeonGenerator* InGenerator, class ADungeonThemeEncounter* InTheme);
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    friend class UFacilityHallSpawnSubsystem;
    void UpdateEncounter();
    bool TrySpawnPendingSlot();
    bool SpawnSlot(int32 SlotIndex);
    bool FindSpawn(const ACharacter* Defaults, const FVector& Candidate, FVector& Location) const;
    bool FindInitialSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void RecordDefeat(AActor* Monster);
    bool DoorOccupied(const FFacilityHallDoor& Door) const;
    void ApplyDoorPose(FFacilityHallDoor& Door);
    APawn* PlayerInHall() const;
    UFUNCTION() void MonsterDamaged(AActor* Actor, float Damage, const UDamageType* DamageType,
        AController* EventInstigator, AActor* Causer);
    UFUNCTION() void MonsterDestroyed(AActor* Actor);
    UFUNCTION() void DungeonDestroyed(AActor* Actor);

    UPROPERTY(Transient) TArray<TSubclassOf<ACharacter>> Members;
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    TWeakObjectPtr<class ADungeonThemeEncounter> Theme;
    FDungeonRunNode Room;
    TArray<FFacilityHallSlot> Slots;
    TArray<FFacilityHallDoor> Doors;
    FRandomStream Placement;
    FTimerHandle EncounterTimer;
    int32 FirstWaveCount = 0;
    int32 FirstWaveKills = 0;
    int32 NextDoor = 0;
    int32 NextSlot = 0;
    bool bSecondWave = false;
    bool bCleared = false;
    bool bStopping = false;
};
