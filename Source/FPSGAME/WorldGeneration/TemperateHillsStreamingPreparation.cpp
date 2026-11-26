#include "TemperateHillsWorld.h"
#include "ForestVillageMap.h"
#include "EastRiverRoad.h"
#include "TemperateVillageGround.h"
#include "HillsNightRaidSubsystem.h"
#include "../NPC/VillageBlacksmithResident.h"
#include "../NPC/VillageCarpenterResident.h"
#include "VT/RuntimeVirtualTexture.h"
#include "TemperateHillsChapel.h"
#include "TemperateHillsPCG.h"
#include "TemperateHillsVisibility.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateHillsBackdrop.h"
#include "TemperateHillsGroundLayers.h"
#include "RiverPilotFXSubsystem.h"
#include "NiagaraSystem.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Async/Async.h"
#include "Algo/AllOf.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Animation/TransformProviderData.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Interfaces/Interface_AsyncCompilation.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "RHIGlobals.h"
#include "HAL/IConsoleManager.h"
#include "PCGGraph.h"
#include "PCGComponent.h"
#include "PCGWorldActor.h"
#include "RuntimeGen/PCGGenSourceManager.h"
#include "PCGGraphExecutionStateInterface.h"
#include "Subsystems/PCGSubsystem.h"
#include "ContentStreaming.h"
#include "RenderCommandFence.h"
#include "Misc/ScopeExit.h"
#include "UObject/GarbageCollection.h"

#include "TemperateHillsStreamingPrivate.h"
namespace HillsStreaming
{
void CountVegetationCells(UPCGComponent* Component,FVector Center,double Radius,double Half,int32& Required,int32& Complete)
{
    auto& State=Component->GetExecutionState();
    const auto* Graph=State.GetGraph();
    if(!Graph)return;
    const uint32 Grid=Graph->GetDefaultGridSize();
    if(!Grid||Grid==PCGHiGenGrid::UnboundedGridSize())return;
    const FPCGGridDescriptor Descriptor=FPCGGridDescriptor().SetGridSize(Grid).SetIs2DGrid(true).SetIsRuntime(true);
    const int32 MinX=FMath::FloorToInt(FMath::Max(-Half,Center.X-Radius)/Grid);
    const int32 MaxX=FMath::FloorToInt(FMath::Min(Half-1,Center.X+Radius)/Grid);
    const int32 MinY=FMath::FloorToInt(FMath::Max(-Half,Center.Y-Radius)/Grid);
    const int32 MaxY=FMath::FloorToInt(FMath::Min(Half-1,Center.Y+Radius)/Grid);
    for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
    {
        const double DX=FMath::Max(0.0,FMath::Abs(Center.X-(X+.5)*Grid)-Grid*.5);
        const double DY=FMath::Max(0.0,FMath::Abs(Center.Y-(Y+.5)*Grid)-Grid*.5);
        if(DX*DX+DY*DY>Radius*Radius)continue;
        ++Required;
        if(auto* Local=State.GetLocalSource(Descriptor,FIntVector(X,Y,0)))
            if(Local->GetExecutionState().IsGenerated()&&!Local->GetExecutionState().IsGenerating())++Complete;
    }
}
template<class T> void AddPaths(TArray<FSoftObjectPath>& Out,const TArray<TSoftObjectPtr<T>>& Values)
{for(const auto& V:Values)if(!V.IsNull())Out.AddUnique(V.ToSoftObjectPath());}
template<class T> bool Loaded(const TArray<TSoftObjectPtr<T>>& Values)
{return !Values.IsEmpty()&&Algo::AllOf(Values,[](const auto& V){return V.IsValid();});}

#if WITH_EDITOR
bool MaterialPending(UMaterialInterface* Material,EShaderPlatform Platform)
{
    if(!Material)return false;
    const auto* Resource=Material->GetMaterialResource(Platform);
    return Material->IsCompiling()||(Resource&&!Resource->IsCompilationFinished());
}
#endif

int32 RequiredGroundMips(const UTexture2D* Texture)
{
    const auto& State=Texture->GetStreamableResourceState();
    // Respect cooked/quality limits; optional (unmounted) mip payloads must not
    // make entry impossible. The curated ground textures use ordinary 2D mips.
    return FMath::Min(int32(State.NumNonOptionalLODs),
        FMath::Max(1,int32(State.MaxNumLODs)-Texture->NumCinematicMipLevels));
}

bool GroundTextureReady(const UTexture2D* Texture)
{
    if(!Texture||!Texture->GetResource()||Texture->HasPendingInitOrStreaming())return false;
    const auto& State=Texture->GetStreamableResourceState();
    return State.IsValid()&&State.NumResidentLODs>=RequiredGroundMips(Texture);
}
}
UMaterialInterface* ATemperateHillsWorld::GetMapGroundMaterial() const
{
    // Do not cache a map of the old shore while an edit's water plan is still computing.
    return bReady && Streaming && ForestWaterPlan && !Streaming->ForestWaterPending &&
        Streaming->ForestWaterRevision==TerrainEditRevision ? GroundMID.Get() : nullptr;
}

