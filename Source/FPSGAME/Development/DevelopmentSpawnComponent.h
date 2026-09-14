#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DevelopmentSpawnComponent.generated.h"

class ACharacter;
class APlayerController;
class ANavigationData;
class UNavigationSystemV1;

USTRUCT(BlueprintType)
struct FDevelopmentMonsterEntry
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FText Name;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftClassPtr<ACharacter> CharacterClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1", Units="cm")) float FootprintRadius = 50.f;
};

/** Owns the developer spawn catalogue and only the instances created through it. */
UCLASS(ClassGroup=(Development), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UDevelopmentSpawnComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDevelopmentSpawnComponent();
    UPROPERTY(EditAnywhere, Category="Development") TArray<FDevelopmentMonsterEntry> Monsters;
    const TArray<FDevelopmentMonsterEntry>& GetMonsters() const { return Monsters; }
    int32 SpawnInFront(FName Id, int32 Count, float DistanceMeters, FText& Result);
    int32 ClearSpawned();
    int32 GetSpawnedCount() const;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    bool FindLocation(APlayerController* Player, const ACharacter* Defaults, float Distance,
        float Footprint, int32 Attempt, const UNavigationSystemV1* Navigation,
        const ANavigationData* NavData, FVector& Location, FRotator& Facing) const;
    TArray<TWeakObjectPtr<ACharacter>> Spawned;
};
