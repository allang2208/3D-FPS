#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PoisonMaggotSpawner.generated.h"
class APoisonMaggotMonster;
UCLASS(Blueprintable)
class FPSGAME_API APoisonMaggotSpawner : public AActor
{
 GENERATED_BODY()
public:
 APoisonMaggotSpawner();
 virtual void BeginPlay() override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") TSubclassOf<APoisonMaggotMonster> MonsterClass;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") float RespawnSeconds=300;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") float MinimumPlayerDistance=500;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Spawn") bool bEnabled=true;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Spawn") TObjectPtr<APoisonMaggotMonster> LiveMonster;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Spawn") int32 SpawnCount=0;
 UFUNCTION(BlueprintCallable,Category="Spawn") void SpawnMonster();
 UFUNCTION(BlueprintCallable,Category="Spawn|Editor",meta=(WorldContext="Context")) static bool FindVillageSpawn(UObject* Context,FVector Origin,FRotator Facing,FVector& Location);
private:
 UFUNCTION() void MonsterDestroyed(AActor* Actor);
 FTimerHandle Timer;
};
