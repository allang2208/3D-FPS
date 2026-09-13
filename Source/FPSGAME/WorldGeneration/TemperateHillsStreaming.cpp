#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "TemperateHillsBackdrop.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Async/Async.h"
#include "Algo/AllOf.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "HAL/IConsoleManager.h"
#include "PCGGraph.h"
#include "PCGComponent.h"
#include "PCGGraphExecutionStateInterface.h"
#include "Subsystems/PCGSubsystem.h"
#include "ShaderPipelineCache.h"
#include "ContentStreaming.h"
#include "RenderCommandFence.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif

namespace HillsStreaming
{
constexpr double CellSize=6400.0;
struct FMeshResult
{
    FIntPoint Key;
    bool Detailed=false;
    UE::Geometry::FDynamicMesh3 Mesh;
    UE::Geometry::FDynamicMesh3 Water;
};
struct FJob
{
    FIntPoint Key;
    TFuture<TSharedPtr<FMeshResult,ESPMode::ThreadSafe>> Future;
};
struct FCell
{
    TWeakObjectPtr<UDynamicMeshComponent> Mesh;
    TWeakObjectPtr<UDynamicMeshComponent> Pending;
    TWeakObjectPtr<UInstancedStaticMeshComponent> Trunks;
    TWeakObjectPtr<UDynamicMeshComponent> Water;
    bool Detailed=false;
    bool PendingDetailed=false;
};
struct FCVarOverride
{
    IConsoleVariable* Variable=nullptr;
    float Previous=0;
    float Applied=0;
};

TSharedPtr<FMeshResult,ESPMode::ThreadSafe> MakeMesh(FIntPoint Key,bool Detailed,double Half,int32 Seed,TemperateRiver::FPlanPtr River)
{
    auto Result=MakeShared<FMeshResult,ESPMode::ThreadSafe>();Result->Key=Key;Result->Detailed=Detailed;
    auto& Mesh=Result->Mesh;Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
    auto* Colors=Mesh.Attributes()->PrimaryColors();
    const double OX=-Half+Key.X*CellSize,OY=-Half+Key.Y*CellSize;
    const bool RiverCell=River&&River->IntersectsCell(OX,OY,CellSize);
    // Even distant river cells retain 2 m terrain spacing to avoid a coarse LOD
    // spanning across the shallow channel and covering its water surface.
    const int32 Quads=RiverCell?(Detailed?64:32):(Detailed?32:8);
    const double Step=CellSize/Quads;
    for(int32 Y=0;Y<=Quads;++Y)for(int32 X=0;X<=Quads;++X)
    {
        const double WX=OX+X*Step,WY=OY+Y*Step;
        Mesh.AppendVertex(FVector3d(X*Step,Y*Step,River?River->Height(WX,WY,Seed):TemperateHillsSurface::Height(WX,WY,Seed)));
        Normals->AppendElement(FVector3f(River?River->Normal(WX,WY,Seed):TemperateHillsSurface::Normal(WX,WY,Seed)));
        UVs->AppendElement(FVector2f(WX/400,WY/400));
        const auto Bank=River?River->Sample(WX,WY):TemperateRiver::FSample();
        Colors->AppendElement(FVector4f(Bank.Bank,Bank.Wet,0,1));
    }
    auto Tri=[&](int32 A,int32 B,int32 C)
    {const int32 ID=Mesh.AppendTriangle(A,B,C);const UE::Geometry::FIndex3i Indices(A,B,C);Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);};
    for(int32 Y=0;Y<Quads;++Y)for(int32 X=0;X<Quads;++X)
    {const int32 A=Y*(Quads+1)+X;Tri(A,A+Quads+2,A+1);Tri(A,A+Quads+1,A+Quads+2);}
    // Downward skirts cover the different edge subdivisions at the LOD boundary.
    TArray<int32> Edge;
    for(int32 X=0;X<=Quads;++X)Edge.Add(X);
    for(int32 Y=1;Y<=Quads;++Y)Edge.Add(Y*(Quads+1)+Quads);
    for(int32 X=Quads-1;X>=0;--X)Edge.Add(Quads*(Quads+1)+X);
    for(int32 Y=Quads-1;Y>0;--Y)Edge.Add(Y*(Quads+1));
    TArray<int32> Bottom;
    for(int32 Top:Edge)
    {
        const FVector3d P=Mesh.GetVertex(Top);
        const double Proxy=TemperateBackdrop::CoreTriangleHeight(OX+P.X,OY+P.Y,Half,Seed,River);
        Bottom.Add(Mesh.AppendVertex(FVector3d(P.X,P.Y,FMath::Min(P.Z-800,Proxy-50))));
        Normals->AppendElement(Normals->GetElement(Top));UVs->AppendElement(UVs->GetElement(Top));
        Colors->AppendElement(Colors->GetElement(Top));
    }
    for(int32 I=0;I<Edge.Num();++I){const int32 J=(I+1)%Edge.Num();Tri(Edge[I],Bottom[J],Bottom[I]);Tri(Edge[I],Edge[J],Bottom[J]);}
    if(RiverCell)River->BuildWaterMesh(OX,OY,CellSize,Result->Water);
    return Result;
}
template<class T> void AddPaths(TArray<FSoftObjectPath>& Out,const TArray<TSoftObjectPtr<T>>& Values)
{for(const auto& V:Values)if(!V.IsNull())Out.AddUnique(V.ToSoftObjectPath());}
template<class T> bool Loaded(const TArray<TSoftObjectPtr<T>>& Values)
{return !Values.IsEmpty()&&Algo::AllOf(Values,[](const auto& V){return V.IsValid();});}
}

