#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonBossEncounter.generated.h"

class UBoxComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;
class ASceneTestPortal;

/** Authored terminal walk supports and reward fixtures; combat lives in the room encounter. */
UCLASS()
class FPSGAME_API ADungeonBossEncounter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonBossEncounter();
    UPROPERTY(EditAnywhere, Category="Dungeon|Fixtures") FVector DoorPoint=FVector::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Dungeon|Fixtures") FVector2D DoorSize=FVector2D(300,280);
    UPROPERTY(EditAnywhere, Category="Dungeon|Fixtures") TObjectPtr<UMaterialInterface> GateMaterial;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void ConfigureRewardExit(UStaticMesh* LeafMesh,const FVector& Position,const FVector& Travel,
        const FVector& ClearSize,AActor* Chest,ASceneTestPortal* ReturnPortal);
private:
    void UpdateFinalProgress();
    TWeakObjectPtr<AActor> RewardChest;
    TWeakObjectPtr<ASceneTestPortal> RewardPortal;
    FVector RewardClosed=FVector::ZeroVector,RewardTravel=FVector::ZeroVector;
    float RewardOpenAlpha=0.f;
    bool bRewardReleased=false;
    FTimerHandle ProgressTimer;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Gate;
    UPROPERTY() TObjectPtr<UBoxComponent> GateCollision;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RewardGate;
    UPROPERTY() TObjectPtr<UBoxComponent> RewardGateCollision;
};
