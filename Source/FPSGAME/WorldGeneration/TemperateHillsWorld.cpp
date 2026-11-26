#include "TemperateHillsWorld.h"
#include "VillageMechanicalWorkshop.h"
#include "TemperateHillsMap.h"
#include "Algo/Compare.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Net/UnrealNetwork.h" // M4: DOREPLIFETIME
#include "TemperateHillsSurface.h"
#include "TemperateHillsVisibility.h"
#include "TemperateForestHabitat.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Engine/GameInstance.h"
#include "PCGComponent.h"
#include "PCGManagedResource.h"
#include "PCGGraph.h"
#include "PCGWorldActor.h"
#include "Subsystems/PCGSubsystem.h"
#include "RuntimeGen/SchedulingPolicies/PCGSchedulingPolicyDistanceAndDirection.h"
#include "Components/BoxComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/ConfigCacheIni.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateVegetationPlacement.h"
#include "../UI/ColdSteelStatusModel.h"

#include "TemperateHillsMathPrivate.h"
namespace TemperateHills
{
uint32 Mix(uint32 V) { V ^= V >> 16; V *= 0x7feb352dU; V ^= V >> 15; V *= 0x846ca68bU; return V ^ (V >> 16); }
uint32 Key(int32 X, int32 Y, uint32 Seed, uint32 Salt) { return Mix(Mix(uint32(X)*0x9e3779b9U) ^ Mix(uint32(Y)*0x85ebca6bU+0x1b873593U) ^ Mix(Seed+Salt)); }
uint64 CellId(int32 X,int32 Y) { return (uint64(uint32(X))<<32)|uint32(Y); }
double Unit(uint32 V) { return double(Mix(V) & 0x00ffffffU) / 16777216.0; }
double Smooth(double T) { T=FMath::Clamp(T,0.0,1.0); return T*T*(3-2*T); }
double ValleyY(double X, int32 Seed) { return 1900*FMath::Sin(X*.000065+Unit(Seed)*3)+850*FMath::Sin(X*.00014); } // Keep in sync with TemperateHillsSurface::ValleyY.
}

ATemperateHillsWorld::ATemperateHillsWorld()
{
    PrimaryActorTick.bCanEverTick=true;
    bReplicates=true; // M4：会话(种子/编辑)复制给客户端做确定性重建
    bAlwaysRelevant=true; // One session actor serves the entire kilometre-wide map.
    GenerationBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("WorldBounds"));
    RootComponent=GenerationBounds;
    GenerationBounds->SetMobility(EComponentMobility::Static);
    GenerationBounds->SetBoxExtent(FVector(51200,51200,50000));
    GenerationBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GenerationBounds->SetCanEverAffectNavigation(false);
    for(int32 Layer=0;Layer<4;++Layer)
    {
        auto* C=CreateDefaultSubobject<UPCGComponent>(*FString::Printf(TEXT("PCGLayer%d"),Layer));
        C->GenerationTrigger=EPCGComponentGenerationTrigger::GenerateAtRuntime;
        C->bIsComponentPartitioned=true;
        C->bOverrideGenerationRadii=true;
        C->SetSchedulingPolicyClass(UPCGSchedulingPolicyDistanceAndDirection::StaticClass());
        PCGLayers.Add(C);
    }
}

void ATemperateHillsWorld::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
#if WITH_EDITOR
    if(GetWorld()&&!GetWorld()->IsGameWorld())
        if(auto* Sub=GetWorld()->GetSubsystem<UPCGSubsystem>())Sub->GetPCGWorldActor();
#endif
}