struct FTemperateHillsStreamingState
{
    TMap<FIntPoint,HillsStreaming::FCell> Cells;
    TArray<HillsStreaming::FJob> Jobs;
    TFuture<TemperateRiver::FPlanPtr> RiverJob;
    bool RiverPending=false;
    TArray<TSharedPtr<FStreamableHandle>> Handles;
    TArray<HillsStreaming::FCVarOverride> CVars;
    TMap<int32,TWeakObjectPtr<AActor>> Fog;
    TWeakObjectPtr<ACharacter> HeldPawn;
    FText Status=FText::FromString(TEXT("正在准备出生区域…"));
    bool GroundReady=false;
    bool LoadingAssets=false;
    bool TreesActive=false;
    bool FogReady=false;
    bool Stopping=false;
    bool Failed=false;
    TArray<FSoftObjectPath> CompilingPaths;
    int32 Stage=0;
    int32 CompletedStages=0;
    int32 ActivatedLayers=0;
    int32 WarmupAsset=0;
    int32 SettledFrames=0;
    int32 InitialPCGTotal=0;
    int32 InitialPCGReady=0;
    bool ResourcesRetained=false;
    bool WarmupRemoved=false;
    FRenderCommandFence RenderFence;
    double TextureWaitStart=0;
    double NextAssetTime=0;
    double NextFogTime=0;
    FIntPoint StartCell;
};

void ATemperateHillsWorld::BeginStreaming()
{
    Streaming=MakeShared<FTemperateHillsStreamingState>();
    auto& S=*Streaming;
    DetailRadiusMeters=FMath::Clamp(DetailRadiusMeters,96.f,256.f);
    ViewRadiusMeters=FMath::Clamp(ViewRadiusMeters,DetailRadiusMeters+96.f,512.f);
    const double Half=SizeMeters*50;
    const FVector Start=GetStartLocation();
    if(!Assets->RiverMaterial.IsNull())
    {
        S.RiverPending=true;
        S.RiverJob=Async(EAsyncExecution::ThreadPool,[WorldSeed=Seed,Half,Spawn=FVector2D(Start)]()
            {return TemperateRiver::Generate(WorldSeed,Half,Spawn);});
    }
    S.StartCell=FIntPoint(FMath::FloorToInt((Start.X+Half)/HillsStreaming::CellSize),FMath::FloorToInt((Start.Y+Half)/HillsStreaming::CellSize));
    // Apply only while this world exists; returning home restores previous budgets.
    for(const auto& Setting:TArray<TPair<const TCHAR*,float>>{
        {TEXT("pcg.FrameTime"),2.f},{TEXT("pcg.RuntimeGeneration.NumGeneratingComponents"),2.f},{TEXT("pcg.RuntimeGeneration.BasePoolSize"),16.f},
        {TEXT("s.AsyncLoadingTimeLimit"),2.f},{TEXT("s.LevelStreamingActorsUpdateTimeLimit"),2.f},{TEXT("s.UnregisterComponentsTimeLimit"),1.f}})
        if(auto* C=IConsoleManager::Get().FindConsoleVariable(Setting.Key))
        {S.CVars.Add({C,C->GetFloat(),Setting.Value});C->Set(Setting.Value,ECVF_SetByCode);}
    S.LoadingAssets=true;
    TArray<FSoftObjectPath> SurfacePaths={Assets->GroundMaterial.ToSoftObjectPath()};
    if(!Assets->RiverMaterial.IsNull())SurfacePaths.Add(Assets->RiverMaterial.ToSoftObjectPath());
    if(!Assets->BackdropMaterial.IsNull())SurfacePaths.Add(Assets->BackdropMaterial.ToSoftObjectPath());
    S.Handles.Add(UAssetManager::GetStreamableManager().RequestAsyncLoad(SurfacePaths,FStreamableDelegate::CreateWeakLambda(this,[this]()
    {
        if(!Streaming||Streaming->Stopping)return;
        Streaming->LoadingAssets=false;
        if(auto* Ground=Assets->GroundMaterial.Get();Ground&&(Assets->RiverMaterial.IsNull()||Assets->RiverMaterial.IsValid())&&
            (Assets->BackdropMaterial.IsNull()||Assets->BackdropMaterial.IsValid()))
        {GroundMID=UMaterialInstanceDynamic::Create(Ground,this);Streaming->GroundReady=true;}
        else
        {
            Streaming->Failed=true;
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->FailPreparation(FText::FromString(TEXT("地面资源加载失败，请返回主场景。")));
        }
    })));
}

