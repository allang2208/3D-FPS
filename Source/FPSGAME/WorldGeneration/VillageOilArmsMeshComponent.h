#pragma once

#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "VillageOilArmsMeshComponent.generated.h"

/**
 * First-person oil-carry skeletal arms compatible with UFPSModularOutfitComponent followers.
 * Applies solved component-space arm transforms inside FinalizeBoneTransform and updates posed bounds.
 */
UCLASS()
class FPSGAME_API UVillageOilArmsMeshComponent : public USkeletalMeshComponent
{
	GENERATED_BODY()

public:
	void CommitStationPose(const TArray<FTransform>& StationPose, const TArray<int32>& ArmBones);
	virtual void FinalizeBoneTransform() override;
	virtual FBoxSphereBounds CalcBounds(const FTransform& LocalToWorld) const override;

private:
	TArray<FTransform> PendingPose;
	FBox PosedLocalBounds = FBox(ForceInit);
};
