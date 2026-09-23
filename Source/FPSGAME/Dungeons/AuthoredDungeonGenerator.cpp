#include "AuthoredDungeonGenerator.h"
#include "DungeonPusChannel.h"
#include "Async/Async.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "DungeonPerformanceScope.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Animation/SkeletalMeshActor.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Materials/MaterialInterface.h"
#include "Misc/DateTime.h"
#include "TimerManager.h"
#include "DungeonBossEncounter.h"
#include "../Monsters/HandBrainMonster.h"
#include "NavigationSystem.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Components/BrushComponent.h"
#include "EngineUtils.h"
#include "AuthoredDungeonDressing.inl"
#include "AuthoredDungeonDressingGeometry.inl"
#include "AuthoredDungeonDressingTests.inl"
#include <queue>

namespace AuthoredDungeon
{
using JObject=TSharedPtr<FJsonObject>;
FVector Vec(const JObject& O,const TCHAR* Key)
{
    const auto& V=O->GetArrayField(Key);return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
}
struct FPort { FVector P,N; double Width=300,Height=280; };
FPort ReadPort(const JObject& Data)
{
    FPort Port{Vec(Data,TEXT("position")),Vec(Data,TEXT("normal"))};
    Data->TryGetNumberField(TEXT("width"),Port.Width);Data->TryGetNumberField(TEXT("height"),Port.Height);
    return Port;
}
struct FSideSocket { FPort Port; JObject Data; };
struct FModule { FString Id; FBox Bounds; TArray<FPort> Ports; JObject Data; TArray<FBox> Cells; TArray<FSideSocket> SideSockets; };
struct FPlaced { int32 Module; FTransform Transform; FBox Bounds; FString Route; TArray<FBox> Cells; int32 Side=-1; };
struct FSocket { FVector P,N; int32 Owner=-1; double Width=300,Height=280; };
struct FPlan
{
    TArray<FModule> Modules;
    TArray<FPlaced> Pieces;
    FBox Reserved;
    FRandomStream Random;
    int32 Transit=-1,Threshold=-1,Junction=-1,End=-1;
    int32 Treasure=-1,TreasureLink=-1,TreasureCount=0;
    double TreasureChance=0;
    TArray<int32> Combat;
    int32 SearchBudget=0;
    int32 MinRooms=3,MaxRooms=5,GroupLinks=3,BranchLinks=6;
    bool bStrictPorts=false;
    bool Compatible(const FSocket& Socket,int32 Module,int32 Entry)const
    {
        if(!Modules.IsValidIndex(Module)||!Modules[Module].Ports.IsValidIndex(Entry))return false;
        const auto& Port=Modules[Module].Ports[Entry];
        return !bStrictPorts||(Port.Width>=300&&Port.Height>=280&&FMath::Abs(Port.Width-Socket.Width)<1&&FMath::Abs(Port.Height-Socket.Height)<1);
    }
    TArray<int32> Counts;
    int32 Find(const FString& Id)const{return Modules.IndexOfByPredicate([&](const FModule& M){return M.Id==Id;});}
    bool Overlap(const FBox& A,const FBox& B)const
    {
        return FMath::Min(A.Max.X,B.Max.X)-FMath::Max(A.Min.X,B.Min.X)>8 &&
               FMath::Min(A.Max.Y,B.Max.Y)-FMath::Max(A.Min.Y,B.Min.Y)>8;
    }
    FTransform Fit(int32 Module,int32 Entry,const FSocket& S)const
    {
        const FPort& P=Modules[Module].Ports[Entry];
        const double Yaw=(-S.N).Rotation().Yaw-P.N.Rotation().Yaw;
        const FQuat Q=FRotator(0,Yaw,0).Quaternion();return FTransform(Q,S.P-Q.RotateVector(P.P));
    }
    FSocket Socket(int32 Owner,int32 Port)const
    {
        const auto& A=Pieces[Owner];const auto& M=Modules[A.Module];
        const auto& P=Port<M.Ports.Num()?M.Ports[Port]:M.SideSockets[A.Side].Port;
        return {A.Transform.TransformPosition(P.P),A.Transform.TransformVectorNoScale(P.N),Owner,P.Width,P.Height};
    }
    int32 PortCount(int32 Owner)const{return Modules[Pieces[Owner].Module].Ports.Num()+(Pieces[Owner].Side>=0?1:0);}
    bool Place(int32 Module,const FTransform& T,const FString& Route,int32 IgnoreFrom=-2,int32 IgnoreOwner=-2,
               FVector SectorOrigin=FVector::ZeroVector,FVector SectorDir=FVector::ZeroVector,int32 SecondOwner=-2)
    {
        const FBox B=Modules[Module].Bounds.TransformBy(T);
        TArray<FBox> Cells;for(const FBox& Local:Modules[Module].Cells)Cells.Add(Local.TransformBy(T));
        if(IgnoreOwner!=-1)for(const FBox& Cell:Cells)if(Overlap(Cell,Reserved))return false;
        for(int32 I=0;I<Pieces.Num();++I)
            if(I!=IgnoreOwner && I!=SecondOwner && !(IgnoreFrom>=0&&I>=IgnoreFrom) && Overlap(B,Pieces[I].Bounds))
                for(const FBox& Cell:Cells)for(const FBox& Other:Pieces[I].Cells)if(Overlap(Cell,Other))return false;
        if(!SectorDir.IsNearlyZero())
        {
            const FVector Side(-SectorDir.Y,SectorDir.X,0);
            for(double X:{B.Min.X,B.Max.X})for(double Y:{B.Min.Y,B.Max.Y})
            {
                const FVector D=FVector(X,Y,0)-SectorOrigin;
                const double Forward=FVector::DotProduct(D,SectorDir);
                if(Forward<400||FMath::Abs(FVector::DotProduct(D,Side))>Forward*.85+150)return false;
            }
        }
        Pieces.Add({Module,T,B,Route,Cells});return true;
    }
    bool Corridor(int32 Count,FSocket& S,const FString& Route,int32 Connector=-1)
    {
        if(Connector<0)Connector=Transit;
        const int32 Before=Pieces.Num(),InitialOwner=S.Owner;const FSocket Initial=S;
        for(int32 I=0;I<Count;++I)
        {
            if(!Compatible(S,Connector,0)||!Place(Connector,Fit(Connector,0,S),Route,Before,InitialOwner)){Pieces.SetNum(Before);S=Initial;return false;}
            S=Socket(Pieces.Num()-1,1);
        }
        return true;
    }
    bool Chain(int32 Remaining,FSocket& S,const FString& Route,FVector SectorOrigin={},FVector SectorDir={})
    {
        if(Remaining==0)return true;
        if(--SearchBudget<0)return false;
        TArray<TPair<int32,int32>> Choices;
        for(int32 M:Combat)for(int32 Entry=0;Entry<2;++Entry)Choices.Emplace(M,Entry);
        for(int32 I=Choices.Num()-1;I>0;--I)Choices.Swap(I,Random.RandRange(0,I));
        const int32 Before=Pieces.Num();const FSocket Initial=S;
        for(const auto& Choice:Choices)for(int32 Length:{1,2,3,5})
        {
            Pieces.SetNum(Before);S=Initial;
            if(!Corridor(Length,S,Route,Threshold))continue;
            if(!Compatible(S,Choice.Key,Choice.Value)||!Place(Choice.Key,Fit(Choice.Key,Choice.Value,S),Route,Before,-2,SectorOrigin,SectorDir))continue;
            S=Socket(Pieces.Num()-1,1-Choice.Value);
            if(Chain(Remaining-1,S,Route,SectorOrigin,SectorDir))return true;
        }
        Pieces.SetNum(Before);S=Initial;return false;
    }
    #include "AuthoredDungeonRouting.inl"
    bool Build(int32 Seed,const FSocket& Start)
    {
        for(int32 Attempt=0;Attempt<80;++Attempt)
        {
            Pieces.Reset();Counts.Reset();Random.Initialize(Seed+Attempt*7919);SearchBudget=2500;
            FSocket S=Start;const int32 MainCount=Random.RandRange(MinRooms,MaxRooms);Counts.Add(MainCount);
            if(!Chain(MainCount,S,TEXT("Approach"))||!Corridor(GroupLinks,S,TEXT("Approach")))continue;
            if(!Place(Junction,Fit(Junction,0,S),TEXT("Junction"),-2,S.Owner))continue;
            const int32 Hub=Pieces.Num()-1;
            const FVector Center=Pieces[Hub].Bounds.GetCenter()*FVector(1,1,0);
            TArray<FSocket> BossTargets;
            if(bBossTerminal&&!ReserveBoss(Center,Socket(Hub,1).N,BossTargets))continue;
            TArray<FSocket> Exits;TArray<FVector> Directions;bool Good=true;
            // Reserve all three leads before extending any route, so one branch cannot close another door.
            for(int32 Port=1;Port<4;++Port)
            {
                FSocket Branch=Socket(Hub,Port);Directions.Add(Branch.N);
                if(!Corridor(BranchLinks,Branch,FString::Printf(TEXT("Route%d"),Port))){Good=false;break;}
                Exits.Add(Branch);
            }
            if(!Good)continue;
            for(int32 I=0;I<3;++I)
            {
                const FString Route=FString::Printf(TEXT("Route%d"),I+1);const int32 Count=Random.RandRange(MinRooms,MaxRooms);Counts.Add(Count);
                FSocket Branch=Exits[I];
                if(!Chain(Count,Branch,Route,Center,Directions[I])||!Corridor(GroupLinks,Branch,Route))
                {Good=false;break;}
                if(bBossTerminal? !RouteTo(Branch,BossTargets[I],Route+TEXT("_Confluence")):
                   !Place(End,Fit(End,0,Branch),Route,-2,Branch.Owner)){Good=false;break;}
            }
            if(Good)return true;
        }
        return false;
    }
    void AddTreasureRooms(int32 Seed)
    {
        if(Treasure<0||TreasureLink<0||TreasureChance<=0)return;
        FRandomStream SideRandom(Seed^0x54A391);const int32 MainPieces=Pieces.Num();
        // One independent chance per ordinary room. The completed route graph reserves its space first.
        for(int32 Owner=0;Owner<MainPieces;++Owner)
        {
            const int32 ParentModule=Pieces[Owner].Module;
            if(!Combat.Contains(ParentModule)||Modules[ParentModule].SideSockets.IsEmpty()||SideRandom.FRand()>=TreasureChance)continue;
            TArray<int32> Choices;for(int32 I=0;I<Modules[ParentModule].SideSockets.Num();++I)Choices.Add(I);
            for(int32 I=Choices.Num()-1;I>0;--I)Choices.Swap(I,SideRandom.RandRange(0,I));
            const int32 Before=Pieces.Num();
            for(int32 Side:Choices)
            {
                Pieces.SetNum(Before);const auto& P=Modules[ParentModule].SideSockets[Side].Port;
                const FTransform ParentTransform=Pieces[Owner].Transform;
                FSocket S{ParentTransform.TransformPosition(P.P),ParentTransform.TransformVectorNoScale(P.N),Owner,P.Width,P.Height};
                const FString Route=Pieces[Owner].Route+FString::Printf(TEXT("_Treasure%d"),Owner);
                if(!Place(TreasureLink,Fit(TreasureLink,0,S),Route,-2,Owner))continue;
                S=Socket(Pieces.Num()-1,1);
                if(!Place(Treasure,Fit(Treasure,0,S),Route,-2,S.Owner))continue;
                // The wall is opened only after both the vestibule and the entire side room fit.
                Pieces[Owner].Side=Side;++TreasureCount;break;
            }
            if(Pieces[Owner].Side<0)Pieces.SetNum(Before);
        }
    }
};
FTransform Local(const JObject& P)
{
    double Yaw=0,Pitch=0,Roll=0;P->TryGetNumberField(TEXT("yaw"),Yaw);
    P->TryGetNumberField(TEXT("pitch"),Pitch);P->TryGetNumberField(TEXT("roll"),Roll);
    return FTransform(FRotator(Pitch,Yaw,Roll),Vec(P,TEXT("position")),Vec(P,TEXT("scale")));
}
}

