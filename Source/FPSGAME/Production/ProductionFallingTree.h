#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ProductionFallingTree.generated.h"

struct FProductionResource;
class USkeletalMeshComponent;

/** Short-lived cosmetic fall. Resources were already committed by the profile. */
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
    float Elapsed=0;
};
