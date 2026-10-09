#include "AuthoredDungeonGenerator.h"
#include "Templates/Atomic.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
#include "DungeonPusChannel.h"
#include "Async/Async.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Misc/PackageName.h"
#include "UObject/ObjectSaveContext.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "DungeonPerformanceScope.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Animation/SkeletalMeshActor.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Engine/RectLight.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/DecalComponent.h"
#include "Engine/DecalActor.h"
#include "Misc/DateTime.h"
#include "Misc/SecureHash.h"
#include "TimerManager.h"
#include "DungeonBossEncounter.h"
#include "DungeonProgressionGate.h"
#include "WardRoomAssembly.h"
#include "StaffLivingRoomAssembly.h"
#include "CargoWarehouseContainers.h"
#include "StationWorkshopAssembly.h"
#include "DungeonWallArt.h"
#include "DungeonRunSubsystem.h"
#include "DungeonSpawnDirector.h"
#include "AuthoredDungeonRoomScenes.h"
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
    const TArray<TSharedPtr<FJsonValue>>* V=nullptr;
    if(!O.IsValid()||!O->TryGetArrayField(Key,V)||!V||V->Num()<3||!(*V)[0].IsValid()||!(*V)[1].IsValid()||!(*V)[2].IsValid())
        return FVector::ZeroVector;
    return FVector((*V)[0]->AsNumber(),(*V)[1]->AsNumber(),(*V)[2]->AsNumber());
}
struct FPort { FVector P,N; double Width=300,Height=280; };
FPort ReadPort(const JObject& Data)
{
    FPort Port{Vec(Data,TEXT("position")),Vec(Data,TEXT("normal"))};
    Data->TryGetNumberField(TEXT("width"),Port.Width);Data->TryGetNumberField(TEXT("height"),Port.Height);
    return Port;
}
struct FSideSocket { FPort Port; JObject Data; int32 SourcePort=INDEX_NONE; };
struct FModule { FString Id,Family; FBox Bounds; TArray<FPort> Ports; JObject Data; TArray<FBox> Cells; TArray<FSideSocket> SideSockets; TArray<FIntPoint> PortPairs; FString SelectionRoute; int32 MaxPerRun=MAX_int32; bool bRunEligible=true; };
struct FPlaced { int32 Module; FTransform Transform; FBox Bounds; FString Route; TArray<FBox> Cells; int32 Side=-1; int32 LinkTurns=-1; double LinkLength=0; TArray<int32> ActivePorts; FString MissionId,EncounterRole; int32 ThreatBonus=0; double RewardMultiplier=1.; int32 MissionDepth=INDEX_NONE; bool bThemeBridge=false; };
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
    uint32 ConnectionSeed=0;
    double PlanningDeadline=DBL_MAX;
    bool bSearchExpired=false;
    TAtomic<bool>* CancelRequested=nullptr;
    bool CanSearch()
    {
        if(CancelRequested&&CancelRequested->Load())return false;
        if(bSearchExpired)return false;
        if(FPlatformTime::Seconds()>PlanningDeadline){bSearchExpired=true;return false;}
        return true;
    }
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
        // A cardinal yaw round-trip can move an 8 cm contact by ~1e-12 cm.
        // Keep the authored tolerance stable across candidate save/replay.
        constexpr double ContactTolerance=8.001;
        return FMath::Min(A.Max.X,B.Max.X)-FMath::Max(A.Min.X,B.Min.X)>ContactTolerance &&
               FMath::Min(A.Max.Y,B.Max.Y)-FMath::Max(A.Min.Y,B.Min.Y)>ContactTolerance &&
               FMath::Min(A.Max.Z,B.Max.Z)-FMath::Max(A.Min.Z,B.Min.Z)>ContactTolerance;
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
    int32 OptionalPort(int32 Owner,int32 Side)const
    {
        const auto& M=Modules[Pieces[Owner].Module];
        return M.SideSockets[Side].SourcePort>=0?M.SideSockets[Side].SourcePort:M.Ports.Num();
    }
    TArray<int32> OpenPorts(int32 Owner)const
    {
        const auto& P=Pieces[Owner];TArray<int32> Result=P.ActivePorts;
        if(Result.IsEmpty())for(int32 I=0;I<Modules[P.Module].Ports.Num();++I)Result.Add(I);
        if(P.Side>=0)Result.AddUnique(OptionalPort(Owner,P.Side));return Result;
    }
    bool SideAvailable(int32 Owner,int32 Side)const
    {return Pieces[Owner].Side<0&&!OpenPorts(Owner).Contains(OptionalPort(Owner,Side));}
    int32 PairedExit(int32 Module,int32 Entry)const
    {
        for(const FIntPoint& Pair:Modules[Module].PortPairs)
        {if(Pair.X==Entry)return Pair.Y;if(Pair.Y==Entry)return Pair.X;}
        return INDEX_NONE;
    }
    #include "AuthoredDungeonRoomChoices.inl"
    bool Place(int32 Module,const FTransform& T,const FString& Route,int32 IgnoreFrom=-2,int32 IgnoreOwner=-2,
               FVector SectorOrigin=FVector::ZeroVector,FVector SectorDir=FVector::ZeroVector,int32 SecondOwner=-2,
               const TArray<int32>& ActivePorts={})
    {
        // Room shells stay rigid. Only straight connector length may change.
        if(Combat.Contains(Module)&&!RoomAllowed(Module,Route))return false;
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
                    if(!JoinedWallSeam(Module,T,I,Cell.Overlap(Other),ActivePorts))
                    {
                        if(bLayoutProbe)++ProbeRejects.FindOrAdd(Route+TEXT("/")+Modules[Module].Id+TEXT("/overlap/")+Modules[Pieces[I].Module].Id);
                        return false;
                    }
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
        const int32 Added=Pieces.Add({Module,T,B,Route,Cells});Pieces[Added].ActivePorts=ActivePorts;return true;
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
        if(SearchBudget<=0||!CanSearch())return false;
        const auto Choices=RoomChoices(Route);
        const int32 Before=Pieces.Num();const FSocket Initial=S;
        auto Links=RoomLinks(Initial);
        RankRoomLinks(Links,Initial,Route);
        for(const auto& Choice:Choices)for(const auto& Link:Links)
        {
            Pieces.SetNum(Before);S=Initial;
            if(--SearchBudget<0||!CanSearch()){Pieces.SetNum(Before);S=Initial;return false;}
            if(!AttachRoom(Choice.Key,Choice.Value,Initial,Link,Route,S,SectorOrigin,SectorDir,Choice.Exit))continue;
            if(Chain(Remaining-1,S,Route,SectorOrigin,SectorDir))return true;
        }
        Pieces.SetNum(Before);S=Initial;return false;
    }
    #include "AuthoredDungeonRouting.inl"
    TAtomic<int32>* SearchProgress=nullptr;
    TAtomic<int32>* SearchProgressLimit=nullptr;
    void NoteSearch(int32 Attempt,int32 Limit)
    {
        if(SearchProgress)SearchProgress->Store(Attempt);
        if(SearchProgressLimit)SearchProgressLimit->Store(Limit);
    }
    #include "AuthoredDungeonCompactRouting.inl"
    #include "AuthoredDungeonTopology.inl"
    #include "AuthoredDungeonMission.inl"
    #include "AuthoredDungeonThemedRoutes.inl"
    #include "AuthoredDungeonSplitLevels.inl"
    #include "AuthoredDungeonJointRouting.inl"
    #include "AuthoredDungeonLayoutBank.inl"
    bool BuildOpen(int32 Seed,const FSocket& Start,double Deadline)
    {
        constexpr int32 OpenTries=48;
        for(int32 Attempt=0;Attempt<OpenTries;++Attempt)
        {
            if(FPlatformTime::Seconds()>Deadline||!CanSearch())break;
            NoteSearch(Attempt+1,OpenTries);
            Pieces.Reset();Counts.Reset();Random.Initialize(int32(uint32(Seed)+uint32(Attempt)*7919u));SearchBudget=2500;CompactBudget=20000;
            FSocket S=Start;const int32 MainCount=TopologyCounts[0];Counts.Add(MainCount);
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
                const FString Route=FString::Printf(TEXT("Route%d"),I+1);const int32 Count=TopologyCounts[I+1];Counts.Add(Count);
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
    bool Build(int32 Seed,const FSocket& Start)
    {
        if(bBossTerminal&&bCompactBoss)
        {
            if(bPairedFacility&&bUseJointFacilityLayout)return BuildFacility(Seed,Start);
            // A failed underground plan must never become the old same-floor,
            // 220 m terminal while still reporting an underground manifest.
            return BuildCompact(Seed,Start,PlanningDeadline);
        }
        return BuildOpen(Seed,Start,PlanningDeadline);
    }
    void AddTreasureRooms(int32 Seed)
    {
        if(Treasure<0||TreasureLink<0||TreasureChance<=0)return;
        FRandomStream SideRandom(Seed^0x54A391);const int32 MainPieces=Pieces.Num();
        // One independent chance per ordinary room. The completed route graph reserves its space first.
        for(int32 Owner=0;Owner<MainPieces;++Owner)
        {
            const int32 ParentModule=Pieces[Owner].Module;
            if(!Combat.Contains(ParentModule)||Modules[ParentModule].SideSockets.IsEmpty())continue;
            const bool bTryTreasure=SideRandom.FRand()<TreasureChance;
            if(Pieces[Owner].Side>=0||!bTryTreasure)continue;
            TArray<int32> Choices;for(int32 I=0;I<Modules[ParentModule].SideSockets.Num();++I)if(SideAvailable(Owner,I))Choices.Add(I);
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
                if(!MeasureMissionBudget()){Pieces.SetNum(Before);Pieces[Owner].Side=-1;continue;}
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
    struct FResourceBatch
    {
        TArray<FString> Paths;
        TSharedPtr<FStreamableHandle> Handle;
        double StartedAt = 0;
    };
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
    TWeakObjectPtr<AActor> PhysicsRefreshActor;
    FText LoadingStatus;
    double StartedAt=FPlatformTime::Seconds(),FinishedAt=0,PlanMs=0,PeakSliceMs=0;
    FString Error;
    FString PendingDescription,PendingManifest;
    TArray<TObjectPtr<AActor>> PreviousActors;
    TArray<FAuthoredDungeonLightModule> NextLights;
    TArray<FAuthoredDungeonRenderGroup> NextRenderGroups;
    TMap<UPrimitiveComponent*, int32> RenderGroupByComponent;
    TArray<FString> ResourcePaths;
    TArray<FResourceBatch> ResourceBatches;
    int32 ResourceCursor=0,ResourcesCompleted=0,PreviousResourceCount=0;
    bool bStaging=false,bCommitted=false,bNavigationRequested=false;
    double NavigationRequestedAt=0;
    bool bPlanning=true,bPlanSucceeded=false,bRuntime=false,bCompleted=false;
    TAtomic<int32> SearchAttempt{0};
    TAtomic<int32> SearchAttemptLimit{1};
    TAtomic<bool> CancelRequested{false};
};

namespace
{
TAutoConsoleVariable<float> DungeonBuildBudget(TEXT("fps.Dungeon.Generation.BudgetMs"),3.f,
    TEXT("Game-thread assembly budget per frame, milliseconds. One indivisible mesh/physics registration may exceed it."));
TAutoConsoleVariable<int32> DungeonInstancing(TEXT("fps.Dungeon.Instancing"),1,
    TEXT("Instance repeated rigid Nanite meshes in spatial groups on next generation. Non-Nanite meshes retain individual components for Lumen."));
TAutoConsoleVariable<int32> DungeonDressingEnabled(TEXT("fps.Dungeon.Dressing"),1,
    TEXT("Generate cosmetic wall-side prop clusters with the next dungeon. Never consumes the route random stream."));

FSoftObjectPath GenerationAssetPath(const FString& Path)
{
    FString ObjectPath=FPackageName::ExportTextPathToObjectPath(Path);
    // Authors use both package-only and fully qualified object paths.
    if(!ObjectPath.Contains(TEXT(".")))ObjectPath+=TEXT(".")+FPackageName::GetShortName(ObjectPath);
    return FSoftObjectPath(ObjectPath);
}

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
    bool RoomCull=true;Part->TryGetBoolField(TEXT("room_render_culling"),RoomCull);Key+=RoomCull?TEXT("|RoomCull"):TEXT("|Keep");
    double DrawDistance=0;Part->TryGetNumberField(TEXT("max_draw_distance_cm"),DrawDistance);
    Key+=FString::Printf(TEXT("|Cull%.1f"),DrawDistance);
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
#if WITH_EDITOR
void AAuthoredDungeonGenerator::PreSave(FObjectPreSaveContext SaveContext)
{
    // Old importers can keep supplying objects. Saved maps retain soft cook
    // dependencies instead of eagerly loading every possible room with the map.
    for(UObject* Asset:ModuleAssets)
        if(Asset)ModuleAssetPaths.AddUnique(TSoftObjectPtr<UObject>(Asset));
    ModuleAssets.Reset();
    Super::PreSave(SaveContext);
}
#endif
void AAuthoredDungeonGenerator::ClearGenerated()
{
    ResetRoomLighting();LightModules.Reset();RenderGroups.Reset();
    for(AActor* A:GeneratedActors)if(IsValid(A))A->Destroy();GeneratedActors.Reset();
}
void AAuthoredDungeonGenerator::GeneratePreview(){Generate(PreviewSeed);}
void AAuthoredDungeonGenerator::BeginPlay()
{
    Super::BeginPlay();if(GetNetMode()==NM_Client)return;
    // The background map installer authors the entrance floor before a run
    // exists. Retire that floor with the previous assembly once the new one is ready.
    for(TActorIterator<AActor> It(GetWorld());It;++It)
        if(It->GetOwner()==this&&It->ActorHasTag(TEXT("DungeonFacilityEntryPreview")))
            GeneratedActors.AddUnique(*It);
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
    State->PreviousResourceCount=GenerationResources.Num();
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
    Plan.bLayoutProbe=IsRunningCommandlet()&&FParse::Param(FCommandLine::Get(),TEXT("DungeonLayoutProbe"));
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
        const JObject* Selection=nullptr;
        if(D->TryGetObjectField(TEXT("selection"),Selection))
        {
            double Chance=1.;(*Selection)->TryGetNumberField(TEXT("chance_per_run"),Chance);
            (*Selection)->TryGetNumberField(TEXT("max_per_run"),M.MaxPerRun);
            (*Selection)->TryGetStringField(TEXT("route"),M.SelectionRoute);
            // One draw per seed/module, outside backtracking and decoration streams.
            FRandomStream Eligibility(int32(HashCombineFast(uint32(Seed)^0x53504543u,GetTypeHash(M.Id))));
            M.bRunEligible=Eligibility.FRand()<FMath::Clamp(Chance,0.,1.);
        }
        for(const auto& V:D->GetArrayField(TEXT("ports")))M.Ports.Add(ReadPort(V->AsObject()));
        for(const auto& V:D->GetArrayField(TEXT("cells"))){JObject C=V->AsObject();M.Cells.Add(FBox(Vec(C,TEXT("min")),Vec(C,TEXT("max"))));}
        const TArray<TSharedPtr<FJsonValue>>* Sides=nullptr;
        if(D->TryGetArrayField(TEXT("side_sockets"),Sides))for(const auto& V:*Sides)
        {JObject S=V->AsObject();int32 Port=INDEX_NONE;S->TryGetNumberField(TEXT("port_index"),Port);M.SideSockets.Add({ReadPort(S),S,Port});}
        const TArray<TSharedPtr<FJsonValue>>* Pairs=nullptr;
        if(D->TryGetArrayField(TEXT("port_pairs"),Pairs))for(const auto& V:*Pairs)
        {const auto& Pair=V->AsArray();if(Pair.Num()==2)M.PortPairs.Add(FIntPoint(int32(Pair[0]->AsNumber()),int32(Pair[1]->AsNumber())));}
        else if(M.Ports.Num()==2)M.PortPairs.Add(FIntPoint(0,1));
        if(Plan.Find(M.Id)>=0||M.Cells.IsEmpty()||M.Ports.IsEmpty())
        {State->Error=TEXT("地牢模块重复或缺少占地/端口：")+M.Id;State->bPlanning=false;PumpAssembly(true);return;}
        Plan.Modules.Add(M);
    }
    Plan.Transit=Plan.Find(TEXT("Transit"));Plan.Threshold=Plan.Find(TEXT("Threshold"));Plan.Junction=Plan.Find(TEXT("Junction"));Plan.End=Plan.Find(TEXT("RouteEnd"));
    const JObject* FacilityFlow=nullptr;
    if(Catalog->TryGetObjectField(TEXT("facility_flow"),FacilityFlow))
        Plan.Junction=Plan.Find((*FacilityFlow)->GetStringField(TEXT("junction")));
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
        if(Room.PortPairs.IsEmpty()||RoomRole==TEXT("boss_terminal")||RoomRole==TEXT("terminal_confluence"))
        {State->Error=TEXT("普通房池缺少合法门位配对：")+Room.Id;State->bPlanning=false;PumpAssembly(true);return;}
        for(const auto& Pair:Room.PortPairs)if(Pair.X==Pair.Y||!Room.Ports.IsValidIndex(Pair.X)||!Room.Ports.IsValidIndex(Pair.Y))
        {State->Error=TEXT("房间门位配对越界：")+Room.Id;State->bPlanning=false;PumpAssembly(true);return;}
        if(Room.Ports.Num()>2)for(int32 Port=0;Port<Room.Ports.Num();++Port)
        {
            const TArray<TSharedPtr<FJsonValue>>* Closures=nullptr;bool HasClosure=false;
            if(Room.Data->TryGetArrayField(TEXT("closed_port_parts"),Closures))for(const auto& V:*Closures)
                if(int32(V->AsObject()->GetNumberField(TEXT("port_index")))==Port&&!V->AsObject()->GetArrayField(TEXT("parts")).IsEmpty())HasClosure=true;
            if(!HasClosure){State->Error=TEXT("多门房缺少实体封门构件：")+Room.Id;State->bPlanning=false;PumpAssembly(true);return;}
        }
    }
    if(Plan.Modules[Plan.Transit].Ports.Num()!=2||Plan.Modules[Plan.Threshold].Ports.Num()!=2||Plan.Modules[Plan.Junction].Ports.Num()!=4)
    {State->Error=TEXT("连接件或岔路房端口数量错误");State->bPlanning=false;PumpAssembly(true);return;}
    const AuthoredDungeon::FSocket Start{Vec(Catalog,TEXT("start_position")),Vec(Catalog,TEXT("start_normal")),-1};
    Plan.SearchProgress=&State->SearchAttempt;
    Plan.SearchProgressLimit=&State->SearchAttemptLimit;
    Plan.CancelRequested=&State->CancelRequested;
    auto PlanWork=[State,Start]()
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Dungeon_LayoutSearch);
        const double Begin=FPlatformTime::Seconds();
        State->Plan.PlanningDeadline=Begin+12.;
        State->Plan.ConfigureTopology(State->Seed);
        if(!State->Plan.ConfigureThemedRoutes(State->Seed,State->Catalog))
        {State->bPlanSucceeded=false;State->PlanMs=(FPlatformTime::Seconds()-Begin)*1000.;return;}
        State->Plan.ConfigureMission(State->Seed,State->Catalog);
        State->bPlanSucceeded=State->Plan.Build(State->Seed,Start);
        if(State->bPlanSucceeded)
        {
            if(!State->Plan.bMissionEnabled)State->Plan.AddRouteLoops(Start);
            State->Plan.AddTreasureRooms(State->Seed);
            State->Plan.BindRewardMissions(Start);
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
    else
    {
        PlanWork();State->bPlanning=false;
#if WITH_EDITOR
        // Explicit commandlet-only repro: exercise the production planner and
        // catalog without spawning geometry, touching saves, or trusting headless physics.
        if(IsRunningCommandlet()&&FParse::Param(FCommandLine::Get(),TEXT("DungeonLayoutProbe")))
        {
            auto Report=MakeShared<FJsonObject>();
            Report->SetNumberField(TEXT("seed"),Seed);
            Report->SetBoolField(TEXT("success"),State->bPlanSucceeded);
            Report->SetStringField(TEXT("failure"),Plan.CompactFailure);
            Report->SetNumberField(TEXT("plan_ms"),State->PlanMs);
            Report->SetBoolField(TEXT("expired"),Plan.bSearchExpired);
            Report->SetNumberField(TEXT("grammar_requested"),Plan.RequestedGrammar);
            Report->SetNumberField(TEXT("grammar"),Plan.ActualGrammar);
            Report->SetNumberField(TEXT("split_after"),Plan.SplitAfter);
            Report->SetBoolField(TEXT("theme_bridges_enabled"),Plan.bThemeBridgeSearch);
            Report->SetStringField(TEXT("layout_solver"),Plan.LayoutSolver);
            Report->SetStringField(TEXT("catalog_contract_sha1"),Plan.FacilityContractHash);
            auto DrawnPairs=MakeShared<FJsonObject>();
            for(const auto& Pair:Plan.DrawnThemePairs)
            {
                TArray<TSharedPtr<FJsonValue>> Themes;
                for(const auto& Id:Pair.Value)Themes.Add(MakeShared<FJsonValueString>(Id));
                DrawnPairs->SetArrayField(Pair.Key,Themes);
            }
            Report->SetObjectField(TEXT("drawn_theme_pairs"),DrawnPairs);
            Report->SetNumberField(TEXT("attempt"),State->SearchAttempt.Load());
            Report->SetNumberField(TEXT("corridor_cm"),Plan.CorridorTotal);
            Report->SetNumberField(TEXT("corridor_budget_cm"),Plan.CorridorBudget);
            Report->SetNumberField(TEXT("route_estimate_cm"),Plan.LongestRouteEstimate);
            Report->SetNumberField(TEXT("route_budget_cm"),Plan.RouteBudget);
            Report->SetArrayField(TEXT("route_length_details"),Plan.MissionRouteLengthsJson());
            auto JsonVector=[](FVector V){return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};};
            auto JsonSocket=[&](const AuthoredDungeon::FSocket& S)
            {
                auto Value=MakeShared<FJsonObject>();Value->SetArrayField(TEXT("position"),JsonVector(S.P));
                Value->SetArrayField(TEXT("normal"),JsonVector(S.N));Value->SetNumberField(TEXT("width"),S.Width);Value->SetNumberField(TEXT("height"),S.Height);
                return Value;
            };
            Report->SetObjectField(TEXT("start"),JsonSocket(Start));
            TArray<TSharedPtr<FJsonValue>> Routes,MissionEdgesJson,Loops;
            for(double Length:Plan.RouteEstimates)Routes.Add(MakeShared<FJsonValueNumber>(Length));
            Report->SetArrayField(TEXT("route_estimates_cm"),Routes);
            for(const auto& E:Plan.MissionEdges)
            {
                auto Edge=MakeShared<FJsonObject>();Edge->SetStringField(TEXT("from"),E.From);Edge->SetStringField(TEXT("to"),E.To);
                Edge->SetBoolField(TEXT("optional"),E.bOptional);Edge->SetBoolField(TEXT("realized"),E.bRealized);MissionEdgesJson.Add(MakeShared<FJsonValueObject>(Edge));
            }
            Report->SetArrayField(TEXT("mission_edges"),MissionEdgesJson);
            for(const auto& L:Plan.LoopConnections)
            {
                auto Loop=MakeShared<FJsonObject>();Loop->SetNumberField(TEXT("from"),L.From);Loop->SetNumberField(TEXT("to"),L.To);
                Loop->SetNumberField(TEXT("length"),L.Length);Loops.Add(MakeShared<FJsonValueObject>(Loop));
            }
            Report->SetArrayField(TEXT("loops"),Loops);
            TArray<TSharedPtr<FJsonValue>> CountsJson,PiecesJson;
            for(int32 Count:Plan.Counts)CountsJson.Add(MakeShared<FJsonValueNumber>(Count));
            Report->SetArrayField(TEXT("counts"),CountsJson);
            for(int32 I=0;I<Plan.Pieces.Num();++I)
            {
                const auto& P=Plan.Pieces[I];
                auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("module"),Plan.Modules[P.Module].Id);
                Item->SetStringField(TEXT("route"),P.Route);Item->SetStringField(TEXT("transform"),P.Transform.ToString());
                Item->SetStringField(TEXT("mission_id"),P.MissionId);Item->SetNumberField(TEXT("mission_depth"),P.MissionDepth);
                Item->SetNumberField(TEXT("side"),P.Side);Item->SetNumberField(TEXT("link_cm"),P.LinkLength);Item->SetNumberField(TEXT("link_turns"),P.LinkTurns);
                Item->SetBoolField(TEXT("theme_bridge"),P.bThemeBridge);
                Item->SetBoolField(TEXT("combat"),Plan.Combat.Contains(P.Module));
                Item->SetArrayField(TEXT("origin"),JsonVector(P.Transform.GetLocation()));
                Item->SetNumberField(TEXT("yaw"),P.Transform.Rotator().Yaw);Item->SetArrayField(TEXT("scale"),JsonVector(P.Transform.GetScale3D()));
                TArray<TSharedPtr<FJsonValue>> Ports,Cells,Active;
                for(int32 Port:Plan.OpenPorts(I)){auto S=JsonSocket(Plan.Socket(I,Port));S->SetNumberField(TEXT("index"),Port);Ports.Add(MakeShared<FJsonValueObject>(S));}
                for(int32 Port:P.ActivePorts)Active.Add(MakeShared<FJsonValueNumber>(Port));
                for(const auto& C:P.Cells)
                {
                    auto Cell=MakeShared<FJsonObject>();Cell->SetArrayField(TEXT("min"),JsonVector(C.Min));Cell->SetArrayField(TEXT("max"),JsonVector(C.Max));
                    Cells.Add(MakeShared<FJsonValueObject>(Cell));
                }
                Item->SetArrayField(TEXT("ports"),Ports);Item->SetArrayField(TEXT("active_ports"),Active);Item->SetArrayField(TEXT("cells"),Cells);
                PiecesJson.Add(MakeShared<FJsonValueObject>(Item));
            }
            Report->SetArrayField(TEXT("pieces"),PiecesJson);
            TArray<TSharedPtr<FJsonValue>> ProbeJson;
            for(const auto& P:Plan.ProbePieces)
            {
                auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("module"),Plan.Modules[P.Module].Id);
                Item->SetStringField(TEXT("route"),P.Route);
                TArray<TSharedPtr<FJsonValue>> Cells;
                for(const auto& C:P.Cells)
                {
                    auto Cell=MakeShared<FJsonObject>();Cell->SetStringField(TEXT("min"),C.Min.ToString());Cell->SetStringField(TEXT("max"),C.Max.ToString());
                    Cells.Add(MakeShared<FJsonValueObject>(Cell));
                }
                Item->SetArrayField(TEXT("cells"),Cells);ProbeJson.Add(MakeShared<FJsonValueObject>(Item));
            }
            Report->SetArrayField(TEXT("probe_pieces"),ProbeJson);
            auto Rejects=MakeShared<FJsonObject>();
            for(const auto& Rejection:Plan.ProbeRejects)Rejects->SetNumberField(Rejection.Key,Rejection.Value);
            Report->SetObjectField(TEXT("probe_rejects"),Rejects);
            Report->SetStringField(TEXT("probe_lead"),Plan.ProbeLead.P.ToString());Report->SetStringField(TEXT("probe_top"),Plan.ProbeTop.P.ToString());
            Report->SetStringField(TEXT("probe_route"),Plan.ProbeRoute);
            FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&LastGenerationMetricsJson));
            LayoutDescription=LastGenerationMetricsJson; // Reflected, in-memory commandlet result; never saved.
            BuildState.Reset();return;
        }
