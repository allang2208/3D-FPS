#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonThemeEncounter.generated.h"

class UDungeonRunSubsystem;
class AAuthoredDungeonGenerator;
class ADungeonRoomGate;
class ACharacter;
struct FDungeonRunDoor;
enum class EDungeonThemeObjective : uint8 { WelcomeElite, MedicalBoss, FreightBoss, EcologyBoss, PowerBoss, IncinerationBoss, FinalBoss, StaffLivingBoss };

/** Room spawners own kills; each configured area's objective unlocks its boundary gates. */
UCLASS(NotBlueprintable, Transient)
class FPSGAME_API ADungeonThemeEncounter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonThemeEncounter();
    bool Configure(UDungeonRunSubsystem* InRun, AAuthoredDungeonGenerator* InGenerator,
        const TArray<int32>& InRooms, const TArray<FDungeonRunDoor>& Boundaries,
        EDungeonThemeObjective InObjective = EDungeonThemeObjective::WelcomeElite);
    bool HasStarted() const { return bStarted; }
    bool HasEnteredArea() const { return bBoundaryActivated; }
    bool IsPlayerOnSpawnApproach() const { return bPlayerOnSpawnApproach; }
    APawn* PlayerInArea() const;
    bool ContainsLocation(const FVector& Location) const;
    void RegisterHall(class AFacilityHallEncounter* Hall);
    bool AllowsHallRestPoint(const FVector& Feet, float Radius) const;
    bool HasHallSpace(const FVector& Feet, float Radius, const ACharacter* Ignore, float Gap, bool Reservations) const;
    /** Cached once per area update, shared by all room preparation requests. */
    int32 PreparationPriority(double& DistanceSquared) const;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    friend class UFacilitySpawnRecheckCommandlet;
    void UpdateEncounter();
    void UpdatePreparation();
    bool IsSpawnApproachLocation(const FVector& Location) const;
    bool UsesBoundaryAdmission() const { return Objective != EDungeonThemeObjective::WelcomeElite; }
    bool IsObjectiveDefeated() const;
    const TCHAR* ObjectiveId() const;
    UFUNCTION() void DungeonDestroyed(AActor* Actor);
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    TArray<int32> Rooms;
    TArray<int32> PreparationApproachNodes;
    /** Only connecting passages; never the previous room or the fixed shrine space. */
    TArray<int32> SpawnApproachNodes;
    TArray<FVector> PreparationEntrances;
    TArray<TWeakObjectPtr<class AFacilityHallEncounter>> Halls;
    double LastOccupiedAt=-1.;
    int32 PreparationRank = INDEX_NONE;
    double PreparationDistanceSquared = TNumericLimits<double>::Max();
    UPROPERTY(Transient) TArray<TObjectPtr<ADungeonRoomGate>> Gates;
    FTimerHandle EncounterTimer;
    float OpenFraction = 1.f;
    bool bStarted = false, bCleared = false;
    bool bBoundaryActivated = false;
    bool bPlayerOnSpawnApproach = false;
    EDungeonThemeObjective Objective = EDungeonThemeObjective::WelcomeElite;
    /** Fixed entry/shrine space is reserved by the catalog, outside generated nodes. */
    FBox PreparationStartVolume = FBox(ForceInit);
};
