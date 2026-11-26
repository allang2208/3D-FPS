#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "TemperateVegetationRenderAudit.h"
#include "HAL/PlatformStackWalk.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Containers/Ticker.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "PCGComponent.h"
#include "PCGGraph.h"
#include "PCGGraphExecutionStateInterface.h"
#include "RuntimeGen/PCGGenSourceManager.h"
#include "Subsystems/PCGSubsystem.h"
#include "UnrealClient.h"

namespace
{
struct FVegetationStreamingCheck
{
    TWeakObjectPtr<UWorld> World;
    double Started=FPlatformTime::Seconds(),StageStarted=Started,NextLog=0;
    int32 Stage=0;
    FVector Entry=FVector::ZeroVector;
    TSet<TWeakObjectPtr<UObject>> HeldCells;
    TWeakObjectPtr<ACameraActor> ReviewCamera;
    FVector ReviewEye,ReviewTarget;
    int32 ReviewFrame=0;
    double NextCapture=0;
    const bool FrameAudit=FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationFrameAudit"));
    struct FObservedVegetation
    {
        FBox Bounds;
        int32 Count=0;
        FString Path;
        bool HadProxy=false;
        double Radius=2500.;
        UPTRINT ProxyAddress=0;
    };
    TMap<TWeakObjectPtr<UPrimitiveComponent>,FObservedVegetation> Observed;
    double NextObserve=0,NextAuditLog=0;
    int32 AuditSamples=0;
    bool RequestedGC=false;
    bool DetectedLoss=false;
    FDelegateHandle RenderDirtyHandle;
    TSharedPtr<FTemperateVegetationRenderAudit,ESPMode::ThreadSafe> RenderAudit;
    TSet<uint32> CallerStacks;

    ~FVegetationStreamingCheck()
    {
        if(RenderDirtyHandle.IsValid())UActorComponent::MarkRenderStateDirtyEvent.Remove(RenderDirtyHandle);
    }