void ATemperateHillsWorld::CopyMapGround(TemperateHillsGround::FMapSource& Out) const
{
    const FVector2D Half(SizeMeters*50.);
    Out={Seed,GeneratorVersion,FBox2D(-Half,Half),RiverPlan,ForestWaterPlan,ChapelSite,VillageSite,TerrainEdits};
}

bool ATemperateHillsWorld::PrepareSpawnGround(AController* Controller)
{
    if(!Streaming||Streaming->Failed||!bSurfaceReady)return false;
    if(Streaming->ReadySpawnCellCount()==Streaming->SpawnCells.Num())return true;
    Streaming->WaitingToSpawn.Add(Controller);
    return false;
}

TSharedPtr<FStreamableHandle> ATemperateHillsWorld::RequestResidentAppearance(UWorld* World, TArray<FSoftObjectPath> Paths, FSimpleDelegate OnLoaded)
{
    auto& Manager=UAssetManager::GetStreamableManager();
    if(TemperateHillsChapel::IsChapelWorld(World) || ForestVillageMap::Is(World))
    {
        for(TActorIterator<ATemperateHillsWorld> It(World); It; ++It)
        {
            const FString Label=Paths.IsEmpty()?TEXT("Village resident"):Paths[0].GetAssetName();
            auto Handle=Manager.RequestAsyncLoad(MoveTemp(Paths),MoveTemp(OnLoaded),
                FStreamableManager::DefaultAsyncLoadPriority,false,true,Label);
            if(Handle)It->PendingResidentAppearances.Add(Handle);
            return Handle;
        }
    }
    return Manager.RequestAsyncLoad(MoveTemp(Paths),MoveTemp(OnLoaded));
}

void ATemperateHillsWorld::TickResidentAppearanceLoads()
{
    auto& S=*Streaming;
    if(S.Failed || S.LoadingAssets)return;
    const auto* Transit=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    const bool Full=!GUsingNullRHI && Transit && Transit->IsCompletePreloadSelected();
    if(S.StaggerVillageEntry)
    {
        const auto& Sky=S.Batches[HillsStreaming::Atmosphere];
        if(!S.Batches[HillsStreaming::GroundCover].Ready || ((Full || Sky.Requested) && !Sky.Ready))return;
    }
    // Full preload includes repaired workshops even if their residents have not spawned.
    // Normal travel uses the same view-based appearance requests as walking into town.
    if(Full && !bReady && GetNetMode()!=NM_DedicatedServer && bVillageBlacksmithRepaired && !S.SmithAppearance)
        S.SmithAppearance=RequestResidentAppearance(GetWorld(),AVillageBlacksmithResident::AppearancePaths());
    if(Full && !bReady && GetNetMode()!=NM_DedicatedServer && IsVillageCarpenterRepaired() && !S.CarpenterAppearance)
        S.CarpenterAppearance=RequestResidentAppearance(GetWorld(),AVillageCarpenterResident::AppearancePaths());

    if(PendingResidentAppearances.IsEmpty())return;
    const auto Handle=PendingResidentAppearances[0];
    if(!Handle->WasCanceled())
    {
        if(Handle->IsStalled())
        {
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP resident=%s queued=%d"),*Handle->GetDebugName(),PendingResidentAppearances.Num());
            Handle->StartStalledHandle();
            return;
        }
        if(!Handle->HasLoadCompleted())return;
#if WITH_EDITOR
        bool Compiling=false;
        Handle->ForEachLoadedAsset([&Compiling](UObject* Asset)
        {
            if(const auto* Build=Cast<IInterface_AsyncCompilation>(Asset))Compiling|=Build->IsCompiling();
        });
        if(Compiling)return;
#endif
    }
    PendingResidentAppearances.RemoveAt(0);
}

