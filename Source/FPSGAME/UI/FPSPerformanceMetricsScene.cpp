#include "FPSPerformanceMetrics.h"
#include "ColdSteelWeaponIcons.h"
#include "../Dungeons/AuthoredDungeonGenerator.h"
#include "Engine/GameInstance.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicRHI.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/DateTime.h"
#include "NiagaraComponent.h"
#include "Particles/ParticleSystemComponent.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "SceneView.h"

namespace
{
void ReadGeometry(UPrimitiveComponent* Primitive, FFPSComponentCost& Out)
{
    if (const auto* Static = Cast<UStaticMeshComponent>(Primitive))
    {
        Out.ForcedLodModel = Static->ForcedLodModel;
        Out.ComponentMinLod = Static->MinLOD;
        Out.bOverrideMinLod = Static->bOverrideMinLOD;
        Out.Kind = TEXT("静态网格");
        if (const auto* Instances = Cast<UInstancedStaticMeshComponent>(Static))
        {
            Out.bInstanced = true;
            Out.Instances = Instances->GetInstanceCount();
            Out.Kind = TEXT("实例网格");
        }
        if (const UStaticMesh* Mesh = Static->GetStaticMesh())
        {
            Out.Detail = Mesh->GetPathName();
            Out.bHasNaniteData = Mesh->HasValidNaniteData();
            const int32 LODCount = Mesh->GetNumLODs();
            Out.bHasGeometry = LODCount > 0 && Mesh->HasValidRenderData();
            if (Out.bHasGeometry)
            {
                Out.Triangles = FMath::Max(0, Mesh->GetNumTriangles(0));
                Out.Vertices = FMath::Max(0, Mesh->GetNumVertices(0));
                for (int32 LOD = 0; LOD < LODCount; ++LOD)
                    Out.LODTriangles.Add(FMath::Max(0, Mesh->GetNumTriangles(LOD)));
            }
        }
    }
    else if (const auto* Skeletal = Cast<USkeletalMeshComponent>(Primitive))
    {
        Out.Kind = TEXT("骨骼网格");
        if (const USkeletalMesh* Mesh = Skeletal->GetSkeletalMeshAsset())
        {
            Out.Detail = Mesh->GetPathName();
            if (const FSkeletalMeshRenderData* Data = Mesh->GetResourceForRendering())
            {
                Out.bHasGeometry = !Data->LODRenderData.IsEmpty();
                for (int32 LOD = 0; LOD < Data->LODRenderData.Num(); ++LOD)
                {
                    const FSkeletalMeshLODRenderData& Lod = Data->LODRenderData[LOD];
                    int64 Triangles = 0;
                    for (const FSkelMeshRenderSection& Section : Lod.RenderSections)
                        Triangles += Section.NumTriangles;
                    Out.LODTriangles.Add(Triangles);
                    if (LOD == 0) { Out.Triangles = Triangles; Out.Vertices = Lod.GetNumVertices(); }
                }
            }
        }
    }
    else if (const auto* Dynamic = Cast<UDynamicMeshComponent>(Primitive))
    {
        Out.Kind = TEXT("动态网格");
        Out.Detail = TEXT("CPU 源网格；渲染后处理/实际提交几何未采集");
        Out.bDynamicGeometry = true;
        Dynamic->ProcessMesh([&Out](const UE::Geometry::FDynamicMesh3& Mesh)
        {
            Out.Triangles = Mesh.TriangleCount();
            Out.Vertices = Mesh.VertexCount();
            Out.bHasGeometry = true;
        });
    }
}

FString CVarValue(const TCHAR* Name)
{
    if (const IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(Name))
        return Variable->GetString();
    return TEXT("未知");
}
}