    bool ObserveVegetation(UWorld* W,const FVector& Eye)
    {
        bool AllPresent=true;
        // Keep weak references: the diagnostic must not conceal a GC/lifetime bug.
        auto Near=[&](const FBox& B,double Radius)
        {
            const FVector P(Eye.X,Eye.Y,FMath::Clamp(Eye.Z,B.Min.Z,B.Max.Z));
            return B.ComputeSquaredDistanceToPoint(P)<FMath::Square(Radius);
        };
        for(const auto& Pair:Observed)
        {
            if(!Near(Pair.Value.Bounds,Pair.Value.Radius))continue; // Normal distance cleanup is allowed.
            auto* C=Pair.Key.Get();
            const auto* Static=Cast<UInstancedStaticMeshComponent>(C);
            const auto* Skinned=Cast<UInstancedSkinnedMeshComponent>(C);
            const int32 Count=Static?Static->GetInstanceCount():Skinned?Skinned->GetInstanceCount():0;
            if(FrameAudit&&C&&Pair.Value.ProxyAddress!=reinterpret_cast<UPTRINT>(C->GetSceneProxy()))
                UE_LOG(LogTemp,Display,TEXT("VEGETATION_AUDIT proxy_changed frame=%llu path=%s old=%p new=%p dirty=%d pso=%d"),
                    GFrameCounter,*Pair.Value.Path,reinterpret_cast<void*>(Pair.Value.ProxyAddress),C->GetSceneProxy(),C->IsRenderStateDirty(),C->IsPSOPrecaching());
            if(!C||!C->IsRegistered()||!C->ShouldRender()||Count<Pair.Value.Count||
                (Pair.Value.HadProxy&&!C->GetSceneProxy()))
            {
                UE_LOG(LogTemp,Error,TEXT("VEGETATION_AUDIT lost frame=%llu path=%s old_count=%d count=%d registered=%d render=%d proxy=%d eye=%s"),
                    GFrameCounter,*Pair.Value.Path,Pair.Value.Count,Count,C&&C->IsRegistered(),C&&C->ShouldRender(),C&&C->GetSceneProxy(),*Eye.ToString());
                if(!FrameAudit)FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("vegetation-audit-loss.png"),false,false);
                AllPresent=false;
            }
        }
        TMap<TWeakObjectPtr<UPrimitiveComponent>,FObservedVegetation> Current;
        FTemperateVegetationRenderAudit::FTargets RenderTargets;
        for(const auto& Pair:Observed)
            if(auto* C=Pair.Key.Get();C&&Near(Pair.Value.Bounds,Pair.Value.Radius))
                RenderTargets.Add(C->GetPrimitiveSceneId(),{Pair.Value.Path,Pair.Value.Count});
        int32 StaticCount=0,SkinnedCount=0;
        for(TObjectIterator<UPrimitiveComponent> It;It;++It)
        {
            auto* C=*It;if(C->GetWorld()!=W||!C->IsRegistered())continue;
            UObject* Mesh=nullptr;int32 Count=0,StartCull=0,EndCull=0;
            if(auto* Static=Cast<UInstancedStaticMeshComponent>(C)){Mesh=Static->GetStaticMesh();Count=Static->GetInstanceCount();Static->GetCullDistances(StartCull,EndCull);}
            else if(auto* Skinned=Cast<UInstancedSkinnedMeshComponent>(C)){Mesh=Skinned->GetSkinnedAsset();Count=Skinned->GetInstanceCount();Skinned->GetCullDistances(StartCull,EndCull);}
            if(!Mesh||!Count||!Mesh->GetPathName().StartsWith(TEXT("/Game/WorldGeneration/TemperateHills/")))continue;
            if(Cast<UInstancedStaticMeshComponent>(C))StaticCount+=Count;else SkinnedCount+=Count;
            const FBox Bounds=C->Bounds.GetBox();
            // Cover distant visible trees too, keeping a 10 m margin from their
            // configured fade endpoint. A missing endpoint retains the near test.
            const double Radius=EndCull>1000?EndCull-1000.:2500.;
            if(Near(Bounds,Radius))
            {
                Current.Add(C,{Bounds,Count,C->GetPathName(),C->GetSceneProxy()!=nullptr,Radius,reinterpret_cast<UPTRINT>(C->GetSceneProxy())});
                RenderTargets.Add(C->GetPrimitiveSceneId(),{C->GetPathName(),Count});
                if(const auto* Previous=Observed.Find(C);Previous&&
                    ((!Previous->HadProxy&&C->GetSceneProxy())||Count>Previous->Count))
                    UE_LOG(LogTemp,Display,TEXT("VEGETATION_AUDIT recovered frame=%llu path=%s count=%d proxy=%p"),
                        GFrameCounter,*C->GetPathName(),Count,C->GetSceneProxy());
            }
        }
        if(RenderAudit)RenderAudit->SetTargets(MoveTemp(RenderTargets));
        Observed=MoveTemp(Current);++AuditSamples;
        const double Now=FPlatformTime::Seconds();
        if(Now>=NextAuditLog)
        {
            NextAuditLog=Now+5;
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_AUDIT elapsed_s=%.2f frame=%llu samples=%d nearby_components=%d static_instances=%d skinned_instances=%d eye=%s"),
                Now-StageStarted,GFrameCounter,AuditSamples,Observed.Num(),StaticCount,SkinnedCount,*Eye.ToString());
        }
        return AllPresent;
    }

    bool Finish(bool Pass,const TCHAR* Reason)
    {
        if(RenderDirtyHandle.IsValid())
        {
            UActorComponent::MarkRenderStateDirtyEvent.Remove(RenderDirtyHandle);
            RenderDirtyHandle.Reset();
        }
        RenderAudit.Reset();
        UE_LOG(LogTemp,Display,TEXT("VEGETATION_CHECK pass=%d reason=%s elapsed_s=%.3f"),Pass,Reason,FPlatformTime::Seconds()-Started);
        FPlatformMisc::RequestExitWithStatus(false,Pass?0:1);return false;
    }

    // Observe the native scheduler's local execution sources, including empty
    // cells. Instance counts alone cannot distinguish a meadow from missing work.
    bool Cells(ATemperateHillsWorld& Hills,double Radius,int32 OnlyLayer,TSet<TWeakObjectPtr<UObject>>* Snapshot=nullptr)
    {
        auto* Sub=Hills.GetWorld()->GetSubsystem<UPCGSubsystem>();
        auto* Manager=Sub?Sub->GetGenSourceManager():nullptr;
        if(!Manager)return false;
        int32 Required=0,Ready=0;
        TInlineComponentArray<UPCGComponent*> Components(&Hills);
        for(const auto* Source:Manager->GetAllGenSources(Sub->GetPCGWorldActor()))
        {
            const auto Position=Source->GetPosition();
            if(!Source->IsLocal()||!Position)continue;
            // Teleport updates the pawn before the camera manager / PCG source.
            // Never use the old camera's completed cells for the new grass plot.
            if(Stage==3)
            {
                auto* PC=Hills.GetWorld()->GetFirstPlayerController();
                APawn* Pawn=PC?PC->GetPawn():nullptr;
                if(!Pawn||FVector::Dist2D(*Position,Pawn->GetActorLocation())>400.)return false;
            }
            for(int32 Layer=0;Layer<4;++Layer)
            {
                if(OnlyLayer>=0&&Layer!=OnlyLayer)continue;
                auto** Found=Components.FindByPredicate([Layer](const UPCGComponent* C){return C->GetFName()==FName(*FString::Printf(TEXT("PCGLayer%d"),Layer));});
                if(!Found||!(*Found)->GetGraph())return false;
                auto& State=(*Found)->GetExecutionState();
                const int32 Grid=(*Found)->GetGraph()->GetDefaultGridSize();
                const auto Descriptor=FPCGGridDescriptor().SetGridSize(Grid).SetIs2DGrid(true).SetIsRuntime(true);
                const double Half=Hills.SizeMeters*50.;
                for(int32 Y=FMath::FloorToInt(FMath::Max(-Half,Position->Y-Radius)/Grid);Y<=FMath::FloorToInt(FMath::Min(Half-1,Position->Y+Radius)/Grid);++Y)
                for(int32 X=FMath::FloorToInt(FMath::Max(-Half,Position->X-Radius)/Grid);X<=FMath::FloorToInt(FMath::Min(Half-1,Position->X+Radius)/Grid);++X)
                {
                    const FBox Box(FVector(X*Grid,Y*Grid,Position->Z-1),FVector((X+1)*Grid,(Y+1)*Grid,Position->Z+1));
                    if(Box.ComputeSquaredDistanceToPoint(*Position)>Radius*Radius)continue;
                    ++Required;
                    auto* Local=State.GetLocalSource(Descriptor,FIntVector(X,Y,0));
                    if(!Local||!Local->GetExecutionState().IsGenerated()||Local->GetExecutionState().IsGenerating())continue;
                    ++Ready;
                    if(Snapshot)Snapshot->Add(Cast<UObject>(Local));
                }
            }
        }
        if(FPlatformTime::Seconds()>=NextLog)
        {
            NextLog=FPlatformTime::Seconds()+5;
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CHECK progress stage=%d radius_m=%.0f layer=%d ready=%d/%d elapsed_s=%.3f"),Stage,Radius/100,OnlyLayer,Ready,Required,FPlatformTime::Seconds()-Started);
        }
        return Required>0&&Ready==Required;
    }

    bool Tick(float)
    {
        auto* W=World.Get();if(!W)return Finish(false,TEXT("world lost"));
        const double Now=FPlatformTime::Seconds();
        if(Now-StageStarted>(Stage==7?240:180))return Finish(false,TEXT("stage timed out"));
        TActorIterator<ATemperateHillsWorld> HillsIt(W);
        auto* PC=W->GetFirstPlayerController();APawn* Pawn=PC?PC->GetPawn():nullptr;
        if(!HillsIt||!Pawn)return true;
        auto& Hills=**HillsIt;
        if(!Hills.bReady||PC->IsMoveInputIgnored())return true;
        if(Stage==0)
        {
            if(!Cells(Hills,1600,-1))return Finish(false,TEXT("entry released before nearby vegetation"));
            int32 Meshes=0;
            for(const auto* List:{&Hills.Assets->Trees,&Hills.Assets->ForestSaplings,&Hills.Assets->ForestShrubs,&Hills.Assets->ForestFerns})
                for(const auto& Ref:*List)
                {
                    const auto* Mesh=Ref.Get();if(!Mesh)return Finish(false,TEXT("wind mesh missing"));
                    const auto Rest=Mesh->GetImportedBounds(),Padded=Mesh->GetBounds();
                    // Render/Nanite bounds can already exceed imported geometry,
                    // even with zero authored Z extension. Validate that extension
                    // directly; equality of the two final boxes is not required.
                    if(Padded.BoxExtent.X<=Rest.BoxExtent.X||Padded.BoxExtent.Y<=Rest.BoxExtent.Y||
                        Padded.BoxExtent.Z+.01<Rest.BoxExtent.Z||
                        !FMath::IsNearlyZero(Mesh->GetPositiveBoundsExtension().Z,.01)||
                        !FMath::IsNearlyZero(Mesh->GetNegativeBoundsExtension().Z,.01))
                    {
                        UE_LOG(LogTemp,Error,TEXT("VEGETATION_CHECK wind_mesh=%s imported=%s padded=%s positive=%s negative=%s"),
                            *Mesh->GetPathName(),*Rest.BoxExtent.ToString(),*Padded.BoxExtent.ToString(),
                            *Mesh->GetPositiveBoundsExtension().ToString(),*Mesh->GetNegativeBoundsExtension().ToString());
                        return Finish(false,TEXT("wind bounds mismatch"));
                    }
                    ++Meshes;
                }
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CHECK entry_ready_s=%.3f wind_meshes=%d"),Now-Started,Meshes);
            Entry=Pawn->GetActorLocation();Stage=1;StageStarted=Now;
        }
        else if(Stage==1&&Cells(Hills,8000,3))
        {
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CHECK grass_80m_ready_after_entry_s=%.3f"),Now-StageStarted);
            Cells(Hills,1600,-1,&HeldCells);
            FRotator Rotation=PC->GetControlRotation();Rotation.Yaw+=180;PC->SetControlRotation(Rotation);
            Stage=2;StageStarted=Now;
        }
        else if(Stage==2&&Now-StageStarted>=3)
        {
            // A first-person camera offset can cross a cell edge while turning.
            // Check the captured sources themselves, not a new camera-centered set.
            for(const auto& Cell:HeldCells)
            {
                auto* Local=Cast<IPCGGraphExecutionSource>(Cell.Get());
                if(!Local||!Local->GetExecutionState().IsGenerated()||Local->GetExecutionState().IsGenerating())
                    return Finish(false,TEXT("turning removed or regenerated nearby PCG cells"));
            }
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CHECK rotation_retained_cells=%d"),HeldCells.Num());
            PC->ConsoleCommand(TEXT("fps.Hills.VisitRainforest"));Stage=3;StageStarted=Now;
        }
        else if(Stage==3&&FVector::Dist2D(Entry,Pawn->GetActorLocation())>1000&&Cells(Hills,3200,3))
        {
            int32 Tufts=0;
            const FBox Plot(Pawn->GetActorLocation()-FVector(1600,1600,1500),Pawn->GetActorLocation()+FVector(1600,1600,1500));
            for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
            {
                if(It->GetWorld()!=W||!It->IsRegistered())continue;
                const auto Matches=[&](const auto& Ref){return Ref.Get()==It->GetStaticMesh();};
                if(Hills.Assets->RainforestGrass.ContainsByPredicate(Matches)||Hills.Assets->RainforestCarpetGrass.ContainsByPredicate(Matches))
                    Tufts+=It->GetInstancesOverlappingBox(Plot,true).Num();
            }
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CHECK rainforest_32m_ready_s=%.3f tufts_in_32m_square=%d"),Now-StageStarted,Tufts);
            if(Tufts==0)return Finish(false,TEXT("rainforest grass missing"));
            FRotator Rotation=PC->GetControlRotation();Rotation.Pitch=-18;PC->SetControlRotation(Rotation);
            FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("vegetation-check.png"),false,false);
            Stage=4;StageStarted=Now;
        }
        else if(Stage==4&&Now-StageStarted>=2)
        {
            const bool Audit=FrameAudit||FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationAudit"));
            if(!Audit&&!FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationCapture")))
                return Finish(true,TEXT("entry, expansion, rotation, rainforest"));
            ReviewEye=PC->PlayerCameraManager->GetCameraLocation();
            double Best=DBL_MAX;
            for(TObjectIterator<UInstancedSkinnedMeshComponent> It;It;++It)
            {
                if(It->GetWorld()!=W||!It->IsRegistered())continue;
                if(!Hills.Assets->Trees.ContainsByPredicate([&](const auto& Ref){return Ref.Get()==It->GetSkinnedAsset();}))continue;
                for(int32 I=0;I<It->GetInstanceCount();++I)
                {
                    FTransform T;if(!It->GetInstanceTransform(It->GetInstanceId(I),T,true))continue;
                    const double Distance=FVector::Dist2D(ReviewEye,T.GetLocation());
                    if(Distance<700||Distance>3500||Distance>=Best)continue;
                    Best=Distance;ReviewTarget=T.GetLocation()+FVector(0,0,350);
                }
            }
            if(Best==DBL_MAX)return Finish(false,TEXT("no nearby tree for visual capture"));
            if(FrameAudit)
            {
                // Retain the player's view target and first-person body/groom
                // visibility. A review camera changes the rendering conditions.
                PC->SetControlRotation((ReviewTarget-ReviewEye).Rotation());
                HeldCells.Reset();
                RenderAudit=FSceneViewExtensions::NewExtension<FTemperateVegetationRenderAudit>(W);
                for(const TCHAR* Name:{TEXT("r.PSOPrecache.ProxyCreationStrategy"),TEXT("r.InstanceCulling.OcclusionQueries"),
                    TEXT("r.StencilForLODDither"),TEXT("r.HZBOcclusion"),TEXT("r.AllowOcclusionQueries"),
                    TEXT("r.HairStrands.Enable"),TEXT("r.Nanite"),TEXT("r.Nanite.Foliage")})
                    if(const auto* Variable=IConsoleManager::Get().FindConsoleVariable(Name))
                        UE_LOG(LogTemp,Display,TEXT("VEGETATION_RENDER_CONFIG %s=%s"),Name,*Variable->GetString());
                // ASLR bases make raw caller PCs usable after this process exits.
                TArray<FStackWalkModuleInfo> Modules;
                Modules.SetNumZeroed(FPlatformStackWalk::GetProcessModuleCount());
                const int32 ModuleCount=FPlatformStackWalk::GetProcessModuleSignatures(Modules.GetData(),Modules.Num());
                for(int32 I=0;I<ModuleCount;++I)
                    UE_LOG(LogTemp,Display,TEXT("VEGETATION_RENDER_MODULE base=%016llx size=%u timestamp=%u path=%s"),
                        Modules[I].BaseOfImage,Modules[I].ImageSize,Modules[I].TimeDateStamp,Modules[I].LoadedImageName);
                RenderDirtyHandle=UActorComponent::MarkRenderStateDirtyEvent.AddLambda([this](UActorComponent& Component)
                {
                    if(!IsInGameThread()||Component.GetWorld()!=World.Get())return;
                    auto* C=Cast<UPrimitiveComponent>(&Component);
                    UObject* Mesh=nullptr;
                    if(auto* Static=Cast<UInstancedStaticMeshComponent>(C))Mesh=Static->GetStaticMesh();
                    else if(auto* Skinned=Cast<UInstancedSkinnedMeshComponent>(C))Mesh=Skinned->GetSkinnedAsset();
                    if(Mesh&&Mesh->GetPathName().StartsWith(TEXT("/Game/WorldGeneration/TemperateHills/")))
                    {
                        UE_LOG(LogTemp,Display,TEXT("VEGETATION_AUDIT render_dirty frame=%llu path=%s pso=%d proxy=%p"),
                            GFrameCounter,*C->GetPathName(),C->IsPSOPrecaching(),C->GetSceneProxy());
                        // Record raw PCs without loading symbols on the frame
                        // being diagnosed. Distinct callers are resolved later.
                        uint64 Stack[16]={};
                        const uint32 Depth=FPlatformStackWalk::CaptureStackBackTrace(Stack,UE_ARRAY_COUNT(Stack));
                        const uint32 StackId=FCrc::MemCrc32(Stack,Depth*sizeof(uint64));
                        if(!CallerStacks.Contains(StackId))
                        {
                            CallerStacks.Add(StackId);
                            FString PCs;
                            for(uint32 I=0;I<Depth;++I)PCs+=FString::Printf(TEXT(" %016llx"),Stack[I]);
                            UE_LOG(LogTemp,Display,TEXT("VEGETATION_RENDER_CALLER stack_id=%u stack=%s"),StackId,*PCs);
                        }
                        UE_LOG(LogTemp,Display,TEXT("VEGETATION_RENDER_CAUSE frame=%u counter=%llu id=%u stack_id=%u"),
                            GFrameNumber,GFrameCounter,C->GetPrimitiveSceneId().PrimIDValue,StackId);
                    }
                });
                UE_LOG(LogTemp,Display,TEXT("VEGETATION_CAPTURE first_person begin eye=%s target=%s"),*ReviewEye.ToString(),*ReviewTarget.ToString());
                Stage=7;StageStarted=Now;NextCapture=Now+3;
                return true;
            }
            auto* Camera=W->SpawnActor<ACameraActor>();
            if(!Camera)return Finish(false,TEXT("review camera spawn failed"));
            ReviewCamera=Camera;Camera->SetActorLocationAndRotation(ReviewEye,(ReviewTarget-ReviewEye).Rotation());
            PC->SetViewTarget(Camera);HeldCells.Reset();Cells(Hills,1600,-1,&HeldCells);
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CAPTURE begin eye=%s target=%s"),*ReviewEye.ToString(),*ReviewTarget.ToString());
            Stage=Audit?7:5;StageStarted=Now;NextCapture=Now+3;
        }
        else if(Stage==7)
        {
            auto* Camera=ReviewCamera.Get();if(!FrameAudit&&!Camera)return Finish(false,TEXT("audit camera lost"));
            const double Elapsed=Now-StageStarted;
            // 90 s stationary, 150 m out-and-back across 16/32/64 m grids,
            // a complete turn, then settle. Keep normal wind, AI and rendering.
            const double Offset=FrameAudit?0:Elapsed<90?0:Elapsed<120?(Elapsed-90)/30:Elapsed<150?(150-Elapsed)/30:0;
            const FVector Side=FVector::CrossProduct((ReviewTarget-ReviewEye).GetSafeNormal(),FVector::UpVector).GetSafeNormal();
            FVector Eye=ReviewEye+Side*(Offset*15000.);
            Eye.Z=Hills.Height(Eye.X,Eye.Y)+(ReviewEye.Z-Hills.Height(ReviewEye.X,ReviewEye.Y));
            FRotator Rotation=(ReviewTarget-ReviewEye).Rotation();
            if(Elapsed>=150&&Elapsed<180)Rotation.Yaw+=(Elapsed-150)*12.;
            if(FrameAudit)Eye=PC->PlayerCameraManager->GetCameraLocation();
            else Camera->SetActorLocationAndRotation(Eye,Rotation);
            if(Now>=NextObserve)
            {
                NextObserve=Now+(FrameAudit?0.:.1);
                if(!ObserveVegetation(W,Eye))
                {
                    if(!FrameAudit)return Finish(false,TEXT("nearby vegetation lifetime/render-state changed"));
                    DetectedLoss=true; // Keep recording the disappearance and recovery.
                }
            }
            if(!RequestedGC&&Elapsed>=45)
            {
                RequestedGC=true;GEngine->ForceGarbageCollection(true);
                UE_LOG(LogTemp,Display,TEXT("VEGETATION_AUDIT requested GC while stationary"));
            }
            if(Now>=NextCapture&&!FScreenshotRequest::IsScreenshotRequested())
            {
                FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/FString::Printf(TEXT("vegetation-audit-%03d.png"),ReviewFrame++),false,false);
                if(FrameAudit)UE_LOG(LogTemp,Display,TEXT("VEGETATION_FRAME_CAPTURE image=%d frame=%llu elapsed_s=%.4f"),ReviewFrame-1,GFrameCounter,Elapsed);
                NextCapture=Now+(FrameAudit?0.:1.);
            }
            if(Elapsed>=(FrameAudit?90:210))
            {
                UE_LOG(LogTemp,Display,TEXT("VEGETATION_AUDIT complete samples=%d captures=%d"),AuditSamples,ReviewFrame);
                return Finish(!DetectedLoss,FrameAudit?TEXT("stationary frame capture and GC; images require review"):TEXT("entry, expansion, stationary GC, 150m streaming route, rotation; images require review"));
            }
        }
        else if(Stage==5&&Now>=NextCapture)
        {
            if(ReviewFrame>=120){Stage=6;StageStarted=Now;return true;}
            if(FScreenshotRequest::IsScreenshotRequested())return true;
            auto* Camera=ReviewCamera.Get();if(!Camera)return Finish(false,TEXT("review camera lost"));
            // First 40 frames hold still, then move 4 m sideways and back while
            // tracking the same tree. Capture timing is excluded from load timing.
            const double Offset=ReviewFrame<40?0:ReviewFrame<80?(ReviewFrame-40)/39.:(119-ReviewFrame)/39.;
            const FVector Side=FVector::CrossProduct((ReviewTarget-ReviewEye).GetSafeNormal(),FVector::UpVector).GetSafeNormal();
            const FVector Eye=ReviewEye+Side*(Offset*400.);
            Camera->SetActorLocationAndRotation(Eye,(ReviewTarget-Eye).Rotation());
            const FString File=FPaths::ProjectSavedDir()/FString::Printf(TEXT("vegetation-tree-%03d.png"),ReviewFrame++);
            FScreenshotRequest::RequestScreenshot(File,false,false);NextCapture=Now+.05;
        }
        else if(Stage==6&&Now-StageStarted>=2)
        {
            for(const auto& Cell:HeldCells)
            {
                auto* Local=Cast<IPCGGraphExecutionSource>(Cell.Get());
                if(!Local||!Local->GetExecutionState().IsGenerated())return Finish(false,TEXT("camera movement removed nearby PCG cells"));
            }
            UE_LOG(LogTemp,Display,TEXT("VEGETATION_CAPTURE frames=%d retained_cells=%d"),ReviewFrame,HeldCells.Num());
            return Finish(true,TEXT("entry, expansion, rotation, rainforest, capture"));
        }
        return true;
    }
};

FAutoConsoleCommandWithWorld VegetationCheck(TEXT("fps.Test.HillsVegetationStreaming"),TEXT("Check hills loading in an isolated offscreen game."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationCheck")))return;
        auto Check=MakeShared<FVegetationStreamingCheck>();Check->World=W;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Check](float Dt){return Check->Tick(Dt);}),
            (FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationCapture"))||FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationAudit"))||FParse::Param(FCommandLine::Get(),TEXT("HillsVegetationFrameAudit")))?0.f:.25f);
    }));
}
#endif
