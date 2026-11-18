#include "VoxelBuildComponent.h"
#include "VoxelBuildPalette.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"

bool UVoxelBuildComponent::PreparePreviewAssets()
{
    if (!PreviewAssetHandle)
    {
        TArray<FSoftObjectPath> Paths = {
            PaletteAsset.ToSoftObjectPath(),
            FSoftObjectPath(TEXT("/Engine/BasicShapes/Cube.Cube")),
            FSoftObjectPath(TEXT("/Game/Building/Voxels/Rounded/M_Voxel_PlacementPreview.M_Voxel_PlacementPreview")),
            FSoftObjectPath(TEXT("/Game/Building/Voxels/Rounded/M_VoxelAimEdge.M_VoxelAimEdge"))
        };
        for (const TCHAR* Name : {TEXT("SM_VoxelWedge45"), TEXT("SM_VoxelWedge26L"),
                                 TEXT("SM_VoxelWedge26U"), TEXT("SM_VoxelTent")})
            Paths.Emplace(FString::Printf(TEXT("/Game/Building/Voxels/Rounded/%s.%s"), Name, Name));
        PreviewAssetHandle = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths);
        InitializationMessage = TEXT("正在准备建造预览资源");
        return false;
    }
    if (!PreviewAssetHandle->HasLoadCompleted()) return false;
    TArray<UObject*> Loaded;
    PreviewAssetHandle->GetLoadedAssets(Loaded);
#if WITH_EDITOR
    for (UObject* Object : Loaded)
        if (auto* Mesh = Cast<UStaticMesh>(Object); Mesh && Mesh->IsCompiling()) return false;
#endif
    if (!PaletteAsset.Get())
    {
        InitializationMessage = TEXT("体素材质资源未能载入");
        bInitializeFailed = true;
        return false;
    }
    if (!bSurfaceAssetsRequested)
    {
        bSurfaceAssetsRequested=true;
        TArray<FSoftObjectPath> Paths;
        for (const auto& Material : PaletteAsset.Get()->Materials)
            if (!Material.Surface.IsNull()) Paths.AddUnique(Material.Surface.ToSoftObjectPath());
        if (!PaletteAsset.Get()->PreviewMaterial.IsNull())
            Paths.AddUnique(PaletteAsset.Get()->PreviewMaterial.ToSoftObjectPath());
        if (!Paths.IsEmpty())
        {
            SurfaceAssetHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths);
            return false;
        }
    }
    if (SurfaceAssetHandle && !SurfaceAssetHandle->HasLoadCompleted()) return false;
    return true;
}