void ATemperateHillsWorld::LoadNextEnvironmentStage()
{
    using namespace HillsStreaming;
    auto& S=*Streaming;
    if(S.LoadingAssets||S.Failed||S.CompletedStages==BatchCount)return;
    auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    const bool Full=!GUsingNullRHI&&Loading&&Loading->IsCompletePreloadSelected();
    const bool RoadForest=S.StaggerVillageEntry&&Seed==TemperateHillsMap::Seed&&GeneratorVersion==TemperateHillsMap::GeneratorVersion;

    for(int32 Stage=0;Stage<BatchCount;++Stage)
    {
        auto& Batch=S.Batches[Stage];
        if(Batch.Ready)continue;
        if(S.StaggerVillageEntry && Stage>0 && !S.Batches[Stage-1].Ready)break;
        if(!Batch.Requested)
        {
            // Quick entry can defer atmosphere until existing resident loads finish.
            if(Stage==Atmosphere&&!Full&&(!bReady||(Loading&&Loading->IsHoldingGameplayInput())||
                (S.StaggerVillageEntry&&!PendingResidentAppearances.IsEmpty())))continue;
            Batch.Requested=true;
            TArray<FSoftObjectPath> Paths;
            switch(Stage)
            {
            case Solids:
                Paths.Add(Assets->Graphs[0].ToSoftObjectPath());
                Paths.Add(Assets->Graphs[1].ToSoftObjectPath());
                Paths.Add(Assets->TrunkCollisionMesh.ToSoftObjectPath());
                AddPaths(Paths,Assets->Trees);
                if(RoadForest)EastRiverRoad::AddTreePaths(Paths);
                AddPaths(Paths,Assets->Rocks);AddPaths(Paths,Assets->RiverRocks);
                AddPaths(Paths,Assets->FallenLogs);AddPaths(Paths,Assets->ForestRoots);AddPaths(Paths,Assets->Cliffs);
                Paths.Add(Assets->RainforestBankBoulder.ToSoftObjectPath());
                Paths.Append(ProductionOreRocks::AllMeshes());
                break;
            case Understory:
                Paths.Add(Assets->Graphs[2].ToSoftObjectPath());
                AddPaths(Paths,Assets->Shrubs);AddPaths(Paths,Assets->ForestSaplings);
                AddPaths(Paths,Assets->WetBankSaplings);
                AddPaths(Paths,Assets->ForestShrubs);AddPaths(Paths,Assets->ForestFerns);
                break;
            case GroundCover:
                if (GetNetMode()!=NM_DedicatedServer && TemperateHillsChapel::IsChapelWorld(GetWorld()))
                    TemperateVillageGround::AddMeshPaths(Paths);
                Paths.Add(Assets->Graphs[3].ToSoftObjectPath());
                AddPaths(Paths,Assets->Grass);AddPaths(Paths,Assets->GrassAccents);
                AddPaths(Paths,Assets->RainforestGrass);AddPaths(Paths,Assets->RainforestCarpetGrass);
                AddPaths(Paths,Assets->RainforestTwigs);AddPaths(Paths,Assets->RainforestHerbs);
                AddPaths(Paths,Assets->ForestFungi);AddPaths(Paths,Assets->ForestMoss);
                AddPaths(Paths,Assets->RiverGroundCover);AddPaths(Paths,Assets->RiverPebbles);
                AddPaths(Paths,Assets->RiverReeds);AddPaths(Paths,Assets->RiverBankGrasses);AddPaths(Paths,Assets->RiverUnderstory);
                AddPaths(Paths,Assets->MeadowFlowers);
                for(const auto& Family:Assets->ClearingFlowers)AddPaths(Paths,Family.Variants);
                break;
            case Atmosphere:
                Paths.Add(Assets->ValleyFogClass.ToSoftObjectPath());
                Paths.Add(Assets->ValleyFogMaterial.ToSoftObjectPath());
                AddPaths(Paths,Assets->BackdropTrees);
                break;
            }
            Paths.RemoveAll([](const FSoftObjectPath& Path){return Path.IsNull();});
            Batch.Paths=MoveTemp(Paths);
        }
        const double Now=FPlatformTime::Seconds();
        if(Batch.Finished==Batch.Submitted && Batch.Submitted<Batch.Paths.Num())
        {
            // Each root can bring its own dependencies and editor compilation jobs.
            constexpr int32 VillagePathsPerRequest=12;
            const int32 Remaining=Batch.Paths.Num()-Batch.Submitted;
            const int32 Count=S.StaggerVillageEntry?FMath::Min(VillagePathsPerRequest,Remaining):Remaining;
            TArray<FSoftObjectPath> Slice(Batch.Paths.GetData()+Batch.Submitted,Count);
            Batch.Submitted+=Count;
            Batch.Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(MoveTemp(Slice),FStreamableDelegate(),
                Stage==Solids?FStreamableManager::AsyncLoadHighPriority:FStreamableManager::DefaultAsyncLoadPriority);
            if(Batch.Handle)S.Handles.Add(Batch.Handle);
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP requested_batch=%d range=%d-%d/%d elapsed=%.2fs"),
                Stage,Batch.Finished+1,Batch.Submitted,Batch.Paths.Num(),Now-StartSeconds);
        }
        if(Batch.Handle&&!Batch.Handle->HasLoadCompleted())continue;
        if(!Batch.Loaded && Batch.Submitted==Batch.Paths.Num())
        {
            Batch.Loaded=true;
            bool Valid=true;
            for(const auto& Path:Batch.Paths)if(!Path.ResolveObject())
            {
                UE_LOG(LogTemp,Error,TEXT("HILLS_PREP missing batch=%d asset=%s"),Stage,*Path.ToString());
                Valid=false;
            }
            if(Stage==Solids)
                Valid&=Loaded(Assets->Trees)&&Loaded(Assets->Rocks)&&(Assets->TrunkCollisionMesh.IsNull()||Assets->TrunkCollisionMesh.IsValid())
                    &&(!RoadForest||EastRiverRoad::TreesLoaded());
            else if(Stage==Understory)Valid&=Loaded(Assets->Shrubs);
            else if(Stage==GroundCover)Valid&=Loaded(Assets->Grass)&&Loaded(Assets->GrassAccents);
            else S.FogReady=Assets->ValleyFogClass.IsValid()&&Assets->ValleyFogMaterial.IsValid();
            const int32 FirstLayer=Stage==Solids?0:Stage+1;
            const int32 EndLayer=Stage==Solids?2:FMath::Min(FirstLayer+1,4);
            for(int32 Layer=FirstLayer;Layer<EndLayer;++Layer)
            {
                const auto* Graph=Assets->Graphs[Layer].Get();
                if(!Graph||!Graph->Use2DGrid()||Graph->GetDefaultGridSize()==0||Graph->GetDefaultGridSize()==PCGHiGenGrid::UnboundedGridSize())
                {
                    UE_LOG(LogTemp,Error,TEXT("HILLS_PREP layer=%d requires a loaded bounded 2D graph"),Layer);
                    Valid=false;
                }
            }
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP loaded_batch=%d valid=%d elapsed=%.2fs"),
                Stage,Valid,FPlatformTime::Seconds()-StartSeconds);
            if(!Valid&&(Stage!=Atmosphere||Full))
            {
                S.Failed=true;
                if(Loading)
                    Loading->FailPreparation(FText::FromString(TEXT("环境资源未能载入，请返回主场景后重试。")));
            }
            if(S.Failed)return;
        }
        // Package completion can precede mesh compilation in the editor. Placement
        // uses mesh bounds, but does not need unused material shader permutations.
        bool Compiling=false;
