#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FPSPerformanceMetrics.generated.h"

class UActorComponent;
class UPrimitiveComponent;

/** 一个组件对渲染的贡献。数值全部从组件与网格资产真实读取，不是常量估算；
 *  只有 Rank 是加权推导出来的排序分。 */
USTRUCT()
struct FFPSComponentCost
{
    GENERATED_BODY()
    /** 各 LOD 的三角面数，索引 0 即 LOD0。骨骼网格专用。
     *  用途是回答「这个网格在远处能以多少面渲染」——联机时每个远端玩家
     *  都会走这条 LOD 链，链越短或末端越重，多玩家场景的开销就越难压。
     *  静态网格不走这里（UStaticMesh 有 GetNumTriangles(LOD) 直接可查）。 */
    UPROPERTY() TArray<int64> LODTriangles;
    /** 排序用的加权分。跨平台可比，但绝对值没有物理单位，只用于相对排序。 */
    UPROPERTY() float Rank = 0.f;
    /** 占榜首 Rank 的比例（榜首为 1.0）。面板用它在行首画占比条，
     *  与 `Rank / 总和` 的占比不同：它表达「和最大的那个差多少」。 */
    UPROPERTY() float ShareOfTop = 0.f;
    /** 组件所属 Actor。 */
    UPROPERTY() TWeakObjectPtr<AActor> Owner;
    UPROPERTY() TWeakObjectPtr<UActorComponent> Component;
    /** 显示名：Actor 名 + 组件名，重复时在面板里再区分。 */
    UPROPERTY() FString Label;
    /** 组件类名，用于按类聚合。 */
    UPROPERTY() FString ClassName;
    /** 组件中心到摄像机的距离（米）。 */
    UPROPERTY() float DistanceMeters = 0.f;
    /** 视锥内判定结果，供面板区分「在画面里」与「在背后」。 */
    UPROPERTY() bool bOnScreen = false;
    /** 是否投射阴影——阴影项是 GPU 上的大头，单独标记。 */
    UPROPERTY() bool bCastsShadow = false;
    UPROPERTY() bool bVisible = false;
    /** 网格三角形与顶点数；光源/粒子等非网格组件为 0。
     *  Nanite 开关无法在独立构建里读取（编辑器专用接口），故不设该维度。 */
    UPROPERTY() int64 Triangles = 0;
    UPROPERTY() int64 Vertices = 0;
    UPROPERTY() int32 MaterialSlots = 0;
    /** 参与渲染的图元数量：光源 1、粒子按发射器数、音频不参与。 */
    UPROPERTY() int32 Primitives = 0;
    /** 粒子系统当前存活粒子数。 */
    UPROPERTY() int32 Particles = 0;
    /** 该组件消耗的渲染类别，面板用它做过滤与误导排查。 */
    UPROPERTY() FString Kind;
    /** 人类可读的开销构成，例如 "1.2M tri · 3 mat · shadow"。 */
    UPROPERTY() FString Detail;
};

/** 帧预算。取自引擎自身的统计量，与 `stat unit` 同源。
 *  Game/Draw 是真实线程耗时；它们与 GPU 时间在时间轴上**重叠**，
 *  不得相加当作 CPU 计算耗时。 */
