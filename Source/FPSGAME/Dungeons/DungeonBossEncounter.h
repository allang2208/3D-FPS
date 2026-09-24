#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonBossEncounter.generated.h"

class AHandBrainMonster;
class UBoxComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;
class ASceneTestPortal;

/** One encounter per generated terminal. The generator arms it only after navigation is ready. */
UCLASS()
class FPSGAME_API ADungeonBossEncounter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonBossEncounter();
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") TSubclassOf<AHandBrainMonster> BossClass;
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") FVector SpawnPoint=FVector(0,-1550,0);
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") FVector ArenaMin=FVector(-1450,-2500,0);
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") FVector ArenaMax=FVector(1470,50,820);
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") FVector DoorPoint=FVector::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") FVector2D DoorSize=FVector2D(300,280);
    UPROPERTY(EditAnywhere, Category="Dungeon|Boss") TObjectPtr<UMaterialInterface> GateMaterial;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|Boss") bool bEncounterComplete=false;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|Boss") TObjectPtr<AHandBrainMonster> LiveBoss;
    virtual void OnConstruction(const FTransform& Transform) override;
    void ActivateEncounter();
    /** All assets/actors are prepared by the generator before this encounter is armed. */
    void ConfigureRewardExit(UStaticMesh* LeafMesh,const FVector& Position,const FVector& Travel,
        const FVector& ClearSize,AActor* Chest,ASceneTestPortal* ReturnPortal);
protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Gate;
    UPROPERTY() TObjectPtr<UBoxComponent> GateCollision;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RewardGate;
    UPROPERTY() TObjectPtr<UBoxComponent> RewardGateCollision;
    TWeakObjectPtr<AActor> RewardChest;
    TWeakObjectPtr<ASceneTestPortal> RewardPortal;
    FVector RewardDoorPoint=FVector::ZeroVector,RewardDoorTravel=FVector::ZeroVector;
    float RewardGateOpen=0.f;
    bool bRewardsUnlocked=false;
    TWeakObjectPtr<APawn> Entrant;
    bool bArmed=false,bActive=false,bAwaitExit=false;
    float GateOpen=1.f;
    bool Contains(const APawn* Pawn) const;
    bool SpawnBoss(APawn* Player);
    void UpdateGate();
    void ResetEncounter();
    void UpdateRewardExit(float DeltaSeconds);
};