void ATemperateHillsWorld::ResolveSession()
{
    bAudit=FParse::Param(FCommandLine::Get(),TEXT("HillsAudit"));
    bNullAudit=FParse::Param(FCommandLine::Get(),TEXT("nullrhi"));
    FString Label=TEXT("initial");
    FParse::Value(FCommandLine::Get(),TEXT("HillsLabel="),Label);
    AuditDir=FPaths::ProjectSavedDir()/TEXT("TemperateHills")/Label;
    Slot=bAudit?TEXT("TemperateHills_Audit"):TEXT("TemperateHills_World");
#if !UE_BUILD_SHIPPING
    // Portal regression needs real hills travel without touching the player's world save.
    if(FParse::Param(FCommandLine::Get(),TEXT("GrassPortalAudit")))Slot=TEXT("TemperateHills_GrassPortalAudit");
    if(FParse::Param(FCommandLine::Get(),TEXT("ChapelReview")))Slot=TEXT("TemperateHills_ChapelReview");
#endif
    if(IsForestVillage()) Slot=bAudit?TEXT("ForestPathVillage_Audit"):TEXT("ForestPathVillage_World");
    int32 Requested=TemperateHillsMap::Seed;
    int32 RequestedGen=TemperateHillsMap::GeneratorVersion;
    const bool ContinueWorld=GetWorld()->URL.HasOption(TEXT("HillsContinue"));
    bool Explicit=false;
#if !UE_BUILD_SHIPPING
    // Existing authoring and regression fixtures can still request a particular
    // historical map. Normal play and portal re-entry use the authored map or save.
    Explicit=!ContinueWorld&&FParse::Value(FCommandLine::Get(),TEXT("HillsSeed="),Requested);
    FParse::Value(FCommandLine::Get(),TEXT("HillsGen="),RequestedGen);
#endif
    const bool NewWorld=!ContinueWorld&&FParse::Param(FCommandLine::Get(),TEXT("HillsNewWorld"));
    UTemperateHillsSave* Saved=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Saved&&!NewWorld&&!Explicit&&UGameplayStatics::DoesSaveGameExist(Slot,0))
    {
        UE_LOG(LogTemp,Error,TEXT("HILLS_SESSION could not read existing world %s"),*Slot);
        Slot.Reset();return;
    }
    if(Saved&&!NewWorld&&!Explicit&&(Saved->Version>6||Saved->GeneratorVersion>3||Saved->VillagePlanVersion>UTemperateHillsSave::CurrentVillagePlanVersion))
    {
        UE_LOG(LogTemp,Error,TEXT("HILLS_SESSION incompatible version=%d; original save retained"),Saved->Version);
        Slot.Reset();return;
    }
    if(Saved&&!NewWorld&&!Explicit)
    {
        // V1 stored plans without repairing buildings. Resolve those unlocks before
        // scene generation; no live pawns or building collision exist at this point.
        if(Saved->VillagePlanVersion<2&&(Saved->VillagePlansUnlocked&3))
        {
            const bool OldWall=Saved->bVillageWallRepaired,OldShop=Saved->bVillageBlacksmithRepaired;
            const int32 OldPlanVersion=Saved->VillagePlanVersion;
            Saved->bVillageWallRepaired|=(Saved->VillagePlansUnlocked&1)!=0;
            Saved->bVillageBlacksmithRepaired|=(Saved->VillagePlansUnlocked&2)!=0;
            Saved->VillagePlanVersion=2;
            if(!UGameplayStatics::SaveGameToSlot(Saved,Slot,0))
            {
                Saved->bVillageWallRepaired=OldWall;Saved->bVillageBlacksmithRepaired=OldShop;
                Saved->VillagePlanVersion=OldPlanVersion;
                UE_LOG(LogTemp,Warning,TEXT("HILLS_SESSION village plan migration could not be saved; repair remains available from the nun"));
            }
        }
        Seed=Saved->Seed;WorldId=Saved->WorldId;
        PlaythroughSeed=Saved->PlaythroughSeed;
        VillageDefenseGeneration=Saved->VillageDefenseGeneration;
        bVillageWallRepaired=Saved->bVillageWallRepaired;
        bVillageBlacksmithRepaired=Saved->bVillageBlacksmithRepaired;
        VillagePlansUnlocked=Saved->SavedVillagePlans();
        bVillageBakeryRepaired=Saved->VillagePlanVersion>=9 && Saved->bVillageBakeryRepaired;
        bVillageGunshopRepaired=Saved->VillagePlanVersion>=10 && Saved->bVillageGunshopRepaired;
        bGarrisonMechanics=Saved->VillagePlanVersion>=11 && Saved->bGarrisonMechanics;
        // Old saves have no GeneratorVersion and must keep the frozen V1 field.
        GeneratorVersion=FMath::Clamp(Saved->GeneratorVersion,1,3);
        // V1 saves carry no edits and simply start with untouched ground. V2 stored
        // circular craters only; they migrate to the general edit list as bowls.
        TerrainEdits.Reset(Saved->Edits.Num()+Saved->Craters.Num());
        for(const FHillsCraterRecord& Record:Saved->Craters)
        {
            TemperateHillsSurface::FTerrainEdit Edit;
            Edit.Type=0;Edit.X=Record.X;Edit.Y=Record.Y;Edit.Radius=Record.Radius;
            Edit.Amplitude=-Record.Depth;Edit.Lip=Record.Rim;
            Edit.Seed=TemperateHills::Key(int32(Record.X),int32(Record.Y),uint32(Seed),7043);
            if(TemperateHillsSurface::TerrainEditValid(Edit))TerrainEdits.Add(Edit);
        }
        for(const FHillsTerrainEditRecord& Record:Saved->Edits)
        {
            TemperateHillsSurface::FTerrainEdit Edit;
            Edit.Type=Record.Type;Edit.X=Record.X;Edit.Y=Record.Y;Edit.Radius=Record.Radius;
            Edit.HalfX=Record.HalfX;Edit.HalfY=Record.HalfY;Edit.Amplitude=Record.Amplitude;
            Edit.Lip=Record.Lip;Edit.Seed=uint32(Record.Seed);
            if(TemperateHillsSurface::TerrainEditValid(Edit))TerrainEdits.Add(Edit);
        }
        if(!TerrainEdits.IsEmpty())UE_LOG(LogTemp,Display,TEXT("HILLS_EDIT restored=%d seed=%d"),TerrainEdits.Num(),Seed);
        RebuildEditBuckets();
    }
    else
    {
        Seed=Requested;
        WorldId=FGuid::NewGuid();
        if(!Explicit) PlaythroughSeed=int32(GetTypeHash(WorldId) | 1u);
        GeneratorVersion=FMath::Clamp(RequestedGen,1,3);
        auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::CreateSaveGameObject(UTemperateHillsSave::StaticClass()));
        Save->Version=6;Save->Seed=Seed;Save->WorldId=WorldId;Save->GeneratorVersion=GeneratorVersion;
        Save->PlaythroughSeed=PlaythroughSeed;
        Save->VillagePlanVersion=2;
        if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0)){UE_LOG(LogTemp,Error,TEXT("HILLS_SESSION save failed"));Slot.Reset();}
    }
    UE_LOG(LogTemp,Display,TEXT("HILLS_SESSION seed=%d generator=%d world=%s"),Seed,GeneratorVersion,*WorldId.ToString());
}

