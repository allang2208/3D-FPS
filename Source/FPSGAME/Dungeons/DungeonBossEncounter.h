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

/** Legacy class name retained for saved maps; now only passive terminal walk supports and open gates. */
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
    void ConfigureRewardExit(UStaticMesh* LeafMesh,const FVector& Position,const FVector& Travel,
        const FVector& ClearSize,AActor* Chest,ASceneTestPortal* ReturnPortal);
private:
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Gate;
    UPROPERTY() TObjectPtr<UBoxComponent> GateCollision;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RewardGate;
    UPROPERTY() TObjectPtr<UBoxComponent> RewardGateCollision;
};
