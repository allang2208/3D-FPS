#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VillageDefenseDebris.generated.h"
class UStaticMeshComponent;

/** Local cosmetic fragments; only intact gameplay collision is replicated. */
UCLASS(NotBlueprintable,Transient)
class AVillageDefenseDebris : public AActor
{
    GENERATED_BODY()
public:
    AVillageDefenseDebris();
    static void Spawn(AActor& Section,const FTransform& Transform,const FVector& Size,const FVector& Direction,int32 Seed,bool Wood);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Chunks;
    TArray<float> ReleaseAt;
    TArray<FVector> Scales,Velocities,Spins;
    float Age=0.f;
};