void ATemperateHillsWorld::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ATemperateHillsWorld,Seed);
    DOREPLIFETIME(ATemperateHillsWorld,GeneratorVersion);
    DOREPLIFETIME(ATemperateHillsWorld,WorldId);
    DOREPLIFETIME(ATemperateHillsWorld,ForestGrowthDay);
    DOREPLIFETIME_CONDITION(ATemperateHillsWorld,PlaythroughSeed,COND_InitialOnly);
    DOREPLIFETIME(ATemperateHillsWorld,bVillageWallRepaired);
    DOREPLIFETIME(ATemperateHillsWorld,bVillageBlacksmithRepaired);
    DOREPLIFETIME(ATemperateHillsWorld,VillagePlansUnlocked);
    DOREPLIFETIME(ATemperateHillsWorld,bVillageBakeryRepaired);
    DOREPLIFETIME(ATemperateHillsWorld,bVillageGunshopRepaired);
    DOREPLIFETIME(ATemperateHillsWorld,bGarrisonMechanics);
    DOREPLIFETIME(ATemperateHillsWorld,SiegeRanks);
    DOREPLIFETIME_CONDITION(ATemperateHillsWorld,SizeMeters,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(ATemperateHillsWorld,NetEcology,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(ATemperateHillsWorld,bTerrainDestructionEnabled,COND_InitialOnly);
    DOREPLIFETIME(ATemperateHillsWorld,NetEdits);
    DOREPLIFETIME(ATemperateHillsWorld,NetEditsVersion);
}
void ATemperateHillsWorld::BeginPlay()
{
    // The generated world is fixed in space, including previously saved map actors.
    RootComponent->SetMobility(EComponentMobility::Static);
    Super::BeginPlay();
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        Loading->BeginHillsPreparation();
    StartSeconds=FPlatformTime::Seconds();
    // M4 联机：专用服暂不支持；客户端走确定性重建（Tick 里等复制的会话就绪）；
    // 监听服与单机照常权威生成。
    if(GetNetMode()==NM_DedicatedServer){UE_LOG(LogTemp,Error,TEXT("HILLS_V1 dedicated server unsupported"));return;}
    if(GetNetMode()==NM_Client){UE_LOG(LogTemp,Display,TEXT("HILLS_NET client: awaiting replicated session"));return;}
    NetEcology.Profile=TemperateEcology::Get();
    NetEcology.Ready=true;
    GConfig->GetBool(TEXT("TemperateHills.Gameplay"),TEXT("TerrainDestructionEnabled"),bTerrainDestructionEnabled,GGameIni);
    ResolveSession();
    if(GetNetMode()!=NM_Standalone)SyncNetEdits(); // 会话(种子+存量编辑)首帧广播
    StartWorldPipeline();
}
bool ATemperateHillsWorld::StartWorldPipeline()
{
    // 客户端不落盘（Slot 恒空）；服务端/单机的 Slot 为空意味着会话解析失败。
    if((GetNetMode()!=NM_Client&&Slot.IsEmpty())||!Assets||Assets->GroundMaterial.IsNull()||Assets->Trees.IsEmpty()||Assets->Graphs.Num()!=4)
    {
        UE_LOG(LogTemp,Error,TEXT("HILLS_ASSETS missing curated biome data"));
        if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
            Loading->FailPreparation(FText::FromString(TEXT("世界数据无法读取，请返回主场景后重试。")));
        return false;
    }
    GeneratorVersion=FMath::Clamp(GeneratorVersion,1,3);
    // The expanded hilltop reservation and its slopes need a full 512 m study area.
    SizeMeters=FMath::Clamp(FMath::RoundToFloat(SizeMeters/128)*128,GeneratorVersion>=3?512.f:256.f,1024.f);
    bStartLocationCached=false;
    UE_LOG(LogTemp,Display,TEXT("HILLS_GEN generator=%d seed=%d size=%.0fm"),GeneratorVersion,Seed,SizeMeters);
    GenerationBounds->SetBoxExtent(FVector(SizeMeters*50,SizeMeters*50,50000));
    if(IsForestVillage()) BeginForestVillage();
    else BeginStreaming();
    return true;
}
void ATemperateHillsWorld::ConvertNetEdits()
{
    TerrainEdits.Reset(NetEdits.Num());
    for(const FHillsTerrainEditRecord& Record:NetEdits)
    {
        TemperateHillsSurface::FTerrainEdit Edit;
        Edit.Type=Record.Type;Edit.X=Record.X;Edit.Y=Record.Y;Edit.Radius=Record.Radius;
        Edit.HalfX=Record.HalfX;Edit.HalfY=Record.HalfY;Edit.Amplitude=Record.Amplitude;
        Edit.Lip=Record.Lip;Edit.Seed=uint32(Record.Seed);
        if(TemperateHillsSurface::TerrainEditValid(Edit))TerrainEdits.Add(Edit);
    }
    RebuildEditBuckets();
}
void ATemperateHillsWorld::SyncNetEdits()
{
    if(!HasAuthority())return;
    NetEdits.Reset(TerrainEdits.Num());
    for(const TemperateHillsSurface::FTerrainEdit& Edit:TerrainEdits)
    {
        FHillsTerrainEditRecord Record;
        Record.Type=Edit.Type;Record.X=Edit.X;Record.Y=Edit.Y;Record.Radius=Edit.Radius;
        Record.HalfX=Edit.HalfX;Record.HalfY=Edit.HalfY;Record.Amplitude=Edit.Amplitude;
        Record.Lip=Edit.Lip;Record.Seed=Edit.Seed;
        NetEdits.Add(Record);
    }
    ++NetEditsVersion;
}
void ATemperateHillsWorld::OnRep_NetEdits()
{
    if(GetNetMode()!=NM_Client||!bClientWorldInit)return;
    const auto Previous=MoveTemp(TerrainEdits);
    ConvertNetEdits();
    // The authority appends edits and retires the oldest. A client may receive several
    // changes together, including a replacement at the 256-entry limit.
    const auto Old=MakeArrayView(Previous);
    const auto Current=MakeArrayView(TerrainEdits);
    int32 Retained=FMath::Min(Old.Num(),Current.Num());
    while(Retained>0 && !Algo::Compare(Old.Right(Retained),Current.Left(Retained)))--Retained;
    for(const auto& Edit:Old.Left(Old.Num()-Retained))
        InvalidateTerrainCells(FVector2D(Edit.X,Edit.Y),TemperateHillsSurface::TerrainEditReach(Edit));
    for(const auto& Edit:Current.RightChop(Retained))
    {
        InvalidateTerrainCells(FVector2D(Edit.X,Edit.Y),TemperateHillsSurface::TerrainEditReach(Edit));
        ClearCoverForEdit(Edit);
    }
    UE_LOG(LogTemp,Warning,TEXT("MPTEST hills client edits applied: count=%d version=%d"),TerrainEdits.Num(),NetEditsVersion);
}

double ATemperateHillsWorld::ForestWeight(double X,double Y) const
{return TemperateForestHabitat::Canopy(X,Y,Seed,RainforestWeight(X,Y), EcologyProfile());}
FVector ATemperateHillsWorld::GetStartLocation() const
{
    if(IsForestVillage() && VillageSite.bPlaced && GetWorld()->URL.HasOption(TEXT("VisitVillage")))
    {
        const FVector2D P=VillageSite.World(VillageSite.WallHalfSize().X-750.,500.);
        return FVector(P,Height(P.X,P.Y)+106.);
    }
    if(ChapelSite.bPlaced)
    {
        const FVector2D Entry=ChapelSite.Entry();
        return FVector(Entry,Height(Entry.X,Entry.Y)+106.);
    }
    return GetGenerationAnchor();
}
FVector ATemperateHillsWorld::GetGenerationAnchor() const
{
    const double X0=-SizeMeters*25+173;
    if(GeneratorVersion<2)
    {
        const double Y=TemperateHills::ValleyY(X0,Seed);
        return FVector(X0,Y,Height(X0,Y)+106);
    }
    // V2 relief can put a ridge on the old fixed spawn. Walk east along the
    // valley in 2 m steps and keep the first walkable (<=8 deg) spot; fall back
    // to the flattest sample if the whole search strip is steep.
    if(bStartLocationCached)return CachedStartLocation;
    const bool FixedSurvey=PlaythroughSeed!=0 && Seed==TemperateHillsMap::Seed && GeneratorVersion==TemperateHillsMap::GeneratorVersion;
    double BestX=X0,BestY=TemperateHills::ValleyY(X0,Seed),BestZ=0,BestSlope=DBL_MAX;
    for(int32 I=0;I<65;++I)
    {
        const double X=X0+I*200.0;
        const double Y=TemperateHills::ValleyY(X,Seed);
        const double Z=FixedSurvey?TemperateHillsSurface::Height(X,Y,Seed,GeneratorVersion):Height(X,Y);
        const FVector N=FixedSurvey?TemperateHillsSurface::Normal(X,Y,Seed,GeneratorVersion):SurfaceNormal(X,Y);
        const double Slope=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(N.Z,-1.0,1.0)));
        if(Slope<BestSlope){BestSlope=Slope;BestX=X;BestY=Y;BestZ=Z;}
        if(Slope<=8.0)break;
    }
    CachedStartLocation=FVector(BestX,BestY,BestZ+106);
    bStartLocationCached=true;
    return CachedStartLocation;
}

