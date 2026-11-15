#pragma once

#include "PrimitiveSceneProxy.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "SceneViewExtension.h"

// Opt-in diagnostic only. Observe render-thread inputs after scene submission;
// do not retain UObjects/proxies or force instance-update tasks/GPU readbacks.
class FTemperateVegetationRenderAudit final : public FWorldSceneViewExtension
{
public:
    struct FTarget
    {
        FString Path;
        int32 Count=0;
    };
    using FTargets=TMap<FPrimitiveComponentId,FTarget>;

    FTemperateVegetationRenderAudit(const FAutoRegister& AutoRegister,UWorld* World)
        :FWorldSceneViewExtension(AutoRegister,World){}

    void SetTargets(FTargets&& InTargets)
    {
        // Capture the extension, not its owner or game-thread component pointers.
        auto KeepAlive=StaticCastSharedRef<FTemperateVegetationRenderAudit>(AsShared());
        ENQUEUE_RENDER_COMMAND(HillsRenderAuditTargets)(
            [KeepAlive,NewTargets=MoveTemp(InTargets)](FRHICommandListImmediate&) mutable
            {KeepAlive->Targets=MoveTemp(NewTargets);});
    }

    virtual void PostRenderViewFamily_RenderThread(FRDGBuilder&,FSceneViewFamily& Family) override
    {
        if(!Family.Scene||Targets.IsEmpty()||Family.Views.IsEmpty())return;
        // Exclude sky, scope, RVT and other offscreen capture views.
        const FSceneView* View=Family.Views[0];
        if(View->bIsSceneCapture)return;
        TMap<FPrimitiveComponentId,FState> Current;
        for(const FPrimitiveSceneProxy* Proxy:Family.Scene->GetPrimitiveSceneProxies())
        {
            if(!Proxy)continue;
            const auto Id=Proxy->GetPrimitiveComponentId();
            const FTarget* Target=Targets.Find(Id);
            if(!Target)continue;
            const auto Header=Proxy->GetInstanceDataHeader();
            const auto& Bounds=Proxy->GetBounds();
            FState State;
            State.Proxy=reinterpret_cast<UPTRINT>(Proxy);
            State.Count=Header.NumInstances;
            State.Shown=Proxy->IsShown(View);
            State.InFrustum=View->ViewFrustum.IntersectBox(Bounds.Origin,Bounds.BoxExtent);
            State.ValidBounds=!Bounds.Origin.ContainsNaN()&&!Bounds.BoxExtent.ContainsNaN()&&
                FMath::IsFinite(Bounds.SphereRadius)&&Bounds.SphereRadius>0;
            State.Nanite=Proxy->IsNaniteMesh();
            Current.Add(Id,State);
        }
        int32 Missing=0,Hidden=0,Empty=0,Outside=0;
        for(const auto& Pair:Targets)
        {
            const FState State=Current.FindRef(Pair.Key);
            const FState* Previous=Last.Find(Pair.Key);
            Missing+=State.Proxy==0;Hidden+=State.Proxy&&!State.Shown;
            Empty+=State.Proxy&&State.Count==0;Outside+=State.Proxy&&!State.InFrustum;
            // Baseline once, then changes only. Missing proxies remain in Last so
            // recovery is explicit and pointer reuse cannot conceal a gap.
            if(!Previous||!State.Equals(*Previous))
                UE_LOG(LogTemp,Display,TEXT("VEGETATION_RENDER frame=%u id=%u path=%s proxy=%p instances=%d expected_gt=%d shown=%d frustum=%d bounds_valid=%d nanite=%d camera_cut=%d"),
                    Family.FrameNumber,Pair.Key.PrimIDValue,*Pair.Value.Path,reinterpret_cast<void*>(State.Proxy),
                    State.Count,Pair.Value.Count,State.Shown,State.InFrustum,State.ValidBounds,State.Nanite,View->bCameraCut);
            Current.FindOrAdd(Pair.Key)=State;
        }
        Last=MoveTemp(Current);
        if(Family.FrameNumber>=NextSummary)
        {
            NextSummary=Family.FrameNumber+120;
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_RENDER_FRAME frame=%u targets=%d missing=%d hidden=%d empty=%d outside_frustum=%d"),
                Family.FrameNumber,Targets.Num(),Missing,Hidden,Empty,Outside);
        }
    }

private:
    struct FState
    {
        UPTRINT Proxy=0;
        int32 Count=0;
        bool Shown=false,InFrustum=false,ValidBounds=false,Nanite=false;
        bool Equals(const FState& Other) const
        {
            return Proxy==Other.Proxy&&Count==Other.Count&&Shown==Other.Shown&&
                InFrustum==Other.InFrustum&&ValidBounds==Other.ValidBounds&&Nanite==Other.Nanite;
        }
    };
    FTargets Targets;
    TMap<FPrimitiveComponentId,FState> Last;
    uint32 NextSummary=0;
};