struct FAuthoredDungeonBuildState
{
    struct FJob { FName Stage; TFunction<void()> Run; };
    AuthoredDungeon::FPlan Plan;
    AuthoredDungeon::JObject Catalog;
    TArray<FJob> Jobs;
    TMap<FString,UObject*> Assets; // Retained by generator's GenerationResources during assembly.
    TMap<FString,TWeakObjectPtr<UInstancedStaticMeshComponent>> InstanceGroups;
    TMap<FString,int32> InstanceCandidates;
    TMap<FName,double> PhaseMs;
    DungeonDressing::FPlacementScene DressingScene;
    TMap<FString,int32> DressingRejections;
    int32 DressingCandidates=0,DressingSkipped=0;
    int32 Seed=0,Cursor=0,Parts=0,Instances=0,InstanceComponents=0,StaticFallbacks=0,Hazards=0,Props=0,DressingProps=0,Lights=0,AssetResolutions=0,Slices=0;
    double StartedAt=FPlatformTime::Seconds(),FinishedAt=0,PlanMs=0,PeakSliceMs=0;
    FString Error;
    FString PendingDescription,PendingManifest;
    TArray<TObjectPtr<AActor>> PreviousActors;
    TArray<FAuthoredDungeonLightModule> NextLights;
    bool bStaging=false,bCommitted=false,bNavigationRequested=false;
    double NavigationRequestedAt=0;
    bool bPlanning=true,bPlanSucceeded=false,bRuntime=false,bCompleted=false;
};

namespace
{
TAutoConsoleVariable<float> DungeonBuildBudget(TEXT("fps.Dungeon.Generation.BudgetMs"),3.f,
    TEXT("Game-thread assembly budget per frame, milliseconds. One indivisible mesh/physics registration may exceed it."));
TAutoConsoleVariable<int32> DungeonInstancing(TEXT("fps.Dungeon.Instancing"),1,
    TEXT("Instance repeated rigid Nanite meshes in spatial groups on next generation. Non-Nanite meshes retain individual components for Lumen."));
TAutoConsoleVariable<int32> DungeonDressingEnabled(TEXT("fps.Dungeon.Dressing"),1,
    TEXT("Generate cosmetic wall-side prop clusters with the next dungeon. Never consumes the route random stream."));

bool PartAffectsNavigation(const AuthoredDungeon::JObject& Part)
{
    const FString Path=Part->GetStringField(TEXT("mesh"));
    // Authored wall tiles sit over a collidable Shell. Exporting their bevel/fracture triangles
    // repeats the same wall at enormous cost; keep their physical/ballistic collision untouched.
    bool Affects=!Path.EndsWith(TEXT("_Tiles"))&&!Path.EndsWith(TEXT("_Fixtures"));
    Part->TryGetBoolField(TEXT("affects_navigation"),Affects);
    return Affects&&!Part->GetBoolField(TEXT("fluid"))&&Part->GetBoolField(TEXT("collision"));
}

FString InstanceKey(const AuthoredDungeon::JObject& Part,const AuthoredDungeon::FPlaced& Piece,bool bOptimizeLights)
{
    // Limit bounds to a 40 m spatial group; materials, collision and shadow policy never mix.
    const FVector P=Piece.Transform.GetLocation();
    FString Key=FString::Printf(TEXT("%d,%d|%d|%d|%s"),FMath::FloorToInt(P.X/4000.),FMath::FloorToInt(P.Y/4000.),
        Part->GetBoolField(TEXT("collision")),bOptimizeLights,*Part->GetStringField(TEXT("mesh")));
    bool Shadow=true;Part->TryGetBoolField(TEXT("cast_shadow"),Shadow);Key+=Shadow?TEXT("|S"):TEXT("|N");
    Key+=PartAffectsNavigation(Part)?TEXT("|Nav"):TEXT("|NoNav");
    for(const auto& Material:Part->GetArrayField(TEXT("materials")))Key+=TEXT("|")+Material->AsString();
    return Key;
}

UTransitLoadingSubsystem* DungeonLoading(const AActor* Actor)
{
    const UWorld* World=Actor->GetWorld();
    return World&&World->IsGameWorld()&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
}
}