#if WITH_EDITOR
        const auto Platform=GetFeatureLevelShaderPlatform_Checked(GetWorld()->GetFeatureLevel());
        // A retained package that has finished compiling need not be polled again
        // while the next tree mesh or shared foliage material is still pending.
        for(;Batch.NextCompilationPath<Batch.Submitted;++Batch.NextCompilationPath)
        {
            const FSoftObjectPath& Path=Batch.Paths[Batch.NextCompilationPath];
            UObject* Asset=Path.ResolveObject();
            if(auto* Mesh=Cast<UStaticMesh>(Asset))
            {
                Compiling|=Mesh->IsCompiling();
                if(!Compiling&&Full)for(const auto& MaterialSlot:Mesh->GetStaticMaterials())Compiling|=MaterialPending(MaterialSlot.MaterialInterface,Platform);
            }
            else if(auto* Skin=Cast<USkeletalMesh>(Asset))
            {
                Compiling|=Skin->IsCompiling();
                if(!Compiling&&Full)for(const auto& MaterialSlot:Skin->GetMaterials())Compiling|=MaterialPending(MaterialSlot.MaterialInterface,Platform);
            }
            else if(Full)Compiling|=MaterialPending(Cast<UMaterialInterface>(Asset),Platform);
            if(Compiling)
            {
                if(Now>=Batch.NextWaitLog)
                {
                    Batch.NextWaitLog=Now+5.;
                    UE_LOG(LogTemp,Display,TEXT("HILLS_PREP waiting_batch=%d phase=compilation asset=%s elapsed=%.2fs"),
                        Stage,*Path.ToString(),Now-StartSeconds);
                }
                break;
            }
        }