USTRUCT()
struct FFPSFrameBudget
{
    GENERATED_BODY()
    /** 帧时间，取引擎的 GAverageMS 指数平均。 */
    UPROPERTY() float FrameMs = 0.f;
    /** 游戏线程耗时（不含空闲）。 */
    UPROPERTY() float GameMs = 0.f;
    /** 渲染线程耗时（不含空闲）。 */
    UPROPERTY() float DrawMs = 0.f;
    /** 游戏线程关键路径：含依赖等待，比 GameMs 更能反映卡顿。 */
    UPROPERTY() float GameCriticalMs = 0.f;
    /** 渲染线程关键路径。 */
    UPROPERTY() float DrawCriticalMs = 0.f;
    /** RHI 线程耗时。 */
    UPROPERTY() float RhiMs = 0.f;
    /** 主线程空闲等待；偏高说明被渲染或 RHI 拖住。 */
    UPROPERTY() float GameWaitMs = 0.f;
    /** GPU 帧时间，RHI 报告时才有。 */
    UPROPERTY() float GpuMs = 0.f;
    UPROPERTY() bool bHasGpu = false;
    /** 帧率，直接取引擎的 GAverageFPS。 */
    UPROPERTY() float Fps = 0.f;
    /** 面板自己按帧采样的滚动统计。百分位用近邻法（sorted[int((n-1)*p)]），
     *  契约对齐原 Godot 性能面板，不做插值。 */
    UPROPERTY() float AverageFrameMs = 0.f;
    UPROPERTY() float P50FrameMs = 0.f;
    UPROPERTY() float P95FrameMs = 0.f;
    UPROPERTY() float P99FrameMs = 0.f;
    UPROPERTY() float PeakFrameMs = 0.f;
    /** 采样窗口内超过 16.7 ms / 33.3 ms 的帧数占比（0~1）。 */
    UPROPERTY() float Over60Pct = 0.f;
    UPROPERTY() float Over30Pct = 0.f;
    UPROPERTY() int32 SampleCount = 0;
    /** 面板自身扫描耗时的统计。采集器也要计入开销，否则「零成本观测」是假的。 */
    UPROPERTY() float MonitorAverageMs = 0.f;
    UPROPERTY() float MonitorPeakMs = 0.f;
};

/** 每帧的「引擎内部动作计数」。
 *
 *  这一组是排查游戏线程耗时最有力的工具，原因见 .cpp 里的说明：
 *  引擎不提供逐组件 tick 计时，但把「哪些昂贵的 setter 被调了多少次」
 *  数出来是可行的，而游戏线程的回归通常就藏在这些次数里
 *  （SetOwnerNoSee / SetCastShadow 各自会置脏渲染状态并触发组件重注册）。 */
USTRUCT()
struct FFPSFrameCounters
{
    GENERATED_BODY()
    /** 本帧 ApplyOwnerVisibilityFlags 实际改动标志的次数（不是调用次数）。 */
    UPROPERTY() int32 VisibilityFlagChanges = 0;
    /** 本帧装备副本重建次数（RebuildWeapons/ApplyOutfit 等）。 */
    UPROPERTY() int32 EquipmentRebuilds = 0;
    /** 本帧 CaptureEquipment（0.2 s 节流路径）执行次数。 */
    UPROPERTY() int32 EquipmentCaptures = 0;
    /** 本帧 UpdateOwnerVisibility 执行次数（相机路径每帧都来）。 */
    UPROPERTY() int32 VisibilityUpdates = 0;
    /** 世界里的骨骼网格组件数、总骨骼数——决定骨骼动画求值规模。 */
    UPROPERTY() int32 SkeletalMeshComponents = 0;
    UPROPERTY() int32 TotalBones = 0;
    /** 开着 AlwaysTickPoseAndRefreshBones 的骨骼网格数。
     *  该选项每帧强制求值骨骼变换（即使不可见），比默认贵得多。
     *  它不随装备变化，因此是「换任何武器都卡」这类现象的头号候选。 */
    UPROPERTY() int32 AlwaysRefreshBones = 0;
    /** 开着 AlwaysTickPose 的骨骼网格数（求值 pose 但不刷骨骼变换）。 */
    UPROPERTY() int32 AlwaysTickPose = 0;
    /** 只注册在阴影场景里的隐藏投影网格数（bCastHiddenShadow）。 */
    UPROPERTY() int32 HiddenShadowCasters = 0;
    /** 引擎线程耗时（毫秒），与帧预算同源，这里单列便于对照计数。 */
    UPROPERTY() float GameThreadMs = 0.f;
    UPROPERTY() float RenderThreadMs = 0.f;
    UPROPERTY() float GameThreadWaitMs = 0.f;
    UPROPERTY() float RenderThreadWaitMs = 0.f;
    /** 采样窗口内的每秒平均值，把本帧计数换算成速率才看得出「是否每帧都在跑」。 */
    UPROPERTY() float VisibilityFlagChangesPerSec = 0.f;
    UPROPERTY() float EquipmentRebuildsPerSec = 0.f;
    UPROPERTY() float VisibilityUpdatesPerSec = 0.f;
};

