#include "FPSPerformanceMetrics.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/LightComponent.h"
#include "Particles/ParticleSystemComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "RenderTimer.h"
#include "RHIUtilities.h"

extern ENGINE_API float GAverageMS;
extern ENGINE_API float GAverageFPS;

namespace
{
/** 引擎的线程计时是周期数，换算成毫秒。 */
float CyclesToMs(uint32 Cycles)
{
    return static_cast<float>(Cycles) * FPlatformTime::GetSecondsPerCycle() * 1000.f;
}

/** 取网格资产里的三角面数。
 *
 *  两条硬约束决定了只能用这几个接口：
 *   1. UStaticMesh / USkeletalMesh 都是 `MinimalAPI` 类，只有带 ENGINE_API 的
 *      方法在别的模块里可见。
 *   2. `IsNaniteEnabled()` / `GetMeshDescription()` / `GetNumImportedVertices()`
 *      都被包在 `#if WITH_EDITORONLY_DATA` 里——编辑器构建有，**独立游戏构建没有**。
 *
 *  所以静态网格用 GetNumTriangles/GetNumVertices，骨骼网格只能走运行时可见的
 *  GetResourceForRendering()。Nanite 无法在运行时判定，本面板不显示该维度。 */
void ReadMeshStats(UPrimitiveComponent* Primitive, int64& OutTriangles, int64& OutVertices,
                   TArray<int64>* OutLODTriangles)
{
    if (const auto* Static = Cast<UStaticMeshComponent>(Primitive))
    {
        if (const UStaticMesh* Mesh = Static->GetStaticMesh())
        {
            // LOD0：渲染器实际评估的那一档，作为几何量代表。
            OutTriangles = FMath::Max<int64>(Mesh->GetNumTriangles(0), 0);
            OutVertices = FMath::Max<int64>(Mesh->GetNumVertices(0), 0);
            // 静态网格的 LOD 数没有公开取数接口，用 -1 探到空为止（上限 8 档）。
            if (OutLODTriangles)
            {
                for (int32 LOD = 0; LOD < 8; ++LOD)
                {
                    const int32 Count = Mesh->GetNumTriangles(LOD);
                    if (Count < 0) break;
                    OutLODTriangles->Add(Count);
                    if (Count == 0) break;
                }
            }
        }
        return;
    }
    if (const auto* Skeletal = Cast<USkeletalMeshComponent>(Primitive))
    {
        if (const USkeletalMesh* Mesh = Skeletal->GetSkeletalMeshAsset())
        {
            if (const FSkeletalMeshRenderData* RenderData = Mesh->GetResourceForRendering())
            {
                // 逐 LOD、逐 render section 累加 NumTriangles。
                // 注意：FSkeletalMeshLODRenderData::NumTriangles 那个成员不可见，
                // 但 RenderSections 与 FSkelMeshRenderSection::NumTriangles 都是公开的，
                // 所以真实三角数是可以算出来的——不要退回用顶点数代替。
                for (int32 LOD = 0; LOD < RenderData->LODRenderData.Num(); ++LOD)
                {
                    const FSkeletalMeshLODRenderData& LODData = RenderData->LODRenderData[LOD];
                    int64 LODTriangles = 0;
                    for (const FSkelMeshRenderSection& Section : LODData.RenderSections)
                    {
                        LODTriangles += Section.NumTriangles;
                    }
                    if (LOD == 0)
                    {
                        OutTriangles = LODTriangles;
                        OutVertices = LODData.GetNumVertices();
                    }
                    if (OutLODTriangles) OutLODTriangles->Add(LODTriangles);
                }
            }
        }
    }
}
}

void UFPSPerformanceMetricsSubsystem::SampleFrame(float DeltaSeconds)
{
    // 帧时间用面板自己的实测 delta，比引擎的指数平均更能反映瞬时抖动。
    if (DeltaSeconds <= 0.f) return;
    FrameSamples.Add(DeltaSeconds * 1000.f);
    if (FrameSamples.Num() > MaxSamples) FrameSamples.RemoveAt(0, FrameSamples.Num() - MaxSamples, EAllowShrinking::No);
}

void UFPSPerformanceMetricsSubsystem::ClearSamples()
{
    FrameSamples.Reset();
    MonitorSamples.Reset();
}