AAuthoredDungeonGenerator::AAuthoredDungeonGenerator()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickGroup=TG_PrePhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("DungeonRoot")));
}
void AAuthoredDungeonGenerator::ClearGenerated()
{
    GetWorldTimerManager().ClearTimer(RoomLightingTimer);LightModules.Reset();
    for(AActor* A:GeneratedActors)if(IsValid(A))A->Destroy();GeneratedActors.Reset();
}
void AAuthoredDungeonGenerator::GeneratePreview(){Generate(PreviewSeed);}
void AAuthoredDungeonGenerator::BeginPlay()
{
    Super::BeginPlay();if(GetNetMode()!=NM_Standalone)return;
    const TCHAR* Option=GetWorld()->URL.GetOption(TEXT("DungeonSeed="),nullptr);
    const int32 Seed=Option?FCString::Atoi(Option):bRandomizeOnEntry?int32(FDateTime::UtcNow().GetTicks()&0x7fffffff):PreviewSeed;
    Generate(Seed);
}
void AAuthoredDungeonGenerator::Generate(int32 Seed)
{
    using namespace AuthoredDungeon;
    CancelAssembly();
    Tags.Remove(TEXT("DungeonAssembly.Ready"));Tags.Remove(TEXT("DungeonAssembly.Failed"));
    BuildState=MakeShared<FAuthoredDungeonBuildState,ESPMode::ThreadSafe>();
    auto State=BuildState;State->Seed=Seed;State->bRuntime=GetWorld()->IsGameWorld();
    if(State->bRuntime)
    {
        if(auto* Loading=DungeonLoading(this))Loading->BeginDungeonPreparation();
        HoldPlayers();SetActorTickEnabled(true);
    }
    DungeonPerformance::FScope CatalogScope(this,TEXT("Dungeon.Catalog"));
    JObject Catalog;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(ModuleCatalogJson),Catalog)||!Catalog)
    {State->Error=TEXT("地牢目录无法读取");State->bPlanning=false;PumpAssembly(true);return;}
    State->Catalog=Catalog;
    FPlan& Plan=State->Plan;
    Plan.MinRooms=FMath::Max(1,int32(Catalog->GetNumberField(TEXT("min_rooms"))));
    Plan.MaxRooms=FMath::Max(Plan.MinRooms,int32(Catalog->GetNumberField(TEXT("max_rooms"))));
    Plan.GroupLinks=FMath::Max(1,int32(Catalog->GetNumberField(TEXT("group_links"))));
    Plan.BranchLinks=FMath::Max(1,int32(Catalog->GetNumberField(TEXT("branch_links"))));
    Catalog->TryGetBoolField(TEXT("strict_ports"),Plan.bStrictPorts);
    Plan.Reserved=FBox(Vec(Catalog,TEXT("reserved_min")),Vec(Catalog,TEXT("reserved_max")));
    for(const auto& Value:Catalog->GetArrayField(TEXT("modules")))
    {
        JObject D=Value->AsObject();FModule M;M.Data=D;M.Id=D->GetStringField(TEXT("id"));M.Bounds=FBox(Vec(D,TEXT("min")),Vec(D,TEXT("max")));
        for(const auto& V:D->GetArrayField(TEXT("ports")))M.Ports.Add(ReadPort(V->AsObject()));
        for(const auto& V:D->GetArrayField(TEXT("cells"))){JObject C=V->AsObject();M.Cells.Add(FBox(Vec(C,TEXT("min")),Vec(C,TEXT("max"))));}
        const TArray<TSharedPtr<FJsonValue>>* Sides=nullptr;
        if(D->TryGetArrayField(TEXT("side_sockets"),Sides))for(const auto& V:*Sides)
        {JObject S=V->AsObject();M.SideSockets.Add({ReadPort(S),S});}
        if(Plan.Find(M.Id)>=0||M.Cells.IsEmpty()||M.Ports.IsEmpty())
        {State->Error=TEXT("地牢模块重复或缺少占地/端口：")+M.Id;State->bPlanning=false;PumpAssembly(true);return;}
        Plan.Modules.Add(M);
    }
    Plan.Transit=Plan.Find(TEXT("Transit"));Plan.Threshold=Plan.Find(TEXT("Threshold"));Plan.Junction=Plan.Find(TEXT("Junction"));Plan.End=Plan.Find(TEXT("RouteEnd"));
    Plan.Treasure=Plan.Find(TEXT("Treasure"));Plan.TreasureLink=Plan.Find(TEXT("TreasureLink"));
    Catalog->TryGetBoolField(TEXT("boss_terminal_enabled"),Plan.bBossTerminal);
    Plan.BossRoom=Plan.Find(TEXT("BossPumpHall"));Plan.BossConfluence=Plan.Find(TEXT("BossConfluence"));
    Plan.BossApproach=Plan.Find(TEXT("BossApproach"));Plan.Elbow=Plan.Find(TEXT("RouteElbow"));
    if(Plan.bBossTerminal&&(Plan.BossRoom<0||Plan.BossConfluence<0||Plan.BossApproach<0||Plan.Elbow<0))
    {State->Error=TEXT("Boss 汇流目录缺少终端或转角模块");State->bPlanning=false;PumpAssembly(true);return;}
    Catalog->TryGetNumberField(TEXT("treasure_chance_per_room"),Plan.TreasureChance);Plan.TreasureChance=FMath::Clamp(Plan.TreasureChance,0.0,1.0);
    const TArray<TSharedPtr<FJsonValue>>* RoomIds=nullptr;
    if(Catalog->TryGetArrayField(TEXT("room_ids"),RoomIds))
    {
        for(const auto& Id:*RoomIds)Plan.Combat.AddUnique(Plan.Find(Id->AsString()));
    }
    else
    {
        for(const FString Id:{TEXT("Distribution"),TEXT("Drainage"),TEXT("ShoredBreach")})Plan.Combat.Add(Plan.Find(Id));
    }
    if(Plan.Transit<0||Plan.Threshold<0||Plan.Junction<0||Plan.End<0||Plan.Combat.IsEmpty()||Plan.Combat.Contains(-1))
    {State->Error=TEXT("地牢目录缺少必需模块");State->bPlanning=false;PumpAssembly(true);return;}
    for(int32 Index:Plan.Combat)
    {
        const auto& Room=Plan.Modules[Index];FString RoomRole;Room.Data->TryGetStringField(TEXT("role"),RoomRole);
        if(Room.Ports.Num()!=2||RoomRole==TEXT("boss_terminal")||RoomRole==TEXT("terminal_confluence"))
        {State->Error=TEXT("普通房池必须使用双门战斗房：")+Room.Id;State->bPlanning=false;PumpAssembly(true);return;}
    }
    if(Plan.Modules[Plan.Transit].Ports.Num()!=2||Plan.Modules[Plan.Threshold].Ports.Num()!=2||Plan.Modules[Plan.Junction].Ports.Num()!=4)
    {State->Error=TEXT("连接件或岔路房端口数量错误");State->bPlanning=false;PumpAssembly(true);return;}
    const AuthoredDungeon::FSocket Start{Vec(Catalog,TEXT("start_position")),Vec(Catalog,TEXT("start_normal")),-1};
    auto PlanWork=[State,Start]()
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Dungeon_LayoutSearch);
        const double Begin=FPlatformTime::Seconds();
        State->bPlanSucceeded=State->Plan.Build(State->Seed,Start);
        if(State->bPlanSucceeded)State->Plan.AddTreasureRooms(State->Seed);
        State->PlanMs=(FPlatformTime::Seconds()-Begin)*1000.;
    };
    if(State->bRuntime)
    {
        const uint64 Serial=GenerationSerial;
        TWeakObjectPtr<AAuthoredDungeonGenerator> WeakThis(this);
        // The worker owns only immutable catalog JSON and plain layout data, never UObjects.
        Async(EAsyncExecution::ThreadPool,[State,PlanWork=MoveTemp(PlanWork),WeakThis,Serial]() mutable
        {
            PlanWork();
            AsyncTask(ENamedThreads::GameThread,[State,WeakThis,Serial]()
            {
                auto* Generator=WeakThis.Get();
                if(!Generator||Generator->GenerationSerial!=Serial)return;
                State->bPlanning=false;Generator->PrepareAssembly();
            });
        });
    }
    else {PlanWork();State->bPlanning=false;PrepareAssembly();PumpAssembly(true);}
}

