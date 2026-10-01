#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonProgressionGate.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UBoxComponent;

/** One-way progression shutter; owned and retired by the dungeon assembly. */
UCLASS(NotBlueprintable)
class FPSGAME_API ADungeonProgressionGate : public AActor
{
    GENERATED_BODY()
public:
    ADungeonProgressionGate();
    void Configure(UStaticMesh* Mesh,int32 NodeId,bool bAnyRoute,const FVector& ClearSize,const FVector& Travel);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Leaf;
    UPROPERTY() TObjectPtr<UBoxComponent> Blocker;
    int32 RequiredNode=INDEX_NONE;
    bool bRequireAnyRoute=false,bReleased=false;
    FVector Lift=FVector::ZeroVector,Opening=FVector::ZeroVector;
    float OpenFraction=0.f;
};
