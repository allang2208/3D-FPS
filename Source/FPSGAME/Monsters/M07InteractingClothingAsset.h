#pragma once
#include "WitchRebuiltClothingAsset.h"
#include "M07InteractingClothingAsset.generated.h"

/** One six-island particle set and reference frame, with island-filtered captures. */
UCLASS()
class FPSGAME_API UM07InteractingClothingAsset : public UWitchRebuiltClothingAsset
{
    GENERATED_BODY()
public:
#if WITH_EDITORONLY_DATA
    UPROPERTY() TArray<FClothPhysicalMeshData> PanelSimulations;
    UPROPERTY() TArray<int32> PanelVertexOffsets;
    UPROPERTY() TArray<FName> PanelMaterialSlots;
#endif
#if WITH_EDITOR
    virtual bool BindToSkeletalMesh(USkeletalMesh* Mesh, int32 MeshLod, int32 SectionIndex, int32 AssetLod) override;
#endif
};