void AAuthoredDungeonGenerator::PrepareAssembly()
{
    using namespace AuthoredDungeon;
    auto* State=BuildState.Get();
    FPlan& Plan=State->Plan;const JObject Catalog=State->Catalog;const int32 Seed=State->Seed;
    if(!State->bPlanSucceeded)
    {State->Error=FString::Printf(TEXT("种子 %d 未找到完整布局，保留原场景"),Seed);return;}
    DungeonPerformance::FScope Scope(this,TEXT("Dungeon.PrepareJobs"));
    const double PrepareStarted=FPlatformTime::Seconds();
    // A complete plan is obtained before replacing the current preview or runtime assembly.
    if(State->bRuntime)
    {
        // Teardown is sorted after successful staging; keep the old room lights alive until commit.
        // Keep ownership entries until destruction completes, including cancellation/re-generation.
        for(AActor* Actor:GeneratedActors)if(IsValid(Actor))
        {
            TWeakObjectPtr<AActor> Old(Actor);
            State->Jobs.Add({TEXT("Dungeon.Teardown"),[Old](){if(auto* A=Old.Get())A->Destroy();}});
        }
    }
    // Editor preview also retains the previous geometry until staging succeeds.
    const bool bOptimizeLights=AuthoredDungeonLighting::IsOptimizationEnabled();
    bLightingOptimizationApplied=bOptimizeLights;
    auto& StagedLightModules=State->NextLights;
    StagedLightModules.SetNum(Plan.Pieces.Num()+1);
    StagedLightModules.Last().Cells.Add(Plan.Reserved); // Preserved start: connectivity only, no changes to its lights.
    for(int32 I=0;I<Plan.Pieces.Num();++I)
    {
        StagedLightModules[I].Cells=Plan.Pieces[I].Cells;
        const FString& Id=Plan.Modules[Plan.Pieces[I].Module].Id;
        StagedLightModules[I].bConnector=Id==TEXT("Transit")||Id==TEXT("Threshold")||Id==TEXT("TreasureLink")||Id==TEXT("RouteElbow")||Id==TEXT("BossApproach");
    }
    auto ConnectLights=[&](int32 From,int32 To,FVector Door)
    {
        const FVector Center=Door+FVector(0,0,180);
        const FVector Extent(200,200,180); // Encloses the authored door opening in either orientation.
        StagedLightModules[From].Portals.Add({To,Center,Extent});
        StagedLightModules[To].Portals.Add({From,Center,Extent});
    };
    ConnectLights(Plan.Pieces.Num(),0,Vec(Catalog,TEXT("start_position")));
    JObject Graph=MakeShared<FJsonObject>();Graph->SetNumberField(TEXT("seed"),Seed);
    TArray<TSharedPtr<FJsonValue>> Nodes,Edges;
    auto JsonVector=[](FVector V){return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};};
    for(int32 I=0;I<Plan.Pieces.Num();++I)
    {
        const auto& P=Plan.Pieces[I];JObject N=MakeShared<FJsonObject>();N->SetNumberField(TEXT("id"),I);N->SetStringField(TEXT("module"),Plan.Modules[P.Module].Id);N->SetStringField(TEXT("route"),P.Route);N->SetArrayField(TEXT("origin"),JsonVector(P.Transform.GetLocation()));N->SetNumberField(TEXT("yaw"),P.Transform.Rotator().Yaw);
        Nodes.Add(MakeShared<FJsonValueObject>(N));
        if(P.Side>=0)N->SetStringField(TEXT("side_socket"),Plan.Modules[P.Module].SideSockets[P.Side].Data->GetStringField(TEXT("id")));
        for(int32 J=0;J<I;++J)for(int32 A=0;A<Plan.PortCount(I);++A)for(int32 B=0;B<Plan.PortCount(J);++B)
        {
            const auto SA=Plan.Socket(I,A),SB=Plan.Socket(J,B);
            if(SA.P.Equals(SB.P,1)&&FVector::DotProduct(SA.N,SB.N)<-.99)
            {
                JObject E=MakeShared<FJsonObject>();E->SetNumberField(TEXT("from"),J);E->SetNumberField(TEXT("from_port"),B);E->SetNumberField(TEXT("to"),I);E->SetNumberField(TEXT("to_port"),A);Edges.Add(MakeShared<FJsonValueObject>(E));
                ConnectLights(J,I,SA.P);
            }
        }
    }
    Graph->SetNumberField(TEXT("treasure_rooms"),Plan.TreasureCount);
    Graph->SetNumberField(TEXT("boss_rooms"),Plan.bBossTerminal?1:0);
    Graph->SetArrayField(TEXT("nodes"),Nodes);Graph->SetArrayField(TEXT("connections"),Edges);State->PendingManifest.Empty();FJsonSerializer::Serialize(Graph.ToSharedRef(),TJsonWriterFactory<>::Create(&State->PendingManifest));
    TSet<FString> QueuedAssets;
    auto QueueAsset=[this,State,&QueuedAssets](const FString& Path)
    {
        if(Path.IsEmpty()||QueuedAssets.Contains(Path))return;
        QueuedAssets.Add(Path);
        State->Jobs.Add({TEXT("Dungeon.Resources"),[this,Path](){ResolveGenerationAsset(Path);}});
    };
    bool RequireNavigation=false;Catalog->TryGetBoolField(TEXT("navigation_required"),RequireNavigation);
    if(RequireNavigation)State->Jobs.Add({TEXT("Dungeon.Resources"),[this,State]()
    {
        bool Found=false;for(TActorIterator<ANavMeshBoundsVolume> It(GetWorld());It;++It)Found|=It->ActorHasTag(TEXT("DungeonRouteNavigation"));
        if(!Found||!FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))State->Error=TEXT("地牢导航模板缺失，保留原布局");
    }});
    FActorSpawnParameters Params;Params.Owner=this;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const bool bDressRooms=DungeonDressingEnabled.GetValueOnGameThread()!=0;
    for(int32 Index=0;Index<Plan.Pieces.Num();++Index)
    {
        const FPlaced& Piece=Plan.Pieces[Index];const JObject D=Plan.Modules[Piece.Module].Data;
        TArray<TSharedPtr<FJsonValue>> Parts=D->GetArrayField(TEXT("parts"));
        if(Piece.Side>=0)
        {
            const auto& Side=Plan.Modules[Piece.Module].SideSockets[Piece.Side].Data;
            const auto& Remove=Side->GetArrayField(TEXT("replace_suffixes"));
            Parts.RemoveAll([&](const TSharedPtr<FJsonValue>& V){const FString Path=V->AsObject()->GetStringField(TEXT("mesh"));for(const auto& S:Remove)if(Path.EndsWith(S->AsString()))return true;return false;});
            Parts.Append(Side->GetArrayField(TEXT("parts")));
        }
        if(bDressRooms) Parts.Append(DungeonDressing::Build(D,Seed,Index));
        for(const auto& V:Parts)
        {
            const JObject Part=V->AsObject();
            bool Dressing=false;Part->TryGetBoolField(TEXT("dressing"),Dressing);
            QueueAsset(Part->GetStringField(TEXT("mesh")));
            for(const auto& M:Part->GetArrayField(TEXT("materials")))QueueAsset(M->AsString());
            const FString Key=InstanceKey(Part,Piece,bOptimizeLights);
            if(!Part->GetBoolField(TEXT("fluid"))&&!Part->HasField(TEXT("half_size")))++State->InstanceCandidates.FindOrAdd(Key);
            State->Jobs.Add({Dressing?FName(TEXT("Dungeon.Dressing")):FName(TEXT("Dungeon.MeshCollision")),[this,State,Part,Piece,Index,Params,bOptimizeLights,Key,Dressing,bDressRooms]()
            {
            auto* Mesh=Cast<UStaticMesh>(ResolveGenerationAsset(Part->GetStringField(TEXT("mesh"))));
            if(!Mesh){State->Error=TEXT("地牢网格无法载入：")+Part->GetStringField(TEXT("mesh"));return;}
            FTransform T=Local(Part)*Piece.Transform;
            const bool Hazard=Part->HasField(TEXT("half_size")),Fluid=Part->GetBoolField(TEXT("fluid"));
            if(Dressing)
            {
                ++State->DressingCandidates;FString Reason;
                if(!State->DressingScene.Place(Mesh->GetBoundingBox(),Part,State->Plan.Modules[Piece.Module].Data,Piece.Transform,Index,T,Reason))
                {++State->DressingSkipped;++State->DressingRejections.FindOrAdd(Reason);return;}
            }
            else if(bDressRooms)
            {
                if(Fluid || Hazard) State->DressingScene.FixedBoxes.Add(Mesh->GetBoundingBox().TransformBy(T).ExpandBy(5));
                else State->DressingScene.AddMesh(Mesh,T,Index,Part->GetStringField(TEXT("mesh")));
            }
            const bool bInstance=!Dressing&&!Fluid&&!Hazard&&DungeonInstancing.GetValueOnGameThread()!=0&&Mesh->HasValidNaniteData()
                &&State->InstanceCandidates.FindRef(Key)>1;
            if(bInstance)
            {
                if(auto* Existing=State->InstanceGroups.FindRef(Key).Get())
                {
                    Existing->AddInstance(T,true);
                    Existing->ComponentTags.AddUnique(FName(*FString::Printf(TEXT("DungeonModule.%d.%s"),Index,*State->Plan.Modules[Piece.Module].Id)));
                    ++State->Parts;++State->Instances;return;
                }
            }
            AActor* A=nullptr;UStaticMeshComponent* C=nullptr;
            if(Hazard)
            {
                auto* H=GetWorld()->SpawnActorDeferred<ADungeonPusChannel>(ADungeonPusChannel::StaticClass(),T,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                if(!H){State->Error=TEXT("积液区域创建失败");return;}
                const auto& Half=Part->GetArrayField(TEXT("half_size"));H->HalfSize=FVector2D(Half[0]->AsNumber(),Half[1]->AsNumber());
                if(Part->GetBoolField(TEXT("radial")))H->Tags.Add(TEXT("PusRadialFootprint"));H->FinishSpawning(T);A=H;C=H->Surface;
                ++State->Hazards;
            }
            else if(bInstance)
            {
                A=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),FTransform::Identity,Params);
                if(!A){State->Error=TEXT("实例网格组创建失败");return;}
                C=NewObject<UInstancedStaticMeshComponent>(A,TEXT("DungeonInstances"));
                A->AddInstanceComponent(C);A->SetRootComponent(C);
            }
            else
            {
                auto* S=GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),T,Params);
                if(!S){State->Error=TEXT("地牢网格组件创建失败");return;}
                A=S;C=S->GetStaticMeshComponent();if(!Fluid)++State->StaticFallbacks;
            }
            OwnGenerated(A,Index);C->SetCanEverAffectNavigation(PartAffectsNavigation(Part));C->SetStaticMesh(Mesh);
            if(Dressing){A->Tags.Add(TEXT("DungeonDressing"));++State->DressingProps;}
            const auto& Materials=Part->GetArrayField(TEXT("materials"));for(int32 I=0;I<Materials.Num();++I)if(!Materials[I]->AsString().IsEmpty())C->SetMaterial(I,Cast<UMaterialInterface>(ResolveGenerationAsset(Materials[I]->AsString())));
            C->SetMobility(Fluid?EComponentMobility::Movable:EComponentMobility::Static);
            const FString MeshPath=Part->GetStringField(TEXT("mesh"));
            bool CastShadow=!Fluid;
            if(bOptimizeLights)
            {
                CastShadow=!Fluid&&!MeshPath.EndsWith(TEXT("_Fixtures"))&&!MeshPath.EndsWith(TEXT("_Debris"));
                Part->TryGetBoolField(TEXT("cast_shadow"),CastShadow);
                CastShadow=CastShadow&&!Fluid;
            }
            if(Dressing) Part->TryGetBoolField(TEXT("cast_shadow"),CastShadow);
            C->SetCollisionProfileName(Part->GetBoolField(TEXT("collision"))?TEXT("BlockAll"):TEXT("NoCollision"));C->SetCastShadow(CastShadow);
            if(Fluid){C->SetEvaluateWorldPositionOffset(true);C->SetVisibleInRayTracing(false);C->SetAffectDistanceFieldLighting(false);}
            if(bInstance)
            {
                auto* Instances=CastChecked<UInstancedStaticMeshComponent>(C);
                Instances->AddInstance(T,true);Instances->RegisterComponent();
                Instances->ComponentTags.Add(FName(*FString::Printf(TEXT("DungeonModule.%d.%s"),Index,*State->Plan.Modules[Piece.Module].Id)));
                State->InstanceGroups.Add(Key,Instances);++State->Instances;++State->InstanceComponents;
            }
            ++State->Parts;
            }});
        }
        const TArray<TSharedPtr<FJsonValue>>* Props=nullptr;
        if(D->TryGetArrayField(TEXT("props"),Props))for(const auto& V:*Props)
        {
            const JObject Prop=V->AsObject();QueueAsset(Prop->GetStringField(TEXT("skeletal_mesh")));QueueAsset(Prop->GetStringField(TEXT("closed_animation")));
            FString OpeningPath;if(Prop->TryGetStringField(TEXT("opening_animation"),OpeningPath))QueueAsset(OpeningPath);
            for(const auto& M:Prop->GetObjectField(TEXT("material_overrides"))->Values)QueueAsset(M.Value->AsString());
            State->Jobs.Add({TEXT("Dungeon.Props"),[this,State,Prop,Piece,Index,Params]()
            {
            auto* Mesh=Cast<USkeletalMesh>(ResolveGenerationAsset(Prop->GetStringField(TEXT("skeletal_mesh"))));
            if(!Mesh){State->Error=TEXT("宝箱骨骼网格无法载入");return;}
            auto* A=GetWorld()->SpawnActor<ASkeletalMeshActor>(ASkeletalMeshActor::StaticClass(),Local(Prop)*Piece.Transform,Params);
            if(!A){State->Error=TEXT("宝箱创建失败");return;}OwnGenerated(A,Index);
            A->Tags.Add(TEXT("DungeonTreasureChest"));A->Tags.Add(TEXT("FutureTreasureLoot"));
            auto* C=A->GetSkeletalMeshComponent();C->SetSkeletalMeshAsset(Mesh);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            const auto& Surfaces=Prop->GetObjectField(TEXT("material_overrides"));
            for(int32 I=0;I<C->GetNumMaterials();++I){FString Path;if(C->GetMaterial(I)&&Surfaces->TryGetStringField(C->GetMaterial(I)->GetName(),Path))C->SetMaterial(I,Cast<UMaterialInterface>(ResolveGenerationAsset(Path)));}
            if(auto* Closed=Cast<UAnimSequence>(ResolveGenerationAsset(Prop->GetStringField(TEXT("closed_animation")))))
            {
                C->PlayAnimation(Closed,false);C->SetPosition(Closed->GetPlayLength(),false);C->SetPlayRate(0);
                // Evaluate the authored closed pose once before stopping animation ticks.
                C->TickAnimation(0.f,false);C->RefreshBoneTransforms();C->SetComponentTickEnabled(false);
                C->ComponentTags.Add(TEXT("DungeonClosedPoseFrozen"));
            }
            const FVector ChestExtent=Prop->HasTypedField<EJson::Array>(TEXT("collision_extent"))?Vec(Prop,TEXT("collision_extent")):FVector(55,73,37);
            const FVector ChestCenter=Prop->HasTypedField<EJson::Array>(TEXT("collision_center"))?Vec(Prop,TEXT("collision_center")):FVector(0,0,37);
            auto* Box=NewObject<UBoxComponent>(A);A->AddInstanceComponent(Box);Box->SetupAttachment(C);Box->SetBoxExtent(ChestExtent);Box->SetRelativeLocation(ChestCenter);Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();
            FBox ChestBounds=FBox(ChestCenter-ChestExtent,ChestCenter+ChestExtent).TransformBy(Local(Prop)*Piece.Transform);
            ChestBounds+=C->CalcBounds(C->GetComponentTransform()).GetBox();
            State->DressingScene.FixedBoxes.Add(ChestBounds.ExpandBy(5));
            ++State->Props;
            }});
        }
        if(D->HasTypedField<EJson::Object>(TEXT("boss_encounter")))
        {
            const JObject Encounter=D->GetObjectField(TEXT("boss_encounter"));
            QueueAsset(Encounter->GetStringField(TEXT("class")));QueueAsset(Encounter->GetStringField(TEXT("gate_material")));
            State->Jobs.Add({TEXT("Dungeon.BossEncounter"),[this,State,Encounter,Piece,Index]()
            {
                auto* Class=Cast<UClass>(ResolveGenerationAsset(Encounter->GetStringField(TEXT("class"))));
                if(!Class||!Class->IsChildOf(AHandBrainMonster::StaticClass())){State->Error=TEXT("地牢首领类无法载入");return;}
                auto* E=GetWorld()->SpawnActorDeferred<ADungeonBossEncounter>(ADungeonBossEncounter::StaticClass(),Piece.Transform,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                if(!E){State->Error=TEXT("首领入场控制器创建失败");return;}
                E->BossClass=Class;E->SpawnPoint=Vec(Encounter,TEXT("spawn"));
                E->ArenaMin=Vec(Encounter,TEXT("arena_min"));E->ArenaMax=Vec(Encounter,TEXT("arena_max"));
                E->DoorPoint=Vec(Encounter,TEXT("door"));
                const auto& Size=Encounter->GetArrayField(TEXT("door_size"));E->DoorSize=FVector2D(Size[0]->AsNumber(),Size[1]->AsNumber());
                E->GateMaterial=Cast<UMaterialInterface>(ResolveGenerationAsset(Encounter->GetStringField(TEXT("gate_material"))));
                E->FinishSpawning(Piece.Transform);OwnGenerated(E,Index);
            }});
        }
        const auto& Lights=D->GetArrayField(TEXT("lights"));
        TArray<int32> Brightest;
        for(int32 I=0;I<Lights.Num();++I)Brightest.Add(I);
        Brightest.StableSort([&](int32 A,int32 B){return Lights[A]->AsObject()->GetNumberField(TEXT("intensity"))>Lights[B]->AsObject()->GetNumberField(TEXT("intensity"));});
        for(int32 LightIndex=0;LightIndex<Lights.Num();++LightIndex)
        {
            const JObject L=Lights[LightIndex]->AsObject();
            const bool Corridor=Plan.Modules[Piece.Module].Id==TEXT("Transit");
            FString LightRole=Corridor?TEXT("corridor"):Brightest.Find(LightIndex)<2?TEXT("key"):TEXT("fill");
            L->TryGetStringField(TEXT("role"),LightRole);
            State->Jobs.Add({TEXT("Dungeon.Lights"),[this,State,L,Piece,Index,Params,bOptimizeLights,Corridor,LightRole]()
            {
            const bool Fill=LightRole==TEXT("fill");
            FString Type=(Fill||Corridor)?TEXT("spot"):TEXT("point");L->TryGetStringField(TEXT("type"),Type);
            const bool Spot=bOptimizeLights&&Type==TEXT("spot");
            double Outer=Corridor?80.0:65.0;L->TryGetNumberField(TEXT("outer_cone_degrees"),Outer);Outer=FMath::Clamp(Outer,10.0,85.0);
            const FVector Position=Piece.Transform.TransformPosition(Vec(L,TEXT("position")));
            ALight* A=nullptr;
            if(Spot)A=GetWorld()->SpawnActor<ASpotLight>(Position,FRotator(-90,0,0),Params);
            else A=GetWorld()->SpawnActor<APointLight>(Position,FRotator::ZeroRotator,Params);
            if(!A){State->Error=TEXT("地牢灯光创建失败");return;}
            OwnGenerated(A,Index);A->Tags.Add(FName(*(TEXT("DungeonLight.")+(bOptimizeLights?LightRole:TEXT("legacy")))));
            auto* C=Cast<UPointLightComponent>(A->GetLightComponent());C->SetMobility(EComponentMobility::Movable);C->SetIntensityUnits(ELightUnits::Lumens);
            float Intensity=L->GetNumberField(TEXT("intensity"));
            if(Spot)
            {
                auto* S=CastChecked<USpotLightComponent>(C);S->SetOuterConeAngle(Outer);S->SetInnerConeAngle(FMath::Max(0.0,Outer-15.0));
                // UE remaps spot lumens over its cone; preserve the original point's central brightness.
                Intensity*=.5f*(1.f-FMath::Cos(FMath::DegreesToRadians(float(Outer))));
            }
            double Radius=L->GetNumberField(TEXT("radius"));
            double DrawDistance=2400,FadeRange=500;bool Shadows=true;
            if(bOptimizeLights)
            {
                Radius=Fill?FMath::Min(Radius*.8,300.0):Radius;
                DrawDistance=Fill?1400:Corridor?1800:2400;FadeRange=Fill?400:500;Shadows=!Fill;
                L->TryGetNumberField(TEXT("optimized_radius_cm"),Radius);
                L->TryGetNumberField(TEXT("max_draw_distance_cm"),DrawDistance);
                L->TryGetNumberField(TEXT("fade_range_cm"),FadeRange);
                if(Fill)
                {
                    // An unshadowed fill must fit inside an occupied floor cell. Lamps near walls
                    // retain shadows instead of illuminating the neighboring room through solid walls.
                    const FVector LocalPosition=Vec(L,TEXT("position"));
                    double Clearance=0;
                    for(const FBox& Cell:State->Plan.Modules[Piece.Module].Cells)
                    {
                        const double Margin=FMath::Min(FMath::Min(LocalPosition.X-Cell.Min.X,Cell.Max.X-LocalPosition.X),
                            FMath::Min(LocalPosition.Y-Cell.Min.Y,Cell.Max.Y-LocalPosition.Y))-35.0;
                        Clearance=FMath::Max(Clearance,Margin);
                    }
                    const double HorizontalReach=Spot?Radius*FMath::Sin(FMath::DegreesToRadians(Outer)):Radius;
                    Shadows=HorizontalReach>Clearance;
                }
                L->TryGetBoolField(TEXT("cast_shadows"),Shadows);
            }
            C->SetIntensity(Intensity);C->SetAttenuationRadius(FMath::Max(1.0,Radius));
            const FVector Color=Vec(L,TEXT("color"));C->SetLightColor(FLinearColor(Color.X,Color.Y,Color.Z));C->SetSourceRadius(5);C->SetSourceLength(Spot?0:60);C->SetCastShadows(Shadows);
            C->SetMaxDrawDistance(FMath::Max(0.0,DrawDistance));C->SetMaxDistanceFadeRange(FMath::Clamp(FadeRange,0.0,FMath::Max(0.0,DrawDistance)));
            State->NextLights[Index].Lights.Add({C,Intensity,1.f});
            ++State->Lights;
            }});
        }
        for(const auto& V:D->GetArrayField(TEXT("anchors")))
        {
            const JObject P=V->AsObject();State->Jobs.Add({TEXT("Dungeon.Anchors"),[this,State,P,Piece,Index,Params]()
            {
                auto* A=GetWorld()->SpawnActor<ATargetPoint>(Piece.Transform.TransformPosition(Vec(P,TEXT("position"))),Piece.Transform.Rotator(),Params);
                if(!A){State->Error=TEXT("地牢定位点创建失败");return;}
                OwnGenerated(A,Index);A->Tags.Add(FName(*P->GetStringField(TEXT("role"))));A->SetActorHiddenInGame(true);
            }});
        }
    }
    State->PendingDescription=FString::Printf(TEXT("Seed %d | approach %d rooms | branches %d / %d / %d rooms | %d modules | treasure %d"),Seed,Plan.Counts[0],Plan.Counts[1],Plan.Counts[2],Plan.Counts[3],Plan.Pieces.Num(),Plan.TreasureCount);
    if(bDressRooms) State->Jobs.Add({TEXT("Dungeon.DressingScene"),[this,State]()
    {
        FBox Bounds(ForceInit);for(const auto& Piece:State->Plan.Pieces) Bounds+=Piece.Bounds;
        State->DressingScene.AddPlacedActors(GetWorld(),this,Bounds);
    }});
    // All structural geometry and fixed props must exist before dressing, including
    // later modules and side-door variants. Teardown remains last for rollback.
    State->Jobs.StableSort([](const auto& A,const auto& B)
    {
        auto Rank=[](FName Stage)
        {return Stage==TEXT("Dungeon.Resources")?0:Stage==TEXT("Dungeon.DressingScene")?2:Stage==TEXT("Dungeon.Dressing")?3:Stage==TEXT("Dungeon.Teardown")?4:1;};
        return Rank(A.Stage)<Rank(B.Stage);
    });
    State->PhaseMs.Add(TEXT("Dungeon.PrepareJobs"),(FPlatformTime::Seconds()-PrepareStarted)*1000.);
}

