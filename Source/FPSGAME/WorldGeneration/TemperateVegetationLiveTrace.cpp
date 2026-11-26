#include "TemperateVegetationLiveTrace.h"
#include "TemperateHillsWorld.h"

#if !UE_BUILD_SHIPPING
#include "../UI/FPSGpuTraceCapture.h"
#include "TemperateVegetationRenderAudit.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformStackWalk.h"
#include "Misc/CoreDelegates.h"
#include "PCGComponent.h"

namespace HillsLiveTrace
{
// A passive trace for the real player view. Unlike HillsVegetationCheck it never
// teleports, changes the camera, forces GC, captures images or exits the process.
struct FTrace : TSharedFromThis<FTrace>
{
    struct FState
    {
        UPTRINT Proxy=0;
        int32 Count=0;
        bool Alive=false,Registered=false,Created=false,Render=false,Dirty=false,PSO=false;

        bool operator==(const FState& B) const
        {
            return Proxy==B.Proxy&&Count==B.Count&&Alive==B.Alive&&Registered==B.Registered&&
                Created==B.Created&&Render==B.Render&&Dirty==B.Dirty&&PSO==B.PSO;
        }
    };
    struct FTracked
    {
        FPrimitiveComponentId Id;
        FString Path;
        FBox Bounds=FBox(ForceInit);
        FState Last;
        double MissingSince=0;
        bool Sampled=false;
    };
    struct FPCGWatch
    {
        FDelegateHandle Start,Generated,Cleaned,Cancelled;
    };

    TWeakObjectPtr<UWorld> World;
    TMap<TWeakObjectPtr<UPrimitiveComponent>,FTracked> Tracked;
    TMap<TWeakObjectPtr<UPCGComponent>,FPCGWatch> PCG;
    TSharedPtr<FTemperateVegetationRenderAudit,ESPMode::ThreadSafe> RenderAudit;
    TWeakPtr<FFPSGpuTraceCapture,ESPMode::ThreadSafe> GpuCapture;
    FDelegateHandle EndFrameHandle,CleanupHandle,DirtyHandle;
    TSet<uint32> Stacks;
    double Started=0,Deadline=0,NextDiscovery=0,NextSummary=0;
    uint64 Samples=0;
    bool Stopped=false;
    bool OwnedByGpuCapture=false;

    ~FTrace(){Stop(TEXT("destroyed"));}

    static FState Read(UPrimitiveComponent* C)
    {
        FState S;
        if(!C)return S;
        S.Alive=true;S.Registered=C->IsRegistered();S.Created=C->IsRenderStateCreated();
        S.Render=C->ShouldRender();S.Dirty=C->IsRenderStateDirty();S.PSO=C->IsPSOPrecaching();
        S.Proxy=reinterpret_cast<UPTRINT>(C->GetSceneProxy());
        if(const auto* Static=Cast<UInstancedStaticMeshComponent>(C))S.Count=Static->GetInstanceCount();
        else if(const auto* Skinned=Cast<UInstancedSkinnedMeshComponent>(C))S.Count=Skinned->GetInstanceCount();
        return S;
    }

    void Caller(const TCHAR* Event,const FString& Path,uint32 Id)
    {
        uint64 Stack[16]={};
        const uint32 Depth=FPlatformStackWalk::CaptureStackBackTrace(Stack,UE_ARRAY_COUNT(Stack));
        const uint32 Key=FCrc::MemCrc32(Stack,Depth*sizeof(uint64));
        if(!Stacks.Contains(Key))
        {
            Stacks.Add(Key);
            FString PCs;
            for(uint32 I=0;I<Depth;++I)PCs+=FString::Printf(TEXT(" %016llx"),Stack[I]);
            UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_CALLER stack=%u pcs=%s"),Key,*PCs);
        }
        UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_EVENT event=%s frame=%u counter=%llu id=%u path=%s stack=%u"),
            Event,GFrameNumber,GFrameCounter,Id,*Path,Key);
    }

