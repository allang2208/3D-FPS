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
    // Wood-class default; stone/marble get 450000 in UVoxelBuildPalette::Physical().
    // Every material must hold a 2.0 m clear span with a player on it; see Docs/Building/voxel-build-workflow.md.
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

/** One placeable prefab: a mesh plus the grid footprint it occupies. */
USTRUCT(BlueprintType)
struct FVoxelBuildPrefab
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grid", meta=(ClampMin="1")) FIntVector Footprint=FIntVector(1,1,1);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Surface") TSoftObjectPtr<UMaterialInterface> Surface;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grid", meta=(Units="cm")) FVector PivotOffsetCm=FVector::ZeroVector;
};

/** Shared material IDs, not separate wall/floor inventory items. Grid size is a save contract. */
UCLASS(BlueprintType)
class FPSGAME_API UVoxelBuildPalette : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FVoxelBuildMaterial> Materials;
    /** Prefabricated pieces the player can place as whole units (roman column, balustrade, ...).
        Footprint is measured in 20 cm grid cells; placement snaps to that same grid. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Components") TArray<FVoxelBuildPrefab> Components;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UMaterialInterface> PreviewMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Surface", meta=(ClampMin="0.25",ClampMax="3.0",Units="cm")) float EdgeRadiusCm=1.4f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Support", meta=(ClampMin="0",Units="cm")) float MaxCantileverCm=200.f;
    const FVoxelBuildMaterial* Find(FName Id) const;
    FVoxelPhysicalMaterial Physical(FName Id) const;
    const FVoxelBuildPrefab* FindComponent(FName Id) const
    {
        return Components.FindByPredicate([Id](const FVoxelBuildPrefab& Entry){return Entry.Id==Id;});
    }
};
