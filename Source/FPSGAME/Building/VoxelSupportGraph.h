#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildPalette.h"

struct FVoxelSupportNode
{
    FVoxelBuildKey Key;
    FVector Min;
    bool bAnchor=false;
    bool bBearing=true;
    FName Material;
    FVoxelPhysicalMaterial Physics;
    float Damage=0;
    float AddedMassKg=0;
};

struct FVoxelContact
{
    FVector Center,Normal;
    double Area=0,Width=0,Height=0; // SI units; center remains UE cm.
};

/** Incremental world-space face graph, including independently translated grids. */
struct FVoxelSupportGraph
{
    TMap<FVoxelBuildKey,FVoxelSupportNode> Nodes;
    TMap<FVoxelBuildKey,TSet<FVoxelBuildKey>> Edges;
    TSet<FVoxelBuildKey> Supported;
    TSet<FVoxelBrokenBond> Broken;
    void Add(const FVoxelSupportNode& Node);
    void Remove(FVoxelBuildKey Key);
    void Break(FVoxelBrokenBond Bond);
    void SolveConnectivity();
    bool Overlaps(const FVector& Min) const;
    TArray<FVoxelBuildKey> Near(const FVector& Min) const;
    /**
     * 审计 P6：`Near()` 按值返回 TArray，每次调用都堆分配（结果数不定，装不进小的内联缓冲）。
     * 它被瞄准（每帧）、放置校验（每格）、载荷登记（每 0.25 s）等高频路径调用，仅瞄准路径每帧
     * 就是十几次分配。本入口改为写入调用方缓冲：缓冲可跨调用复用，稳态零分配。
     * 语义与 `Near()` 完全一致（同样是 [C-2,C+2]³ 桶范围内的全部键，未排序、可能含重复）。
     */
    void NearInto(const FVector& Min,TArray<FVoxelBuildKey>& Out) const;
    TArray<FVoxelBuildKey> Within(FVector Point,float Radius) const;
    static bool Contact(const FVector& A,const FVector& B,FVoxelContact& Result);
private:
    TMap<FIntVector,TSet<FVoxelBuildKey>> Buckets;
};

struct FVoxelStressInput
{
    TArray<FVoxelSupportNode> Nodes;
    TSet<FVoxelBrokenBond> Broken;
    uint64 Revision=0;
    int32 Iterations=256;
    float GravityMS2=-9.81f;
    /** 过载渐进损伤：ratio=1 时的断裂秒数（上限）与最低秒数；越超载越快。 */
    float OverloadGraceSeconds=30.f;
    float OverloadMinSeconds=3.f;
    /**
     * 局部求解的边界节点（2026-09-16 简化）：超大结构不再整块解算，只解算变化附近的一块，边界节点
     * 视为固定支撑，因此不会把远处误判成"失去地基"。
     */
    TSet<FVoxelBuildKey> Boundary;
};

/** 一个过载格每秒要承受的损伤（已按该格自身耐久换算，因此各材质时间一致）。 */
struct FVoxelOverloadCell
{
    FVoxelBuildKey Key;
    float RatePerSecond=0;
    float Ratio=0;
};

/** Which stress term governs a joint; used by the panel's weakest-joint readout. */
enum class EVoxelBondStress : uint8 { Compression=0, Tension=1, Shear=2 };

/** Worst joint of one solve: ratio 1.0 breaks it. Kept so the panel can name the seam to reinforce. */
struct FVoxelBondStress
{
    bool bValid=false;
    FVoxelBuildKey A,B;
    EVoxelBondStress Kind=EVoxelBondStress::Tension;
    float Ratio=0,StressPa=0,LimitPa=0;
};

struct FVoxelStressResult
{
    uint64 Revision=0;
    TSet<FVoxelBuildKey> Evaluated,Supported;
    TArray<FVoxelBrokenBond> Broken;
    TArray<FVoxelBuildKey> Crushed;
    TArray<TArray<FVoxelSupportNode>> Detached;
    TMap<FVoxelBuildKey,float> LoadRatios;
    FVoxelBondStress WorstBond;
    /** 过载格与损伤速率；世界按帧累积，损伤满耐久才掉块/断键（渐进损伤，2026-09-16）。 */
    TArray<FVoxelOverloadCell> Overload;
    bool bConverged=true;
    int32 Iterations=256;
};
namespace VoxelStress { FVoxelStressResult Solve(FVoxelStressInput Input); }