namespace
{
/** 近邻法百分位：sorted[int((n-1)*p)]，与 sample_stats 的原契约一致，不做插值。
 *  样本为空时返回 0。调用方保证 Sorted 已升序。 */
float NearestRank(const TArray<float>& Sorted, float Percentile)
{
    if (Sorted.Num() == 0) return 0.f;
    const int32 Index = FMath::Clamp(
        static_cast<int32>((Sorted.Num() - 1) * Percentile), 0, Sorted.Num() - 1);
    return Sorted[Index];
}
}

int32 UFPSPerformanceMetricsSubsystem::GFrameVisibilityFlagChanges = 0;
int32 UFPSPerformanceMetricsSubsystem::GFrameEquipmentRebuilds = 0;
int32 UFPSPerformanceMetricsSubsystem::GFrameEquipmentCaptures = 0;
int32 UFPSPerformanceMetricsSubsystem::GFrameVisibilityUpdates = 0;

void UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange() { ++GFrameVisibilityFlagChanges; }
void UFPSPerformanceMetricsSubsystem::CountEquipmentRebuild() { ++GFrameEquipmentRebuilds; }
void UFPSPerformanceMetricsSubsystem::CountEquipmentCapture() { ++GFrameEquipmentCaptures; }
void UFPSPerformanceMetricsSubsystem::CountVisibilityUpdate() { ++GFrameVisibilityUpdates; }

float UFPSPerformanceMetricsSubsystem::ComputeRank(const FFPSComponentCost& Cost) const
{
    float Weight = 0.f;

    // 几何量是主要项。顶点权重较低：同样顶点数下光栅化成本主要由三角面决定。
    const float Geometry = static_cast<float>(Cost.Triangles) * TriangleWeight
                         + static_cast<float>(Cost.Vertices) * 0.1f * TriangleWeight;
    Weight += Geometry;

    // 材质槽影响绘制调用与着色器开销。
    Weight += static_cast<float>(Cost.MaterialSlots) * 2500.f;
    // 阴影是 GPU 上的大头：额外的阴影深度 pass + 阴影投射体注册。
    if (Cost.bCastsShadow && Cost.bVisible) Weight *= ShadowWeight;
    // 粒子按存活粒子数计。
    Weight += static_cast<float>(Cost.Particles) * ParticleWeight * 1000.f;

    // 视锥外的组件仍可能有阴影/距离场贡献，但不该排在最前面。
    if (!Cost.bOnScreen) Weight *= 0.15f;
    if (!Cost.bVisible) Weight *= 0.05f;

    // 距离衰减：远处同样的网格在屏幕上的像素贡献更小。
    if (bUseDistanceFalloff && DistanceFalloffMeters > 0.f)
    {
        const float Scale = FMath::Clamp(1.f - Cost.DistanceMeters / DistanceFalloffMeters, 0.1f, 1.f);
        Weight *= Scale;
    }
    return Weight;
}