    void OnDirty(UActorComponent& Component)
    {
        if(!IsInGameThread()||Stopped)return;
        if(auto* C=Cast<UPrimitiveComponent>(&Component);C&&Tracked.Contains(C))
            Caller(TEXT("render_dirty"),C->GetPathName(),C->GetPrimitiveSceneId().PrimIDValue);
    }

    void OnPCG(UPCGComponent* C,const TCHAR* Event)
    {
        if(!Stopped&&C)Caller(Event,C->GetPathName(),0);
    }

    void Discover(UWorld* W,const FVector& Eye,double Now)
    {
        // Discover at 1 Hz, then sample cached weak components every frame.
        // Include imported meshes outside the Hills folder: folder filtering in
        // the older test could omit active grass variants entirely.
        for(TObjectIterator<UPrimitiveComponent> It;It;++It)
        {
            auto* C=*It;
            if(C->GetWorld()!=W||!C->IsRegistered())continue;
            UObject* Mesh=nullptr;
            if(auto* Static=Cast<UInstancedStaticMeshComponent>(C))Mesh=Static->GetStaticMesh();
            else if(auto* Skinned=Cast<UInstancedSkinnedMeshComponent>(C))Mesh=Skinned->GetSkinnedAsset();
            if(!Mesh||!Read(C).Render||C->Bounds.GetBox().ComputeSquaredDistanceToPoint(Eye)>FMath::Square(25000.))continue;
            if(Tracked.Contains(C))continue;
            FTracked T;T.Id=C->GetPrimitiveSceneId();T.Path=C->GetPathName();T.Bounds=C->Bounds.GetBox();
            Tracked.Add(C,MoveTemp(T));
            UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_TRACK frame=%u id=%u path=%s mesh=%s"),
                GFrameNumber,C->GetPrimitiveSceneId().PrimIDValue,*C->GetPathName(),*Mesh->GetPathName());
        }
        for(auto It=Tracked.CreateIterator();It;++It)
        {
            auto* C=It.Key().Get();
            if((!C&&It.Value().MissingSince>0&&Now-It.Value().MissingSince>5.)||
                (C&&C->Bounds.GetBox().ComputeSquaredDistanceToPoint(Eye)>FMath::Square(30000.)))
            {
                UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_UNTRACK frame=%u id=%u reason=%s"),
                    GFrameNumber,It.Value().Id.PrimIDValue,C?TEXT("outside_300m"):TEXT("destroyed_5s"));
                It.RemoveCurrent();
            }
        }
        for(auto It=PCG.CreateIterator();It;++It)if(!It.Key().IsValid())It.RemoveCurrent();
        for(TObjectIterator<UPCGComponent> It;It;++It)
        {
            auto* C=*It;
            if(C->GetWorld()!=W||PCG.Contains(C))continue;
            const auto* Original=C->GetOriginalComponent();
            if(!Original||!Cast<ATemperateHillsWorld>(Original->GetOwner()))continue;
            const TWeakPtr<FTrace> Weak=AsShared();
            FPCGWatch Watch;
            Watch.Start=C->OnPCGGraphStartGeneratingDelegate.AddLambda([Weak](UPCGComponent* P)
                {if(auto T=Weak.Pin())T->OnPCG(P,TEXT("pcg_start"));});
            Watch.Generated=C->OnPCGGraphGeneratedDelegate.AddLambda([Weak](UPCGComponent* P)
                {if(auto T=Weak.Pin())T->OnPCG(P,TEXT("pcg_generated"));});
            Watch.Cleaned=C->OnPCGGraphCleanedDelegate.AddLambda([Weak](UPCGComponent* P)
                {if(auto T=Weak.Pin())T->OnPCG(P,TEXT("pcg_cleaned"));});
            Watch.Cancelled=C->OnPCGGraphCancelledDelegate.AddLambda([Weak](UPCGComponent* P)
                {if(auto T=Weak.Pin())T->OnPCG(P,TEXT("pcg_cancelled"));});
            PCG.Add(C,Watch);
        }
    }

    void Tick()
    {
        if(Stopped)return;
        if(OwnedByGpuCapture)
        {
            const auto Capture=GpuCapture.Pin();
            if(!Capture||!Capture->IsRunning()){Stop(TEXT("gpu_capture_finished"));return;}
        }
        auto* W=World.Get();
        const double Now=FPlatformTime::Seconds();
        if(!W||Now>=Deadline){Stop(W?TEXT("duration"):TEXT("world_lost"));return;}
        const auto* PC=W->GetFirstPlayerController();
        if(!PC||!PC->PlayerCameraManager)return;
        const FVector Eye=PC->PlayerCameraManager->GetCameraLocation();
        bool TargetsChanged=Now>=NextDiscovery;
        if(TargetsChanged){NextDiscovery=Now+1.;Discover(W,Eye,Now);}
        for(auto& Pair:Tracked)
        {
            auto& T=Pair.Value;auto* C=Pair.Key.Get();
            const FState S=Read(C);
            if(C)T.Bounds=C->Bounds.GetBox();
            else if(T.MissingSince==0)T.MissingSince=Now;
            if(T.Sampled&&S==T.Last)continue;
            UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_STATE frame=%u counter=%llu id=%u baseline=%d alive=%d count=%d registered=%d created=%d render=%d proxy=%p dirty=%d pso=%d distance_m=%.1f"),
                GFrameNumber,GFrameCounter,T.Id.PrimIDValue,!T.Sampled,S.Alive,S.Count,S.Registered,S.Created,
                S.Render,reinterpret_cast<void*>(S.Proxy),S.Dirty,S.PSO,
                FMath::Sqrt(T.Bounds.ComputeSquaredDistanceToPoint(Eye))/100.);
            T.Sampled=true;T.Last=S;TargetsChanged=true;
        }
        if(TargetsChanged)
        {
            FTemperateVegetationRenderAudit::FTargets Targets;
            for(const auto& Pair:Tracked)Targets.Add(Pair.Value.Id,{Pair.Value.Path,Pair.Value.Last.Count});
            RenderAudit->SetTargets(MoveTemp(Targets));
        }
        ++Samples;
        if(Now>=NextSummary)
        {
            NextSummary=Now+1.;
            UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_FRAME frame=%u counter=%llu seconds=%.3f samples=%llu components=%d pcg=%d eye=%s rotation=%s"),
                GFrameNumber,GFrameCounter,Now-Started,Samples,Tracked.Num(),PCG.Num(),*Eye.ToString(),
                *PC->PlayerCameraManager->GetCameraRotation().ToString());
        }
    }

    void OnCleanup(UWorld* W,bool,bool){if(W==World.Get())Stop(TEXT("world_cleanup"));}

    void Stop(const TCHAR* Reason)
    {
        if(Stopped)return;
        Stopped=true;
        FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
        FWorldDelegates::OnWorldCleanup.Remove(CleanupHandle);
        UActorComponent::MarkRenderStateDirtyEvent.Remove(DirtyHandle);
        for(const auto& Pair:PCG)if(auto* C=Pair.Key.Get())
        {
            C->OnPCGGraphStartGeneratingDelegate.Remove(Pair.Value.Start);
            C->OnPCGGraphGeneratedDelegate.Remove(Pair.Value.Generated);
            C->OnPCGGraphCleanedDelegate.Remove(Pair.Value.Cleaned);
            C->OnPCGGraphCancelledDelegate.Remove(Pair.Value.Cancelled);
        }
        RenderAudit.Reset();PCG.Empty();Tracked.Empty();Stacks.Empty();
        UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_STOP reason=%s seconds=%.3f samples=%llu gpu_draw_result=unobserved"),
            Reason,FPlatformTime::Seconds()-Started,Samples);
    }

    void Start(UWorld* W,double Seconds)
    {
        World=W;Started=FPlatformTime::Seconds();Deadline=Started+Seconds;
        RenderAudit=FSceneViewExtensions::NewExtension<FTemperateVegetationRenderAudit>(W);
        EndFrameHandle=FCoreDelegates::OnEndFrame.AddSP(AsShared(),&FTrace::Tick);
        CleanupHandle=FWorldDelegates::OnWorldCleanup.AddSP(AsShared(),&FTrace::OnCleanup);
        DirtyHandle=UActorComponent::MarkRenderStateDirtyEvent.AddSP(AsShared(),&FTrace::OnDirty);
        UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_START world=%s seconds=%.0f passive=1 output=Saved/Logs/FPSGAME.log"),*W->GetPathName(),Seconds);
        for(const TCHAR* Name:{TEXT("r.PSOPrecache.ProxyCreationStrategy"),TEXT("r.InstanceCulling.OcclusionQueries"),
            TEXT("r.StencilForLODDither"),TEXT("r.HZBOcclusion"),TEXT("r.AllowOcclusionQueries"),
            TEXT("r.HairStrands.Enable"),TEXT("r.Nanite"),TEXT("r.Nanite.Foliage")})
            if(const auto* V=IConsoleManager::Get().FindConsoleVariable(Name))
                UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_CONFIG %s=%s"),Name,*V->GetString());
        TArray<FStackWalkModuleInfo> Modules;
        Modules.SetNumZeroed(FPlatformStackWalk::GetProcessModuleCount());
        const int32 Count=FPlatformStackWalk::GetProcessModuleSignatures(Modules.GetData(),Modules.Num());
        for(int32 I=0;I<Count;++I)
            UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_MODULE base=%016llx size=%u timestamp=%u path=%s"),
                Modules[I].BaseOfImage,Modules[I].ImageSize,Modules[I].TimeDateStamp,Modules[I].LoadedImageName);
    }
};