void ATemperateHillsWorld::LoadNextEnvironmentStage()
{
    auto& S=*Streaming;
    if(S.LoadingAssets||S.Failed||S.Stage>=8||GetWorld()->GetTimeSeconds()<S.NextAssetTime)return;
    const int32 Stage=S.Stage++;
    TArray<FSoftObjectPath> Paths;
    const int32 Layer=Stage==0?3:(Stage==1?2:(Stage==2?1:0));
    if(Stage<3)
    {
        Paths.Add(Assets->Graphs[Layer].ToSoftObjectPath());
        if(Stage==0){HillsStreaming::AddPaths(Paths,Assets->Grass);HillsStreaming::AddPaths(Paths,Assets->GrassAccents);}
        if(Stage==1)HillsStreaming::AddPaths(Paths,Assets->Shrubs);
        if(Stage==2){HillsStreaming::AddPaths(Paths,Assets->Rocks);HillsStreaming::AddPaths(Paths,Assets->RiverRocks);}
        S.Status=FText::FromString(Stage==0?TEXT("正在载入附近草地…"):Stage==1?TEXT("正在载入林下灌木…"):TEXT("正在载入坡地岩石…"));
    }
    else if(Stage<7)
    {
        const int32 Variant=Stage-3;
        if(Assets->Trees.IsValidIndex(Variant))Paths.Add(Assets->Trees[Variant].ToSoftObjectPath());
        if(Stage==3){Paths.Add(Assets->Graphs[0].ToSoftObjectPath());Paths.Add(Assets->TrunkCollisionMesh.ToSoftObjectPath());}
        S.Status=FText::FromString(FString::Printf(TEXT("正在准备黑杨 %d/4…"),Variant+1));
    }
    else
    {
        Paths.Add(Assets->ValleyFogClass.ToSoftObjectPath());Paths.Add(Assets->ValleyFogMaterial.ToSoftObjectPath());
        S.Status=FText::FromString(TEXT("正在准备谷地薄雾…"));
    }
    Paths.RemoveAll([](const FSoftObjectPath& P){return P.IsNull();});
    S.LoadingAssets=true;
    S.Handles.Add(UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Stage,Layer,Paths]()
    {
        if(!Streaming||Streaming->Stopping)return;
        auto& State=*Streaming;State.LoadingAssets=false;State.NextAssetTime=GetWorld()->GetTimeSeconds();
        State.CompilingPaths=Paths;
        State.Failed=Paths.ContainsByPredicate([](const FSoftObjectPath& Path){return !Path.ResolveObject();});
        if(State.Failed)
        {
            State.Status=FText::FromString(TEXT("环境资源未能载入，请返回主场景后重试。"));
            UE_LOG(LogTemp,Error,TEXT("HILLS_PREP asset stage %d failed"),Stage);
            return;
        }
        if(Stage<3)
        {
            const bool Ready=Stage==0?(HillsStreaming::Loaded(Assets->Grass)&&HillsStreaming::Loaded(Assets->GrassAccents)):Stage==1?HillsStreaming::Loaded(Assets->Shrubs):HillsStreaming::Loaded(Assets->Rocks);
            State.Failed=!(Ready&&Assets->Graphs[Layer].IsValid());
        }
        else if(Stage==6)
        {
            if(HillsStreaming::Loaded(Assets->Trees)&&Assets->Graphs[0].IsValid())
            {}
            else State.Failed=true;
        }
        else if(Stage==7)State.FogReady=Assets->ValleyFogClass.IsValid()&&Assets->ValleyFogMaterial.IsValid();
    })));
}

