#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "Async/Async.h"
#include "Algo/AllOf.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
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
#include "Widgets/Layout/SBorder.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace HillsStreaming
{
constexpr double CellSize=6400.0;
struct FMeshResult
{
    FIntPoint Key;
    bool Detailed=false;
    UE::Geometry::FDynamicMesh3 Mesh;
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
    bool Detailed=false;
    bool PendingDetailed=false;
};
struct FCVarOverride
{
    IConsoleVariable* Variable=nullptr;
    float Previous=0;
    float Applied=0;
};

TSharedPtr<FMeshResult,ESPMode::ThreadSafe> MakeMesh(FIntPoint Key,bool Detailed,double Half,int32 Seed)
{
    auto Result=MakeShared<FMeshResult,ESPMode::ThreadSafe>();Result->Key=Key;Result->Detailed=Detailed;
    auto& Mesh=Result->Mesh;Mesh.EnableAttributes();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
    const int32 Quads=Detailed?32:8;
    const double Step=CellSize/Quads,OX=-Half+Key.X*CellSize,OY=-Half+Key.Y*CellSize;
    for(int32 Y=0;Y<=Quads;++Y)for(int32 X=0;X<=Quads;++X)
    {
        const double WX=OX+X*Step,WY=OY+Y*Step;
        Mesh.AppendVertex(FVector3d(X*Step,Y*Step,TemperateHillsSurface::Height(WX,WY,Seed)));
        Normals->AppendElement(FVector3f(TemperateHillsSurface::Normal(WX,WY,Seed)));
        UVs->AppendElement(FVector2f(WX/400,WY/400));
    }
    auto Tri=[&](int32 A,int32 B,int32 C)
    {const int32 ID=Mesh.AppendTriangle(A,B,C);Normals->SetTriangle(ID,UE::Geometry::FIndex3i(A,B,C));UVs->SetTriangle(ID,UE::Geometry::FIndex3i(A,B,C));};
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
        Bottom.Add(Mesh.AppendVertex(Mesh.GetVertex(Top)-FVector3d(0,0,800)));
        Normals->AppendElement(Normals->GetElement(Top));UVs->AppendElement(UVs->GetElement(Top));
    }
    for(int32 I=0;I<Edge.Num();++I){const int32 J=(I+1)%Edge.Num();Tri(Edge[I],Bottom[J],Bottom[I]);Tri(Edge[I],Edge[J],Bottom[J]);}
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
    TArray<TSharedPtr<FStreamableHandle>> Handles;
    TArray<HillsStreaming::FCVarOverride> CVars;
    TMap<int32,TWeakObjectPtr<AActor>> Fog;
    TSharedPtr<SWidget> LoadingWidget;
    TWeakObjectPtr<ACharacter> HeldPawn;
    FText Status=FText::FromString(TEXT("正在准备出生区域…"));
    bool GroundReady=false;
    bool LoadingAssets=false;
    bool TreesActive=false;
    bool FogReady=false;
    bool Stopping=false;
    bool Failed=false;
    TArray<FSoftObjectPath> CompilingPaths;
    int32 PendingLayer=INDEX_NONE;
    int32 Stage=0;
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
    S.StartCell=FIntPoint(FMath::FloorToInt((Start.X+Half)/HillsStreaming::CellSize),FMath::FloorToInt((Start.Y+Half)/HillsStreaming::CellSize));
    // Apply only while this world exists; returning home restores previous budgets.
    for(const auto& Setting:TArray<TPair<const TCHAR*,float>>{{TEXT("pcg.FrameTime"),2.f},{TEXT("pcg.RuntimeGeneration.NumGeneratingComponents"),2.f},{TEXT("pcg.RuntimeGeneration.BasePoolSize"),16.f}})
        if(auto* C=IConsoleManager::Get().FindConsoleVariable(Setting.Key))
        {S.CVars.Add({C,C->GetFloat(),Setting.Value});C->Set(Setting.Value,ECVF_SetByCode);}
    const TWeakObjectPtr<ATemperateHillsWorld> Weak(this);
    if(auto* Viewport=GetWorld()->GetGameViewport())
    {
        S.LoadingWidget=SNew(SOverlay)+SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(24,0,0,130)
            [SNew(SBorder).Padding(14).BorderBackgroundColor(FLinearColor(.015,.025,.02,.85))
                .Visibility_Lambda([Weak](){return Weak.IsValid()&&Weak->Streaming&&(!Weak->bReady||Weak->Streaming->LoadingAssets||Weak->Streaming->Stage<8||Weak->Streaming->HeldPawn.IsValid()||Weak->Streaming->Failed)?EVisibility::HitTestInvisible:EVisibility::Collapsed;})
                [SNew(STextBlock).ColorAndOpacity(FLinearColor(.8,1,.85,1))
                    .Text_Lambda([Weak](){return Weak.IsValid()&&Weak->Streaming?Weak->Streaming->Status:FText::GetEmpty();})]];
        Viewport->AddViewportWidgetContent(S.LoadingWidget.ToSharedRef(),30);
    }
    S.LoadingAssets=true;
    S.Handles.Add(UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets->GroundMaterial.ToSoftObjectPath(),FStreamableDelegate::CreateWeakLambda(this,[this]()
    {
        if(!Streaming||Streaming->Stopping)return;
        Streaming->LoadingAssets=false;
        if(auto* Ground=Assets->GroundMaterial.Get())
        {GroundMID=UMaterialInstanceDynamic::Create(Ground,this);Streaming->GroundReady=true;}
        else{Streaming->Failed=true;Streaming->Status=FText::FromString(TEXT("地面资源加载失败，请返回主场景。"));}
    })));
}