void AAuthoredDungeonGenerator::OwnGenerated(AActor* Actor,int32 ModuleIndex)
{
    const auto& Piece=BuildState->Plan.Pieces[ModuleIndex];
    Actor->SetActorHiddenInGame(true);Actor->SetActorEnableCollision(false);
    GeneratedActors.Add(Actor);Actor->Tags.Add(TEXT("DungeonRouteGenerated"));Actor->Tags.Add(FName(*Piece.Route));
    Actor->Tags.Add(FName(*FString::Printf(TEXT("DungeonModule.%d.%s"),ModuleIndex,*BuildState->Plan.Modules[Piece.Module].Id)));
#if WITH_EDITOR
    Actor->SetActorLabel(FString::Printf(TEXT("DGN_G_%03d_%s_%s"),ModuleIndex,*Piece.Route,*Actor->GetClass()->GetName()));
    Actor->SetFolderPath(FName(*(TEXT("DungeonRoutes/")+Piece.Route)));
#endif
}

UObject* AAuthoredDungeonGenerator::ResolveGenerationAsset(const FString& Path)
{
    if(Path.IsEmpty())return nullptr;
    if(UObject** Cached=BuildState->Assets.Find(Path))return *Cached;
    UObject* Asset=LoadObject<UObject>(nullptr,*Path);
    BuildState->Assets.Add(Path,Asset);++BuildState->AssetResolutions;
    if(Asset)GenerationResources.Add(Asset);
    else BuildState->Error=TEXT("地牢资源无法载入：")+Path;
    return Asset;
}

