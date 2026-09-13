#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "VoxelBuildPalette.generated.h"

class UMaterialInterface;
class UStaticMesh;

USTRUCT(BlueprintType)
struct FVoxelBuildMaterial
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UMaterialInterface> Surface;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UStaticMesh> ExampleMesh;
};

/** Shared material IDs, not separate wall/floor inventory items. Grid size is a save contract. */
UCLASS(BlueprintType)
class FPSGAME_API UVoxelBuildPalette : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FVoxelBuildMaterial> Materials;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UMaterialInterface> PreviewMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Surface", meta=(ClampMin="0.25",ClampMax="3.0",Units="cm")) float EdgeRadiusCm=1.4f;
    const FVoxelBuildMaterial* Find(FName Id) const;
};