void ATemperateHillsWorld::TickStreaming()
{
    if(!Streaming||Streaming->Stopping||!Streaming->GroundReady)return;
    auto& S=*Streaming;
    if(S.RiverPending)
    {
        if(!S.RiverJob.IsReady())
        {
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->UpdatePreparation(FText::FromString(TEXT("正在计算河道与河滩…")),.01f);
            return;
        }
        RiverPlan=S.RiverJob.Get();S.RiverPending=false;
        UE_LOG(LogTemp,Display,TEXT("HILLS_RIVER seed=%d samples=%d length_m=%.1f"),Seed,RiverPlan->Points.Num(),RiverPlan->Points.IsEmpty()?0:RiverPlan->Points.Last().Distance/100);
    }
    constexpr double Size=HillsStreaming::CellSize;
    const int32 Count=FMath::RoundToInt(SizeMeters*100/Size);
    const double Half=SizeMeters*50;
    auto* Pawn=UGameplayStatics::GetPlayerCharacter(this,0);
    const FVector Center=Pawn?Pawn->GetActorLocation():GetStartLocation();
    auto CellOrigin=[&](FIntPoint K){return FVector(-Half+K.X*Size,-Half+K.Y*Size,0);};
    auto DistanceSquared=[&](FIntPoint K)
    {
        const FVector O=CellOrigin(K);
        return FMath::Square(FMath::Max(0.0,FMath::Abs(Center.X-O.X-Size*.5)-Size*.5))+FMath::Square(FMath::Max(0.0,FMath::Abs(Center.Y-O.Y-Size*.5)-Size*.5));
    };
    auto IsStart=[&](FIntPoint K){return FMath::Abs(K.X-S.StartCell.X)<=1&&FMath::Abs(K.Y-S.StartCell.Y)<=1;};
    auto Wanted=[&](FIntPoint K,bool& Detailed)
    {
        if(K.X<0||K.Y<0||K.X>=Count||K.Y>=Count)return false;
        if(!bSurfaceReady){Detailed=true;return IsStart(K);}
        const auto* Existing=S.Cells.Find(K);
        const double FineRadius=DetailRadiusMeters*100+(Existing&&Existing->Detailed?Size:0);
        Detailed=DistanceSquared(K)<=FMath::Square(FineRadius);
        return DistanceSquared(K)<=FMath::Square(ViewRadiusMeters*100.0);
    };
    auto RemoveMesh=[&](UDynamicMeshComponent* C){if(C){Terrain.Remove(C);RemoveInstanceComponent(C);C->DestroyComponent();}};
    // Poll cooking completion without blocking. Keep the old LOD until replacement is usable.
    for(auto& Pair:S.Cells)
    {
        auto& Cell=Pair.Value;auto* Pending=Cell.Pending.Get();if(!Pending)continue;
        bool Ready=!Cell.PendingDetailed;
        if(!Ready)
        {
            const FVector O=CellOrigin(Pair.Key)+FVector(Size*.5+17,Size*.5+23,0);
            const double Z=Height(O.X,O.Y);FHitResult Hit;FCollisionQueryParams Q;Q.bTraceComplex=true;
            Ready=Pending->LineTraceComponent(Hit,FVector(O.X,O.Y,Z+500),FVector(O.X,O.Y,Z-500),Q);
        }
        if(Ready)
        {
            RemoveMesh(Cell.Mesh.Get());Pending->SetVisibility(true);Cell.Mesh=Pending;Cell.Pending.Reset();Cell.Detailed=Cell.PendingDetailed;
            SetBackdropCellVisible(Pair.Key,true);
        }
    }
    // At most one completed mesh is submitted to rendering/physics in a frame.
    for(int32 I=0;I<S.Jobs.Num();++I)
    {
        if(!S.Jobs[I].Future.IsReady())continue;
        auto Result=S.Jobs[I].Future.Get();S.Jobs.RemoveAt(I);
        bool Detailed=false;
        if(!Wanted(Result->Key,Detailed)||Detailed!=Result->Detailed)break;
        auto& Cell=S.Cells.FindOrAdd(Result->Key);
        auto* C=NewObject<UDynamicMeshComponent>(this);
        AddInstanceComponent(C);C->SetupAttachment(RootComponent);C->SetRelativeLocation(CellOrigin(Result->Key));
        C->SetMobility(EComponentMobility::Movable);C->SetCanEverAffectNavigation(false);
        C->SetVisibility(false);
        C->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);C->SetMaterial(0,GroundMID);
        C->bUseAsyncCooking=true;C->SetDeferredCollisionUpdatesEnabled(true,false);
        C->SetComplexAsSimpleCollisionEnabled(Result->Detailed,false);
        C->SetCollisionProfileName(Result->Detailed?TEXT("BlockAll"):TEXT("NoCollision"));
        C->SetMesh(MoveTemp(Result->Mesh));C->RegisterComponent();
        if(Result->Detailed)C->UpdateCollision(false);
        Terrain.Add(C);Cell.Pending=C;Cell.PendingDetailed=Result->Detailed;
        if(!Cell.Water.IsValid()&&Result->Water.TriangleCount()>0&&Assets->RiverMaterial.IsValid())
        {
            auto* Water=NewObject<UDynamicMeshComponent>(this);
            AddInstanceComponent(Water);Water->SetupAttachment(RootComponent);Water->SetRelativeLocation(CellOrigin(Result->Key));
            Water->SetMobility(EComponentMobility::Movable);Water->SetCanEverAffectNavigation(false);
            Water->SetCollisionEnabled(ECollisionEnabled::NoCollision);Water->SetCastShadow(false);
            Water->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
            Water->SetMaterial(0,Assets->RiverMaterial.Get());Water->SetMesh(MoveTemp(Result->Water));
            Water->RegisterComponent();Water->PrecachePSOs();Cell.Water=Water;Terrain.Add(Water);
        }
        break;
    }
    // A single unload per frame avoids a matching destruction spike when moving.
    for(auto It=S.Cells.CreateIterator();It;++It)
    {
        if(DistanceSquared(It.Key())<=FMath::Square(ViewRadiusMeters*100.0+Size))continue;
        SetBackdropCellVisible(It.Key(),false);
        RemoveMesh(It.Value().Mesh.Get());RemoveMesh(It.Value().Pending.Get());
        RemoveMesh(It.Value().Water.Get());
        if(auto* T=It.Value().Trunks.Get()){RemoveInstanceComponent(T);T->DestroyComponent();}
        It.RemoveCurrent();break;
    }
    // Two numerical jobs maximum; workers only receive copied seed/coordinate values.
    while(S.Jobs.Num()<2)
    {
        FIntPoint Best(-1,-1);bool BestDetailed=false;double Score=DBL_MAX;
        for(int32 Y=0;Y<Count;++Y)for(int32 X=0;X<Count;++X)
        {
            const FIntPoint Key(X,Y);bool Detailed=false;if(!Wanted(Key,Detailed))continue;
            const auto* Cell=S.Cells.Find(Key);
            if(Cell&&(Cell->Pending.IsValid()||(Cell->Mesh.IsValid()&&Cell->Detailed==Detailed)))continue;
            if(S.Jobs.ContainsByPredicate([&](const auto& J){return J.Key==Key;}))continue;
            const double Candidate=DistanceSquared(Key)+(Detailed?0:1.e12);
            if(Candidate<Score){Score=Candidate;Best=Key;BestDetailed=Detailed;}
        }
        if(Best.X<0)break;
        HillsStreaming::FJob Job;Job.Key=Best;
        Job.Future=Async(EAsyncExecution::ThreadPool,[Best,BestDetailed,Half,WorldSeed=Seed,River=RiverPlan](){return HillsStreaming::MakeMesh(Best,BestDetailed,Half,WorldSeed,River);});
        S.Jobs.Add(MoveTemp(Job));
    }
    // The worker starts before the first cell can finish; mask uploads follow all
    // cell swaps/removals in this frame. Submit at most one backdrop mesh per tick.
    TickBackdrop();
    if(!bSurfaceReady)
    {
        int32 Ready=0,Required=0;
        for(int32 Y=S.StartCell.Y-1;Y<=S.StartCell.Y+1;++Y)for(int32 X=S.StartCell.X-1;X<=S.StartCell.X+1;++X)
        {
            if(X<0||Y<0||X>=Count||Y>=Count)continue;
            ++Required;const auto* Cell=S.Cells.Find(FIntPoint(X,Y));if(Cell&&Cell->Mesh.IsValid()&&Cell->Detailed)++Ready;
        }
        if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
            Loading->UpdatePreparation(FText::FromString(FString::Printf(TEXT("正在生成出生区域 %d/%d…"),Ready,Required)),.1f*Ready/FMath::Max(1,Required));
        if(Ready==Required&&Required>0)
        {
            bSurfaceReady=true;
            UE_LOG(LogTemp,Display,TEXT("HILLS_SURFACE_READY seed=%d startup_cells=%d ms=%.2f"),Seed,Ready,(FPlatformTime::Seconds()-StartSeconds)*1000);
        }
        return;
    }
    if(!bReady)TickPreparation();
    // Guard an uncooked frontier or a teleport while its local collision catches up.
    if(Pawn)
    {
        const FVector Probe=Pawn->GetActorLocation()+Pawn->GetVelocity()*.35;
        const FIntPoint K(FMath::FloorToInt((Probe.X+Half)/Size),FMath::FloorToInt((Probe.Y+Half)/Size));
        const auto* Cell=S.Cells.Find(K);
        const bool Ready=bReady&&Cell&&Cell->Detailed&&Cell->Mesh.IsValid();
        auto* Move=Pawn->GetCharacterMovement();
        if(!Ready&&!S.HeldPawn.IsValid())
        {Move->StopMovementImmediately();Move->DisableMovement();S.HeldPawn=Pawn;}
        else if(Ready&&S.HeldPawn.IsValid())
        {Move->SetMovementMode(MOVE_Falling);S.HeldPawn.Reset();}
        if(S.HeldPawn.IsValid())S.Status=FText::FromString(TEXT("正在准备前方地面，请稍候…"));
    }
    // Only nearby tree trunks own physics, one cell added/removed each frame.
    if(S.TreesActive&&Assets->TrunkCollisionMesh.IsValid())for(auto& Pair:S.Cells)
    {
        auto& Cell=Pair.Value;const double D=DistanceSquared(Pair.Key);
        if(auto* T=Cell.Trunks.Get())
        {if(D>FMath::Square(12800.0)){RemoveInstanceComponent(T);T->DestroyComponent();Cell.Trunks.Reset();break;}continue;}
        if(D>FMath::Square(9600.0)||!Cell.Detailed||!Cell.Mesh.IsValid())continue;
        const FVector O=CellOrigin(Pair.Key);TArray<FTemperatePlacement> Trees;
        GetPlacements(0,FBox(O+FVector(0,0,-50000),O+FVector(Size,Size,50000)),Trees);
        auto* T=NewObject<UInstancedStaticMeshComponent>(this);AddInstanceComponent(T);T->SetupAttachment(RootComponent);
        T->SetStaticMesh(Assets->TrunkCollisionMesh.Get());T->SetCollisionProfileName(TEXT("BlockAll"));
        T->SetVisibility(false);T->SetCastShadow(false);T->SetCanEverAffectNavigation(false);T->RegisterComponent();
        TArray<FTransform> Transforms;
        for(const auto& Tree:Trees){const double Scale=Tree.Transform.GetScale3D().X;Transforms.Emplace(Tree.Transform.GetRotation(),Tree.Transform.GetLocation()+FVector(0,0,300*Scale),FVector(.42*Scale,.42*Scale,6*Scale));}
        T->AddInstances(Transforms,false,true,false);Cell.Trunks=T;break;
    }
    if(S.FogReady&&GetWorld()->GetTimeSeconds()>=S.NextFogTime){BuildValleyFog();S.NextFogTime=GetWorld()->GetTimeSeconds()+.5;}
}

