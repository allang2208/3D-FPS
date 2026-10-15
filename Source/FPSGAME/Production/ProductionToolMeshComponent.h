#pragma once
#include "../Weapons/RuneSwordMeshComponent.h"
#include "ProductionToolMeshComponent.generated.h"

/** Warhammer floor contact is fitted as one hand/weapon group before publication. */
UCLASS()
class FPSGAME_API UProductionToolMeshComponent : public URuneSwordMeshComponent
{
    GENERATED_BODY()
public:
    void SetFloorContact(const FVector& Point,float Weight){FloorPoint=Point;FloorWeight=Weight;}
    virtual void FinalizeBoneTransform() override;
private:
    FVector FloorPoint=FVector::ZeroVector;
    float FloorWeight=0.f;
};
