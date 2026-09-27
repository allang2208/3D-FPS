#pragma once
#include "Components/PoseableMeshComponent.h"
#include "BowFlexMeshComponent.generated.h"

/** Eleven-bone wood body, driven by the bow's existing action clock. */
UCLASS()
class FPSGAME_API UBowFlexMeshComponent : public UPoseableMeshComponent
{
    GENERATED_BODY()
public:
    void SetFlexMesh(USkeletalMesh* Mesh);
    void ApplyStringLoad(const FVector& NockCM,const FVector& BraceCM,float Distribution,float RingDegrees=0.f);
    bool Tips(FVector& Upper,FVector& Lower) const;
private:
    TArray<FTransform> ReferenceCS;
    int32 Chain[2][5]={{INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE},{INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE}};
    bool bFlexReady=false;
    FVector LastNock=FVector(BIG_NUMBER),LastBrace=FVector(BIG_NUMBER);
    float LastDistribution=-1.f,LastRing=BIG_NUMBER;
    FVector TipPosition(int32 Side,float Angle,float Distribution) const;
};
