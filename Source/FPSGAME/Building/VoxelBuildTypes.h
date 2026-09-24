#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.generated.h"

// An invalid Volume identifies the original world-aligned voxel lattice.
USTRUCT()
struct FVoxelBuildKey
{
    GENERATED_BODY()
    UPROPERTY() FGuid Volume;
    UPROPERTY() FIntVector Cell=FIntVector::ZeroValue;
    bool operator==(const FVoxelBuildKey& Other) const {return Volume==Other.Volume&&Cell==Other.Cell;}
    friend uint32 GetTypeHash(const FVoxelBuildKey& Key){return HashCombine(GetTypeHash(Key.Volume),GetTypeHash(Key.Cell));}
};

USTRUCT()
struct FVoxelSavedCell
{
    GENERATED_BODY()
    UPROPERTY() FIntVector Position=FIntVector::ZeroValue;
    UPROPERTY() FName Material;
};

USTRUCT()
struct FVoxelFreeVolume
{
    GENERATED_BODY()
    UPROPERTY() FGuid Id;
    UPROPERTY() FVector Origin=FVector::ZeroVector;
    UPROPERTY() TMap<FIntVector,FName> Cells;
};

struct FVoxelEditCell
{
    FIntVector Position;
    FName Before;
    FName After;
    FGuid Volume;
};

USTRUCT()
struct FVoxelBrokenBond
{
    GENERATED_BODY()
    UPROPERTY() FVoxelBuildKey A;
    UPROPERTY() FVoxelBuildKey B;
    bool operator==(const FVoxelBrokenBond& O) const {return (A==O.A&&B==O.B)||(A==O.B&&B==O.A);}
    friend uint32 GetTypeHash(const FVoxelBrokenBond& B){return GetTypeHash(B.A)^GetTypeHash(B.B);}
};

USTRUCT()
struct FVoxelDebrisCell
{
    GENERATED_BODY()
    UPROPERTY() FVoxelBuildKey Key;
    UPROPERTY() FVector Min=FVector::ZeroVector;
    UPROPERTY() FName Material;
    UPROPERTY() float Damage=0;
};

USTRUCT()
struct FVoxelFragmentSave
{
    GENERATED_BODY()
    UPROPERTY() FGuid Id;
    UPROPERTY() FTransform Transform;
    UPROPERTY() TArray<FVoxelDebrisCell> Cells;
    UPROPERTY() TSet<FVoxelBrokenBond> BrokenBonds;
    UPROPERTY() FVector Velocity=FVector::ZeroVector;
    UPROPERTY() FVector AngularVelocity=FVector::ZeroVector;
    UPROPERTY() bool bSleeping=false;
};

// One placed prefab piece (roman column, balustrade, ...) on the 20 cm building lattice.
// Cell is the min corner of the occupied box; Footprint is already rotated by Yaw.
struct FVoxelBuildPrefabInstance
{
    FName Id;
    FIntVector Cell=FIntVector::ZeroValue;
    int32 Yaw=0;
    FIntVector Footprint=FIntVector(1,1,1);
};

/** 可冶炼构件的调色板稳定 ID（Docs/Gameplay/blast-furnace-model-20260923.md）。
 *  归属放数据而不是散落的字符串比较：交互白名单、拆除退回与面板都引用这一个键。 */
inline const FName VoxelSmeltingFurnaceId(TEXT("blast_furnace"));

/** 工作台构件的调色板稳定 ID（SourceAssets/WorkbenchBuildable20260924，面板规划
 *  Docs/UI/workbench-panel-plan-20260924.md）：E 交互与制作面板引用这一个键。 */
inline const FName VoxelWorkbenchId(TEXT("workbench_table"));

// VBX v5（只读兼容）：纯挂钟冶炼任务——今天引入 v5 后当天就升级成燃料模型，
// 老档按"挂钟全额补进度"迁移进 v6（见 AVoxelBuildWorld::Initialize）。
struct FVoxelSmeltingJobV5
{
    FIntVector Cell=FIntVector::ZeroValue;
    FName Recipe;
    int64 StartTicks=0;
};

// One in-progress ore→ingot smelting job on a placed furnace, keyed by the prefab's anchor
// cell. v6 model: ProgressSeconds accumulates only while the furnace burns; BurnStartTicks is
// the UTC start of the current burning segment (FDateTime::UtcNow().GetTicks()), 0 = stoked
// out / finished. Wall-clock segments keep counting while the game is closed, but fuel caps
// how much of a segment actually burns (settle in UColdSteelSmeltingSystem).
// v7 adds BatchCount: the job covers N×(input→output) of one recipe in one furnace, total
// time = recipe seconds × N ÷ 炉等级速度倍率（老档读入默认 1，行为与 v6 完全一致）。
struct FVoxelSmeltingJob
{
    FIntVector Cell=FIntVector::ZeroValue;
    FName Recipe;
    double ProgressSeconds=0;
    int64 BurnStartTicks=0;
    int64 BatchCount=1;
};

// Per-furnace stored fuel (seconds), independent of the job: it survives collect and can be
// topped up before starting a batch. Refunded as wood on teardown (floor(fuel/SecondsPerUnit)).
// v7 also carries the furnace upgrade level (1..VoxelFurnaceMaxLevel)：升级只加速这座炉。
// v8 adds FireStartTicks：空闲火种段起点。2026-09-24 用户截图定稿语义——炉内有存料就随挂钟
// 持续燃烧（没矿也烧，烧完即熄）；任务在烧时由任务段扣料，火种戳只跟挂钟钉住不重复扣。
// v9 adds FuelLevel/BatchLevel：升级从单轴变三轴（2026-09-24 用户"添加最大燃料槽的升级、
// 每次冶炼矿石数升级"）——Level=冶炼速度（+25%/级），FuelLevel=燃料仓上限（10 分钟×等级，
// 封顶 Lv6=60 分钟），BatchLevel=每次投料上限（5×级）。三轴独立、同成本曲线（10×当前级 铁锭）；
// 各轴封顶见 VoxelFurnaceAxisMax（速度/批量 Lv5，燃料仓 Lv6——用户 2026-09-24 数值调参定档）。
struct FVoxelFurnaceFuel
{
    FIntVector Cell=FIntVector::ZeroValue;
    double FuelSeconds=0;
    int32 Level=1;
    int64 FireStartTicks=0;
    int32 FuelLevel=1;
    int32 BatchLevel=1;
};

/** 高炉升级上限（VBX v7）：每级 +25% 冶炼速度，Lv5=+100%。 */
inline constexpr int32 VoxelFurnaceMaxLevel=5;
/** 三轴升级（VBX v9）的轴号：速度（+25%/级）/燃料仓（+10 分钟/级）/每次投料（5×级）。 */
inline constexpr int32 VoxelFurnaceAxisSpeed=0,VoxelFurnaceAxisFuelCapacity=1,VoxelFurnaceAxisBatch=2;
/** 各轴封顶（2026-09-24 数值调参）：燃料仓 5 次升级＝6 档（Lv6=60 分钟）；速度/批量仍 5 档。 */
inline constexpr int32 VoxelFurnaceAxisMax(int32 Axis)
{   return Axis==VoxelFurnaceAxisFuelCapacity?6:VoxelFurnaceMaxLevel;   }
