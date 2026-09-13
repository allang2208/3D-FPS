#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ProductionTreeFallPlan.h"
#include "ProductionFallingTree.generated.h"

struct FProductionResource;
class USkeletalMeshComponent;

/** Cosmetic fall; persistent ground drops are committed before the animation starts. */
UCLASS(NotBlueprintable)
class FPSGAME_API AProductionFallingTree : public AActor
{
    GENERATED_BODY()
public:
    AProductionFallingTree();
    void InitializeFall(const FProductionResource& Resource,const FVector& Direction);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<USkeletalMeshComponent> Tree;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> CutCap;
    UPROPERTY() TArray<TObjectPtr<class UMaterialInstanceDynamic>> Materials;
    FProductionTreeFallPlan Plan;
    FVector Scale=FVector::OneVector;
    FVector LocalFallDirection=FVector::ForwardVector;
    FQuat InitialRotation=FQuat::Identity;
    float CrownBend=0,PreviousAngle=0;
    uint32 EffectSeed=0;
    bool Landed=false;
    bool CrownTouched=false;
    float Elapsed=0;
};
