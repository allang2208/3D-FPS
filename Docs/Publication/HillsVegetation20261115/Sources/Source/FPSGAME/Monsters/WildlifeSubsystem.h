#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "HillsWildlifeGroups.h"
#include "WildlifeSubsystem.generated.h"

class AColdSteelAnimal;
class UWildlifeDistanceActivity;
struct FWildlifeSpecies;

struct FWildlifeGroundLoot
{
    FString Definition;
    int32 Count;
    FVector Origin;
    float Radius;
    float Angle;
};

/**
 * Keeps an ambient population of wildlife around the players. Server only:
 * it also coordinates hills herds and crow flocks on the server.
 */
UCLASS()
class FPSGAME_API UWildlifeSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    static bool IsWildlifeMap(const UWorld* World);
    static bool IsCatalogClass(const FSoftObjectPath& ClassPath);
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

    /** Spawn one species next to the given player; used by the development panel. */
    UFUNCTION(BlueprintCallable, Category="Wildlife")
    int32 SpawnHerd(const FString& SpeciesId, const FVector& Near, int32 Count);

    UFUNCTION(BlueprintPure, Category="Wildlife")
    int32 GetLiveCount() const;

    void RegisterHillsGroup(const TArray<AColdSteelAnimal*>& Animals);
    void RegisterActivity(UWildlifeDistanceActivity* Activity);
    void UnregisterActivity(UWildlifeDistanceActivity* Activity);
    void BeginCorpse(ACharacter& Animal, const FWildlifeSpecies& Species);
    void DropLoot(const ACharacter& Animal, const FWildlifeSpecies& Species, const FVector& Ground);
    /** Commit queued deaths before travel/quit. Failure retains the queue for retry. */
    bool FlushLoot();
    static bool FlushPendingLoot(UWorld* World);
    void AlarmHillsGroup(AColdSteelAnimal* Animal, const FVector& Source);
    bool FindEscapeStep(const ACharacter& Animal, const FVector& Threat, FVector& Out);

private:
    bool IsDay() const;
    bool FindSpawnPoint(const FVector& Center, const struct FWildlifeSpecies& Species, FVector& OutLocation);
    bool ResolveSpawnCenter(const FWildlifeSpecies& Species, const FVector& Probe, FVector& OutLocation);
    void SpawnRiverbankBoars(const ATemperateHillsWorld& Terrain, const FWildlifeSpecies& Species,
        TConstArrayView<FVector> Players, const FVector& Center, int32 Wanted);
    void TickHillsGroups(TConstArrayView<FVector> LivingPlayers);
    ATemperateHillsWorld* FindHills();
    AActor* SpawnOne(const struct FWildlifeSpecies& Row, const FVector& Location, const FRotator& Facing,
        ESpawnActorCollisionHandlingMethod CollisionHandling = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
    void UpdateActivity(TConstArrayView<FVector> Players);
    void PruneAndDespawn(TConstArrayView<FVector> Players);
    void OnWorldBeginTearDown(UWorld* World);

    TArray<FWildlifeGroundLoot> PendingLoot;
    double NextLootAttempt = 0.;
    TArray<TWeakObjectPtr<AActor>> Spawned;
    // Also includes placed / development animals, without charging them to the natural population.
    TArray<TWeakObjectPtr<UWildlifeDistanceActivity>> ActivityMembers;
    TArray<FHillsWildlifeGroup> HillsGroups;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    float GroupAccumulator = 0.f;
    float SpawnAccumulator = 0.f;
    float DespawnAccumulator = 0.f;
    mutable float CachedDayValue = .5f;
    mutable double CachedDaySampleTime = -1000.;
    bool bLoggedMissingClass = false;
};