void UFPSPerformanceMetricsSubsystem::ScanComponent(UActorComponent* Component, const FVector& ViewLocation,
    const AActor* ViewActor, const FConvexVolume* Frustum, FFPSComponentCost& Out) const
{
    Out.Component = Component;
    Out.Owner = Component->GetOwner();
    Out.ClassName = Component->GetClass()->GetName();
    Out.ObjectPath = Component->GetPathName();
    Out.bRegistered = Component->IsRegistered();
    Out.Label = Out.Owner.IsValid()
        ? FString::Printf(TEXT("%s · %s"), *Out.Owner->GetActorNameOrLabel(), *Component->GetName())
        : Component->GetName();
    const auto* Scene = Cast<USceneComponent>(Component);
    Out.bVisible = Out.bRegistered && Scene && Scene->IsVisible() && !Scene->bHiddenInGame
        && (!Out.Owner.IsValid() || !Out.Owner->IsHidden());
    Out.bViewVisibilityKnown = ViewActor != nullptr;
    Out.bVisibleToView = Out.bVisible;
    Out.bHasFrustum = Frustum != nullptr;
    if (Scene)
    {
        const FBoxSphereBounds Bounds = Scene->GetBounds();
        Out.DistanceMeters = FVector::Distance(Bounds.Origin, ViewLocation) / 100.f;
        Out.bOnScreen = Frustum && Frustum->IntersectBox(Bounds.Origin, Bounds.BoxExtent);
    }
    if (auto* Primitive = Cast<UPrimitiveComponent>(Component))
    {
        const bool bOwnedByView = ViewActor && Out.Owner.IsValid()
            && (Out.Owner.Get() == ViewActor || Out.Owner->IsOwnedBy(ViewActor));
        if (ViewActor)
        {
            Out.bVisibleToView &= !Primitive->bOwnerNoSee || !bOwnedByView;
            Out.bVisibleToView &= !Primitive->bOnlyOwnerSee || bOwnedByView;
        }
        Out.bCastsShadow = Primitive->CastShadow;
        Out.bHiddenShadowEligible = Out.bRegistered && Out.bViewVisibilityKnown
            && !Out.bVisibleToView && Primitive->CastShadow && Primitive->bCastHiddenShadow;
        Out.MaterialSlots = Primitive->GetNumMaterials();
        ReadGeometry(Primitive, Out);
    }
    if (Out.bHasGeometry && Out.bRegistered && Out.Instances > 0)
    {
        // Deliberately a source-complexity score, independent of camera and truncation.
        // No visibility/LOD/GPU cost is inferred from distance or material slot count.
        Out.Rank = static_cast<float>((Out.Triangles + Out.Vertices * .1
            + Out.MaterialSlots * 2500.0) * Out.Instances);
    }
}

