#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "VoxelBuildTypes.h"   // 三轴升级轴号常量（默认参数用）
#include "SmeltingSystem.generated.h"

class AVoxelBuildWorld;
class UColdSteelStatusModel;
struct FVoxelSmeltingJob;

/** One ore→ingot recipe from Content/ColdSteelData/smelting-recipes.json.
 *  输入输出都是 items.json 的稳定定义 id；进度只在有燃料的燃烧段内推进。 */
struct FColdSteelSmeltingRecipe
{
    FName Id;
    FString Input;
    int64 InputCount=1;
    FString Output;
    int64 OutputCount=1;
    double Seconds=8.0;
};

/** 燃料配置（smelting-recipes.json 顶层 "fuel" 对象）：一件燃料折算的燃烧秒数与炉内上限。
 *  默认：木材、每件 60 秒（1 分钟）、每炉存 600 秒（10 件）——2026-09-24 数值调参（用户定档）。
 *  存料跨批次保留，拆除按整件折回；燃料仓升级每级再 +10 分钟（capacity×等级，封顶 60 分钟）。 */
struct FColdSteelSmeltingFuel
{
    FString Item=TEXT("wood");
    double SecondsPerUnit=60.0;
    double Capacity=600.0;
};

/**
 * 冶炼配方目录与炉内结算（Docs/UI/smelting-panel-plan-20260923.md）。
 * 世界侧只存状态（锚格→任务{配方+积累秒数+燃烧段起点}、锚格→燃料秒，VBX v6）；
 * 扣料/发放走 UColdSteelStatusModel 的既有事务（背包优先、仓库兜底）。
 * 结算口径：elapsed=(UTC now-BurnStart)/TickPerSec；burn=min(elapsed,配方剩余,存料)；
 * 燃烧段被燃料或配方封顶时停燃（BurnStart=0），添燃料后从停点续燃。
 * 面板只做展示与按钮转发，不自己扣料或写档（UI-WORKFLOW 第 5 节）。
 */
UCLASS()
class FPSGAME_API UColdSteelSmeltingSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    const TArray<FColdSteelSmeltingRecipe>& Catalog() const {return Recipes;}
    const FColdSteelSmeltingRecipe* Find(FName Id) const;
    const FColdSteelSmeltingFuel& FuelConfig() const {return Fuel;}
    /** 把当前燃烧段按挂钟与存料落账（封顶后停燃；有料未燃且未完则续燃）。true=状态有写回。 */
    bool SettleFurnace(AVoxelBuildWorld* World,FIntVector Cell);
    /** 0..1 进度（含正在烧的段的实时预览，不写档）；配方下架读作 0。 */
    float Progress(const AVoxelBuildWorld* World,FIntVector Cell) const;
    bool IsDone(const AVoxelBuildWorld* World,FIntVector Cell) const;
    /** 正在烧：有燃烧段、存料>0 且未完（UI 脉冲/火星用它决定动画开关）。 */
    bool IsBurning(const AVoxelBuildWorld* World,FIntVector Cell) const;
    double RemainingSeconds(const AVoxelBuildWorld* World,FIntVector Cell) const;
    /** 投料起炉：炉内必须有存料（先加燃料再开炉）；扣矿（背包＋仓库合计口径）后写任务并起燃。
     *  Batch=批量数（2026-09-24 用户"是否有批量冶炼功能，如果没有帮我添加"）：一次投 N 份、
     *  出 N 份产物，总时长＝配方秒×N÷炉等级速度；老调用方默认 1 行为不变。 */
    bool BeginSmelting(AVoxelBuildWorld* World,FIntVector Cell,FName Recipe,FString& Reason,int64 Batch=1);
    /** 添一份燃料：扣 1 件木材、存料 +SecondsPerUnit（封顶 Capacity）；停炉中的任务随即续燃。 */
    bool AddFuel(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason);
    /** 按钮可用性预览（不改状态）：有木材、炉子未满、目标是高炉。 */
    bool CanAddFuel(const AVoxelBuildWorld* World,FIntVector Cell) const;
    /** 取出矿锭：必须先结算且已完成、背包放得下；失败原因写进 Reason，任务保留可重试。存料留下。 */
    bool CollectSmelting(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason);
    /** 拆除/脱落退料：完成退产物、未完退原料、存料按整件折回木材；false=背包放不下（状态保留）。 */
    bool RefundForTeardown(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason);
    // —— 高炉三轴升级（VBX v9，2026-09-24 用户"添加最大燃料槽的升级、每次冶炼矿石数升级"）：
    // 轴号 VoxelFurnaceAxis{Speed,FuelCapacity,Batch}，等级各住各字段、互不影响，只影响这座炉。——
    /** 速度倍率＝1＋25%×(等级-1)，封顶 5 级（+100%）。 */
    static double SpeedMultiplier(int32 Level);
    /** 这座炉的燃料仓上限（秒）＝基础 300 ＋60×(燃料仓等级-1)，Lv5＝10 分钟。 */
    double FurnaceCapacity(const AVoxelBuildWorld* World,FIntVector Cell) const;
    /** 每次投料上限＝5×批量等级（Lv5=25 份）；面板再按持有量夹，系统兜底封顶 99。 */
    static int64 BatchCapFor(int32 Level)
    {   return 5LL*FMath::Clamp(Level,1,VoxelFurnaceMaxLevel);   }
    /** 升到下一级所需铁锭：10×当前等级；已满级返回 0。三轴同曲线。 */
    static int64 UpgradeCostFor(int32 Level);
    /** 升级指定轴：扣铁锭（背包＋仓库合计口径）后写等级。 */
    bool UpgradeFurnace(AVoxelBuildWorld* World,FIntVector Cell,FString& Reason,int32 Axis=VoxelFurnaceAxisSpeed);
    /** 升级按钮可用性预览（不改状态）：未满级且铁锭够。 */
    bool CanUpgrade(const AVoxelBuildWorld* World,FIntVector Cell,int32 Axis=VoxelFurnaceAxisSpeed) const;
    /** 任务总秒数＝配方秒×批量÷等级速度（进度分母与结算封顶同源）。 */
    double JobTotalSeconds(const AVoxelBuildWorld* World,const FVoxelSmeltingJob& Job,const FColdSteelSmeltingRecipe& R) const;
private:
    /** 实时进度秒数（不写档）：已积累 + 当前段 min(挂钟,配方剩余,存料)。无任务/无配方返回 -1。 */
    double LiveProgress(const AVoxelBuildWorld* World,FIntVector Cell,const FColdSteelSmeltingRecipe*& OutRecipe) const;
    UColdSteelStatusModel* Model() const;
    TArray<FColdSteelSmeltingRecipe> Recipes;
    FColdSteelSmeltingFuel Fuel;
};
