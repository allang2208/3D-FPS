#pragma once
#include "CoreMinimal.h"
#include "Components/PoseableMeshComponent.h"
#include "ForgeArmsMeshComponent.generated.h"

/** The forge pose moves away from the native bind pose. Cull using the posed arms. */
UCLASS()
class FPSGAME_API UForgeArmsMeshComponent : public UPoseableMeshComponent
{
    GENERATED_BODY()
public:
    void CommitStationPose(const TArray<FTransform>& StationPose,const TArray<int32>& ArmBones);
    virtual FBoxSphereBounds CalcBounds(const FTransform& LocalToWorld) const override;
private:
    FBox PosedLocalBounds=FBox(ForceInit);
};