void AAuthoredDungeonGenerator::HoldPlayers()
{
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();auto* Character=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
        auto* Movement=Character?Character->GetCharacterMovement():nullptr;
        if(Movement&&Movement->IsComponentTickEnabled())
        {
            // Preserve movement mode and location; only stop movement simulation until collision exists.
            HeldMovement.AddUnique(Movement);Movement->SetComponentTickEnabled(false);
        }
    }
}

void AAuthoredDungeonGenerator::ReleasePlayers()
{
    for(auto& Weak:HeldMovement)if(auto* Movement=Weak.Get())Movement->SetComponentTickEnabled(true);
    HeldMovement.Reset();
}

void AAuthoredDungeonGenerator::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!BuildState)return;
    HoldPlayers();
    if(!BuildState->bPlanning)PumpAssembly(false);
}

void AAuthoredDungeonGenerator::PumpAssembly(bool bSynchronous)
{
    if(!BuildState||BuildState->bPlanning)return;
    auto* State=BuildState.Get();
    if(State->Error.IsEmpty())
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Dungeon_AssemblySlice);
        DungeonPerformance::FScope SliceScope(this,TEXT("Dungeon.AssemblySlice"));
        const double Start=FPlatformTime::Seconds();
        const double Budget=FMath::Clamp(double(DungeonBuildBudget.GetValueOnGameThread()),.25,16.)/1000.;
        do
        {
            if(!State->Jobs.IsValidIndex(State->Cursor))break;
            auto& Job=State->Jobs[State->Cursor];
            if(!State->bStaging&&Job.Stage!=TEXT("Dungeon.Resources"))
            {State->PreviousActors=MoveTemp(GeneratedActors);GeneratedActors.Reset();State->bStaging=true;}
            const double JobStart=FPlatformTime::Seconds();
            {
                DungeonPerformance::FScope JobScope(this,Job.Stage);
                Job.Run();
            }
            State->PhaseMs.FindOrAdd(Job.Stage)+=(FPlatformTime::Seconds()-JobStart)*1000.;
            Job.Run=nullptr;++State->Cursor;
        }while(State->Error.IsEmpty()&&(bSynchronous||FPlatformTime::Seconds()-Start<Budget));
        ++State->Slices;State->PeakSliceMs=FMath::Max(State->PeakSliceMs,(FPlatformTime::Seconds()-Start)*1000.);
    }
    if(!State->Error.IsEmpty())
    {
        RollbackAssembly();Tags.AddUnique(TEXT("DungeonAssembly.Failed"));
        State->FinishedAt=FPlatformTime::Seconds();SetActorTickEnabled(false);
        UE_LOG(LogTemp,Error,TEXT("AuthoredDungeon: %s"),*State->Error);
        if(auto* Loading=DungeonLoading(this))Loading->FailPreparation(FText::FromString(State->Error+TEXT("；可取消并返回主场景。")));
        return;
    }
    if(State->Cursor>=State->Jobs.Num()){FinishAssembly();return;}
    if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(FText::FromString(TEXT("正在构建房间、灯光与碰撞…")),
        .1f+.85f*float(State->Cursor)/FMath::Max(1,State->Jobs.Num()));
}

