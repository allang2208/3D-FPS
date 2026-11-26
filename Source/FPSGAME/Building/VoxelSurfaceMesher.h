#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "VoxelSurfaceMesher.generated.h"

class UDynamicMesh;
namespace UE::Geometry { class FDynamicMesh3; }

namespace VoxelSurface
{
    // SampleSlot reads the complete world, including the one-cell chunk halo.
    void Build(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,double Radius,
        TFunctionRef<int32(FIntVector)> SampleSlot);
    // 带楔形切割的变体（2026-10-15 屋顶斜面）：SampleCut 返回该格的 VoxelCut 编码；
    // 0=整格。无切割时与三参版本逐位一致（bAnyCut 快路径）。
    void Build(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,double Radius,
        TFunctionRef<int32(FIntVector)> SampleSlot,TFunctionRef<uint8(FIntVector)> SampleCut);
    /** 2026-10-19 连续屋面：切割格按**解析凸棱柱**直接出网格（顶坡面/竖直面/底面/两端封头），
     *  同平面临格的顶面边严格共线，拼出的是一整张斜面；顶点法线为解析法线，无步进起伏。
     *  调用方必须让 Build 把这些格子当空（SampleSlot 返回 INDEX_NONE），并把 SampleCut 传 0，
     *  否则步进场会再按粗采样切一遍、在解析面下方鼓出台阶。邻格为整格时由步进场补面，
     *  邻格为切格时按共面/脊线内部跳过。只进渲染网格，碰撞仍用 VoxelCut::Corners 凸包。 */
    void AppendCutCells(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,
        TFunctionRef<int32(FIntVector)> SampleSlot,TFunctionRef<uint8(FIntVector)> SampleCut);
}

/** Asset authoring uses the same surface generator as placed buildings. */
UCLASS()
class FPSGAME_API UVoxelSurfaceLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Building|Authoring")
    static UDynamicMesh* CreateExampleMesh(float EdgeRadiusCm=1.4f);
    /** 单格楔形示例网格（预览 ghost/图标用）：按 VoxelCut 编码切割，几何与放置后完全一致。 */
    UFUNCTION(BlueprintCallable,Category="Building|Authoring")
    static UDynamicMesh* CreateExampleMeshCut(float EdgeRadiusCm=1.4f,int32 Cut=1);
};
