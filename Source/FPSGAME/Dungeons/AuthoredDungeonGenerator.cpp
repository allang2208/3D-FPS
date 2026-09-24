#include "AuthoredDungeonGenerator.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
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
#include "Components/PrimitiveComponent.h"
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
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/DecalComponent.h"
#include "Engine/DecalActor.h"
#include "Misc/DateTime.h"
#include "TimerManager.h"
#include "DungeonBossEncounter.h"
#include "../Monsters/HandBrainMonster.h"
#include "../SceneTestPortal.h"
#include "NavigationSystem.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "Components/BrushComponent.h"
#include "EngineUtils.h"
#include "AuthoredDungeonWallStains.inl"
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
struct FModule { FString Id,Family; FBox Bounds; TArray<FPort> Ports; JObject Data; TArray<FBox> Cells; TArray<FSideSocket> SideSockets; };
struct FPlaced { int32 Module; FTransform Transform; FBox Bounds; FString Route; TArray<FBox> Cells; int32 Side=-1; };
struct FSocket { FVector P,N; int32 Owner=-1; double Width=300,Height=280; double ReservedLead=0; };
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
        if(Port.P.ContainsNaN()||Port.N.ContainsNaN()||Socket.P.ContainsNaN()||Socket.N.ContainsNaN()||
           FMath::Abs(Port.N.Z)>.001||FMath::Abs(Socket.N.Z)>.001||
           !FMath::IsNearlyEqual(Port.N.SizeSquared(),1.,.001)||!FMath::IsNearlyEqual(Socket.N.SizeSquared(),1.,.001))return false;
        return !bStrictPorts||(Port.Width>=300&&Port.Height>=280&&FMath::Abs(Port.Width-Socket.Width)<1&&FMath::Abs(Port.Height-Socket.Height)<1);
    }
    TArray<int32> Counts;
    int32 Find(const FString& Id)const{return Modules.IndexOfByPredicate([&](const FModule& M){return M.Id==Id;});}
    bool Overlap(const FBox& A,const FBox& B)const
    {
        return FMath::Min(A.Max.X,B.Max.X)-FMath::Max(A.Min.X,B.Min.X)>8 &&
               FMath::Min(A.Max.Y,B.Max.Y)-FMath::Max(A.Min.Y,B.Min.Y)>8 &&
               FMath::Min(A.Max.Z,B.Max.Z)-FMath::Max(A.Min.Z,B.Min.Z)>8;
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
    #include "AuthoredDungeonRoomChoices.inl"
    bool Place(int32 Module,const FTransform& T,const FString& Route,int32 IgnoreFrom=-2,int32 IgnoreOwner=-2,
               FVector SectorOrigin=FVector::ZeroVector,FVector SectorDir=FVector::ZeroVector,int32 SecondOwner=-2)
    {
        // Room shells stay rigid. Only straight connector length may change.
        const FVector Scale=T.GetScale3D();
        if(T.ContainsNaN()||Scale.GetMin()<=0||!FMath::IsNearlyEqual(Scale.X,1.,.0001)||
           !FMath::IsNearlyEqual(Scale.Z,1.,.0001)||(Module!=Transit&&!FMath::IsNearlyEqual(Scale.Y,1.,.0001)))return false;
        const FBox B=Modules[Module].Bounds.TransformBy(T);
        TArray<FBox> Cells;for(const FBox& Local:Modules[Module].Cells)Cells.Add(Local.TransformBy(T));
        if(bCompactBoss&&!InCompactLane(Cells,Route))return false;
        if(IgnoreOwner!=-1)for(const FBox& Cell:Cells)if(Overlap(Cell,Reserved))return false;
        for(int32 I=0;I<Pieces.Num();++I)
            if(Overlap(B,Pieces[I].Bounds))
                for(const FBox& Cell:Cells)for(const FBox& Other:Pieces[I].Cells)if(Overlap(Cell,Other))
                {
                    if(!JoinedWallSeam(Module,T,I,Cell.Overlap(Other)))return false;
                }
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
    #include "AuthoredDungeonShortLinks.inl"
    bool Chain(int32 Remaining,FSocket& S,const FString& Route,FVector SectorOrigin={},FVector SectorDir={})
    {
        if(Remaining==0)return true;
        if(SearchBudget<=0)return false;
        const auto Choices=RoomChoices(Route);
        const int32 Before=Pieces.Num();const FSocket Initial=S;
        const auto Links=RoomLinks(Initial);
        for(const auto& Choice:Choices)for(const auto& Link:Links)
        {
            Pieces.SetNum(Before);S=Initial;
            if(--SearchBudget<0)return false;
            if(!AttachRoom(Choice.Key,Choice.Value,Initial,Link,Route,S,SectorOrigin,SectorDir))continue;
            if(Chain(Remaining-1,S,Route,SectorOrigin,SectorDir))return true;
        }
        Pieces.SetNum(Before);S=Initial;return false;
    }
    #include "AuthoredDungeonRouting.inl"
    #include "AuthoredDungeonCompactRouting.inl"
    bool Build(int32 Seed,const FSocket& Start)
    {
        if(bBossTerminal&&bCompactBoss)return BuildCompact(Seed,Start);
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
            if(Good&&CompleteSocketGraph(Start))return true;
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
                Pieces[Owner].Side=Side; // Expose the proposed socket to the exact seam rule.
                if(!Place(TreasureLink,Fit(TreasureLink,0,S),Route,-2,Owner)){Pieces[Owner].Side=-1;continue;}
                S=Socket(Pieces.Num()-1,1);
                if(!Place(Treasure,Fit(Treasure,0,S),Route,-2,S.Owner)){Pieces[Owner].Side=-1;continue;}
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
    TMap<int32,TWeakObjectPtr<AActor>> FinalRewardChests;
    TMap<FName,double> PhaseMs;
    DungeonDressing::FPlacementScene DressingScene;
    TMap<FString,int32> DressingRejections;
    int32 DressingCandidates=0,DressingSkipped=0;
    int32 Seed=0,Cursor=0,Parts=0,Instances=0,InstanceComponents=0,StaticFallbacks=0,Hazards=0,Props=0,DressingProps=0,Lights=0,AssetResolutions=0,Slices=0;
    int32 PhysicsActorCursor=0,PhysicsStatesCreated=0,RetireCursor=0,RevealCursor=0;
    FText LoadingStatus;
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

FText AssemblyStatus(FName Stage)
{
    if(Stage==TEXT("Dungeon.Resources"))return FText::FromString(TEXT("正在载入地牢资源…"));
    if(Stage==TEXT("Dungeon.MeshCollision"))return FText::FromString(TEXT("正在铺设地面、连接段与楼梯…"));
    if(Stage==TEXT("Dungeon.MeshVisuals"))return FText::FromString(TEXT("正在布置房间外观…"));
    if(Stage==TEXT("Dungeon.Lights"))return FText::FromString(TEXT("正在准备房间灯光…"));
    if(Stage==TEXT("Dungeon.DressingScene")||Stage==TEXT("Dungeon.Dressing"))return FText::FromString(TEXT("正在布置环境摆件…"));
    return FText::FromString(TEXT("正在准备场景物件…"));
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
    ResetRoomLighting();LightModules.Reset();
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
        JObject D=Value->AsObject();FModule M;M.Data=D;M.Id=D->GetStringField(TEXT("id"));M.Family=M.Id;
        D->TryGetStringField(TEXT("family_id"),M.Family);M.Bounds=FBox(Vec(D,TEXT("min")),Vec(D,TEXT("max")));
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
    Catalog->TryGetBoolField(TEXT("compact_underground_boss"),Plan.bCompactBoss);
    Plan.StairDrop=Plan.Find(TEXT("StairDrop1080"));
    if(Plan.bCompactBoss)
    {
        if(!Plan.bBossTerminal||Plan.StairDrop<0||Plan.Modules[Plan.StairDrop].Ports.Num()!=2||Plan.AuthoredWalk(Plan.StairDrop)<=0)
        {State->Error=TEXT("地下终点缺少完整下行楼梯和路程数据");State->bPlanning=false;PumpAssembly(true);return;}
    }
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
        if(!State->bPlanSucceeded)
        {
            const auto Pool=State->Plan.Combat;
            State->Plan.Combat.RemoveAll([&](int32 M){return State->Plan.Modules[M].Id!=State->Plan.Modules[M].Family;});
            if(!State->Plan.Combat.IsEmpty()&&State->Plan.Combat.Num()<Pool.Num())
                State->bPlanSucceeded=State->Plan.Build(State->Seed,Start);
            State->Plan.Combat=Pool;
        }
        if(State->bPlanSucceeded)
        {
            State->Plan.AddTreasureRooms(State->Seed);
            State->bPlanSucceeded=State->Plan.CompleteSocketGraph(Start);
        }
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
    {State->Error=FString::Printf(TEXT("种子 %d 未找到完整布局，保留原场景。%s"),Seed,*Plan.CompactFailure);return;}
    DungeonPerformance::FScope Scope(this,TEXT("Dungeon.PrepareJobs"));
    const double PrepareStarted=FPlatformTime::Seconds();
    // A complete plan is obtained before replacing the current preview or runtime assembly.
    // FinishAssembly retires the previous actors only after new collision exists.
    // Deleting them as assembly jobs would make collision failures impossible to roll back.
    // Editor preview also retains the previous geometry until staging succeeds.
    const bool bOptimizeLights=AuthoredDungeonLighting::IsOptimizationEnabled();
    bLightingOptimizationApplied=bOptimizeLights;
    auto& StagedLightModules=State->NextLights;
    StagedLightModules.SetNum(Plan.Pieces.Num()+1);
    StagedLightModules.Last().Cells.Add(Plan.Reserved); // Include existing start lights in the room scheduler at runtime.
    for(int32 I=0;I<Plan.Pieces.Num();++I)
    {
        StagedLightModules[I].Cells=Plan.Pieces[I].Cells;
        const FString& Id=Plan.Modules[Plan.Pieces[I].Module].Id;
        StagedLightModules[I].bConnector=Id==TEXT("Transit")||Id==TEXT("Threshold")||Id==TEXT("TreasureLink")||Id==TEXT("RouteElbow")||Id==TEXT("BossApproach")||Id==TEXT("StairDrop1080");
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
    Graph->SetNumberField(TEXT("generator_version"),Plan.bCompactBoss?2:1);
    Graph->SetNumberField(TEXT("room_connection_version"),3);
    if(Plan.bCompactBoss)Graph->SetStringField(TEXT("compact_terminal_placement"),TEXT("completed_middle_branch"));
    Graph->SetNumberField(TEXT("room_connection_max_cm"),FPlan::ShortLinkLimit);
    Graph->SetNumberField(TEXT("room_connection_max_turns"),2);
    Graph->SetNumberField(TEXT("boss_depth_cm"),Plan.bCompactBoss?Plan.BossDepth:0);
    TArray<TSharedPtr<FJsonValue>> WalkLengths;for(double Length:Plan.TerminalWalkLengths)WalkLengths.Add(MakeShared<FJsonValueNumber>(Length));
    Graph->SetArrayField(TEXT("terminal_walk_cm"),WalkLengths);
    TArray<TSharedPtr<FJsonValue>> Nodes,Edges;
    auto JsonVector=[](FVector V){return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};};
    for(int32 I=0;I<Plan.Pieces.Num();++I)
    {
        const auto& P=Plan.Pieces[I];JObject N=MakeShared<FJsonObject>();N->SetNumberField(TEXT("id"),I);N->SetStringField(TEXT("module"),Plan.Modules[P.Module].Id);N->SetStringField(TEXT("route"),P.Route);N->SetArrayField(TEXT("origin"),JsonVector(P.Transform.GetLocation()));N->SetNumberField(TEXT("yaw"),P.Transform.Rotator().Yaw);
        Nodes.Add(MakeShared<FJsonValueObject>(N));
        N->SetNumberField(TEXT("floor"),FMath::RoundToInt((P.Transform.GetLocation().Z-Vec(Catalog,TEXT("start_position")).Z)/540.));
        N->SetArrayField(TEXT("volume_min"),JsonVector(P.Bounds.Min));N->SetArrayField(TEXT("volume_max"),JsonVector(P.Bounds.Max));
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
    Graph->SetNumberField(TEXT("final_reward_rooms"),Plan.bBossTerminal&&Plan.BossRoom>=0&&
        Plan.Modules[Plan.BossRoom].Data->HasField(TEXT("reward_exit"))?1:0);
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
    // Surface selection has its own seed stream; changing wall art never reroutes the dungeon.
    TMap<FString,int32> PreviousSurfaceChoices;
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
            JObject Part=V->AsObject();
            const TArray<TSharedPtr<FJsonValue>>* SurfaceVariants=nullptr;
            if(Part->TryGetArrayField(TEXT("surface_mesh_variants"),SurfaceVariants)&&!SurfaceVariants->IsEmpty())
            {
                const FString BaseMesh=Part->GetStringField(TEXT("mesh"));
                FRandomStream SurfaceRandom(int32(HashCombineFast(uint32(Seed)^0x6D43A917u,
                    HashCombineFast(uint32(Index),GetTypeHash(BaseMesh)))));
                int32 Choice=SurfaceRandom.RandRange(0,SurfaceVariants->Num()-1);
                if(const int32* Previous=PreviousSurfaceChoices.Find(BaseMesh);
                    Previous&&*Previous==Choice&&SurfaceVariants->Num()>1)
                    Choice=(Choice+SurfaceRandom.RandRange(1,SurfaceVariants->Num()-1))%SurfaceVariants->Num();
                PreviousSurfaceChoices.Add(BaseMesh,Choice);
                // Copy the part before changing its mesh. Shared module JSON remains immutable.
                Part=MakeShared<FJsonObject>(*Part);
                Part->SetStringField(TEXT("mesh"),(*SurfaceVariants)[Choice]->AsString());
            }
            bool Dressing=false;Part->TryGetBoolField(TEXT("dressing"),Dressing);
            QueueAsset(Part->GetStringField(TEXT("mesh")));
            for(const auto& M:Part->GetArrayField(TEXT("materials")))QueueAsset(M->AsString());
            const FString Key=InstanceKey(Part,Piece,bOptimizeLights);
            if(!Part->GetBoolField(TEXT("fluid"))&&!Part->HasField(TEXT("half_size")))++State->InstanceCandidates.FindOrAdd(Key);
            const FName Stage=Dressing?TEXT("Dungeon.Dressing"):Part->GetBoolField(TEXT("collision"))?TEXT("Dungeon.MeshCollision"):TEXT("Dungeon.MeshVisuals");
            State->Jobs.Add({Stage,[this,State,Part,Piece,Index,Params,bOptimizeLights,Key,Dressing,bDressRooms]()
            {
            auto* Mesh=Cast<UStaticMesh>(ResolveGenerationAsset(Part->GetStringField(TEXT("mesh"))));
            if(!Mesh){State->Error=TEXT("地牢网格无法载入：")+Part->GetStringField(TEXT("mesh"));return;}
            FTransform T=Local(Part)*Piece.Transform;
            const bool Hazard=Part->HasField(TEXT("half_size")),Fluid=Part->GetBoolField(TEXT("fluid"));
            if(Dressing)
            {
                ++State->DressingCandidates;FString Reason;
                if(!State->DressingScene.Place(Mesh,Part,State->Plan.Modules[Piece.Module].Data,Piece.Transform,Index,T,Reason))
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
            OwnGenerated(A,Index);
            // SpawnActor registers AStaticMeshActor's static component immediately. After BeginPlay,
            // UE rejects SetStaticMesh on that component. Configure it while unregistered so both
            // the render proxy and physics body are created from the assigned mesh on registration.
            if(C->IsRegistered())C->UnregisterComponent();
            C->SetCanEverAffectNavigation(PartAffectsNavigation(Part));C->SetStaticMesh(Mesh);
            if(C->GetStaticMesh()!=Mesh)
            {State->Error=TEXT("地牢网格赋值失败：")+Part->GetStringField(TEXT("mesh"));return;}
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
                Instances->AddInstance(T,true);
                Instances->ComponentTags.Add(FName(*FString::Printf(TEXT("DungeonModule.%d.%s"),Index,*State->Plan.Modules[Piece.Module].Id)));
                State->InstanceGroups.Add(Key,Instances);++State->Instances;++State->InstanceComponents;
            }
            C->RegisterComponent();
            if(!C->IsRegistered())
            {State->Error=TEXT("地牢网格组件注册失败：")+Part->GetStringField(TEXT("mesh"));return;}
            if(auto* WaterFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())WaterFX->RegisterWaterSurface(C);
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
            FString PropRole;
            if(Prop->TryGetStringField(TEXT("role"),PropRole)&&PropRole==TEXT("final_reward_chest"))
            {
                A->Tags.Add(TEXT("DungeonFinalTreasure"));A->Tags.Add(TEXT("DungeonReward.Locked"));
                State->FinalRewardChests.Add(Index,A);
            }
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
            const JObject Reward=D->HasTypedField<EJson::Object>(TEXT("reward_exit"))?D->GetObjectField(TEXT("reward_exit")):nullptr;
            if(Reward)
            {
                QueueAsset(Reward->GetStringField(TEXT("leaf_mesh")));
                for(const auto& Asset:Reward->GetArrayField(TEXT("return_assets")))QueueAsset(Asset->AsString());
            }
            State->Jobs.Add({TEXT("Dungeon.BossEncounter"),[this,State,Encounter,Reward,Piece,Index]()
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
                if(Reward)
                {
                    auto* Leaf=Cast<UStaticMesh>(ResolveGenerationAsset(Reward->GetStringField(TEXT("leaf_mesh"))));
                    AActor* Chest=State->FinalRewardChests.FindRef(Index).Get();
                    if(!Leaf||!IsValid(Chest))
                    {E->Destroy();State->Error=TEXT("最终宝箱房缺少机械门或宝箱");return;}
                    const JObject Return=Reward->GetObjectField(TEXT("return_portal"));
                    const FTransform ReturnTransform=Local(Return)*Piece.Transform;
                    auto* Portal=GetWorld()->SpawnActorDeferred<ASceneTestPortal>(ASceneTestPortal::StaticClass(),ReturnTransform,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                    if(!Portal){E->Destroy();State->Error=TEXT("最终宝箱房返程入口创建失败");return;}
                    Portal->Tags.Add(TEXT("DungeonReward.Locked"));Portal->Tags.Add(TEXT("DungeonFinalReturn"));
                    Portal->Configure(Return->GetStringField(TEXT("destination")),TEXT("RETURN TO BASE"),FString(),FColor(130,230,195));
                    Portal->FinishSpawning(ReturnTransform);OwnGenerated(Portal,Index);
                    E->ConfigureRewardExit(Leaf,Vec(Reward,TEXT("door_position")),Vec(Reward,TEXT("door_travel")),
                        Vec(Reward,TEXT("door_clear_size")),Chest,Portal);
                }
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
            const bool BossHall=Plan.Modules[Piece.Module].Id==TEXT("BossPumpHall");
            FString LightRole=Corridor?TEXT("corridor"):Brightest.Find(LightIndex)<2?TEXT("key"):TEXT("fill");
            L->TryGetStringField(TEXT("role"),LightRole);
            State->Jobs.Add({TEXT("Dungeon.Lights"),[this,State,L,Piece,Index,Params,bOptimizeLights,Corridor,BossHall,LightRole]()
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
                // The 30 x 26 m, two-storey hall cannot use a small room's 3 m fill radius:
                // several overhead fills then end above their floor or at the gallery surface.
                Radius=Fill&&!BossHall?FMath::Min(Radius*.8,300.0):Radius;
                DrawDistance=BossHall?5200:Fill?1400:Corridor?1800:2400;
                FadeRange=BossHall?700:Fill?400:500;Shadows=BossHall||!Fill;
                L->TryGetNumberField(TEXT("optimized_radius_cm"),Radius);
                L->TryGetNumberField(TEXT("max_draw_distance_cm"),DrawDistance);
                L->TryGetNumberField(TEXT("fade_range_cm"),FadeRange);
                if(Fill&&!BossHall)
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
            const FVector Color=Vec(L,TEXT("color"));C->SetLightColor(FLinearColor(Color.X,Color.Y,Color.Z));
            C->SetSourceRadius(BossHall?2:5);C->SetSourceLength(Spot?0:60);C->SetCastShadows(Shadows);
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
    // Build every module's collidable structure first. Each actor's physics is drained
    // by PumpAssembly before the next job; dressing still sees all geometry/fixed props.
    State->Jobs.StableSort([](const auto& A,const auto& B)
    {
        auto Rank=[](FName Stage)
        {
            if(Stage==TEXT("Dungeon.Resources"))return 0;
            if(Stage==TEXT("Dungeon.MeshCollision"))return 1;
            if(Stage==TEXT("Dungeon.MeshVisuals"))return 2;
            if(Stage==TEXT("Dungeon.Lights"))return 3;
            if(Stage==TEXT("Dungeon.DressingScene"))return 5;
            if(Stage==TEXT("Dungeon.Dressing"))return 6;
            return 4;
        };
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
    const int32 InitialJobCursor=State->Cursor,InitialPhysicsCursor=State->PhysicsActorCursor;
    if(State->Error.IsEmpty())
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Dungeon_AssemblySlice);
        DungeonPerformance::FScope SliceScope(this,TEXT("Dungeon.AssemblySlice"));
        const double Start=FPlatformTime::Seconds();
        const double Budget=FMath::Clamp(double(DungeonBuildBudget.GetValueOnGameThread()),.25,16.)/1000.;
        do
        {
            // Complete the newly configured actor before starting another job. Keeping
            // this cursor under the assembly budget avoids a whole-dungeon physics spike
            // at commit. Existing ISM groups already have a physics state when AddInstance
            // appends another instance, so UE creates that instance's body with the job.
            if(State->bStaging&&State->PhysicsActorCursor<GeneratedActors.Num())
            {
                const double PhysicsStart=FPlatformTime::Seconds();
                bool bPendingPhysics=false;
                {
                    DungeonPerformance::FScope PhysicsScope(this,TEXT("Dungeon.PhysicsActivation"));
                    if(AActor* Actor=GeneratedActors[State->PhysicsActorCursor];IsValid(Actor))
                    {
                        Actor->SetActorEnableCollision(true);
                        TInlineComponentArray<UPrimitiveComponent*> Primitives(Actor);
                        for(UPrimitiveComponent* Primitive:Primitives)
                        {
                            if(!Primitive->IsRegistered()||!Primitive->IsCollisionEnabled())continue;
                            if(Primitive->IsAsyncCreatePhysicsStateRunning()){bPendingPhysics=true;continue;}
                            // Registration while OwnGenerated has actor collision disabled
                            // can skip body creation. Enabling only updates existing filters.
                            if(!Primitive->IsPhysicsStateCreated())
                            {
                                Primitive->CreatePhysicsState(false);
                                if(!Primitive->IsPhysicsStateCreated())
                                {
                                    State->Error=TEXT("地牢碰撞体创建失败：")+Primitive->GetPathName();
                                    break;
                                }
                                ++State->PhysicsStatesCreated;
                            }
                        }
                    }
                }
                State->PhaseMs.FindOrAdd(TEXT("Dungeon.PhysicsActivation"))+=(FPlatformTime::Seconds()-PhysicsStart)*1000.;
                if(bPendingPhysics||!State->Error.IsEmpty())break;
                ++State->PhysicsActorCursor;
                continue;
            }
            if(!State->Jobs.IsValidIndex(State->Cursor))break;
            auto& Job=State->Jobs[State->Cursor];
            if(!State->bStaging&&Job.Stage!=TEXT("Dungeon.Resources"))
            {State->PreviousActors=MoveTemp(GeneratedActors);GeneratedActors.Reset();State->bStaging=true;}
            State->LoadingStatus=AssemblyStatus(Job.Stage);
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
    if(State->Cursor>=State->Jobs.Num()&&State->PhysicsActorCursor>=GeneratedActors.Num())
    {
        // Give commit its own frame budget instead of adding it to the final build slice.
        if(!bSynchronous&&(State->Cursor!=InitialJobCursor||State->PhysicsActorCursor!=InitialPhysicsCursor))
        {
            if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(FText::FromString(TEXT("正在切换至新的地牢布局…")),.88f);
            return;
        }
        FinishAssembly(bSynchronous);return;
    }
    if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(State->LoadingStatus,
        .1f+.78f*float(State->Cursor)/FMath::Max(1,State->Jobs.Num()));
}

void AAuthoredDungeonGenerator::FinishAssembly(bool bSynchronous)
{
    DungeonPerformance::FScope FinalizeScope(this,TEXT("Dungeon.Finalize"));
    const double FinalizeStarted=FPlatformTime::Seconds();
    auto* State=BuildState.Get();
    auto RecordFinalize=[State,FinalizeStarted]()
    {State->PhaseMs.FindOrAdd(TEXT("Dungeon.Finalize"))+=(FPlatformTime::Seconds()-FinalizeStarted)*1000.;};
    const double Budget=FMath::Clamp(double(DungeonBuildBudget.GetValueOnGameThread()),.25,16.)/1000.;
    auto OutOfTime=[bSynchronous,FinalizeStarted,Budget]()
    {return !bSynchronous&&FPlatformTime::Seconds()-FinalizeStarted>=Budget;};
    if(!State->bCommitted)
    {
        // PumpAssembly has finished every actor's collision before reaching this point.
        // From the first retirement onwards the new layout owns the scene; rolling back
        // to a partially destroyed old layout is no longer possible.
        ResetRoomLighting();
        State->bCommitted=true;
        LightModules=MoveTemp(State->NextLights);
    }
    // Destroying the saved preview and revealing thousands of new components can also
    // stall the loading UI. Keep both operations resumable, with input still held.
    while(State->RetireCursor<State->PreviousActors.Num())
    {
        const double StepStart=FPlatformTime::Seconds();
        AActor* Actor=State->PreviousActors[State->RetireCursor++];
        if(IsValid(Actor))Actor->Destroy();
        State->PhaseMs.FindOrAdd(TEXT("Dungeon.Teardown"))+=(FPlatformTime::Seconds()-StepStart)*1000.;
        if(OutOfTime())
        {
            if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(FText::FromString(TEXT("正在切换至新的地牢布局…")),
                .88f+.03f*float(State->RetireCursor)/FMath::Max(1,State->PreviousActors.Num()));
            RecordFinalize();return;
        }
    }
    State->PreviousActors.Reset();
    while(State->RevealCursor<GeneratedActors.Num())
    {
        const double StepStart=FPlatformTime::Seconds();
        AActor* Actor=GeneratedActors[State->RevealCursor++];
        if(IsValid(Actor))Actor->SetActorHiddenInGame(false);
        State->PhaseMs.FindOrAdd(TEXT("Dungeon.Reveal"))+=(FPlatformTime::Seconds()-StepStart)*1000.;
        if(OutOfTime())
        {
            if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(FText::FromString(TEXT("正在准备地牢显示…")),
                .91f+.04f*float(State->RevealCursor)/FMath::Max(1,GeneratedActors.Num()));
            RecordFinalize();return;
        }
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
    DungeonWallStains::Apply(GetWorld(),GeneratedSeed);
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
    Report->SetStringField(TEXT("contract"),TEXT("CPU preparation for this generation. Layout search runs on a worker in game worlds. Stage values are inclusive synchronous game-thread wall times, not additive with AssemblySlice/Finalize, GPU timings or measured FPS improvements. MeshCollision covers collidable mesh setup; PhysicsActivation covers staged actor body creation. Teardown/Reveal are also time sliced before navigation and player release. A single indivisible job can exceed BudgetMs. Planning data is not read until worker completion."));
    Report->SetNumberField(TEXT("elapsed_ms"),((S.FinishedAt>0?S.FinishedAt:FPlatformTime::Seconds())-S.StartedAt)*1000.);
    // The worker mutates only Plan, PlanMs and bPlanSucceeded. Do not inspect those while it runs.
    if(S.bPlanning){Report->SetField(TEXT("layout_worker_ms"),MakeShared<FJsonValueNull>());Report->SetField(TEXT("modules"),MakeShared<FJsonValueNull>());}
    else {Report->SetNumberField(TEXT("layout_worker_ms"),S.PlanMs);Report->SetNumberField(TEXT("modules"),S.Plan.Pieces.Num());Report->SetNumberField(TEXT("treasure_rooms"),S.Plan.TreasureCount);}
    Report->SetBoolField(TEXT("time_sliced"),S.bRuntime);Report->SetNumberField(TEXT("budget_ms"),DungeonBuildBudget.GetValueOnGameThread());
    Report->SetNumberField(TEXT("jobs_completed"),S.Cursor);Report->SetNumberField(TEXT("jobs_total"),S.Jobs.Num());
    Report->SetNumberField(TEXT("assembly_slices"),S.Slices);Report->SetNumberField(TEXT("peak_slice_ms"),S.PeakSliceMs);
    Report->SetNumberField(TEXT("unique_assets_resolved"),S.AssetResolutions);Report->SetNumberField(TEXT("parts"),S.Parts);
    Report->SetNumberField(TEXT("instanced_parts"),S.Instances);Report->SetNumberField(TEXT("instance_components"),S.InstanceComponents);
    Report->SetNumberField(TEXT("physics_states_created_during_assembly"),S.PhysicsStatesCreated);
    Report->SetNumberField(TEXT("physics_actors_prepared"),S.PhysicsActorCursor);
    Report->SetNumberField(TEXT("individual_rigid_parts"),S.StaticFallbacks);Report->SetNumberField(TEXT("hazards"),S.Hazards);
    Report->SetNumberField(TEXT("skeletal_props"),S.Props);Report->SetNumberField(TEXT("lights"),S.Lights);
    Report->SetNumberField(TEXT("dressing_props"),S.DressingProps);
    Report->SetNumberField(TEXT("dressing_stacked"),S.DressingScene.StackCount);
    Report->SetNumberField(TEXT("dressing_leaning"),S.DressingScene.LeanCount);
    Report->SetNumberField(TEXT("dressing_fallen"),S.DressingScene.FallenCount);
    Report->SetNumberField(TEXT("dressing_placement_attempts"),S.DressingScene.PlacementAttempts);
    Report->SetNumberField(TEXT("dressing_candidates"),S.DressingCandidates);Report->SetNumberField(TEXT("dressing_skipped"),S.DressingSkipped);
    auto DressingReasons=MakeShared<FJsonObject>();for(const auto& P:S.DressingRejections) DressingReasons->SetNumberField(P.Key,P.Value);
    Report->SetObjectField(TEXT("dressing_rejections"),DressingReasons);
    auto Phases=MakeShared<FJsonObject>();for(const auto& P:S.PhaseMs)Phases->SetNumberField(P.Key.ToString(),P.Value);
    Report->SetObjectField(TEXT("game_thread_phases_ms"),Phases);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;
}