void AAuthoredDungeonGenerator::FinishAssembly()
{
    DungeonPerformance::FScope FinalizeScope(this,TEXT("Dungeon.Finalize"));
    const double FinalizeStarted=FPlatformTime::Seconds();
    auto* State=BuildState.Get();
    auto RecordFinalize=[State,FinalizeStarted]()
    {State->PhaseMs.FindOrAdd(TEXT("Dungeon.Finalize"))+=(FPlatformTime::Seconds()-FinalizeStarted)*1000.;};
    if(!State->bCommitted)
    {
        GetWorldTimerManager().ClearTimer(RoomLightingTimer);
        for(AActor* Actor:State->PreviousActors)if(IsValid(Actor))Actor->Destroy();
        State->PreviousActors.Reset();State->bCommitted=true;
        for(AActor* Actor:GeneratedActors)if(IsValid(Actor)){Actor->SetActorHiddenInGame(false);Actor->SetActorEnableCollision(true);}
        LightModules=MoveTemp(State->NextLights);
    }
    bool RequireNavigation=false;State->Catalog->TryGetBoolField(TEXT("navigation_required"),RequireNavigation);
    if(RequireNavigation&&!State->bNavigationRequested)
    {
        ANavMeshBoundsVolume* Volume=nullptr;
        for(TActorIterator<ANavMeshBoundsVolume> It(GetWorld());It;++It)if(It->ActorHasTag(TEXT("DungeonRouteNavigation"))){Volume=*It;break;}
        auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
        if(!Volume||!Nav){State->Error=TEXT("地牢导航模板缺失，不能启用战斗场景");RecordFinalize();PumpAssembly(false);return;}
        FBox Bounds=State->Plan.Reserved;for(const auto& Piece:State->Plan.Pieces)Bounds+=Piece.Bounds;
        Bounds=Bounds.ExpandBy(FVector(250,250,350));
        // Saved template brush has a 100 cm cube; transform updates work in cooked games too.
        Volume->GetBrushComponent()->SetMobility(EComponentMobility::Movable);
        Volume->SetActorLocation(Bounds.GetCenter());Volume->SetActorScale3D(Bounds.GetSize()/100.);
        Volume->UpdateComponentTransforms();Nav->OnNavigationBoundsUpdated(Volume);
        State->bNavigationRequested=true;State->NavigationRequestedAt=FPlatformTime::Seconds();
        if(State->bRuntime){RecordFinalize();return;}
    }
    if(RequireNavigation&&State->bRuntime)
    {
        if(FPlatformTime::Seconds()-State->NavigationRequestedAt<.25||UNavigationSystemV1::IsNavigationBeingBuiltOrLocked(this))
        {
            if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(FText::FromString(TEXT("正在准备战斗导航…")),.97f);
            RecordFinalize();
            return;
        }
    }
    GeneratedSeed=State->Seed;LayoutDescription=State->PendingDescription;LayoutManifestJson=State->PendingManifest;
    Tags.AddUnique(TEXT("DungeonAssembly.Ready"));Tags.Remove(TEXT("DungeonAssembly.Failed"));
    BuildState->bCompleted=true;BuildState->FinishedAt=FPlatformTime::Seconds();
    RecordFinalize();
    LastGenerationMetricsJson=GetGenerationMetricsJson();
    DungeonPerformance::FMarker::Record(this,TEXT("Dungeon.Ready"),LayoutDescription);
    UE_LOG(LogTemp,Display,TEXT("AuthoredDungeon: %s; %d instances in %d groups; CPU preparation %s"),
        *LayoutDescription,BuildState->Instances,BuildState->InstanceComponents,*LastGenerationMetricsJson);
    BuildState.Reset();GenerationResources.Reset();SetActorTickEnabled(false);
    GeneratedActors.RemoveAll([](const TObjectPtr<AActor>& Actor){return !IsValid(Actor);});
    for(AActor* Actor:GeneratedActors)if(auto* Hazard=Cast<ADungeonPusChannel>(Actor))Hazard->ActivateDamage();
    for(AActor* Actor:GeneratedActors)if(auto* Encounter=Cast<ADungeonBossEncounter>(Actor))Encounter->ActivateEncounter();
    StartRoomLighting();ReleasePlayers();
    if(auto* Loading=DungeonLoading(this))Loading->CompletePreparation();
}