void ATemperateHillsWorld::LoadNextEnvironmentStage()
{
    auto& S=*Streaming;
    if(S.LoadingAssets||S.Stage>=8||GetWorld()->GetTimeSeconds()<S.NextAssetTime)return;
    const int32 Stage=S.Stage++;
    TArray<FSoftObjectPath> Paths;
    const int32 Layer=Stage==0?3:(Stage==1?2:(Stage==2?1:0));
    if(Stage<3)
    {
        Paths.Add(Assets->Graphs[Layer].ToSoftObjectPath());
        if(Stage==0)HillsStreaming::AddPaths(Paths,Assets->Grass);
        if(Stage==1)HillsStreaming::AddPaths(Paths,Assets->Shrubs);
        if(Stage==2)HillsStreaming::AddPaths(Paths,Assets->Rocks);
        S.Status=FText::FromString(Stage==0?TEXT("正在载入附近草地…"):Stage==1?TEXT("正在载入林下灌木…"):TEXT("正在载入坡地岩石…"));
    }
    else if(Stage<7)
    {
        const int32 Variant=Stage-3;
        if(Assets->Trees.IsValidIndex(Variant))Paths.Add(Assets->Trees[Variant].ToSoftObjectPath());
        if(Stage==3){Paths.Add(Assets->Graphs[0].ToSoftObjectPath());Paths.Add(Assets->TrunkCollisionMesh.ToSoftObjectPath());}
        S.Status=FText::FromString(FString::Printf(TEXT("正在载入黑杨 %d/4，可在附近活动…"),Variant+1));
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
        auto& State=*Streaming;State.LoadingAssets=false;State.NextAssetTime=GetWorld()->GetTimeSeconds()+.5;
        State.CompilingPaths=Paths;
        if(Stage<3)
        {
            const bool Ready=Stage==0?HillsStreaming::Loaded(Assets->Grass):Stage==1?HillsStreaming::Loaded(Assets->Shrubs):HillsStreaming::Loaded(Assets->Rocks);
            if(Ready&&Assets->Graphs[Layer].IsValid())State.PendingLayer=Layer;
            else UE_LOG(LogTemp,Error,TEXT("HILLS_STREAM layer %d asset load failed"),Layer);
        }
        else if(Stage==6)
        {
            if(HillsStreaming::Loaded(Assets->Trees)&&Assets->Graphs[0].IsValid())
            {State.PendingLayer=0;}
            else UE_LOG(LogTemp,Error,TEXT("HILLS_STREAM tree asset load failed"));
        }
        else if(Stage==7)State.FogReady=Assets->ValleyFogClass.IsValid()&&Assets->ValleyFogMaterial.IsValid();
    })));
}