void ATemperateHillsWorld::TickPreparation()
{
    auto& S=*Streaming;
    auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    auto Report=[&](const FText& Text,float Progress){if(Loading)Loading->UpdatePreparation(Text,Progress);};
    if(S.Failed)
    {
        if(Loading)Loading->FailPreparation(FText::FromString(TEXT("环境资源未能准备完成，请返回主场景后重试。")));
        return;
    }
    // Includes assembly children and shader jobs, not just the top-level four trees.
    // In uncooked -game builds the editor's usual compilation tick may be absent.
    int32 RemainingAssets=0,RemainingShaders=0;
#if WITH_EDITOR
    FAssetCompilingManager::Get().ProcessAsyncTasks(true);
    RemainingAssets=FAssetCompilingManager::Get().GetNumRemainingAssets();
    if(GShaderCompilingManager)RemainingShaders=GShaderCompilingManager->GetNumRemainingJobs();
#endif
    if(RemainingAssets>0||RemainingShaders>0)
    {
        Report(FText::FromString(FString::Printf(TEXT("正在准备渲染资源：%d 项，着色器：%d 项…"),RemainingAssets,RemainingShaders)),.1f+.6f*S.CompletedStages/8);
        return;
    }
    if(!S.LoadingAssets&&!S.CompilingPaths.IsEmpty())
    {
        S.CompilingPaths.Reset();S.CompletedStages=S.Stage;
        UE_LOG(LogTemp,Display,TEXT("HILLS_PREP resources=%d/8 elapsed=%.2fs"),S.CompletedStages,FPlatformTime::Seconds()-StartSeconds);
    }
    if(S.CompletedStages<8)
    {
        LoadNextEnvironmentStage();
        Report(S.Status,.1f+.6f*S.CompletedStages/8);
        return;
    }
    if(!IsBackdropReady())
    {Report(FText::FromString(TEXT("正在准备远景丘陵…")),.7f);return;}
    if(!S.ResourcesRetained&&Loading){Loading->RetainBiomeResources(S.Handles);S.ResourcesRetained=true;}
    if(!UGameplayStatics::GetPlayerPawn(this,0))
    {Report(FText::FromString(TEXT("正在准备角色与视野…")),.7f);return;}

    // Register one small sample per asset/frame under the opaque loading overlay.
    // Use the same instanced vertex factories as PCG, including all four tree variants.
    const int32 TreeCount=Assets->Trees.Num();
    TArray<TSoftObjectPtr<UStaticMesh>> StaticAssets=Assets->Rocks;
    StaticAssets.Append(Assets->RiverRocks);
    StaticAssets.Append(Assets->Shrubs);StaticAssets.Append(Assets->Grass);
    StaticAssets.Append(Assets->GrassAccents);
    const int32 AssetCount=TreeCount+StaticAssets.Num();
    if(S.WarmupAsset<AssetCount)
    {
        const int32 Index=S.WarmupAsset++;
        UPrimitiveComponent* Sample=nullptr;
        if(Index<TreeCount)
        {
            auto* C=NewObject<UInstancedSkinnedMeshComponent>(this);
            C->SetSkinnedAsset(Assets->Trees[Index].Get());C->AddInstance(FTransform::Identity,0);
            Sample=C;
        }
        else
        {
            auto* C=NewObject<UInstancedStaticMeshComponent>(this);
            C->SetStaticMesh(StaticAssets[Index-TreeCount].Get());C->AddInstance(FTransform::Identity);
            Sample=C;
        }
        AddInstanceComponent(Sample);Sample->SetupAttachment(RootComponent);
        Sample->SetRelativeLocation(GetStartLocation()+FVector(4000,(Index-AssetCount*.5)*600,-100));
        Sample->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sample->SetCanEverAffectNavigation(false);
        Sample->RegisterComponent();Sample->PrecachePSOs();WarmupComponents.Add(Sample);
        Report(FText::FromString(TEXT("正在准备植被显示…")),.7f+.04f*S.WarmupAsset/FMath::Max(1,AssetCount));
        return;
    }
    if(S.ActivatedLayers<4)
    {
        const int32 Layer=S.ActivatedLayers++;
        ActivateVegetationLayer(Layer);if(Layer==0)S.TreesActive=true;
        Report(FText::FromString(TEXT("正在布置出生区域植被…")),.75f);
        return;
    }

    // Count the actual grid cells the runtime scheduler must generate around the
    // loading pawn's view. Missing cells count as pending, so an empty queue cannot
    // falsely release the player before the scheduler discovers those cells.
    FVector Center=GetStartLocation();FRotator Rotation;
    if(auto* PC=UGameplayStatics::GetPlayerController(this,0))PC->GetPlayerViewPoint(Center,Rotation);
    Center.Z=0;
    constexpr uint32 Grids[]={6400,6400,3200,1600};
    int32 Required=0,Complete=0;
    const double Half=SizeMeters*50;
    for(int32 Layer=0;Layer<4;++Layer)
    {
        const uint32 Grid=Grids[Layer];
        auto& State=PCGLayers[Layer]->GetExecutionState();
        const double Radius=State.GetGenerationRadiusFromGrid(Grid);
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
    S.InitialPCGTotal=Required;S.InitialPCGReady=Complete;
    if(Required==0||Complete<Required)
    {
        S.SettledFrames=0;
        Report(FText::FromString(FString::Printf(TEXT("正在布置附近植被 %d/%d…"),Complete,Required)),.75f+.15f*Complete/FMath::Max(1,Required));
        return;
    }
    // Build the initial view ring and trunk collision before release. Subsequent
    // movement still uses two terrain jobs and one mesh/trunk submission per frame.
    const int32 Count=FMath::RoundToInt(SizeMeters*100/HillsStreaming::CellSize);
    bool TerrainPending=!S.Jobs.IsEmpty();
    for(int32 Y=0;Y<Count;++Y)for(int32 X=0;X<Count;++X)
    {
        const double DX=FMath::Max(0.0,FMath::Abs(Center.X+Half-(X+.5)*HillsStreaming::CellSize)-HillsStreaming::CellSize*.5);
        const double DY=FMath::Max(0.0,FMath::Abs(Center.Y+Half-(Y+.5)*HillsStreaming::CellSize)-HillsStreaming::CellSize*.5);
        const double D=DX*DX+DY*DY;
        if(D>FMath::Square(ViewRadiusMeters*100.0))continue;
        const auto* Cell=S.Cells.Find(FIntPoint(X,Y));
        TerrainPending|=!Cell||!Cell->Mesh.IsValid()||Cell->Pending.IsValid();
        if(Cell&&D<=FMath::Square(9600.0))TerrainPending|=!Cell->Trunks.IsValid();
    }
    if(TerrainPending)
    {S.SettledFrames=0;Report(FText::FromString(TEXT("正在准备视野内地形与树干碰撞…")),.91f);return;}

    const uint32 PSOs=FShaderPipelineCache::NumPrecompilesRemaining();
    if(PSOs>0)
    {S.SettledFrames=0;Report(FText::FromString(FString::Printf(TEXT("正在准备显示效果：剩余 %u 项…"),PSOs)),.93f);return;}
    if(S.TextureWaitStart==0)S.TextureWaitStart=FPlatformTime::Seconds();
    // Streaming textures obey the VRAM budget. Don't demand all top mips resident
    // forever on machines where the pool cannot contain them.
    if(IStreamingManager::Get().GetNumWantingResources()>0&&FPlatformTime::Seconds()-S.TextureWaitStart<10)
    {Report(FText::FromString(TEXT("正在细化附近纹理…")),.95f);return;}
    if(!WarmupComponents.IsEmpty())
    {
        auto* C=WarmupComponents.Pop().Get();RemoveInstanceComponent(C);C->DestroyComponent();
        Report(FText::FromString(TEXT("正在完成场景准备…")),.98f);return;
    }
    if(!S.WarmupRemoved){S.WarmupRemoved=true;S.RenderFence.BeginFence();return;}
    if(!S.RenderFence.IsFenceComplete()||++S.SettledFrames<3)return;
    bReady=true;AuditNext=GetWorld()->GetTimeSeconds()+24;
    if(Loading)Loading->CompletePreparation();
    UE_LOG(LogTemp,Display,TEXT("HILLS_READY seed=%d world=%s pcg_cells=%d/%d preparation_ms=%.2f"),Seed,*WorldId.ToString(),Complete,Required,(FPlatformTime::Seconds()-StartSeconds)*1000);
}

void ATemperateHillsWorld::BuildValleyFog()
{
    auto& S=*Streaming;const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    const FVector Center=Pawn?Pawn->GetActorLocation():GetStartLocation();
    // Update a small fixed pool, fading before it leaves the retention radius.
    for(auto It=S.Fog.CreateIterator();It;++It)
    {
        auto* Fog=It.Value().Get();
        if(!Fog){It.RemoveCurrent();continue;}
        const double Distance=FVector::Dist2D(Fog->GetActorLocation(),Center);
        if(Distance>18000)
        {ValleyFog.Remove(Fog);Fog->Destroy();It.RemoveCurrent();return;}
        const float Fade=(1-FMath::SmoothStep(14000.0,18000.0,Distance))*FMath::Clamp(Fog->GetGameTimeSinceCreation()/1.5f,0.f,1.f);
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Fog);
        for(auto* M:Meshes)
            if(auto* MID=Cast<UMaterialInstanceDynamic>(M->GetMaterial(0)))MID->SetScalarParameterValue(TEXT("FogOverallDensity"),Assets->ValleyFogDensity*Fade);
    }
    if(S.Fog.Num()>=4)return;
    const double Half=SizeMeters*50;const int32 Count=FMath::RoundToInt(SizeMeters/64);
    const int32 CX=FMath::FloorToInt((Center.X+Half)/6400),CY=FMath::FloorToInt((Center.Y+Half)/6400);
    int32 Best=-1;double BestScore=DBL_MAX;FVector Position,Normal;
    for(int32 Y=FMath::Max(0,CY-3);Y<=FMath::Min(Count-1,CY+3);++Y)
    for(int32 X=FMath::Max(0,CX-3);X<=FMath::Min(Count-1,CX+3);++X)
    {
        const int32 ID=Y*Count+X;if(S.Fog.Contains(ID))continue;
        const uint32 Key=TemperateHillsSurface::Key(X,Y,Seed,1731);
        const double WX=-Half+(X+.5)*6400+(TemperateHillsSurface::Unit(Key)-.5)*3000;
        const double WY=-Half+(Y+.5)*6400+(TemperateHillsSurface::Unit(Key+1)-.5)*3000;
        const FVector P(WX,WY,Height(WX,WY)+90);const double Distance=FVector::DistSquared2D(P,Center);
        if(Distance>FMath::Square(14000.0))continue;
        const FVector N=SurfaceNormal(WX,WY);if(N.Z<.9)continue;
        const double Nearby=(Height(WX-2000,WY)+Height(WX+2000,WY)+Height(WX,WY-2000)+Height(WX,WY+2000))*.25;
        const auto Bank=RiverPlan?RiverPlan->Sample(WX,WY):TemperateRiver::FSample();
        const bool Low=Bank.Bank>.02||Bank.Wet>.02||PathDistance(WX,WY)<4500||P.Z-90<Nearby-15;
        if(!Low)continue;
        const double Score=Distance+(Bank.Bank>.02||Bank.Wet>.02?0:16000000);
        if(Score<BestScore){Best=ID;BestScore=Score;Position=P;Normal=N;}
    }
    if(Best<0)return;
    const float Yaw=TemperateHillsSurface::Unit(uint32(Seed)+Best*133)*2*PI;
    const FRotator Rotation=FRotationMatrix::MakeFromZX(Normal,FVector(FMath::Cos(Yaw),FMath::Sin(Yaw),0)).Rotator();
    FActorSpawnParameters Params;Params.Owner=this;
    auto* Fog=GetWorld()->SpawnActor<AActor>(Assets->ValleyFogClass.Get(),Position,Rotation,Params);
    if(!Fog)return;
    Fog->SetActorEnableCollision(false);Fog->SetActorHiddenInGame(false);
    TInlineComponentArray<UStaticMeshComponent*> Meshes(Fog);
    for(auto* M:Meshes)
    {
        if(!M->GetStaticMesh())continue;
        const auto Bounds=M->GetStaticMesh()->GetBounds();
        const FVector Scale=FVector(1400,1000,180)/Bounds.BoxExtent;
        // Mesh bounds exclude the Blueprint's editor-only box/billboard bounds.
        M->SetRelativeScale3D(Scale);M->SetRelativeLocation(-Bounds.Origin*Scale);
        M->SetCollisionEnabled(ECollisionEnabled::NoCollision);M->SetCanEverAffectNavigation(false);M->SetCastShadow(false);
        auto* MID=UMaterialInstanceDynamic::Create(Assets->ValleyFogMaterial.Get(),Fog);
        MID->SetScalarParameterValue(TEXT("FogOverallDensity"),0);
        M->SetMaterial(0,MID);M->SetVisibility(true);M->SetHiddenInGame(false);M->PrecachePSOs();
    }
    // This also runs under the loading overlay, warming the volume shader before play.
    ValleyFog.Add(Fog);S.Fog.Add(Best,Fog);
}

void ATemperateHillsWorld::EndStreaming()
{
    EndBackdrop();
    if(!Streaming)return;
    auto& S=*Streaming;S.Stopping=true;
    // Completed handles transferred to the GameInstance keep the curated biome cached.
    if(!S.ResourcesRetained)for(auto& H:S.Handles)if(H){H->CancelHandle();H->ReleaseHandle();}
    for(auto& C:S.CVars)if(FMath::IsNearlyEqual(C.Variable->GetFloat(),C.Applied))C.Variable->Set(C.Previous,ECVF_SetByCode);
    // Pending numerical jobs contain no actor references and may finish after unload.
    Streaming.Reset();RiverPlan.Reset();
}