void UFPSPerformanceMetricsSubsystem::ScanComponent(UActorComponent* Component, const FVector& ViewLocation,
                                                    const FVector& ViewForward, float CosHalfFov,
                                                    FFPSComponentCost& Out) const
{
    Out.Component = Component;
    Out.Owner = Component->GetOwner();
    Out.ClassName = Component->GetClass()->GetName();
    Out.bVisible = Component->IsA<USceneComponent>() && Cast<USceneComponent>(Component)->IsVisible();
    Out.Label = Out.Owner.IsValid()
        ? FString::Printf(TEXT("%s · %s"), *Out.Owner->GetActorNameOrLabel(), *Component->GetName())
        : Component->GetName();

    // 用包围盒中心而不是 Actor 原点：一个 Actor 的多个组件可能分布在很大的范围里。
    FVector Center = Component->GetOwner() ? Component->GetOwner()->GetActorLocation() : ViewLocation;
    FVector Extent = FVector::ZeroVector;
    if (const auto* Scene = Cast<USceneComponent>(Component))
    {
        const FBoxSphereBounds Bounds = Scene->GetBounds();
        Center = Bounds.Origin;
        Extent = Bounds.BoxExtent;
    }
    Out.DistanceMeters = static_cast<float>(FVector::Dist(Center, ViewLocation) / 100.0);

    // 视锥判定用「方向 + 张角」近似，不再依赖引擎的私有视锥类型。
    // 包围盒半径放宽判定，避免贴边的大件被误判成离屏。
    const FVector ToCenter = Center - ViewLocation;
    const float Distance = static_cast<float>(ToCenter.Size());
    if (Distance <= KINDA_SMALL_NUMBER)
    {
        Out.bOnScreen = true;
    }
    else
    {
        const float Radius = static_cast<float>(Extent.Size());
        const float CosAngle = static_cast<float>(FVector::DotProduct(ToCenter / Distance, ViewForward));
        // 近处一律算在画面里；远处按张角判定，留出包围盒半径的余量。
        Out.bOnScreen = Distance < 500.f
            || CosAngle > CosHalfFov - FMath::Clamp(Radius / FMath::Max(Distance, 1.f), 0.f, 1.f);
    }

    if (auto* Primitive = Cast<UPrimitiveComponent>(Component))
    {
        Out.bCastsShadow = Primitive->CastShadow;
        Out.MaterialSlots = Primitive->GetMaterialSlotNames().Num();
        Out.Primitives = 1;
        ReadMeshStats(Primitive, Out.Triangles, Out.Vertices, &Out.LODTriangles);
        Out.Kind = Out.Triangles > 0 ? TEXT("网格") : TEXT("图元");
    }

    // 光源：影响的是整片受照区域，不是自身几何，单独归类。
    if (const auto* Light = Cast<ULightComponent>(Component))
    {
        const bool bShadowed = Light->CastShadows && Out.bVisible;
        Out.Kind = bShadowed ? TEXT("光源·投影") : TEXT("光源");
        Out.bCastsShadow = bShadowed;
        // 动态光源每帧都要更新阴影与光照，比静态光源贵得多。
        Out.Primitives = Light->Mobility == EComponentMobility::Movable ? 4 : 1;
        // ELightComponentType 是共享给着色器的普通枚举，没有 UENUM 反射，只能手动映射。
        const TCHAR* TypeName = TEXT("光源");
        switch (Light->GetLightType())
        {
        case LightType_Directional: TypeName = TEXT("平行光"); break;
        case LightType_Point:       TypeName = TEXT("点光"); break;
        case LightType_Spot:        TypeName = TEXT("聚光"); break;
        case LightType_Rect:        TypeName = TEXT("矩形光"); break;
        default: break;
        }
        Out.Detail = FString::Printf(TEXT("%s · %s"), TypeName,
            Light->Mobility == EComponentMobility::Movable ? TEXT("可移动") : TEXT("静态"));
    }

    // 粒子：存活粒子数是真实开销指标。
    if (const auto* Particles = Cast<UParticleSystemComponent>(Component))
    {
        Out.Kind = TEXT("粒子");
        Out.Particles = Particles->GetNumActiveParticles();
        Out.Primitives = Particles->GetNumMaterials();
        Out.MaterialSlots = Particles->GetNumMaterials();
    }

    // 音频：播放中的音源才计入。
    if (const auto* Audio = Cast<UAudioComponent>(Component))
    {
        const bool bPlaying = Audio->IsPlaying();
        Out.Kind = bPlaying ? TEXT("音频·播放中") : TEXT("音频");
        Out.Primitives = bPlaying ? 1 : 0;
    }

    if (Out.Detail.IsEmpty())
    {
        // 显示实际网格资产名。排行里最需要回答的就是「这个组件用的是哪个网格」，
        // 光看组件名（SkeletalMeshComponent_5）无法判断成本来自哪件装备。
        if (const auto* MeshComp = Cast<UMeshComponent>(Component))
        {
            FString MeshName;
            if (const auto* Skeletal = Cast<USkeletalMeshComponent>(MeshComp))
                if (const USkeletalMesh* Asset = Skeletal->GetSkeletalMeshAsset())
                    MeshName = Asset->GetName();
            if (MeshName.IsEmpty())
                if (const auto* Static = Cast<UStaticMeshComponent>(MeshComp))
                    if (const UStaticMesh* Asset = Static->GetStaticMesh())
                        MeshName = Asset->GetName();
            if (!MeshName.IsEmpty()) Out.Detail = MeshName;
        }
        // 非网格组件（光源另有 Detail，粒子/音频走这里）退回原摘要。
        if (Out.Detail.IsEmpty())
        {
            TArray<FString> Parts;
            if (Out.Particles > 0) Parts.Add(FString::Printf(TEXT("%d 粒子"), Out.Particles));
            if (Out.MaterialSlots > 0) Parts.Add(FString::Printf(TEXT("%d 材质"), Out.MaterialSlots));
            Out.Detail = FString::Join(Parts, TEXT(" · "));
        }
    }

    Out.Rank = ComputeRank(Out);
}

