#pragma once
#include "CoreMinimal.h"
#include "NurseZombie.h"
#include "InfectedMiner.generated.h"

// Reuses the existing humanoid execution/BT adapter; its mesh and clips are owned assets.
UCLASS(Blueprintable)
class FPSGAME_API AInfectedMiner : public ANurseZombie
{
    GENERATED_BODY()
public:
    AInfectedMiner();
    virtual void BeginPlay() override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    UFUNCTION(BlueprintCallable,Category="Miner|Assets") static class UPhysicsAsset* CreatePhysicsAsset(USkeletalMesh* TargetMesh);
    UFUNCTION(BlueprintCallable,Category="Miner|Assets") static bool ApplyAcceptedGrip(class UAnimSequence* TargetClip,class UAnimSequence* AcceptedIdle);
    UFUNCTION(BlueprintCallable,Category="Miner|Assets",meta=(WorldContext="Context")) static bool BakeTestNavigation(UObject* Context);
};

UCLASS(Blueprintable)
class FPSGAME_API AInfectedMinerSpawner : public AActor
{
    GENERATED_BODY()
public:
    AInfectedMinerSpawner();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Miner") TSubclassOf<AInfectedMiner> MonsterClass;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Miner") float RespawnSeconds=90.f;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Miner") TObjectPtr<AInfectedMiner> LiveMiner;
private:
    void SpawnMiner();
    UFUNCTION() void MinerDestroyed(AActor* Actor);
    FTimerHandle RespawnTimer;
};