FRotator ATemperateHillsWorld::GetStartRotation() const
{
    if(ChapelSite.bPlaced)return FVector(ChapelSite.Axis,0.).Rotation();
    if(!RiverPlan||RiverPlan->Points.IsEmpty())return FRotator(0,18,0);
    const FVector2D Start(GetStartLocation());
    FVector2D Target=RiverPlan->Points[0].XY;double Best=DBL_MAX;
    for(const auto& Point:RiverPlan->Points)
    {
        const double D=FVector2D::DistSquared(Start,Point.XY);
        if(D<Best){Best=D;Target=Point.XY;}
    }
    return FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Target.Y-Start.Y,Target.X-Start.X)),0);
}

void ATemperateHillsWorld::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    // M4：客户端确定性重建入口——等服务端会话(种子+编辑)复制到位再启动管线。
    if(GetNetMode()==NM_Client&&!bClientWorldInit)
    {
        if(!WorldId.IsValid()||GeneratorVersion<=0||!NetEcology.Ready)return;
        bClientWorldInit=true;
        Slot.Reset();
        ConvertNetEdits();
        UE_LOG(LogTemp,Warning,TEXT("MPTEST hills client session: seed=%d generator=%d edits=%d"),Seed,GeneratorVersion,TerrainEdits.Num());
        StartWorldPipeline();
    }
    const bool ForestVillage=IsForestVillage();
    if(ForestVillage) TickForestVillage();
    else
    {
        TickStreaming();
        TickDayNightSky();
    }
    if(!bReady)return;
    WeatherLookupLeft-=DeltaSeconds;
    if(!SkyWeather.IsValid()&&WeatherLookupLeft<=0.f)
    {
        WeatherLookupLeft=1.f;
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){SkyWeather=*It;break;}
    }
    if(!ForestVillage) TickForestWind(DeltaSeconds);
    if(SkyWeather.IsValid()&&GroundMID)
    {
        const float Wetness=SkyWeather->GetSurfaceWetness();
        if(WetGroundMaterial!=GroundMID||LastGroundWetness!=Wetness)
        {
            GroundMID->SetScalarParameterValue(TEXT("Wetness"),Wetness);
            WetGroundMaterial=GroundMID;LastGroundWetness=Wetness;
        }
    }
    if(bAudit)
    {
        if(GetWorld()->GetTimeSeconds()>26&&!bNullAudit)FrameSamples.Add(FMath::Max(.0,double(DeltaSeconds))*1000);
        RunAudit();
    }
}