TSharedPtr<FTrace> Active;

void StartForGpuCapture(UWorld* W,const TSharedRef<FFPSGpuTraceCapture,ESPMode::ThreadSafe>& Capture)
{
    check(IsInGameThread());
    if(!W||!W->IsGameWorld()||!Capture->IsRunning())return;
    if(Active&&!Active->Stopped)
    {
        // An explicit manual trace (or another PIE world) owns its recording.
        if(Active->World!=W||!Active->OwnedByGpuCapture)return;
        Active->Stop(TEXT("gpu_capture_replaced"));
    }
    TActorIterator<ATemperateHillsWorld> Hills(W);
    if(!Hills)return;
    Active=MakeShared<FTrace>();
    Active->OwnedByGpuCapture=true;Active->GpuCapture=Capture;
    Active->Start(W,180.);
    UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_CAPTURE directory=%s"),*Capture->GetDirectory());
}

FAutoConsoleCommandWithWorldAndArgs Command(TEXT("fps.Hills.TraceFlicker"),
    TEXT("Passive hills flicker trace: [seconds=90, max=300], 0 stops, mark records a noticed flash. Does not move/capture/GC/exit."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* W)
    {
        if(!W||!W->IsGameWorld())return;
        if(Active&&!Active->Stopped&&Active->World!=W)
        {
            UE_LOG(LogTemp,Warning,TEXT("HILLS_FLICKER trace already belongs to another game world"));return;
        }
        if(!Args.IsEmpty()&&Args[0].Equals(TEXT("mark"),ESearchCase::IgnoreCase))
        {
            if(Active&&!Active->Stopped)
                UE_LOG(LogTemp,Display,TEXT("HILLS_FLICKER_MARK frame=%u counter=%llu seconds=%.3f"),
                    GFrameNumber,GFrameCounter,FPlatformTime::Seconds()-Active->Started);
            return;
        }
        const double Seconds=Args.IsEmpty()?90.:FCString::Atod(*Args[0]);
        if(Active)Active->Stop(TEXT("command"));
        Active.Reset();
        if(Seconds<=0)return;
        TActorIterator<ATemperateHillsWorld> Hills(W);
        if(!Hills){UE_LOG(LogTemp,Warning,TEXT("HILLS_FLICKER no hills world; trace not started"));return;}
        Active=MakeShared<FTrace>();Active->Start(W,FMath::Clamp(Seconds,1.,300.));
    }));
}
#endif