void AAuthoredDungeonGenerator::RollbackAssembly()
{
    if(!BuildState||!BuildState->bStaging||BuildState->bCommitted)return;
    for(AActor* Actor:GeneratedActors)if(IsValid(Actor))Actor->Destroy();
    GeneratedActors=MoveTemp(BuildState->PreviousActors);BuildState->bStaging=false;
    StartRoomLighting();
}

void AAuthoredDungeonGenerator::CancelAssembly()
{
    ++GenerationSerial;RollbackAssembly();BuildState.Reset();GenerationResources.Reset();SetActorTickEnabled(false);ReleasePlayers();
}

FString AAuthoredDungeonGenerator::GetGenerationMetricsJson() const
{
    if(!BuildState)return LastGenerationMetricsJson;
    const auto& S=*BuildState;auto Report=MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("generator"),GetPathName());Report->SetNumberField(TEXT("seed"),S.Seed);
    Report->SetStringField(TEXT("status"),S.bPlanning?TEXT("planning"):!S.Error.IsEmpty()?TEXT("failed"):S.bCompleted?TEXT("ready"):TEXT("assembling"));
    Report->SetStringField(TEXT("error"),S.Error);
    Report->SetStringField(TEXT("contract"),TEXT("CPU preparation for this generation. Layout search runs on a worker in game worlds. Stage values are inclusive synchronous game-thread wall times, not additive with AssemblySlice, GPU timings or measured FPS improvements. MeshCollision includes mesh assignment, component/physics registration; collision cooking is not separately measured. A single indivisible job can exceed BudgetMs. Planning data is not read until worker completion."));
    Report->SetNumberField(TEXT("elapsed_ms"),((S.FinishedAt>0?S.FinishedAt:FPlatformTime::Seconds())-S.StartedAt)*1000.);
    // The worker mutates only Plan, PlanMs and bPlanSucceeded. Do not inspect those while it runs.
    if(S.bPlanning){Report->SetField(TEXT("layout_worker_ms"),MakeShared<FJsonValueNull>());Report->SetField(TEXT("modules"),MakeShared<FJsonValueNull>());}
    else {Report->SetNumberField(TEXT("layout_worker_ms"),S.PlanMs);Report->SetNumberField(TEXT("modules"),S.Plan.Pieces.Num());Report->SetNumberField(TEXT("treasure_rooms"),S.Plan.TreasureCount);}
    Report->SetBoolField(TEXT("time_sliced"),S.bRuntime);Report->SetNumberField(TEXT("budget_ms"),DungeonBuildBudget.GetValueOnGameThread());
    Report->SetNumberField(TEXT("jobs_completed"),S.Cursor);Report->SetNumberField(TEXT("jobs_total"),S.Jobs.Num());
    Report->SetNumberField(TEXT("assembly_slices"),S.Slices);Report->SetNumberField(TEXT("peak_slice_ms"),S.PeakSliceMs);
    Report->SetNumberField(TEXT("unique_assets_resolved"),S.AssetResolutions);Report->SetNumberField(TEXT("parts"),S.Parts);
    Report->SetNumberField(TEXT("instanced_parts"),S.Instances);Report->SetNumberField(TEXT("instance_components"),S.InstanceComponents);
    Report->SetNumberField(TEXT("individual_rigid_parts"),S.StaticFallbacks);Report->SetNumberField(TEXT("hazards"),S.Hazards);
    Report->SetNumberField(TEXT("skeletal_props"),S.Props);Report->SetNumberField(TEXT("lights"),S.Lights);
    Report->SetNumberField(TEXT("dressing_props"),S.DressingProps);
    Report->SetNumberField(TEXT("dressing_candidates"),S.DressingCandidates);Report->SetNumberField(TEXT("dressing_skipped"),S.DressingSkipped);
    auto DressingReasons=MakeShared<FJsonObject>();for(const auto& P:S.DressingRejections) DressingReasons->SetNumberField(P.Key,P.Value);
    Report->SetObjectField(TEXT("dressing_rejections"),DressingReasons);
    auto Phases=MakeShared<FJsonObject>();for(const auto& P:S.PhaseMs)Phases->SetNumberField(P.Key.ToString(),P.Value);
    Report->SetObjectField(TEXT("game_thread_phases_ms"),Phases);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;
}