void ATemperateHillsWorld::TickStreaming()
{
    if(!Streaming||Streaming->Stopping||!Streaming->GroundReady)return;
    auto& S=*Streaming;
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
        if(!bReady){Detailed=true;return IsStart(K);}
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
        if(Ready){RemoveMesh(Cell.Mesh.Get());Pending->SetVisibility(true);Cell.Mesh=Pending;Cell.Pending.Reset();Cell.Detailed=Cell.PendingDetailed;}
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
        C->SetVisibility(!Cell.Mesh.IsValid());
        C->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);C->SetMaterial(0,GroundMID);
        C->bUseAsyncCooking=true;C->SetDeferredCollisionUpdatesEnabled(true,false);
        C->SetComplexAsSimpleCollisionEnabled(Result->Detailed,false);
        C->SetCollisionProfileName(Result->Detailed?TEXT("BlockAll"):TEXT("NoCollision"));
        C->SetMesh(MoveTemp(Result->Mesh));C->RegisterComponent();
        if(Result->Detailed)C->UpdateCollision(false);
        Terrain.Add(C);Cell.Pending=C;Cell.PendingDetailed=Result->Detailed;
        break;
    }
    // A single unload per frame avoids a matching destruction spike when moving.
    for(auto It=S.Cells.CreateIterator();It;++It)
    {
        if(DistanceSquared(It.Key())<=FMath::Square(ViewRadiusMeters*100.0+Size))continue;
        RemoveMesh(It.Value().Mesh.Get());RemoveMesh(It.Value().Pending.Get());
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
        Job.Future=Async(EAsyncExecution::ThreadPool,[Best,BestDetailed,Half,WorldSeed=Seed](){return HillsStreaming::MakeMesh(Best,BestDetailed,Half,WorldSeed);});
        S.Jobs.Add(MoveTemp(Job));
    }
    if(!bReady)
    {
        int32 Ready=0,Required=0;
        for(int32 Y=S.StartCell.Y-1;Y<=S.StartCell.Y+1;++Y)for(int32 X=S.StartCell.X-1;X<=S.StartCell.X+1;++X)
        {
            if(X<0||Y<0||X>=Count||Y>=Count)continue;
            ++Required;const auto* Cell=S.Cells.Find(FIntPoint(X,Y));if(Cell&&Cell->Mesh.IsValid()&&Cell->Detailed)++Ready;
        }
        S.Status=FText::FromString(FString::Printf(TEXT("正在生成出生区域 %d/%d…"),Ready,Required));
        if(Ready==Required&&Required>0)
        {
            bReady=true;S.NextAssetTime=GetWorld()->GetTimeSeconds()+1;
            AuditNext=GetWorld()->GetTimeSeconds()+24;
            UE_LOG(LogTemp,Display,TEXT("HILLS_READY seed=%d world=%s startup_cells=%d startup_ms=%.2f"),Seed,*WorldId.ToString(),Ready,(FPlatformTime::Seconds()-StartSeconds)*1000);
        }
        return;
    }
    bool Compiling=false;
#if WITH_EDITOR
    // Async package completion does not imply Nanite/skinned render-data completion.
    // Never let the PCG spawner force FinishCompilation on the game thread.
    for(const auto& Path:S.CompilingPaths)
    {
        if(auto* Mesh=Cast<USkeletalMesh>(Path.ResolveObject()))Compiling|=Mesh->IsCompiling();
        if(auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject()))Compiling|=Mesh->IsCompiling();
    }
