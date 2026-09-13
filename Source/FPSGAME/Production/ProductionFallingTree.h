#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
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
    FQuat InitialRotation=FQuat::Identity;
    FVector FallAxis=FVector::RightVector;
    FVector LandingPoint=FVector::ZeroVector;
    float LandingAngle=88.f;
    uint32 EffectSeed=0;
    bool Landed=false;
    float Elapsed=0;
};