FFPSPerformanceSnapshot UFPSPerformanceMetricsSubsystem::BuildSnapshot(int32 MaxEntries)
{
    const double ScanStart = FPlatformTime::Seconds();
    FFPSPerformanceSnapshot Snapshot;

    UWorld* World = GetWorld();
    if (!World) return Snapshot;

    // ---- 帧预算：读引擎统计量，与 stat unit 同一来源 ----
    FFPSFrameBudget& Budget = Snapshot.Budget;
    Budget.FrameMs = GAverageMS;
    Budget.Fps = GAverageFPS;
    Budget.GameMs = CyclesToMs(GGameThreadTime);
    Budget.DrawMs = CyclesToMs(GRenderThreadTime);
    Budget.GameCriticalMs = CyclesToMs(GGameThreadTimeCriticalPath);
    Budget.DrawCriticalMs = CyclesToMs(GRenderThreadTimeCriticalPath);
    Budget.RhiMs = CyclesToMs(GRHIThreadTime);
    Budget.GameWaitMs = CyclesToMs(GGameThreadWaitTime);
    const float GpuFrameTime = RHIGetFrameTime();
    Budget.bHasGpu = GpuFrameTime > 0.f;
    Budget.GpuMs = GpuFrameTime;

    if (FrameSamples.Num() > 0)
    {
        TArray<float> Sorted = FrameSamples;
        Sorted.Sort();
        Budget.SampleCount = Sorted.Num();
        float Sum = 0.f;
        for (float Sample : Sorted) Sum += Sample;
        Budget.AverageFrameMs = Sum / Sorted.Num();
        Budget.P50FrameMs = NearestRank(Sorted, 0.5f);
        Budget.P95FrameMs = NearestRank(Sorted, 0.95f);
        Budget.P99FrameMs = NearestRank(Sorted, 0.99f);
        Budget.PeakFrameMs = Sorted.Last();
        int32 Over60 = 0, Over30 = 0;
        // 慢帧阈值与目标帧率都是可调字段，这里按目标预算算「超预算帧」。
        const float BudgetMs = TargetFps > 0.f ? 1000.f / TargetFps : 16.7f;
        for (float Sample : Sorted)
        {
            if (Sample > BudgetMs) ++Over60;
            if (Sample > SlowFrameThresholdMs) ++Over30;
        }
        Budget.Over60Pct = static_cast<float>(Over60) / Sorted.Num();
        Budget.Over30Pct = static_cast<float>(Over30) / Sorted.Num();
    }
    if (MonitorSamples.Num() > 0)
    {
        float Sum = 0.f, Peak = 0.f;
        for (float Sample : MonitorSamples) { Sum += Sample; Peak = FMath::Max(Peak, Sample); }
        Budget.MonitorAverageMs = Sum / MonitorSamples.Num();
        Budget.MonitorPeakMs = Peak;
    }

    // ---- 组件开销：遍历图元组件，读真实几何数据 ----
    // 视点与朝向取玩家摄像机；拿不到就退回世界原点、朝 +X。
    FVector ViewLocation = FVector::ZeroVector;
    FVector ViewForward = FVector::ForwardVector;
    float CosHalfFov = 0.5f; // 约 60° 半角，够宽的保守近似
    if (const APlayerController* Controller = World->GetFirstPlayerController())
    {
        FVector CameraLocation; FRotator CameraRotation;
        Controller->GetPlayerViewPoint(CameraLocation, CameraRotation);
        ViewLocation = CameraLocation;
        ViewForward = CameraRotation.Vector();
        // FOV 取相机组件；PlayerCameraManager 不直接暴露它，拿不到就用 90° 的保守近似。
        float HalfFovDegrees = 45.f;
        if (const UCameraComponent* Camera = Cast<UCameraComponent>(
            Controller->PlayerCameraManager ? Controller->PlayerCameraManager->GetViewTarget() : nullptr))
        {
            HalfFovDegrees = Camera->FieldOfView * 0.5f;
        }
        CosHalfFov = FMath::Cos(FMath::DegreesToRadians(HalfFovDegrees));
    }
    else if (World->ViewLocationsRenderedLastFrame.Num() > 0)
    {
        ViewLocation = World->ViewLocationsRenderedLastFrame[0];
    }

    TArray<FFPSComponentCost> All;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!IsValid(Actor)) continue;
        ++Snapshot.ActorCount;
        TInlineComponentArray<UActorComponent*> Components;
        Actor->GetComponents(Components);
        for (UActorComponent* Component : Components)
        {
            if (!IsValid(Component)) continue;
            // 只统计可能影响帧的组件，避免把纯逻辑组件灌进列表。
            const bool bRelevant = Component->IsA<UPrimitiveComponent>()
                                || Component->IsA<ULightComponent>()
                                || Component->IsA<UAudioComponent>();
            if (!bRelevant) continue;
            ++Snapshot.ComponentCount;

            FFPSComponentCost Cost;
            ScanComponent(Component, ViewLocation, ViewForward, CosHalfFov, Cost);
            if (Cost.Rank <= 0.f) continue;
            All.Add(MoveTemp(Cost));
        }
    }

    All.Sort([](const FFPSComponentCost& A, const FFPSComponentCost& B) { return A.Rank > B.Rank; });
    // ShareOfTop 必须在截断之前按完整列表算，否则「占榜首比例」会随显示条数变化。
    if (All.Num() > 0 && All[0].Rank > 0.f)
    {
        const float Top = All[0].Rank;
        for (FFPSComponentCost& Cost : All) Cost.ShareOfTop = Cost.Rank / Top;
    }
    if (MaxEntries > 0 && All.Num() > MaxEntries) All.SetNum(MaxEntries);
    Snapshot.Costs = MoveTemp(All);
    Snapshot.ScanMs = static_cast<float>((FPlatformTime::Seconds() - ScanStart) * 1000.0);

    // 读走并清零计数器，换算成每秒速率。
    // 速率才是关键：每帧 1 次和每帧 60 次是完全不同的病。
    {
        FFPSFrameCounters& C = Snapshot.Counters;
        const double Now = FPlatformTime::Seconds();
        const double Elapsed = LastCounterReadSeconds > 0.0 ? Now - LastCounterReadSeconds : 0.0;
        const int32 Frames = FMath::Max(FrameSamples.Num() - LastCounterFrames, 0);
        LastCounterReadSeconds = Now;
        LastCounterFrames = FrameSamples.Num();

        C.VisibilityFlagChanges = GFrameVisibilityFlagChanges;
        C.EquipmentRebuilds = GFrameEquipmentRebuilds;
        C.EquipmentCaptures = GFrameEquipmentCaptures;
        C.VisibilityUpdates = GFrameVisibilityUpdates;
        GFrameVisibilityFlagChanges = 0;
        GFrameEquipmentRebuilds = 0;
        GFrameEquipmentCaptures = 0;
        GFrameVisibilityUpdates = 0;

        if (Elapsed > 0.01)
        {
            C.VisibilityFlagChangesPerSec = static_cast<float>(C.VisibilityFlagChanges / Elapsed);
            C.EquipmentRebuildsPerSec = static_cast<float>(C.EquipmentRebuilds / Elapsed);
            C.VisibilityUpdatesPerSec = static_cast<float>(C.VisibilityUpdates / Elapsed);
        }
        C.GameThreadMs = CyclesToMs(GGameThreadTime);
        C.RenderThreadMs = CyclesToMs(GRenderThreadTime);
        C.GameThreadWaitMs = CyclesToMs(GGameThreadWaitTime);
        C.RenderThreadWaitMs = CyclesToMs(GRenderThreadWaitTime);

        // 骨骼网格规模：骨骼动画求值是游戏线程上的固定成本，
        // 组件数与总骨骼数一起看才知道规模。
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            TInlineComponentArray<USkeletalMeshComponent*> SkeletalComps;
            It->GetComponents(SkeletalComps);
            for (const USkeletalMeshComponent* Skeletal : SkeletalComps)
            {
                if (!Skeletal) continue;
                ++C.SkeletalMeshComponents;
                C.TotalBones += Skeletal->GetNumBones();
                if (Skeletal->bCastHiddenShadow && !Skeletal->IsVisible()) ++C.HiddenShadowCasters;
                // tick 选项分布：AlwaysTickPoseAndRefreshBones 每帧强制求值骨骼变换，
                // 即使网格不可见。这是与武器无关的固定开销，重点盯它。
                switch (Skeletal->VisibilityBasedAnimTickOption)
                {
                case EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones:
                    ++C.AlwaysRefreshBones; break;
                case EVisibilityBasedAnimTickOption::AlwaysTickPose:
                    ++C.AlwaysTickPose; break;
                default: break;
                }
            }
        }
    }
    MonitorSamples.Add(Snapshot.ScanMs);
    if (MonitorSamples.Num() > MaxSamples) MonitorSamples.RemoveAt(0, MonitorSamples.Num() - MaxSamples, EAllowShrinking::No);
    return Snapshot;
}