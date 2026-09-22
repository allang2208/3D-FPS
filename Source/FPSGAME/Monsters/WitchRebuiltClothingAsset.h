#pragma once
#include "ClothingAsset.h"
#include "WitchRebuiltClothingAsset.generated.h"

/** Keeps the Witch's generated garment capture stable through mesh/DDC rebuilds. */
UCLASS()
class FPSGAME_API UWitchRebuiltClothingAsset : public UClothingAssetCommon
{
    GENERATED_BODY()
public:
#if WITH_EDITOR
    void InitializeSimulationFrom(UClothingAssetCommon* Extracted);
    virtual bool BindToSkeletalMesh(USkeletalMesh* InSkelMesh,int32 InMeshLodIndex,int32 InSectionIndex,int32 InAssetLodIndex) override;
    virtual TArray<TPair<FText,FText>> GetStats() const override;
#endif
};
