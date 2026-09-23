#include "AuthoredDungeonLighting.h"
#include "AuthoredDungeonGenerator.h"

#include "Components/PointLightComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "SceneView.h"
#include "TimerManager.h"
#include "DungeonPerformanceScope.h"

namespace AuthoredDungeonLighting
{
static TAutoConsoleVariable<int32> Optimize(
    TEXT("fps.Dungeon.Lighting.Optimize"), 1,
    TEXT("Authored dungeon light roles and shadow policy. Applied on next generation; 0 restores legacy lights."));
static TAutoConsoleVariable<int32> RoomCulling(
    TEXT("fps.Dungeon.Lighting.RoomCulling"), 1,
    TEXT("Fade generated dungeon lights by room/portal candidates. 0 keeps all room lights enabled."));

bool IsOptimizationEnabled() { return Optimize.GetValueOnGameThread() != 0; }
}

void AAuthoredDungeonGenerator::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    CancelAssembly();
    GetWorldTimerManager().ClearTimer(RoomLightingTimer);
    LightModules.Reset();
    Super::EndPlay(EndPlayReason);
}

void AAuthoredDungeonGenerator::StartRoomLighting()
{
    if (!GetWorld()->IsGameWorld() || GetNetMode() != NM_Standalone || !bLightingOptimizationApplied) return;
    LastLightingUpdateSeconds = GetWorld()->GetTimeSeconds();
    for (auto& Module : LightModules) Module.LastWantedSeconds = LastLightingUpdateSeconds;
    GetWorldTimerManager().SetTimer(RoomLightingTimer, this, &ThisClass::UpdateRoomLighting, .1f, true);
}

void AAuthoredDungeonGenerator::UpdateRoomLighting()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Dungeon_RoomLighting);
    DungeonPerformance::FScope Scope(this, TEXT("Dungeon.RoomLighting"));
    if (LightModules.IsEmpty()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    const float Delta = FMath::Clamp(float(Now - LastLightingUpdateSeconds), 0.f, .25f);
    LastLightingUpdateSeconds = Now;
    TArray<bool> Wanted;
    Wanted.Init(true, LightModules.Num());

    APlayerController* Viewer = GetWorld()->GetFirstPlayerController();
    if (Viewer && Viewer->GetViewTarget() && bLightingOptimizationApplied
        && AuthoredDungeonLighting::RoomCulling.GetValueOnGameThread() != 0)
    {
        FVector Eye;
        FRotator Rotation;
        Viewer->GetPlayerViewPoint(Eye, Rotation);
        FConvexVolume Frustum;
        bool bHasProjection = false;
        if (const ULocalPlayer* Player = Viewer->GetLocalPlayer())
        {
            if (Player->ViewportClient && Player->ViewportClient->Viewport)
            {
                FSceneViewProjectionData Projection;
                bHasProjection = Player->GetProjectionData(Player->ViewportClient->Viewport, Projection);
                if (bHasProjection) GetViewFrustumBounds(Frustum, Projection.ComputeViewProjectionMatrix(), true);
            }
        }

        // Use occupied cells, not the broad module AABB (L-shaped rooms have empty corners).
        int32 Current = INDEX_NONE;
        double BestDistance = TNumericLimits<double>::Max();
        for (int32 Index = 0; Index < LightModules.Num(); ++Index)
            for (const FBox& Cell : LightModules[Index].Cells)
            {
                const double Distance = Cell.ComputeSquaredDistanceToPoint(Eye);
                if (Distance <= FMath::Square(100.0) && Distance < BestDistance)
                {
                    Current = Index;
                    BestDistance = Distance;
                }
            }

        // No view / outside the authored footprint: native max-draw-distance remains authoritative.
        if (bHasProjection && Current != INDEX_NONE)
        {
            Wanted.Init(false, LightModules.Num());
            TArray<int32> RoomDepth, Queue;
            RoomDepth.Init(MAX_int32, LightModules.Num());
            RoomDepth[Current] = 0;
            Queue.Add(Current);
            // Keep a full adjacent room regardless of look direction, passing through short connectors.
            for (int32 Head = 0; Head < Queue.Num(); ++Head)
            {
                const int32 Index = Queue[Head];
                Wanted[Index] = true;
                for (const auto& Portal : LightModules[Index].Portals)
                {
                    const int32 Next = Portal.Neighbor;
                    const int32 Depth = RoomDepth[Index] + (LightModules[Next].bConnector ? 0 : 1);
                    if (Depth <= 1 && Depth < RoomDepth[Next])
                    {
                        RoomDepth[Next] = Depth;
                        Queue.Add(Next);
                    }
                }
            }

            // Conservative portal candidates: do not claim occlusion or GPU visibility.
            // Door rectangles use generous margins to retain light near doorways and during quick turns.
            TArray<bool> Reached;
            Reached.Init(false, LightModules.Num());
            Queue.Reset();
            Queue.Add(Current);
            Reached[Current] = true;
            for (int32 Head = 0; Head < Queue.Num(); ++Head)
            {
                const int32 Index = Queue[Head];
                Wanted[Index] = true;
                for (const auto& Portal : LightModules[Index].Portals)
                {
                    if (Reached[Portal.Neighbor]) continue;
                    if (FVector::DistSquared(Eye, Portal.Center) < FMath::Square(200.f)
                        || Frustum.IntersectBox(Portal.Center, Portal.Extent + FVector(120.f)))
                    {
                        Reached[Portal.Neighbor] = true;
                        Queue.Add(Portal.Neighbor);
                    }
                }
            }
        }
    }

    for (int32 Index = 0; Index < LightModules.Num(); ++Index)
    {
        auto& Module = LightModules[Index];
        if (Wanted[Index]) Module.LastWantedSeconds = Now;
        const bool bKeep = Wanted[Index] || Now - Module.LastWantedSeconds < 1.0;
        for (auto& State : Module.Lights)
        {
            UPointLightComponent* Light = State.Component.Get();
            if (!Light) continue;
            const float Target = bKeep ? 1.f : 0.f;
            if (State.Alpha == Target) continue;
            State.Alpha = FMath::FInterpConstantTo(State.Alpha, Target, Delta, bKeep ? 1.f / .35f : 1.f / .8f);
            Light->SetIntensity(State.FullIntensity * FMath::SmoothStep(0.f, 1.f, State.Alpha));
            Light->SetVisibility(State.Alpha > 0.f);
        }
    }
}