/** 扫描结果：帧预算 + 已排序的组件开销列表。 */
USTRUCT()
struct FFPSPerformanceSnapshot
{
    GENERATED_BODY()
    UPROPERTY() FFPSFrameBudget Budget;
    UPROPERTY() FFPSFrameCounters Counters;
    UPROPERTY() TArray<FFPSComponentCost> Costs;
    /** 参与统计的 Actor / 组件总数，面板用来显示「N / M」。 */
    UPROPERTY() int32 ActorCount = 0;
    UPROPERTY() int32 ComponentCount = 0;
    /** 扫描耗时（毫秒），让用户知道面板自身要花多少。 */
    UPROPERTY() float ScanMs = 0.f;
};

/** F6 性能监测页的数据层。
 *
 *  分成两半，来源不同，面板里也分开显示：
 *   - 帧预算：读引擎统计量，是真实的线程耗时（与 `stat unit` 同源）。
 *   - 组件开销：遍历世界的图元组件，读取真实的三角形/顶点/材质槽/阴影开关，
 *     加权成 Rank 排序。Rank 是推导值，只用于横向比较，不是毫秒。
 *
 *  引擎没有公开逐组件的 tick 计时接口（FTickTaskLevel 在 TickTaskManager.cpp 里
 *  私有，ULevel::TickTaskLevel 也是私有），所以本模块不假装能给出「某个组件的
 *  CPU 毫秒」。GPU 侧同理：MSM 不导出逐图元 GPU 耗时。面板会把这一点写在页脚，
 *  避免把 Rank 误读成毫秒。 */
UCLASS()
class FPSGAME_API UFPSPerformanceMetricsSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    /** 扫描世界。每帧调用也可，开销由面板的刷新间隔控制。 */
    FFPSPerformanceSnapshot BuildSnapshot(int32 MaxEntries);

    /** 采样帧时间。面板在 NativeTick 里按固定间隔喂进来，用于中位数与百分位。 */
    void SampleFrame(float DeltaSeconds);

    void ClearSamples();
    int32 GetSampleCount() const { return FrameSamples.Num(); }

    // ---- 引擎动作计数器：由游戏线程的代码路径自行累加 ----
    // 每个 setter 调用点只做一次 ++，不做计时（计时做不到，见类注释）。
    static void CountVisibilityFlagChange();
    static void CountEquipmentRebuild();
    static void CountEquipmentCapture();
    static void CountVisibilityUpdate();

    /** 面板可调：Rank 的权重，方便按「阴影 / 几何 / 粒子」偏好排。 */
    float ShadowWeight = 2.5f;
    float TriangleWeight = 1.f;
    float ParticleWeight = 0.05f;
    float DistanceFalloffMeters = 60.f;
    /** 关闭后 Rank 不按距离衰减，纯粹按几何量排序。 */
    bool bUseDistanceFalloff = true;
    /** 慢帧阈值（毫秒）。33.34 = 2 倍 60 FPS 帧预算，沿用原面板口径。 */
    float SlowFrameThresholdMs = 33.34f;
    /** 目标帧率，用来算「超出目标预算的帧」。 */
    float TargetFps = 60.f;

private:
    /** 计数器在全局累加，因为调用点分散在角色代码里，拿不到子系统指针。
     *  面板每次 BuildSnapshot 时读走并清零，得到「每个刷新周期」的增量。 */
    static int32 GFrameVisibilityFlagChanges;
    static int32 GFrameEquipmentRebuilds;
    static int32 GFrameEquipmentCaptures;
    static int32 GFrameVisibilityUpdates;
    /** 上一周期的帧数与秒数，用来把增量换算成每秒速率。 */
    double LastCounterReadSeconds = 0.0;
    int32 LastCounterFrames = 0;
    TArray<float> FrameSamples;
    /** 面板自身扫描耗时，用于 MonitorAverageMs / MonitorPeakMs。 */
    TArray<float> MonitorSamples;
    static constexpr int32 MaxSamples = 240;

    void ScanComponent(UActorComponent* Component, const FVector& ViewLocation,
                       const FVector& ViewForward, float CosHalfFov, FFPSComponentCost& Out) const;
    float ComputeRank(const FFPSComponentCost& Cost) const;
};