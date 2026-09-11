#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HandBrainVillageSpawner.generated.h"
class AHandBrainMonster;
UCLASS(Blueprintable)
class FPSGAME_API AHandBrainVillageSpawner : public AActor
{
 GENERATED_BODY()
public:
 AHandBrainVillageSpawner();
 virtual void BeginPlay() override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") TSubclassOf<AHandBrainMonster> MonsterClass;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") float RespawnSeconds=300.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") bool bEnabled=true;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Spawn") TObjectPtr<AHandBrainMonster> LiveMonster;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Spawn") int32 SpawnCount=0;
 UFUNCTION(BlueprintCallable,Category="Spawn") void SpawnMonster();
private:
 UFUNCTION() void MonsterDestroyed(AActor* Actor);
 FTimerHandle Timer;
};
