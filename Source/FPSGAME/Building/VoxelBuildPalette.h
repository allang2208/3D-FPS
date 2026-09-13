#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "VoxelBuildPalette.generated.h"

class UMaterialInterface;
class UStaticMesh;

USTRUCT(BlueprintType)
struct FVoxelPhysicalMaterial
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadOnly,meta=(ClampMin="1")) float DensityKgM3=600;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,meta=(ClampMin="1")) float CompressionPa=350000;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,meta=(ClampMin="1")) float TensionPa=80000;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,meta=(ClampMin="1")) float ShearPa=60000;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,meta=(ClampMin="1")) float Durability=180;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,meta=(ClampMin="1")) float JoulesPerDamage=6;
};

USTRUCT(BlueprintType)
struct FVoxelBuildMaterial
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UMaterialInterface> Surface;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UStaticMesh> ExampleMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Support") bool bSupportsWeight=true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Physics") bool bOverridePhysics=false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Physics",meta=(EditCondition="bOverridePhysics")) FVoxelPhysicalMaterial Physics;
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
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Support", meta=(ClampMin="0",Units="cm")) float MaxCantileverCm=200.f;
    const FVoxelBuildMaterial* Find(FName Id) const;
    FVoxelPhysicalMaterial Physical(FName Id) const;
};
