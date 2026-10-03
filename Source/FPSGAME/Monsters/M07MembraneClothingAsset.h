#pragma once
#include "WitchRebuiltClothingAsset.h"
#include "M07MembraneClothingAsset.generated.h"

/** Witch cloth capture with one continuous mobility field across M07 material seams. */
UCLASS()
class FPSGAME_API UM07MembraneClothingAsset : public UWitchRebuiltClothingAsset
{
    GENERATED_BODY()
public:
#if WITH_EDITOR
    virtual bool BindToSkeletalMesh(USkeletalMesh* Mesh,int32 MeshLod,int32 SectionIndex,int32 AssetLod) override;
#endif
};