#endif
        PrepareAssembly();PumpAssembly(true);
    }
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
        StagedLightModules[I].bConnector=Id==TEXT("Transit")||Id==TEXT("Threshold")||Id==TEXT("TreasureLink")||Id==TEXT("RouteElbow")||Id==TEXT("BossApproach")||Id==TEXT("StairDrop1080")||Plan.IsThemeRamp(Plan.Pieces[I].Module);
    }
    auto ConnectLights=[&](int32 From,int32 To,FVector Door)
    {
        const FVector Center=Door+FVector(0,0,180);
        const FVector Extent(200,200,180); // Encloses the authored door opening in either orientation.
        StagedLightModules[From].Portals.Add({To,Center,Extent});
        StagedLightModules[To].Portals.Add({From,Center,Extent});
    };
    const AuthoredDungeon::FSocket EntrySocket{Vec(Catalog,TEXT("start_position")),Vec(Catalog,TEXT("start_normal")),-1};
    const int32 EntryNode=Plan.EntryPiece(EntrySocket);
    if(EntryNode==INDEX_NONE){State->Error=TEXT("地牢入口没有匹配的实体接口");return;}
    ConnectLights(Plan.Pieces.Num(),EntryNode,EntrySocket.P);
    const auto ProgressionDepths=Plan.PieceDepths(EntryNode,Plan.PieceGraph(false));
    // Choose bounded visual recipes only after the socket plan is complete. The route RNG
    // and shared module data remain untouched; manifest and assembly use the same choices.
    TArray<JObject> SceneModules;
    TMap<FString,FString> PreviousSceneRecipes,PreviousSceneStates;
    for(int32 I=0;I<Plan.Pieces.Num();++I)
        SceneModules.Add(StationWorkshopAssembly::Compose(CargoWarehouseContainers::Compose(StaffLivingRoomAssembly::Compose(DungeonRoomScenes::Compose(Plan.Modules[Plan.Pieces[I].Module].Data,Seed,I,PreviousSceneRecipes,PreviousSceneStates),Seed,I),Seed,I),Seed,I));
    JObject Graph=MakeShared<FJsonObject>();Graph->SetNumberField(TEXT("seed"),Seed);
    Graph->SetStringField(TEXT("layout_solver"),Plan.LayoutSolver);
    Graph->SetNumberField(TEXT("generator_version"),Plan.bPairedFacility?9:Plan.bThemedRoutes?8:5);
    if(Plan.bThemedRoutes)
    {
        TArray<TSharedPtr<FJsonValue>> Themes;
        for(int32 R=1;R<=3;++R)
        {
            const FString Route=FString::Printf(TEXT("Route%d"),R);
            auto Theme=MakeShared<FJsonObject>();Theme->SetStringField(TEXT("route"),Route);
            Theme->SetStringField(TEXT("theme"),Plan.RouteThemes.FindRef(Route));
            TArray<TSharedPtr<FJsonValue>> Pair;
            for(const auto& Id:Plan.RouteThemePairs.FindChecked(Route))Pair.Add(MakeShared<FJsonValueString>(Id));
            Theme->SetArrayField(TEXT("themes"),Pair);
            TArray<TSharedPtr<FJsonValue>> Sequence;
            for(int32 M:Plan.ThemeSlots.FindChecked(Route))Sequence.Add(MakeShared<FJsonValueString>(M<0?TEXT("facility_transition"):Plan.Modules[M].Id));
            Theme->SetArrayField(TEXT("slots"),Sequence);Themes.Add(MakeShared<FJsonValueObject>(Theme));
        }
        Graph->SetArrayField(TEXT("themed_routes"),Themes);
        Graph->SetStringField(TEXT("boss_access"),TEXT("any_complete_route_then_archive"));
    }
    Graph->SetNumberField(TEXT("room_scene_version"),1);
    Graph->SetNumberField(TEXT("room_connection_version"),Plan.bThemedRoutes?6:4);
    Graph->SetNumberField(TEXT("entry_node"),EntryNode);
    Graph->SetStringField(TEXT("topology_recipe"),Plan.TopologyRecipe);
    Graph->SetNumberField(TEXT("loop_goal"),Plan.LoopGoal);
    Graph->SetNumberField(TEXT("loop_count"),Plan.LoopConnections.Num());
    Graph->SetNumberField(TEXT("mission_grammar_requested"),Plan.RequestedGrammar);
    Graph->SetNumberField(TEXT("mission_grammar_realized"),Plan.ActualGrammar);
    Graph->SetNumberField(TEXT("corridor_total_cm"),Plan.CorridorTotal);
    Graph->SetNumberField(TEXT("corridor_budget_cm"),Plan.CorridorBudget);
    Graph->SetNumberField(TEXT("route_span_estimate_cm"),Plan.LongestRouteEstimate);
    Graph->SetNumberField(TEXT("route_span_budget_cm"),Plan.RouteBudget);
    Graph->SetStringField(TEXT("route_budget_mode"),Plan.bThemedRoutes?TEXT("authored_walk_and_bounded_links"):TEXT("legacy_total_walk"));
    Graph->SetArrayField(TEXT("route_length_details"),Plan.MissionRouteLengthsJson());
    TArray<TSharedPtr<FJsonValue>> MissionEdges;
    for(const auto& Edge:Plan.MissionEdges)
    {
        JObject E=MakeShared<FJsonObject>();E->SetStringField(TEXT("from"),Edge.From);E->SetStringField(TEXT("to"),Edge.To);
        E->SetStringField(TEXT("purpose"),Edge.Purpose);E->SetBoolField(TEXT("optional"),Edge.bOptional);E->SetBoolField(TEXT("realized"),Edge.bRealized);
        MissionEdges.Add(MakeShared<FJsonValueObject>(E));
    }
    Graph->SetArrayField(TEXT("mission_edges"),MissionEdges);
    TArray<TSharedPtr<FJsonValue>> MissionNodes;TSet<FString> MissionIds;
    for(const auto& E:Plan.MissionEdges){MissionIds.Add(E.From);MissionIds.Add(E.To);}
    TArray<FString> OrderedMissionIds=MissionIds.Array();OrderedMissionIds.Sort();
    for(const FString& Id:OrderedMissionIds)
    {
        JObject Node=MakeShared<FJsonObject>();Node->SetStringField(TEXT("id"),Id);int32 PieceIndex=INDEX_NONE;
        for(int32 I=0;I<Plan.Pieces.Num();++I)if(Plan.Pieces[I].MissionId==Id){PieceIndex=I;break;}
        if(Id==TEXT("reward.final"))for(int32 I=0;I<Plan.Pieces.Num();++I)if(Plan.Pieces[I].Module==Plan.BossRoom){PieceIndex=I;break;}
        Node->SetNumberField(TEXT("piece"),PieceIndex);
        Node->SetStringField(TEXT("binding"),Id==TEXT("entry")?TEXT("start_room"):Id==TEXT("reward.final")?TEXT("boss_authored_reward_room"):TEXT("module"));
        MissionNodes.Add(MakeShared<FJsonValueObject>(Node));
    }
    Graph->SetArrayField(TEXT("mission_nodes"),MissionNodes);
    if(Plan.bCompactBoss)Graph->SetStringField(TEXT("compact_terminal_placement"),TEXT("completed_middle_branch"));
    Graph->SetNumberField(TEXT("room_connection_max_cm"),FPlan::ShortLinkLimit);
    Graph->SetNumberField(TEXT("room_connection_max_turns"),2);
    if(Plan.bThemedRoutes)
    {
        Graph->SetNumberField(TEXT("theme_bridge_max_cm"),Plan.ThemeBridgeLimit);
        Graph->SetNumberField(TEXT("theme_bridge_max_turns"),FPlan::ThemeBridgeMaxTurns);
        Graph->SetNumberField(TEXT("theme_ramp_connection_max_cm"),FPlan::ThemeRampLinkLimit);
        JObject Levels=MakeShared<FJsonObject>();
        for(const auto& Level:Plan.ThemeCoreLevels)Levels->SetNumberField(Level.Key,Level.Value);
        Graph->SetObjectField(TEXT("theme_core_elevations_cm"),Levels);
        Graph->SetStringField(TEXT("theme_bridge_placement"),TEXT("outside_fixed_cores"));
        Graph->SetStringField(TEXT("theme_bridge_encounters"),TEXT("reserved_for_future_authoring"));
    }
    Graph->SetNumberField(TEXT("boss_depth_cm"),Plan.bCompactBoss?Plan.BossDepth:0);
    TArray<TSharedPtr<FJsonValue>> WalkLengths;for(double Length:Plan.TerminalWalkLengths)WalkLengths.Add(MakeShared<FJsonValueNumber>(Length));
    Graph->SetArrayField(TEXT("terminal_walk_cm"),WalkLengths);
    TArray<TSharedPtr<FJsonValue>> Nodes,Edges;
    auto JsonVector=[](FVector V){return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};};
    for(int32 I=0;I<Plan.Pieces.Num();++I)
    {
        const auto& P=Plan.Pieces[I];JObject N=MakeShared<FJsonObject>();N->SetNumberField(TEXT("id"),I);N->SetStringField(TEXT("module"),Plan.Modules[P.Module].Id);N->SetStringField(TEXT("route"),P.Route);N->SetArrayField(TEXT("origin"),JsonVector(P.Transform.GetLocation()));N->SetNumberField(TEXT("yaw"),P.Transform.Rotator().Yaw);
        Nodes.Add(MakeShared<FJsonValueObject>(N));
        N->SetArrayField(TEXT("scale"),JsonVector(P.Transform.GetScale3D()));
        N->SetStringField(TEXT("mission_id"),P.MissionId);N->SetStringField(TEXT("encounter_role"),P.EncounterRole);
        if(P.bThemeBridge)
        {
            N->SetBoolField(TEXT("theme_bridge"),true);
            N->SetStringField(TEXT("connection_purpose"),TEXT("theme_route_join"));
        }
        if(Plan.IsThemeRamp(P.Module))
        {
            N->SetBoolField(TEXT("split_level_ramp"),true);
            N->SetStringField(TEXT("encounter_role"),TEXT("reserved_connector"));
            N->SetNumberField(TEXT("vertical_rise_cm"),FMath::Abs(Plan.Modules[P.Module].Ports[1].P.Z-Plan.Modules[P.Module].Ports[0].P.Z));
        }
        N->SetNumberField(TEXT("threat_bonus"),P.ThreatBonus);N->SetNumberField(TEXT("reward_multiplier"),P.RewardMultiplier);
        FString Recipe;Plan.Modules[P.Module].Data->TryGetStringField(TEXT("interior_recipe_id"),Recipe);N->SetStringField(TEXT("interior_recipe_id"),Recipe);
        FString SceneRecipe,SceneState;
        SceneModules[I]->TryGetStringField(TEXT("scene_recipe_id"),SceneRecipe);
        SceneModules[I]->TryGetStringField(TEXT("scene_state_id"),SceneState);
        N->SetStringField(TEXT("scene_recipe_id"),SceneRecipe);N->SetStringField(TEXT("scene_state_id"),SceneState);
        TArray<TSharedPtr<FJsonValue>> Open;for(int32 Port:Plan.OpenPorts(I))Open.Add(MakeShared<FJsonValueNumber>(Port));N->SetArrayField(TEXT("open_ports"),Open);
        N->SetNumberField(TEXT("floor"),FMath::RoundToInt((P.Transform.GetLocation().Z-Vec(Catalog,TEXT("start_position")).Z)/540.));
        N->SetArrayField(TEXT("volume_min"),JsonVector(P.Bounds.Min));N->SetArrayField(TEXT("volume_max"),JsonVector(P.Bounds.Max));
        N->SetNumberField(TEXT("progression_depth"),P.MissionDepth>=0?P.MissionDepth:ProgressionDepths[I]==MAX_int32?0:ProgressionDepths[I]);
        TArray<TSharedPtr<FJsonValue>> CellValues;
        for(const FBox& Cell:P.Cells)
        {
            JObject C=MakeShared<FJsonObject>();C->SetArrayField(TEXT("min"),JsonVector(Cell.Min));C->SetArrayField(TEXT("max"),JsonVector(Cell.Max));
            CellValues.Add(MakeShared<FJsonValueObject>(C));
        }
        N->SetArrayField(TEXT("cells"),CellValues);
        TArray<TSharedPtr<FJsonValue>> WalkCells;const TArray<TSharedPtr<FJsonValue>>* Mask=nullptr;
        if(Plan.Modules[P.Module].Data->TryGetArrayField(TEXT("walk_mask"),Mask))for(const auto& V:*Mask)
        {
            const auto Box=V->AsObject();FBox LocalBox(Vec(Box,TEXT("min")),Vec(Box,TEXT("max")));
            LocalBox.Max.Z=Plan.Modules[P.Module].Bounds.Max.Z;
            const FBox WorldBox=LocalBox.TransformBy(P.Transform);JObject Cell=MakeShared<FJsonObject>();
            Cell->SetArrayField(TEXT("min"),JsonVector(WorldBox.Min));Cell->SetArrayField(TEXT("max"),JsonVector(WorldBox.Max));
            WalkCells.Add(MakeShared<FJsonValueObject>(Cell));
        }
        N->SetArrayField(TEXT("walk_cells"),WalkCells);
        if(P.LinkTurns>=0){N->SetNumberField(TEXT("entry_link_turns"),P.LinkTurns);N->SetNumberField(TEXT("entry_link_cm"),P.LinkLength);}
        if(P.Side>=0)N->SetStringField(TEXT("side_socket"),Plan.Modules[P.Module].SideSockets[P.Side].Data->GetStringField(TEXT("id")));
        for(int32 J=0;J<I;++J)for(int32 A:Plan.OpenPorts(I))for(int32 B:Plan.OpenPorts(J))
        {
            const auto SA=Plan.Socket(I,A),SB=Plan.Socket(J,B);
            if(SA.P.Equals(SB.P,1)&&FVector::DotProduct(SA.N,SB.N)<-.99)
            {
                JObject E=MakeShared<FJsonObject>();E->SetNumberField(TEXT("from"),J);E->SetNumberField(TEXT("from_port"),B);E->SetNumberField(TEXT("to"),I);E->SetNumberField(TEXT("to_port"),A);Edges.Add(MakeShared<FJsonValueObject>(E));
                E->SetArrayField(TEXT("position"),JsonVector(SA.P));
                E->SetArrayField(TEXT("from_normal"),JsonVector(SB.N));E->SetArrayField(TEXT("to_normal"),JsonVector(SA.N));
                E->SetNumberField(TEXT("width"),SA.Width);E->SetNumberField(TEXT("height"),SA.Height);
                E->SetStringField(TEXT("kind"),P.Route.StartsWith(TEXT("Loop."))||Plan.Pieces[J].Route.StartsWith(TEXT("Loop."))?TEXT("loop"):TEXT("main"));
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
        if(State->bRuntime)State->ResourcePaths.Add(Path);
        else State->Jobs.Add({TEXT("Dungeon.Resources"),[this,Path](){ResolveGenerationAsset(Path);}});
    };
    // The fixed shrine uses a separate gameplay stream after the layout commits.
    // Preload its pool in the normal budgeted resource stage, never on interaction.
    const TSharedPtr<FJsonObject>* Shrine=nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Statues=nullptr;
    if(Catalog->TryGetObjectField(TEXT("start_shrine"),Shrine)&&(*Shrine)->TryGetArrayField(TEXT("statues"),Statues))
        for(const auto& Statue:*Statues)QueueAsset(Statue->AsObject()->GetStringField(TEXT("mesh")));
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
        const FPlaced& Piece=Plan.Pieces[Index];const JObject D=SceneModules[Index];
        TArray<TSharedPtr<FJsonValue>> Parts=D->GetArrayField(TEXT("parts"));
        if(Piece.Side>=0)
        {
            const auto& Side=Plan.Modules[Piece.Module].SideSockets[Piece.Side].Data;
            const auto& Remove=Side->GetArrayField(TEXT("replace_suffixes"));
            Parts.RemoveAll([&](const TSharedPtr<FJsonValue>& V){const FString Path=V->AsObject()->GetStringField(TEXT("mesh"));for(const auto& S:Remove)if(Path.EndsWith(S->AsString()))return true;return false;});
            Parts.Append(Side->GetArrayField(TEXT("parts")));
        }
        const TArray<TSharedPtr<FJsonValue>>* Closures=nullptr;
        if(D->TryGetArrayField(TEXT("closed_port_parts"),Closures))for(const auto& V:*Closures)
        {const auto C=V->AsObject();if(!Plan.OpenPorts(Index).Contains(int32(C->GetNumberField(TEXT("port_index")))))Parts.Append(C->GetArrayField(TEXT("parts")));}
        if(bDressRooms) Parts.Append(DungeonDressing::Build(D,Seed,Index));
        Parts.Append(DungeonWallArt::Build(D,Seed,Index));
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
            State->Jobs.Add({Stage,[this,State,Part,Piece,Index,Params,bOptimizeLights,Key,Dressing,bDressRooms,D]()
            {
            auto* Mesh=Cast<UStaticMesh>(ResolveGenerationAsset(Part->GetStringField(TEXT("mesh"))));
            if(!Mesh){State->Error=TEXT("地牢网格无法载入：")+Part->GetStringField(TEXT("mesh"));return;}
            FTransform T=Local(Part)*Piece.Transform;
            const bool Hazard=Part->HasField(TEXT("half_size")),Fluid=Part->GetBoolField(TEXT("fluid"));
            if(Dressing)
            {
                ++State->DressingCandidates;FString Reason;
                if(!State->DressingScene.Place(Mesh,Part,D,Piece.Transform,Index,T,Reason))
                {++State->DressingSkipped;++State->DressingRejections.FindOrAdd(Reason);return;}
            }
            else if(bDressRooms)
            {
                if(Fluid || Hazard) State->DressingScene.FixedBoxes.Add(Mesh->GetBoundingBox().TransformBy(T).ExpandBy(5));
                else State->DressingScene.AddMesh(Mesh,T,Index,Part->GetStringField(TEXT("mesh")));
            }
            bool bGuardrailDrop=false;Part->TryGetBoolField(TEXT("guardrail_drop"),bGuardrailDrop);
            bool bAuthoredInstance=false;Part->TryGetBoolField(TEXT("instanced"),bAuthoredInstance);
            const bool bInstance=!Dressing&&!Fluid&&!Hazard&&!Part->HasField(TEXT("ward_frame"))&&!Part->HasField(TEXT("blood_receiver"))&&!bGuardrailDrop&&DungeonInstancing.GetValueOnGameThread()!=0&&(Mesh->HasValidNaniteData()||bAuthoredInstance)
                &&State->InstanceCandidates.FindRef(Key)>1;
            if(bInstance)
            {
                if(auto* Existing=State->InstanceGroups.FindRef(Key).Get())
                {
                    Existing->AddInstance(T,true);
                    Existing->ComponentTags.AddUnique(FName(*FString::Printf(TEXT("DungeonModule.%d.%s"),Index,*State->Plan.Modules[Piece.Module].Id)));
                    if(const int32* Group=State->RenderGroupByComponent.Find(Existing))
                        State->NextRenderGroups[*Group].Modules.AddUnique(Index);
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
            if(bGuardrailDrop)A->Tags.Add(TEXT("Traversal.GuardrailDrop"));
            FString WardFrame;
            if(Part->TryGetStringField(TEXT("ward_frame"),WardFrame))
                A->Tags.Add(FName(*FString::Printf(TEXT("WardFrame.%d.%s"),Index,*WardFrame)));
            if(Part->HasField(TEXT("blood_receiver")))
                A->Tags.Add(FName(*FString::Printf(TEXT("WardBlood.%d"),Index)));
            if(Part->HasField(TEXT("wall_art")))
            {A->Tags.Add(TEXT("DungeonWallArt"));C->SetReceivesDecals(false);}
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
            Part->TryGetBoolField(TEXT("cast_shadow"),CastShadow);
            if(Part->HasField(TEXT("wall_art")))CastShadow=false;
            C->SetCollisionProfileName(Part->GetBoolField(TEXT("collision"))?TEXT("BlockAll"):TEXT("NoCollision"));C->SetCastShadow(CastShadow);
            double PartDrawDistance=0;
            if(Part->TryGetNumberField(TEXT("max_draw_distance_cm"),PartDrawDistance)&&PartDrawDistance>0)
            {
                if(auto* Instances=Cast<UInstancedStaticMeshComponent>(C))Instances->SetCullDistances(0,FMath::RoundToInt(PartDrawDistance));
                else C->SetCullDistance(PartDrawDistance);
            }
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
            bool bRoomCull=!Fluid&&!Hazard&&!Part->HasField(TEXT("ward_frame"))&&!Part->HasField(TEXT("blood_receiver"));
            bool bAllowRoomCull=true;Part->TryGetBoolField(TEXT("room_render_culling"),bAllowRoomCull);
            if(bRoomCull&&bAllowRoomCull)
            {
                const int32 Group=State->NextRenderGroups.AddDefaulted();
                State->NextRenderGroups[Group].Component=C;
                State->NextRenderGroups[Group].Modules.Add(Index);
                State->RenderGroupByComponent.Add(C,Group);
            }
            if(auto* WaterFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())WaterFX->RegisterWaterSurface(C);
            ++State->Parts;
            }});
        }
        const JObject* ProgressGate=nullptr;
        if(D->TryGetObjectField(TEXT("progression_gate"),ProgressGate))
        {
            const JObject Spec=*ProgressGate;const FString MeshPath=Spec->GetStringField(TEXT("mesh"));QueueAsset(MeshPath);
            State->Jobs.Add({TEXT("Dungeon.ProgressionGate"),[this,State,Spec,Piece,Index,MeshPath]()
            {
                UStaticMesh* Mesh=Cast<UStaticMesh>(ResolveGenerationAsset(MeshPath));
                if(!Mesh){State->Error=TEXT("推进闸门缺少模型：")+MeshPath;return;}
                const FTransform Local(FRotator(0,Spec->GetNumberField(TEXT("yaw")),0),Vec(Spec,TEXT("position")),Vec(Spec,TEXT("scale")));
                auto* Gate=GetWorld()->SpawnActorDeferred<ADungeonProgressionGate>(ADungeonProgressionGate::StaticClass(),Local*Piece.Transform,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                if(!Gate){State->Error=TEXT("推进闸门创建失败");return;}
                Gate->Configure(Mesh,Index,Spec->GetBoolField(TEXT("any_route")),Vec(Spec,TEXT("clear_size")),Vec(Spec,TEXT("travel")));
                Gate->FinishSpawning(Local*Piece.Transform);OwnGenerated(Gate,Index);
            }});
        }
        const TArray<TSharedPtr<FJsonValue>>* WardAssets=nullptr;
        if(D->TryGetArrayField(TEXT("runtime_assets"),WardAssets))
            for(const auto& V:*WardAssets)QueueAsset(V->AsString());
        const TArray<TSharedPtr<FJsonValue>>* WardActors=nullptr;
        if(D->TryGetArrayField(TEXT("runtime_actors"),WardActors))for(int32 WI=0;WI<WardActors->Num();++WI)
        {
            const JObject Spec=(*WardActors)[WI]->AsObject();
            // Queue every asset-valued field in the selected runtime specification,
            // including panes, debris, audio and standalone door leaves.
            TFunction<void(const TSharedPtr<FJsonValue>&)> QueueSpecAssets;
            QueueSpecAssets=[&](const TSharedPtr<FJsonValue>& Value)
            {
                if(Value->Type==EJson::String)
                {
                    const FString Path=Value->AsString();
                    if(Path.StartsWith(TEXT("/Game/"))||Path.StartsWith(TEXT("/Engine/"))||Path.StartsWith(TEXT("/Script/")))QueueAsset(Path);
                }
                else if(Value->Type==EJson::Array)for(const auto& Child:Value->AsArray())QueueSpecAssets(Child);
                else if(Value->Type==EJson::Object)for(const auto& Child:Value->AsObject()->Values)QueueSpecAssets(Child.Value);
            };
            for(const auto& Field:Spec->Values)QueueSpecAssets(Field.Value);
            if(Spec->GetStringField(TEXT("type"))==TEXT("scene_container"))
            {
                QueueAsset(Spec->GetStringField(TEXT("body")));
                QueueAsset(Spec->GetStringField(TEXT("door")));
                for(const TCHAR* Key:{TEXT("body_materials"),TEXT("door_materials")})
                {
                    const TArray<TSharedPtr<FJsonValue>>* Materials=nullptr;
                    if(Spec->TryGetArrayField(Key,Materials))for(const auto& Material:*Materials)QueueAsset(Material->AsString());
                }
            }
            auto Spawned=MakeShared<TWeakObjectPtr<AActor>>();
            State->Jobs.Add({TEXT("Dungeon.WardActors"),[this,State,Spec,Piece,Index,Spawned]()
            {
                AActor* Frame=nullptr;FString FrameId;
                if(Spec->TryGetStringField(TEXT("frame_id"),FrameId))
                {
                    const FName Tag(*FString::Printf(TEXT("WardFrame.%d.%s"),Index,*FrameId));
                    for(const auto& Candidate:GeneratedActors)if(IsValid(Candidate)&&Candidate->ActorHasTag(Tag)){Frame=Candidate;break;}
                    if(!Frame){State->Error=TEXT("病区玻璃门缺少共用门框");return;}
                }
                AActor* Actor=WardRoomAssembly::Spawn(GetWorld(),this,Spec,Piece.Transform,Frame,
                    FName(*FString::Printf(TEXT("WardBlood.%d"),Index)),
                    [this](const FString& Path){return ResolveGenerationAsset(Path);});
                if(!Actor){State->Error=TEXT("病区交互组件创建失败");return;}
                OwnGenerated(Actor,Index);*Spawned=Actor;
            }});
            const FString Type=Spec->GetStringField(TEXT("type"));
            if(Type==TEXT("beds")||Type==TEXT("blood"))
            {
                const int32 ScatterSeed=int32(HashCombineFast(uint32(Seed)^0x57415244u,HashCombineFast(uint32(Index),uint32(WI))));
                const bool bFurniture=Type==TEXT("beds");
                State->Jobs.Add({Type==TEXT("beds")?FName(TEXT("Dungeon.WardFurniture")):FName(TEXT("Dungeon.WardBlood")),
                    [State,Spawned,ScatterSeed,bFurniture]()
                    {
                        if(AActor* Actor=Spawned->Get())
                        {
                            WardRoomAssembly::Populate(Actor,ScatterSeed);
                            // This actor's initial physics pass preceded scattering.
                            // Process its populated components before the next job.
                            if(bFurniture)State->PhysicsRefreshActor=Actor;
                        }
                    }});
            }
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
            const FVector ChestLocal=Vec(Prop,TEXT("position"));
            FString ChestRole=TEXT("chest");Prop->TryGetStringField(TEXT("role"),ChestRole);
            const FString ChestRoom=Piece.MissionId.IsEmpty()?FString::Printf(TEXT("Node%d"),Index):Piece.MissionId;
            A->Tags.Add(FName(*FString::Printf(TEXT("DungeonChestClaim.%s.%s.%d.%d.%d"),*ChestRoom,
                *ChestRole,FMath::RoundToInt(ChestLocal.X),FMath::RoundToInt(ChestLocal.Y),FMath::RoundToInt(ChestLocal.Z))));
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
            FString FunctionPath;if(L->TryGetStringField(TEXT("light_function"),FunctionPath))QueueAsset(FunctionPath);
            const bool Corridor=Plan.Modules[Piece.Module].Id==TEXT("Transit");
            const bool BossHall=Plan.Modules[Piece.Module].Id==TEXT("BossPumpHall");
            FString LightRole=Corridor?TEXT("corridor"):Brightest.Find(LightIndex)<2?TEXT("key"):TEXT("fill");
            L->TryGetStringField(TEXT("role"),LightRole);
            State->Jobs.Add({TEXT("Dungeon.Lights"),[this,State,L,Piece,Index,Params,bOptimizeLights,Corridor,BossHall,LightRole]()
            {
            const bool Fill=LightRole==TEXT("fill");
            FString Type=(Fill||Corridor)?TEXT("spot"):TEXT("point");L->TryGetStringField(TEXT("type"),Type);
            const bool Spot=bOptimizeLights&&Type==TEXT("spot");
            const bool Rect=Type==TEXT("rect");
            double Outer=Corridor?80.0:65.0;L->TryGetNumberField(TEXT("outer_cone_degrees"),Outer);Outer=FMath::Clamp(Outer,10.0,85.0);
            const FVector Position=Piece.Transform.TransformPosition(Vec(L,TEXT("position")));
            ALight* A=nullptr;
            if(Rect)
            {
                double Pitch=-90,Yaw=0,Roll=0;
                L->TryGetNumberField(TEXT("pitch"),Pitch);L->TryGetNumberField(TEXT("yaw"),Yaw);L->TryGetNumberField(TEXT("roll"),Roll);
                A=GetWorld()->SpawnActor<ARectLight>(Position,Piece.Transform.TransformRotation(FQuat(FRotator(Pitch,Yaw,Roll))).Rotator(),Params);
            }
            else if(Spot)A=GetWorld()->SpawnActor<ASpotLight>(Position,FRotator(-90,0,0),Params);
            else A=GetWorld()->SpawnActor<APointLight>(Position,FRotator::ZeroRotator,Params);
            if(!A){State->Error=TEXT("地牢灯光创建失败");return;}
            OwnGenerated(A,Index);A->Tags.Add(FName(*(TEXT("DungeonLight.")+(bOptimizeLights?LightRole:TEXT("legacy")))));
            auto* C=CastChecked<ULocalLightComponent>(A->GetLightComponent());C->SetMobility(EComponentMobility::Movable);C->SetIntensityUnits(ELightUnits::Lumens);
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
            FString FunctionPath;
            if(L->TryGetStringField(TEXT("light_function"),FunctionPath))
            {
                C->SetLightFunctionMaterial(Cast<UMaterialInterface>(ResolveGenerationAsset(FunctionPath)));
                C->LightFunctionFadeDistance=2700.f;C->DisabledBrightness=1.f;
            }
            const FVector Color=Vec(L,TEXT("color"));C->SetLightColor(FLinearColor(Color.X,Color.Y,Color.Z));
            C->SetCastShadows(Shadows);
            double AuthoredValue=0;
            if(auto* Point=Cast<UPointLightComponent>(C))
            {
                Point->SetSourceRadius(BossHall?2:5);Point->SetSourceLength(Spot?0:60);
                if(L->TryGetNumberField(TEXT("source_radius"),AuthoredValue))Point->SetSourceRadius(AuthoredValue);
                if(L->TryGetNumberField(TEXT("source_length"),AuthoredValue))Point->SetSourceLength(AuthoredValue);
            }
            if(auto* Area=Cast<URectLightComponent>(C))
            {
                if(L->TryGetNumberField(TEXT("source_width_cm"),AuthoredValue))Area->SetSourceWidth(AuthoredValue);
                if(L->TryGetNumberField(TEXT("source_height_cm"),AuthoredValue))Area->SetSourceHeight(AuthoredValue);
            }
            if(L->TryGetNumberField(TEXT("indirect_lighting_intensity"),AuthoredValue))C->SetIndirectLightingIntensity(AuthoredValue);
            if(L->TryGetNumberField(TEXT("volumetric_scattering_intensity"),AuthoredValue))C->SetVolumetricScatteringIntensity(AuthoredValue);
            if(L->TryGetNumberField(TEXT("light_function_fade_distance"),AuthoredValue))C->LightFunctionFadeDistance=AuthoredValue;
            if(L->TryGetNumberField(TEXT("disabled_brightness"),AuthoredValue))C->DisabledBrightness=AuthoredValue;
            if(!Rect&&L->TryGetNumberField(TEXT("yaw"),AuthoredValue))A->SetActorRotation(Piece.Transform.TransformRotation(FQuat(FRotator(0,AuthoredValue,0))));
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
    State->PendingDescription=FString::Printf(TEXT("Seed %d | V5 grammar %d | %s | approach %d rooms | branches %d / %d / %d rooms | loops %d/%d | %d modules | treasure %d"),Seed,Plan.ActualGrammar,*Plan.TopologyRecipe,Plan.Counts[0],Plan.Counts[1],Plan.Counts[2],Plan.Counts[3],Plan.LoopConnections.Num(),Plan.LoopGoal,Plan.Pieces.Num(),Plan.TreasureCount);
    if(State->bRuntime)
    {
        // Keep the start corridor clear. Return travel belongs to the final reward exit.
        // 刷怪导演：随布局装配一次（job 队列天然单次），Configure 只缓存指针；
        // 武装（Activate）在导航构建完成的收尾批执行。编辑器预览路径零怪物。
        State->Jobs.Add({TEXT("Dungeon.SpawnDirector"),[this,State]()
        {
            FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Director=GetWorld()->SpawnActor<ADungeonSpawnDirector>(ADungeonSpawnDirector::StaticClass(),GetActorTransform(),Spawn);
            if(!Director){State->Error=TEXT("地牢刷怪导演创建失败");return;}
            OwnGenerated(Director,-1);Director->Configure(this);
        }});
    }
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
            if(Stage==TEXT("Dungeon.WardFurniture"))return 7;
            if(Stage==TEXT("Dungeon.WardBlood"))return 8;
            return 4;
        };
        return Rank(A.Stage)<Rank(B.Stage);
    });
    State->PhaseMs.Add(TEXT("Dungeon.PrepareJobs"),(FPlatformTime::Seconds()-PrepareStarted)*1000.);
}

void AAuthoredDungeonGenerator::OwnGenerated(AActor* Actor,int32 ModuleIndex)
{
    Actor->SetActorHiddenInGame(true);Actor->SetActorEnableCollision(false);
    GeneratedActors.Add(Actor);Actor->Tags.Add(TEXT("DungeonRouteGenerated"));
    if(!BuildState->Plan.Pieces.IsValidIndex(ModuleIndex))
    {
        Actor->Tags.Add(TEXT("Start"));
#if WITH_EDITOR
        Actor->SetActorLabel(FString::Printf(TEXT("DGN_G_Start_%s"),*Actor->GetClass()->GetName()));
        Actor->SetFolderPath(TEXT("DungeonRoutes/Start"));
#endif
        return;
    }
    const auto& Piece=BuildState->Plan.Pieces[ModuleIndex];
    Actor->Tags.Add(FName(*Piece.Route));
    if(!Piece.MissionId.IsEmpty())Actor->Tags.Add(FName(*(TEXT("DungeonMission.")+Piece.MissionId)));
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
    // Runtime assembly never turns an unqueued dependency into a blocking load.
    UObject* Asset=BuildState->bRuntime?GenerationAssetPath(Path).ResolveObject():LoadObject<UObject>(nullptr,*Path);
    BuildState->Assets.Add(Path,Asset);++BuildState->AssetResolutions;
    if(Asset)GenerationResources.Add(Asset);
    else BuildState->Error=TEXT("地牢资源无法载入：")+Path;
    return Asset;
}

bool AAuthoredDungeonGenerator::PumpGenerationResources()
{
    auto& State=*BuildState;
    if(!State.bRuntime||State.ResourcesCompleted==State.ResourcePaths.Num())return true;
    DungeonPerformance::FScope Scope(this,TEXT("Dungeon.Resources"));
    const double Begin=FPlatformTime::Seconds();
    const double Budget=FMath::Clamp(double(DungeonBuildBudget.GetValueOnGameThread()),.25,16.)/1000.;
    // Poll bounded handles; no callback can retain a canceled generation or write
    // into a newer run. UObject adoption and component creation stay on the game thread.
    for(int32 I=State.ResourceBatches.Num()-1;I>=0;--I)
    {
        auto& Batch=State.ResourceBatches[I];
        if(Batch.Handle->WasCanceled())
        {State.Error=TEXT("地牢资源加载已取消");break;}
        if(!Batch.Handle->HasLoadCompleted())
        {
            if(FPlatformTime::Seconds()-Batch.StartedAt>120.)
                State.Error=TEXT("地牢资源加载超时：")+Batch.Paths[0];
            continue;
        }
        for(const FString& Path:Batch.Paths)
        {
            if(!ResolveGenerationAsset(Path))break;
            ++State.ResourcesCompleted;
        }
        Batch.Handle->ReleaseHandle();
        State.ResourceBatches.RemoveAtSwap(I);
        if(!State.Error.IsEmpty()||FPlatformTime::Seconds()-Begin>=Budget)break;
    }
    constexpr int32 BatchSize=32,MaxInFlight=2;
    while(State.Error.IsEmpty()&&State.ResourceCursor<State.ResourcePaths.Num()
        &&State.ResourceBatches.Num()<MaxInFlight&&FPlatformTime::Seconds()-Begin<Budget)
    {
        FAuthoredDungeonBuildState::FResourceBatch Batch;
        FStreamableAsyncLoadParams Params;
        for(int32 I=0;I<BatchSize&&State.ResourceCursor<State.ResourcePaths.Num();++I)
        {
            const FString& Path=State.ResourcePaths[State.ResourceCursor++];
            Batch.Paths.Add(Path);Params.TargetsToStream.Add(GenerationAssetPath(Path));
        }
        Params.bUseJustInTimeAsyncLoader=true;
        Batch.StartedAt=FPlatformTime::Seconds();
        Batch.Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(MoveTemp(Params),TEXT("Dungeon.SelectedRun"));
        if(!Batch.Handle)
        {State.Error=TEXT("地牢资源请求失败：")+Batch.Paths[0];break;}
        State.ResourceBatches.Add(MoveTemp(Batch));
    }
    State.PhaseMs.FindOrAdd(TEXT("Dungeon.Resources"))+=(FPlatformTime::Seconds()-Begin)*1000.;
    const bool bReady=State.ResourcesCompleted==State.ResourcePaths.Num();
    if(!bReady&&State.Error.IsEmpty())
        if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(
            FText::FromString(FString::Printf(TEXT("正在异步载入地牢资源（%d/%d）…"),State.ResourcesCompleted,State.ResourcePaths.Num())),
            .1f+.12f*float(State.ResourcesCompleted)/FMath::Max(1,State.ResourcePaths.Num()));
    return bReady||!State.Error.IsEmpty();
}

void AAuthoredDungeonGenerator::CancelGenerationResources()
{
    if(!BuildState)return;
    for(auto& Batch:BuildState->ResourceBatches)
        if(Batch.Handle)Batch.Handle->CancelHandle();
    BuildState->ResourceBatches.Reset();
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
    if(BuildState->bPlanning)
    {
        if(auto* Loading=DungeonLoading(this))
        {
            const int32 Attempt=FMath::Max(0,BuildState->SearchAttempt.Load());
            const int32 Limit=FMath::Max(1,BuildState->SearchAttemptLimit.Load());
            Loading->UpdatePreparation(
                FText::FromString(FString::Printf(TEXT("正在规划房间与通路（%d/%d）…"),Attempt,Limit)),
                .02f+.08f*float(Attempt)/float(Limit));
        }
        return;
    }
    PumpAssembly(false);
}

void AAuthoredDungeonGenerator::PumpAssembly(bool bSynchronous)
{
    if(!BuildState||BuildState->bPlanning)return;
    auto* State=BuildState.Get();
    if(State->Error.IsEmpty()&&!PumpGenerationResources())return;
    const int32 InitialJobCursor=State->Cursor,InitialPhysicsCursor=State->PhysicsActorCursor;
    const bool bInitialPhysicsRefresh=State->PhysicsRefreshActor.IsValid();
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
            if(State->bStaging&&(State->PhysicsRefreshActor.IsValid()||State->PhysicsActorCursor<GeneratedActors.Num()))
            {
                const double PhysicsStart=FPlatformTime::Seconds();
                bool bPendingPhysics=false;
                const bool bRefreshing=State->PhysicsRefreshActor.IsValid();
                {
                    DungeonPerformance::FScope PhysicsScope(this,TEXT("Dungeon.PhysicsActivation"));
                    AActor* Actor=bRefreshing?State->PhysicsRefreshActor.Get():GeneratedActors[State->PhysicsActorCursor].Get();
                    if(IsValid(Actor))
                    {
                        Actor->SetActorEnableCollision(true);
                        TInlineComponentArray<UPrimitiveComponent*> Primitives(Actor);
                        for(UPrimitiveComponent* Primitive:Primitives)
                        {
                            if(!Primitive->IsRegistered()||!Primitive->IsCollisionEnabled())continue;
                            if(Primitive->IsAsyncCreatePhysicsStateRunning()){bPendingPhysics=true;continue;}
                            // Empty scatter components are valid before Populate (and
                            // after a zero-result draw); there is no body to create yet.
                            // Populated ISMs and all ordinary colliders remain required.
                            if(const auto* Instances=Cast<UInstancedStaticMeshComponent>(Primitive);
                               Instances&&Instances->GetInstanceCount()==0)continue;
                            // Registration while OwnGenerated has actor collision disabled
                            // can skip body creation. Enabling only updates existing filters.
                            if(!Primitive->IsPhysicsStateCreated())
                            {
                                Primitive->CreatePhysicsState(false);
                                if(Primitive->IsAsyncCreatePhysicsStateRunning()){bPendingPhysics=true;continue;}
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
                if(bRefreshing)State->PhysicsRefreshActor.Reset();else ++State->PhysicsActorCursor;
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
        CancelGenerationResources();
        RollbackAssembly();Tags.AddUnique(TEXT("DungeonAssembly.Failed"));
        State->FinishedAt=FPlatformTime::Seconds();SetActorTickEnabled(false);
        UE_LOG(LogTemp,Error,TEXT("AuthoredDungeon: %s"),*State->Error);
        if(auto* Loading=DungeonLoading(this))Loading->FailPreparation(FText::FromString(State->Error+TEXT("；可取消并返回主场景。")));
        return;
    }
    if(State->Cursor>=State->Jobs.Num()&&State->PhysicsActorCursor>=GeneratedActors.Num()&&!State->PhysicsRefreshActor.IsValid())
    {
        // Give commit its own frame budget instead of adding it to the final build slice.
        if(!bSynchronous&&(State->Cursor!=InitialJobCursor||State->PhysicsActorCursor!=InitialPhysicsCursor||bInitialPhysicsRefresh))
        {
            if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(FText::FromString(TEXT("正在切换至新的地牢布局…")),.88f);
            return;
        }
        FinishAssembly(bSynchronous);return;
    }
    if(auto* Loading=DungeonLoading(this))Loading->UpdatePreparation(State->LoadingStatus,
        .22f+.66f*float(State->Cursor)/FMath::Max(1,State->Jobs.Num()));
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
        RenderGroups=MoveTemp(State->NextRenderGroups);
        RoomHideCursor=0;
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
    // 运行状态服务：绑定新布局（解析清单/目录、建图、重置档案运行态）。必须先于导演武装。
    if(State->bRuntime)
        if(auto* Runs=UDungeonRunSubsystem::Get(GetWorld()))Runs->BindCompletedDungeon(this);
    Tags.AddUnique(TEXT("DungeonAssembly.Ready"));Tags.Remove(TEXT("DungeonAssembly.Failed"));
    BuildState->bCompleted=true;BuildState->FinishedAt=FPlatformTime::Seconds();
    RecordFinalize();
    LastGenerationMetricsJson=GetGenerationMetricsJson();
    DungeonPerformance::FMarker::Record(this,TEXT("Dungeon.Ready"),LayoutDescription);
    UE_LOG(LogTemp,Display,TEXT("AuthoredDungeon: %s; %d instances in %d groups; CPU preparation %s"),
        *LayoutDescription,BuildState->Instances,BuildState->InstanceComponents,*LastGenerationMetricsJson);
    // Preserve this run's delayed shrine/animation dependencies; the unused catalog
    // stays soft. Retire the previous run's cache only after successful commit.
    GenerationResources.Reset();
    for(const auto& Asset:State->Assets)if(Asset.Value)GenerationResources.Add(Asset.Value);
    BuildState.Reset();SetActorTickEnabled(false);
    GeneratedActors.RemoveAll([](const TObjectPtr<AActor>& Actor){return !IsValid(Actor);});
    for(AActor* Actor:GeneratedActors)if(auto* Hazard=Cast<ADungeonPusChannel>(Actor))Hazard->ActivateDamage();
    for(AActor* Actor:GeneratedActors)if(auto* Encounter=Cast<ADungeonBossEncounter>(Actor))Encounter->ActivateEncounter();
    for(AActor* Actor:GeneratedActors)if(auto* Director=Cast<ADungeonSpawnDirector>(Actor))Director->Activate();
    StartRoomLighting();ReleasePlayers();
    if(auto* Loading=DungeonLoading(this))
    {
        Loading->CompletePreparation();
        Loading->ReleaseToGameplay();
    }
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
    if(BuildState)BuildState->CancelRequested.Store(true);
    CancelGenerationResources();
    ++GenerationSerial;RollbackAssembly();
    if(BuildState&&!BuildState->bCommitted)GenerationResources.SetNum(FMath::Min(GenerationResources.Num(),BuildState->PreviousResourceCount));
    BuildState.Reset();SetActorTickEnabled(false);ReleasePlayers();
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
    Report->SetNumberField(TEXT("async_assets_requested"),S.ResourcePaths.Num());
    Report->SetNumberField(TEXT("async_assets_completed"),S.ResourcesCompleted);
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
