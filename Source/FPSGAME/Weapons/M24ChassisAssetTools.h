#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "M24ChassisAssetTools.generated.h"
class USkeletalMesh;
class UStaticMesh;

UCLASS()
class FPSGAME_API UM24ChassisAssetTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // Assign only native stock polygons to a removable section. Keep topology,
    // positions, skin weights, UVs and the current arm morph attributes intact.
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool SplitFactoryChassis(USkeletalMesh* Mesh,const TArray<FVector>& SourceVerticesCM);

    // FullBodyV3 replaces the fore-end and static receiver only. Match authored
    // face centers so the retained buttstock boundary and barrel stay exact.
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool SplitFactoryFront(USkeletalMesh* Mesh,const TArray<FVector>& SourceFaceCentersCM);

    // Separate the shoulder stock behind the retained grip without reimporting
    // the current bare arms, clothing correctives or animation skeleton.
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool SplitFactoryStock(USkeletalMesh* Mesh,const TArray<FVector>& SourceFaceCentersCM);

    // The native rear receiver seat overlaps a pistol-grip conversion. Split
    // its measured faces without touching arm weights, morphs or skeleton.
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool SplitFactoryRearSeat(USkeletalMesh* Mesh,const TArray<FVector>& ComponentFaceCentersCM);

    // Freeze authored stock LODs and replace only invalid tangent directions.
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool BakeStockTangentBasis(UStaticMesh* Mesh);
};