void ATemperateHillsWorld::AuditCheck(bool Pass,const TCHAR* Message)
{
    bAuditPassed&=Pass;
    UE_LOG(LogTemp,Display,TEXT("HILLS_CHECK %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Message);
}

void ATemperateHillsWorld::RunAudit()
{
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now<AuditNext)return;
    auto* PC=UGameplayStatics::GetPlayerController(this,0);
    auto* Pawn=UGameplayStatics::GetPlayerCharacter(this,0);
    if(!PC||!Pawn){AuditCheck(false,TEXT("pawn ready"));FPlatformMisc::RequestExitWithStatus(false,1);return;}
    auto Capture=[&](const TCHAR* Name){if(!bNullAudit)FScreenshotRequest::RequestScreenshot(AuditDir/(FString(Name)+TEXT(".png")),false,false);};
    if(AuditStage==0)
    {
        IFileManager::Get().MakeDirectory(*AuditDir,true);
        AuditCheck(Terrain.Num()==FMath::Square(FMath::RoundToInt(SizeMeters/128)),TEXT("all terrain chunks built"));
        AuditCheck(Pawn->GetCharacterMovement()->IsMovingOnGround(),TEXT("player stands on generated collision"));
        bool Hits=true;double Min=DBL_MAX,Max=-DBL_MAX;double Error=0;
        FCollisionQueryParams GroundQuery;GroundQuery.AddIgnoredComponent(Trunks.Get());
        // Rocks are valid obstacles above the terrain, so exclude other actors from the terrain-height check.
        for(TActorIterator<AActor> It(GetWorld());It;++It)if(*It!=this)GroundQuery.AddIgnoredActor(*It);
        for(int32 Y=-4;Y<=4;++Y)for(int32 X=-4;X<=4;++X)
        {
            const double WX=X*10000,WY=Y*10000,Z=Height(WX,WY);Min=FMath::Min(Min,Z);Max=FMath::Max(Max,Z);
            FHitResult Hit;
            const bool Got=GetWorld()->LineTraceSingleByChannel(Hit,FVector(WX,WY,Z+500),FVector(WX,WY,Z-500),ECC_Pawn,GroundQuery);
            Hits&=Got;if(Got)Error=FMath::Max(Error,FMath::Abs(Hit.ImpactPoint.Z-Z));
        }
        AuditCheck(Hits&&Error<15,TEXT("81 terrain traces match height function within 15cm"));
        AuditCheck(Max-Min>1800,TEXT("terrain has more than 18m measured elevation change"));
        AuditCheck(Trunks&&Trunks->GetInstanceCount()>50,TEXT("existing Black Poplar candidates have trunk collision"));
        TArray<FTemperatePlacement> Left,Right,Whole;
        GetPlacements(0,FBox(FVector(-12800,-12800,-50000),FVector(0,12800,50000)),Left);
        GetPlacements(0,FBox(FVector(0,-12800,-50000),FVector(12800,12800,50000)),Right);
        GetPlacements(0,FBox(FVector(-12800,-12800,-50000),FVector(12800,12800,50000)),Whole);
        bool TrunkBlocks=false;
        for(const auto& Tree:Whole)
        {
            const FVector P=Tree.Transform.GetLocation();
            if(SurfaceNormal(P.X,P.Y).Z<.96)continue;
            FHitResult Block;FCollisionQueryParams Q;Q.AddIgnoredActor(Pawn);
            GetWorld()->SweepSingleByChannel(Block,P+FVector(-220,0,200),P+FVector(220,0,200),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(36,90),Q);
            TrunkBlocks=Block.GetComponent()==Trunks.Get();break;
        }
        AuditCheck(TrunkBlocks,TEXT("player-sized capsule is blocked by a generated tree trunk"));
        TSet<uint64> Keys;for(const auto& P:Left)Keys.Add(P.CandidateId);for(const auto& P:Right)Keys.Add(P.CandidateId);
        AuditCheck(Keys.Num()==Whole.Num()&&Keys.Num()==Left.Num()+Right.Num(),TEXT("adjacent cell ownership is complete and duplicate-free"));
        auto* Saved=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
        AuditCheck(Saved&&Saved->Seed==Seed&&Saved->WorldId==WorldId,TEXT("world seed/id save readback"));
        FString Layout=FString::Printf(TEXT("{\"seed\":%d,\"treeHash\":%u,\"rockHash\":%u,\"shrubHash\":%u,\"grassHash\":%u,\"heightMinM\":%.3f,\"heightMaxM\":%.3f,\"traceMaxErrorCm\":%.3f}"),Seed,LayoutHash(0),LayoutHash(1),LayoutHash(2),LayoutHash(3),Min/100,Max/100,Error);
        FFileHelper::SaveStringToFile(Layout,*(AuditDir/TEXT("layout.json")));
        PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);
        PC->SetControlRotation(FRotator(6,18,0));
        Capture(TEXT("01-player-meadow"));
        AuditStage=1;AuditNext=Now+(bNullAudit?1:8);return;
    }
    if(AuditStage==1)
    {
        int32 Trees=0,Static=0;
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        {
            TInlineComponentArray<UInstancedSkinnedMeshComponent*> Skinned(*It);for(auto* C:Skinned)Trees+=C->GetInstanceCount();
            TInlineComponentArray<UInstancedStaticMeshComponent*> ISMs(*It);for(auto* C:ISMs)if(C!=Trunks)Static+=C->GetInstanceCount();
        }
        AuditCheck(Trees>20,TEXT("PCG native skinned tree instances generated"));
        AuditCheck(Static>100,TEXT("PCG static ground-cover instances generated"));
        UE_LOG(LogTemp,Display,TEXT("HILLS_INSTANCES trees=%d ground_cover=%d fog=%d"),Trees,Static,ValleyFog.Num());
        if(!AuditCamera)AuditCamera=GetWorld()->SpawnActor<ACameraActor>();
        const FVector Eye=GetStartLocation()+FVector(-6000,-6000,8000),Target=FVector(1000,2000,Height(1000,2000));
        AuditCamera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());AuditCamera->GetCameraComponent()->SetFieldOfView(67);PC->SetViewTarget(AuditCamera);
        AuditStage=2;AuditNext=Now+(bNullAudit?1:12);return;
    }
    if(AuditStage==2){Capture(TEXT("02-hills-overview"));AuditStage=3;AuditNext=Now+(bNullAudit?1:3);return;}
    if(AuditStage==3)
    {
        TArray<FTemperatePlacement> Trees;GetPlacements(0,FBox(FVector(-30000,-15000,-50000),FVector(0,15000,50000)),Trees);
        if(!Trees.IsEmpty())
        {
            const FVector T=Trees[Trees.Num()/2].Transform.GetLocation();
            const FVector Eye(T.X-2100,T.Y-1200,Height(T.X-2100,T.Y-1200)+200);
            AuditCamera->SetActorLocationAndRotation(Eye,(T+FVector(0,0,1100)-Eye).Rotation());AuditCamera->GetCameraComponent()->SetFieldOfView(70);
            // Exercise streaming at the new camera location as well as the actual pawn source.
            Pawn->SetActorLocation(FVector(T.X-2100,T.Y-1200,Height(T.X-2100,T.Y-1200)+106));
        }
        AuditStage=4;AuditNext=Now+(bNullAudit?1:12);return;
    }
    if(AuditStage==4){Capture(TEXT("03-black-poplar"));AuditStage=5;AuditNext=Now+(bNullAudit?1:3);return;}
    if(AuditStage==5)
    {
        const double X=0,Y=TemperateHills::ValleyY(0,Seed);
        const FVector Eye(X-4800,Y-2500,Height(X-4800,Y-2500)+240);
        AuditCamera->SetActorLocationAndRotation(Eye,(FVector(X+3500,Y,Height(X+3500,Y)+140)-Eye).Rotation());
        AuditCamera->GetCameraComponent()->SetFieldOfView(76);
        Pawn->SetActorLocation(FVector(Eye.X,Eye.Y,Height(Eye.X,Eye.Y)+106));
        AuditStage=6;AuditNext=Now+(bNullAudit?1:12);return;
    }
    if(AuditStage==6){Capture(TEXT("04-valley-fog"));AuditStage=7;AuditNext=Now+(bNullAudit?1:3);return;}
    if(AuditStage==7)
    {
        FrameSamples.Sort();double Median=0,P95=0;
        if(!FrameSamples.IsEmpty()){Median=FrameSamples[FrameSamples.Num()/2];P95=FrameSamples[FMath::Min(FrameSamples.Num()-1,FMath::FloorToInt(FrameSamples.Num()*.95))];}
        UE_LOG(LogTemp,Display,TEXT("HILLS_AUDIT_COMPLETE pass=%d seed=%d frame_median_ms=%.3f frame_p95_ms=%.3f samples=%d mode=%s"),bAuditPassed,Seed,Median,P95,FrameSamples.Num(),bNullAudit?TEXT("NullRHI"):TEXT("StandaloneEditorRuntime"));
        FPlatformMisc::RequestExitWithStatus(false,bAuditPassed?0:1);AuditStage=8;
    }
}

void ATemperateHillsWorld::EndPlay(const EEndPlayReason::Type Reason)
{
    bReady=false;
    if(IsValid(MechanicalWorkshop)&&HasAuthority())MechanicalWorkshop->Destroy();
    if(IsValid(ChapelDoor)&&HasAuthority())ChapelDoor->Destroy();
    if(IsValid(ChapelShrine)&&HasAuthority())ChapelShrine->Destroy();
    ClearVillagePerimeter();
    EndStreaming();
    Super::EndPlay(Reason);
}

void ATemperateHillsGameMode::RestartPlayer(AController* NewPlayer)
{
    if(!IsValid(NewPlayer)||NewPlayer->GetPawn())return;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->PrepareSpawnGround(NewPlayer)){RestartPlayerAtTransform(NewPlayer,FTransform(It->GetStartRotation(),It->GetStartLocation()));return;}
    FTimerHandle Retry;
    GetWorldTimerManager().SetTimer(Retry,FTimerDelegate::CreateWeakLambda(this,[this,Weak=TWeakObjectPtr<AController>(NewPlayer)](){if(Weak.IsValid())RestartPlayer(Weak.Get());}),.15f,false);
}