#endif
        if(Compiling)continue;
        Batch.Finished=Batch.Submitted;
        if(Batch.Finished<Batch.Paths.Num())continue;
        Batch.Paths.Reset();Batch.Ready=true;++S.CompletedStages;
        UE_LOG(LogTemp,Display,TEXT("HILLS_PREP ready_batch=%d completed=%d/%d elapsed=%.2fs"),Stage,S.CompletedStages,int32(BatchCount),FPlatformTime::Seconds()-StartSeconds);
        if(Loading)
        {
            Loading->RetainBiomeResources(S.Handles,S.CompletedStages==BatchCount);
            S.RetainedHandleCount=S.Handles.Num();
        }
        if(S.StaggerVillageEntry)break;
    }
}

void ATemperateHillsWorld::TickPreparation()
{
    auto& S=*Streaming;
    auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    auto Report=[&](const FText& Text,float Progress){if(Loading)Loading->UpdatePreparation(Text,Progress);};
    const bool Full=!GUsingNullRHI&&Loading&&Loading->IsCompletePreloadSelected();
    const int32 RequiredBatches=Full?int32(HillsStreaming::BatchCount):int32(HillsStreaming::Atmosphere);
    bool AssetsReady=true;
    for(int32 Batch=0;Batch<RequiredBatches;++Batch)AssetsReady&=S.Batches[Batch].Ready;
    if(!AssetsReady)
    {
        float Completed=0;
        const TCHAR* Pending=TEXT("附近植被");
        bool Compiling=false,FoundPending=false;
        const TCHAR* Names[]={TEXT("树木与岩石"),TEXT("灌木"),TEXT("草地与花卉"),TEXT("远景")};
        for(int32 Batch=0;Batch<RequiredBatches;++Batch)
        {
            const auto& State=S.Batches[Batch];
            const float LoadedPaths=State.Finished+(State.Submitted-State.Finished)*(State.Handle?State.Handle->GetProgress():0.f);
            Completed+=State.Ready?1.f:(State.Loaded?.9f:.8f*LoadedPaths/FMath::Max(1,State.Paths.Num()));
            if(!State.Ready&&!FoundPending){Pending=Names[Batch];Compiling=State.Loaded;FoundPending=true;}
        }
        Report(FText::FromString(FString::Printf(TEXT("正在%s%s（资源进度 %.0f%%）…"),
            Compiling?TEXT("编译"):TEXT("载入"),Pending,100.f*Completed/RequiredBatches)),.1f+.6f*Completed/RequiredBatches);
        return;
    }
    if(Full&&!IsBackdropReady())
    {Report(FText::FromString(TEXT("正在准备远景丘陵…")),.7f);return;}
    if(!UGameplayStatics::GetPlayerPawn(this,0))
    {Report(FText::FromString(TEXT("正在准备角色与视野…")),.7f);return;}

    if(Full)
    {
        // Register one small sample per asset/frame under the opaque loading overlay.
        // Use the same instanced vertex factories as PCG for canopy and understory.
        if(S.WarmupMeshes.IsEmpty())
        {
            for(const auto& Handle:S.Handles)if(Handle)
                Handle->ForEachLoadedAsset([&](UObject* Asset)
                {
                    if(Asset&&Asset!=Assets->TrunkCollisionMesh.Get()&&(Asset->IsA<UStaticMesh>()||Asset->IsA<USkeletalMesh>()))
                        S.WarmupMeshes.AddUnique(TWeakObjectPtr<UObject>(Asset));
                });
        }
        const int32 AssetCount=S.WarmupMeshes.Num();
        if(S.WarmupAsset<AssetCount)
        {
            const int32 Index=S.WarmupAsset++;
            UObject* Mesh=S.WarmupMeshes[Index].Get();
            UPrimitiveComponent* Sample=nullptr;
            if(auto* Skin=Cast<USkeletalMesh>(Mesh))
            {
                auto* C=NewObject<UInstancedSkinnedMeshComponent>(this);
                if(Assets->ForestWindProvider)C->SetTransformProvider(Assets->ForestWindProvider);
                C->SetSkinnedAsset(Skin);C->AddInstance(FTransform::Identity,0);
                Sample=C;
            }
            else if(auto* Static=Cast<UStaticMesh>(Mesh))
            {
                auto* C=NewObject<UInstancedStaticMeshComponent>(this);
                C->SetStaticMesh(Static);C->AddInstance(FTransform::Identity);
                Sample=C;
            }
            else return;
            AddInstanceComponent(Sample);Sample->SetupAttachment(RootComponent);
            Sample->SetRelativeLocation(GetStartLocation()+FVector(4000,(Index-AssetCount*.5)*600,-100));
            Sample->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sample->SetCanEverAffectNavigation(false);
            Sample->RegisterComponent();Sample->PrecachePSOs();WarmupComponents.Add(Sample);
            Report(FText::FromString(TEXT("正在准备植被显示…")),.7f+.04f*S.WarmupAsset/FMath::Max(1,AssetCount));
            return;
        }
    }
    if(!S.LayerActive[0]||!S.LayerActive[1]||!S.LayerActive[2]||!S.LayerActive[3])
    {
        Report(FText::FromString(TEXT("正在布置出生区域植被…")),.75f);
        return;
    }

    // Wait for all four layers only within 16 m. Distant visual rings remain
    // streamed; nearby grass must no longer start after the player is released.
    int32 Required=0,Complete=0;
    const double Half=SizeMeters*50;
    if(auto* Sub=GetWorld()->GetSubsystem<UPCGSubsystem>())
        if(auto* Manager=Sub->GetGenSourceManager())
            for(const auto* Source:Manager->GetAllGenSources(Sub->GetPCGWorldActor()))
            {
                // Use exactly the scheduler's focus; camera offsets and remote
                // players must not make local entry wait on unrequested cells.
                if(!Source->IsLocal()&&GetNetMode()!=NM_DedicatedServer)continue;
                const auto Position=Source->GetPosition();
                if(!Position)continue;
                for(int32 Layer=0;Layer<4;++Layer)
                {
                    if(!Source->IsLocal()&&Layer!=1)continue;
                    HillsStreaming::CountVegetationCells(PCGLayers[Layer],*Position,HillsStreaming::EntryVegetationRadius,Half,Required,Complete);
                }
            }
    S.InitialPCGTotal=Required;S.InitialPCGReady=Complete;
    if(FPlatformTime::Seconds()>=S.NextEntryProgressLog)
    {
        S.NextEntryProgressLog=FPlatformTime::Seconds()+5.;
        UE_LOG(LogTemp,Display,TEXT("HILLS_ENTRY_VEGETATION ready=%d/%d layers=4 elapsed=%.2fs"),Complete,Required,FPlatformTime::Seconds()-StartSeconds);
    }
    if(Required==0||Complete<Required)
    {
        S.SettledFrames=0;
        Report(FText::FromString(FString::Printf(TEXT("正在准备出生点植被 %d/%d…"),Complete,Required)),.75f+.15f*Complete/FMath::Max(1,Required));
        return;
    }
    // Use the same pawn center/radius as Wanted() and the trunk builder. Camera
    // offsets must not make us wait for a cell outside the requested neighborhood.
    const FVector TerrainCenter=UGameplayStatics::GetPlayerPawn(this,0)->GetActorLocation();
    const int32 Count=FMath::RoundToInt(SizeMeters*100/HillsStreaming::CellSize);
    bool TerrainPending=false;
    int32 NearbyTerrainTotal=0,NearbyTerrainReady=0;
    for(int32 Y=0;Y<Count;++Y)for(int32 X=0;X<Count;++X)
    {
        const double DX=FMath::Max(0.0,FMath::Abs(TerrainCenter.X+Half-(X+.5)*HillsStreaming::CellSize)-HillsStreaming::CellSize*.5);
        const double DY=FMath::Max(0.0,FMath::Abs(TerrainCenter.Y+Half-(Y+.5)*HillsStreaming::CellSize)-HillsStreaming::CellSize*.5);
        const double D=DX*DX+DY*DY;
        if(D>FMath::Square(HillsStreaming::EntryRadius))continue;
        ++NearbyTerrainTotal;
        const auto* Cell=S.Cells.Find(FIntPoint(X,Y));
        const bool CellReady=Cell&&Cell->Mesh.IsValid()&&Cell->Detailed&&!Cell->Dirty&&!Cell->Pending.IsValid()
            &&(!Assets->TrunkCollisionMesh.IsValid()||Cell->Trunks.IsValid());
        TerrainPending|=!CellReady;
        if(CellReady)++NearbyTerrainReady;
    }
    if(TerrainPending)
    {S.SettledFrames=0;Report(FText::FromString(FString::Printf(TEXT("正在准备附近地形与碰撞 %d/%d…"),NearbyTerrainReady,NearbyTerrainTotal)),.91f);return;}

    // UE 5.8 compiles material permutations on demand. "Complete" requires even
    // unused permutations and can remain false forever with no queued work.
    // Nearby terrain already renders behind the overlay, requesting its passes.
    // Wait for those actual jobs plus a renderable map, never force all variants.
    int32 GroundTexturesReady=0;
    if(!GUsingNullRHI)
    {
    auto* GroundResource=GroundMID?GroundMID->GetMaterialResource(GetFeatureLevelShaderPlatform_Checked(GetWorld()->GetFeatureLevel())):nullptr;
    bool GroundCompiling=false;
#if WITH_EDITOR
    GroundCompiling=GroundResource&&!GroundResource->IsCompilationFinished();
    if(GroundResource&&!GroundResource->GetCompileErrors().IsEmpty())
    {
        S.Failed=true;
        UE_LOG(LogTemp,Error,TEXT("HILLS_GROUND material compile failed: %s"),*FString::Join(GroundResource->GetCompileErrors(),TEXT("; ")));
        if(Loading)Loading->FailPreparation(FText::FromString(TEXT("地面材质编译失败，请返回主场景。")));
        return;
    }
#endif
    const auto* GroundShaderMap=GroundResource?GroundResource->GetGameThreadShaderMap():nullptr;
    if(!GroundShaderMap||!GroundShaderMap->IsValidForRendering()||(Full&&GroundCompiling))
    {
        S.SettledFrames=0;
        if(GroundCompiling)S.GroundMaterialIdleWaitStart=0;
        else if(S.GroundMaterialIdleWaitStart==0)S.GroundMaterialIdleWaitStart=FPlatformTime::Seconds();
        else if(FPlatformTime::Seconds()-S.GroundMaterialIdleWaitStart>=30)
        {
            // No pending compilation can resolve this state. Report failure
            // instead of leaving a permanent spinner or releasing blurry ground.
            S.Failed=true;
            UE_LOG(LogTemp,Error,TEXT("HILLS_GROUND no renderable shader map after 30 idle seconds: %s resource=%d map=%d"),
                *GetNameSafe(GroundMID?GroundMID->Parent:nullptr),GroundResource!=nullptr,GroundShaderMap!=nullptr);
            if(Loading)Loading->FailPreparation(FText::FromString(TEXT("地面材质未能就绪，请返回主场景后重试。")));
            return;
        }
        Report(FText::FromString(GroundCompiling?TEXT("正在编译附近地面材质…"):TEXT("正在准备附近地面材质…")),.92f);
        return;
    }
    S.GroundMaterialIdleWaitStart=0;
    if(!S.GroundMaterialReadinessLogged)
    {
        S.GroundMaterialReadinessLogged=true;
        UE_LOG(LogTemp,Display,TEXT("HILLS_GROUND renderable material=%s all_permutations=%d elapsed=%.2fs"),
            *GetNameSafe(GroundMID->Parent),GroundResource->IsGameThreadShaderMapComplete(),FPlatformTime::Seconds()-StartSeconds);
    }

    for(const auto& Weak:S.GroundTextures)
        if(HillsStreaming::GroundTextureReady(Weak.Get()))++GroundTexturesReady;
    // The actual ground mip requirement applies to both entry modes.
    if(!S.GroundTexturesCollected||GroundTexturesReady!=S.GroundTextures.Num())
    {
        S.SettledFrames=0;
        Report(FText::FromString(FString::Printf(TEXT("正在载入清晰地面纹理 %d/%d…"),GroundTexturesReady,S.GroundTextures.Num())),.92f);
        return;
    }
    if(!S.GroundTextureReadinessLogged)
    {
        S.GroundTextureReadinessLogged=true;
        for(const auto& Weak:S.GroundTextures)if(auto* Texture=Weak.Get())
        {
            const auto& State=Texture->GetStreamableResourceState();
            const int32 FirstMip=State.LODCountToAssetFirstLODIdx(State.NumResidentLODs);
            UE_LOG(LogTemp,Display,TEXT("HILLS_GROUND resident %s mips=%d required=%d resolution=%dx%d"),
                *Texture->GetName(),int32(State.NumResidentLODs),HillsStreaming::RequiredGroundMips(Texture),
                FMath::Max(1,Texture->GetSizeX()>>FirstMip),FMath::Max(1,Texture->GetSizeY()>>FirstMip));
        }
    }
    }
    if(Full)
    {
        uint32 PSOs=0;
#if WITH_EDITOR
        const auto Platform=GetFeatureLevelShaderPlatform_Checked(GetWorld()->GetFeatureLevel());
        for(const auto& Sample:WarmupComponents)if(Sample)
            for(int32 I=0;I<Sample->GetNumMaterials();++I)
                if(HillsStreaming::MaterialPending(Sample->GetMaterial(I),Platform))
                {Report(FText::FromString(TEXT("正在准备植被显示材质…")),.93f);return;}
#endif
        for(const auto& StoredSample:WarmupComponents)if(auto* Sample=StoredSample.Get();Sample&&Sample->IsPSOPrecaching())++PSOs;
        if(PSOs>0)
        {S.SettledFrames=0;Report(FText::FromString(FString::Printf(TEXT("正在准备显示效果：剩余 %u 项…"),PSOs)),.93f);return;}
        if(S.TextureWaitStart==0)S.TextureWaitStart=FPlatformTime::Seconds();
        // Noncritical environment textures still obey the global VRAM budget and
        // bounded wait. Ground shader/mips above have an independent, strict gate.
        if(IStreamingManager::Get().GetNumWantingResources()>0&&FPlatformTime::Seconds()-S.TextureWaitStart<10)
        {Report(FText::FromString(TEXT("正在细化附近纹理…")),.95f);return;}
        if(!WarmupComponents.IsEmpty())
        {
            auto* C=WarmupComponents.Pop().Get();RemoveInstanceComponent(C);C->DestroyComponent();
            Report(FText::FromString(TEXT("正在完成场景准备…")),.98f);return;
        }
        if(!S.WarmupRemoved){S.WarmupRemoved=true;S.RenderFence.BeginFence();return;}
        if(!S.RenderFence.IsFenceComplete()||++S.SettledFrames<3)return;
    }
    // The entry level, terrain, near vegetation and required texture mips are ready.
    if(S.StaggerVillageEntry)TickResidentAppearanceLoads();
    if(!PendingResidentAppearances.IsEmpty())
    {Report(FText::FromString(TEXT("正在分批准备村庄居民…")),.98f);return;}
    const auto ResidentReady = [&](const TSharedPtr<FStreamableHandle>& Handle, auto GetPaths, auto IsCompiling)
    {
        if(!Handle || !Handle->HasLoadCompleted() || IsCompiling())
        {Report(FText::FromString(TEXT("正在准备村庄居民…")),.98f);return false;}
        for(const auto& Path:GetPaths())if(!Path.ResolveObject())
        {
            S.Failed=true;
            UE_LOG(LogTemp,Error,TEXT("HILLS_PREP missing resident asset=%s"),*Path.ToString());
            if(Loading)Loading->FailPreparation(FText::FromString(TEXT("村庄居民资源未能载入，请返回主场景后重试。")));
            return false;
        }
        return true;
    };
    if(Full && GetNetMode()!=NM_DedicatedServer && bVillageBlacksmithRepaired && !ResidentReady(S.SmithAppearance, AVillageBlacksmithResident::AppearancePaths,
        AVillageBlacksmithResident::IsAppearanceCompilationPending)) return;
    if(Full && GetNetMode()!=NM_DedicatedServer && IsVillageCarpenterRepaired() &&
        !ResidentReady(S.CarpenterAppearance, AVillageCarpenterResident::AppearancePaths,
            AVillageCarpenterResident::IsAppearanceCompilationPending)) return;
    if(const auto* Raid=GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>();Raid&&!Raid->AreAssetsReady())
    {
        S.SettledFrames=0;
        if(Raid->HasAssetPreparationFailed())
        {
            S.Failed=true;
            if(Loading)Loading->FailPreparation(FText::FromString(TEXT("夜袭资源未能载入，请返回主场景后重试。")));
        }
        else Report(FText::FromString(TEXT("正在准备村庄夜袭资源…")),.98f);
        return;
    }
    // Discard initial load/assembly transients before this world's first input
    // handoff. Ask the engine to collect at its safe end-of-frame point: it can
    // wait for package loading without a synchronous FlushAsyncLoading here.
    // No GC interval changes, no repeat on a guest joining an already-ready world,
    // and no process-wide forced collection while other PIE worlds are playing.
    if(GetWorld()->WorldType==EWorldType::Game && GEngine && Loading && Loading->IsHoldingGameplayInput())
    {
        if(!S.EntryCleanupRequested)
        {
            S.EntryCleanupRequested=true;S.EntryCleanupGCTime=GetLastGCTime();
            GEngine->ForceGarbageCollection(false);
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP requested initial resource cleanup before input release"));
            Report(FText::FromString(TEXT("正在整理入场资源…")),.99f);return;
        }
        if(GetLastGCTime()<=S.EntryCleanupGCTime)return;
    }
    S.SmithAppearance.Reset();
    S.CarpenterAppearance.Reset();
    bReady=true;S.NextVegetationFrontierTime=0;AuditNext=GetWorld()->GetTimeSeconds()+24;
    if(Loading)Loading->CompletePreparation();
    UE_LOG(LogTemp,Display,TEXT("HILLS_READY seed=%d world=%s entry_radius_m=%.0f terrain_cells=%d/%d pcg_cells=%d/%d ground_textures=%d/%d preparation_ms=%.2f"),Seed,*WorldId.ToString(),HillsStreaming::EntryRadius/100,NearbyTerrainReady,NearbyTerrainTotal,Complete,Required,GroundTexturesReady,S.GroundTextures.Num(),(FPlatformTime::Seconds()-StartSeconds)*1000);
}

