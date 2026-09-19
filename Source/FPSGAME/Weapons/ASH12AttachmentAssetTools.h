#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "ASH12AttachmentAssetTools.generated.h"
class UStaticMesh;

// Editor bridge for a protected UStaticMesh flag that Python cannot access.
UCLASS()
class FPSGAME_API UASH12AttachmentAssetTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool IsRuntimeFastBuild(UStaticMesh* Mesh);

    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static void DisableRuntimeFastBuild(UStaticMesh* Mesh);

    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool FinishAndValidateBuild(UStaticMesh* Mesh);
};