FFPSPerformanceSnapshot UFPSPerformanceMetricsSubsystem::BuildSnapshot(int32 MaxEntries, APlayerController* Viewer)
{
    const double Start = FPlatformTime::Seconds();
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Performance_Snapshot);
    FFPSPerformanceScope SnapshotScope(this,TEXT("Panel.Snapshot"));
    FFPSPerformanceSnapshot Snapshot;
    UWorld* World = GetWorld();
    if (!World) return Snapshot;
    ReadWindow(Snapshot, Start);
    if (auto* Instance = World->GetGameInstance())
        if (auto* Icons = Instance->GetSubsystem<UColdSteelWeaponIcons>()) Snapshot.IconTask = Icons->GetPerformanceState();
    Snapshot.CapturedAtUtc = FDateTime::UtcNow().ToIso8601();
    if (!Viewer || Viewer->GetWorld() != World) Viewer = World->GetFirstPlayerController();
    FVector ViewLocation = FVector::ZeroVector;
    FRotator ViewRotation = FRotator::ZeroRotator;
    const AActor* ViewActor = Viewer ? Viewer->GetViewTarget() : nullptr;
    FConvexVolume Frustum;
    FIntPoint ViewportSize = FIntPoint::ZeroValue;
    Snapshot.bHasView = ViewActor != nullptr;
    if (Viewer)
    {
        Viewer->GetPlayerViewPoint(ViewLocation, ViewRotation);
        if (const ULocalPlayer* LocalPlayer = Viewer->GetLocalPlayer())
        {
            if (LocalPlayer->ViewportClient && LocalPlayer->ViewportClient->Viewport)
            {
                FViewport* Viewport = LocalPlayer->ViewportClient->Viewport;
                ViewportSize = Viewport->GetSizeXY();
                FSceneViewProjectionData Projection;
                Snapshot.bHasProjection = LocalPlayer->GetProjectionData(Viewport, Projection);
                if (Snapshot.bHasProjection)
                    GetViewFrustumBounds(Frustum, Projection.ComputeViewProjectionMatrix(), true);
            }
        }
    }
    Snapshot.Environment = FString::Printf(
        TEXT("%s · %s · World=%s · %s · %d×%d\n位置 %s · 朝向 %s · FOV %.1f\nScreenPercentage=%s · VSync=%s · MaxFPS=%s · 暂停=%s"),
        World->WorldType == EWorldType::PIE ? TEXT("PIE（线程数据含编辑器/其它视口）") : TEXT("Game"),
        *World->GetMapName(), *World->GetPathName(), GDynamicRHI ? GDynamicRHI->GetName() : TEXT("RHI 未知"),
        ViewportSize.X, ViewportSize.Y, *ViewLocation.ToCompactString(), *ViewRotation.ToCompactString(),
        Viewer && Viewer->PlayerCameraManager ? Viewer->PlayerCameraManager->GetFOVAngle() : 0.f,
        *CVarValue(TEXT("r.ScreenPercentage")), *CVarValue(TEXT("r.VSync")), *CVarValue(TEXT("t.MaxFPS")),
        World->IsPaused() ? TEXT("是") : TEXT("否"));

    TArray<FFPSComponentCost> Costs;
    for(const TCHAR* Name : {TEXT("r.Shadow.Virtual.Enable"), TEXT("r.RayTracing.Shadows"),
        TEXT("r.MegaLights.Enable"), TEXT("r.MegaLights.Allow"), TEXT("r.Lumen.HardwareRayTracing"),
        TEXT("r.DynamicGlobalIlluminationMethod"), TEXT("r.ReflectionMethod"),
        TEXT("r.VolumetricFog"), TEXT("r.LightMaxDrawDistanceScale"), TEXT("sg.ShadowQuality"),
        TEXT("sg.GlobalIlluminationQuality"), TEXT("sg.ReflectionQuality"),
        TEXT("fps.Dungeon.Lighting.Optimize"), TEXT("fps.Dungeon.Lighting.RoomCulling")})
        Snapshot.LightingCVars.Add(Name, CVarValue(Name));
    FFPSPerformanceCoverage& Coverage = Snapshot.Coverage;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (!IsValid(*It)) continue;
        ++Snapshot.ActorCount;
        if (const auto* Dungeon=Cast<AAuthoredDungeonGenerator>(*It))
        {
            FString Report=Dungeon->GetGenerationMetricsJson();
            if(!Report.IsEmpty())Snapshot.DungeonGenerationReports.Add(MoveTemp(Report));
        }
        TInlineComponentArray<UActorComponent*> Components;
        It->GetComponents(Components);
        for (UActorComponent* Component : Components)
        {
            if (!IsValid(Component)) continue;
            ++Snapshot.ComponentCount;
            if (const auto* Light = Cast<ULightComponent>(Component))
            {
                ScanLight(Light, ViewLocation, Snapshot.bHasProjection ? &Frustum : nullptr, Snapshot);
            }
            if (const auto* Sky = Cast<USkyLightComponent>(Component))
            {
                FFPSSkyLightObservation Row;
                Row.ObjectPath=Sky->GetPathName();Row.Intensity=Sky->Intensity;
                Row.Source=Sky->SourceType==SLS_CapturedScene?TEXT("captured_scene"):TEXT("specified_cubemap");
                Row.bEnabled=Sky->IsRegistered()&&Sky->IsVisible()&&!Sky->bHiddenInGame&&!It->IsHidden()&&Sky->bAffectsWorld&&Sky->Intensity>0.f;
                Row.bRealTimeCapture=Sky->bRealTimeCapture;Row.bCastsShadows=Sky->CastShadows;
                ++Coverage.SkyLights;Coverage.EnabledSkyLights+=Row.bEnabled?1:0;
                Coverage.RealTimeSkyCaptures+=Row.bEnabled&&Row.bRealTimeCapture?1:0;
                Snapshot.SkyLights.Add(MoveTemp(Row));
            }
            if (const auto* Audio = Cast<UAudioComponent>(Component))
            {
                ++Coverage.AudioComponents;
                if (Audio->IsPlaying()) ++Coverage.PlayingAudio;
            }
            if (const auto* Niagara = Cast<UNiagaraComponent>(Component))
            {
                ++Coverage.NiagaraComponents;
                if (Niagara->IsRegistered() && Niagara->IsActive()) ++Coverage.ActiveNiagara;
            }
            if (const auto* Cascade = Cast<UParticleSystemComponent>(Component))
            {
                ++Coverage.CascadeComponents;
                Coverage.CascadeParticles += Cascade->GetNumActiveParticles();
            }
            auto* Primitive = Cast<UPrimitiveComponent>(Component);
            if (!Primitive) continue;
            FFPSComponentCost Cost;
            ScanComponent(Component, ViewLocation, ViewActor, Snapshot.bHasProjection ? &Frustum : nullptr, Cost);
            if (Cost.bHiddenShadowEligible) ++Coverage.HiddenShadowEligible;
            if (const auto* Skeletal = Cast<USkeletalMeshComponent>(Component))
            {
                ++Coverage.SkeletalComponents;
                const bool HasAsset = Skeletal->GetSkeletalMeshAsset() != nullptr;
                const bool Ticks = HasAsset && Skeletal->IsRegistered() && Skeletal->IsComponentTickEnabled();
                if (HasAsset) { ++Coverage.SkeletalWithAsset; Coverage.TotalAssetBones += Skeletal->GetNumBones(); }
                if (Ticks) ++Coverage.SkeletalTickEnabled;
                if (Skeletal->LeaderPoseComponent.IsValid()) ++Coverage.SkeletalLeaderFollowers;
                if (Skeletal->VisibilityBasedAnimTickOption == EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones)
                {
                    ++Coverage.AlwaysRefreshConfigured;
                    if (Ticks) ++Coverage.TickEnabledAlwaysRefresh;
                }
                else if (Skeletal->VisibilityBasedAnimTickOption == EVisibilityBasedAnimTickOption::AlwaysTickPose)
                    ++Coverage.AlwaysPoseConfigured;
            }
            if (Cost.bInstanced) { ++Coverage.InstancedComponents; Coverage.Instances += Cost.Instances; }
            if (Cost.bDynamicGeometry) ++Coverage.DynamicMeshes;
            if (!Cost.Kind.IsEmpty() && !Cost.bHasGeometry) ++Coverage.GeometryUnavailable;
            if (Cost.Kind.IsEmpty() && !Component->IsA<UNiagaraComponent>() && !Component->IsA<UParticleSystemComponent>())
                ++Coverage.OtherPrimitives;
            if (Cost.Rank > 0.f)
            {
                Snapshot.AllRankTotal += Cost.Rank;
                Costs.Add(MoveTemp(Cost));
            }
        }
    }
    Snapshot.Lights.Sort([bHasView=Snapshot.bHasView](const FFPSLightObservation& A, const FFPSLightObservation& B)
    {
        if (A.bViewCandidate != B.bViewCandidate) return A.bViewCandidate;
        if (A.bEnabled != B.bEnabled) return A.bEnabled;
        if (!bHasView) return A.ObjectPath < B.ObjectPath;
        return A.DistanceCm == B.DistanceCm ? A.ObjectPath < B.ObjectPath : A.DistanceCm < B.DistanceCm;
    });
    Costs.Sort([](const FFPSComponentCost& A, const FFPSComponentCost& B)
    {
        return A.Rank == B.Rank ? A.ObjectPath < B.ObjectPath : A.Rank > B.Rank;
    });
    Snapshot.RankedMeshCount = Costs.Num();
    TMap<FString, int32> AssetIndices;
    for (FFPSComponentCost& Cost : Costs)
    {
        if (!Cost.bDynamicGeometry && !Cost.Detail.IsEmpty())
        {
            int32* Found = AssetIndices.Find(Cost.Detail);
            const int32 Index = Found ? *Found : Snapshot.MeshAssets.AddDefaulted();
            if (!Found) AssetIndices.Add(Cost.Detail, Index);
            auto& Asset = Snapshot.MeshAssets[Index];
            Asset.Asset = Cost.Detail;
            ++Asset.Components;
            Asset.Instances += Cost.Instances;
            Asset.SourceLod0Triangles += Cost.Triangles * Cost.Instances;
            Asset.SourceComplexity += Cost.Rank;
            Asset.ViewEligibleComponents += Cost.bViewVisibilityKnown && Cost.bVisibleToView ? 1 : 0;
            Asset.FrustumCandidates += Cost.bHasFrustum && Cost.bOnScreen && Cost.bVisibleToView ? 1 : 0;
        }
        Cost.ShareOfAll = Cost.Rank / Snapshot.AllRankTotal;
        Cost.ShareOfTop = Cost.Rank / Costs[0].Rank;
    }
    Snapshot.MeshAssets.Sort([](const FFPSMeshAssetSummary& A, const FFPSMeshAssetSummary& B)
    { return A.SourceComplexity == B.SourceComplexity ? A.Asset < B.Asset : A.SourceComplexity > B.SourceComplexity; });
    if (MaxEntries > 0 && Costs.Num() > MaxEntries) Costs.SetNum(MaxEntries);
    for (const FFPSComponentCost& Cost : Costs) Snapshot.DisplayedRankTotal += Cost.Rank;
    Snapshot.Costs = MoveTemp(Costs);
    const double End = FPlatformTime::Seconds();
    Snapshot.ScanMs = static_cast<float>((End - Start) * 1000.0);
    AddObserverSample(ScanSamples, Snapshot.ScanMs, End);
    Snapshot.Budget.Scan = ObserverStats(ScanSamples, End - WindowSeconds);
    Snapshot.Budget.UiUpdate = ObserverStats(UiSamples, End - WindowSeconds);
    return Snapshot;
}