#endif
    if(Compiling)S.Status=FText::FromString(TEXT("正在准备植被渲染数据，可在附近活动…"));
    else
    {
        S.CompilingPaths.Reset();
        if(S.PendingLayer!=INDEX_NONE)
        {ActivateVegetationLayer(S.PendingLayer);if(S.PendingLayer==0)S.TreesActive=true;S.PendingLayer=INDEX_NONE;}
        LoadNextEnvironmentStage();
    }
    // Guard an uncooked frontier or a teleport while its local collision catches up.
    if(Pawn)
    {
        const FVector Probe=Pawn->GetActorLocation()+Pawn->GetVelocity()*.35;
        const FIntPoint K(FMath::FloorToInt((Probe.X+Half)/Size),FMath::FloorToInt((Probe.Y+Half)/Size));
        const auto* Cell=S.Cells.Find(K);
        const bool Ready=Cell&&Cell->Detailed&&Cell->Mesh.IsValid();
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

void ATemperateHillsWorld::BuildValleyFog()
{
    auto& S=*Streaming;const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    const FVector Center=Pawn?Pawn->GetActorLocation():GetStartLocation();
    for(auto It=S.Fog.CreateIterator();It;++It)
        if(auto* Fog=It.Value().Get())if(FVector::DistSquared2D(Fog->GetActorLocation(),Center)>FMath::Square(18000.f))
        {ValleyFog.Remove(Fog);Fog->Destroy();It.RemoveCurrent();return;}
    if(S.Fog.Num()>=3)return;
    for(int32 I=0;I<9;++I)
    {
        if(S.Fog.Contains(I))continue;
        const double X=(-.42+I*.105)*SizeMeters*100;
        const double Y=TemperateHillsSurface::ValleyY(X,Seed)+(TemperateHillsSurface::Unit(uint32(Seed)+I*133)-.5)*4500;
        const FVector Position(X,Y,Height(X,Y)+90);
        if(FVector::DistSquared2D(Position,Center)>FMath::Square(14000.f))continue;
        FActorSpawnParameters Params;Params.Owner=this;
        auto* Fog=GetWorld()->SpawnActor<AActor>(Assets->ValleyFogClass.Get(),Position,FRotator(0,I*41,0),Params);
        if(!Fog)return;
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Fog);
        for(auto* M:Meshes)
        {M->SetCollisionEnabled(ECollisionEnabled::NoCollision);M->SetCanEverAffectNavigation(false);M->SetCastShadow(false);M->SetMaterial(0,Assets->ValleyFogMaterial.Get());}
        Fog->SetActorEnableCollision(false);FVector Origin,Extent;Fog->GetActorBounds(false,Origin,Extent);
        if(Extent.GetMin()>1)Fog->SetActorScale3D(Fog->GetActorScale3D()*FVector(4200/Extent.X,2700/Extent.Y,220/Extent.Z));
        ValleyFog.Add(Fog);S.Fog.Add(I,Fog);return;
    }
}

void ATemperateHillsWorld::EndStreaming()
{
    if(!Streaming)return;
    auto& S=*Streaming;S.Stopping=true;
    for(auto& H:S.Handles)if(H){H->CancelHandle();H->ReleaseHandle();}
    if(S.LoadingWidget)if(auto* Viewport=GetWorld()->GetGameViewport())Viewport->RemoveViewportWidgetContent(S.LoadingWidget.ToSharedRef());
    for(auto& C:S.CVars)if(FMath::IsNearlyEqual(C.Variable->GetFloat(),C.Applied))C.Variable->Set(C.Previous,ECVF_SetByCode);
    // Pending numerical jobs contain no actor references and may finish after unload.
    Streaming.Reset();
}
