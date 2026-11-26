#include "HillsNightRaidSubsystem.h"
#include "ForestVillageMap.h"
#include "ForestVillageRegion.h"
#include "LandscapeHeightfieldCollisionComponent.h"
#include "HillsNightRaidSave.h"
#include "VillageDefenseCombat.h"
#include "HillsNightPortal.h"
#include "ChapelShrine.h"
#include "TemperateHillsWorld.h"
#include "../FPSWeatherManager.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/FatZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/ConfigCacheIni.h"
#include "NavigationSystem.h"
#include "NavigationData.h"

namespace
{
const TCHAR* Section=TEXT("TemperateHills.NightRaid");
bool IsRaidGround(const UPrimitiveComponent* Component,const ATemperateHillsWorld* Hills)
{
    if(!Component || !Hills)return false;
    const bool TaggedFloor=Component->ComponentHasTag(TEXT("HillsGround"));
    if(Component->GetOwner()==Hills)return TaggedFloor;
    if(!Hills->IsForestVillage())return false;
    // The painted trail crosses from the village foundation onto baked region tiles and Landscape.
    return Component->IsA<ULandscapeHeightfieldCollisionComponent>() ||
        (TaggedFloor && Component->GetOwner() && Component->GetOwner()->IsA<AForestVillageRegion>());
}

// Sample the same two-metre road mask used by the forest map. The outer trail bends
// away from the gate axis; fixed offsets alone can put an entire night's sites in the trees.
void ForestRoadSites(const FTemperateVillageSite& Site,const AForestVillageRegion& Region,TArray<FVector2D>& Out)
{
    for(double Side:{-1.,1.})
    {
        for(int32 Forward=600;Forward<=3800;Forward+=200)
        {
            for(int32 Across=-3600;Across<=3600;Across+=200)
            {
                const int32 DistanceSq=Forward*Forward+Across*Across;
                if(DistanceSq<2200*2200 || DistanceSq>3800*3800)continue;
                const FVector2D Point=Site.World(Side*(Site.WallHalfSize().X+Forward),Site.GateY(Side)+Across);
                if(Region.MapRoadWeight(Point.X,Point.Y)>=.45)Out.Add(Point);
            }
        }
    }
}
}
bool UHillsNightRaidSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{return Super::ShouldCreateSubsystem(Outer)&&(ForestVillageMap::Is(Cast<UWorld>(Outer))||UWildlifeSubsystem::IsWildlifeMap(Cast<UWorld>(Outer)));}
bool UHillsNightRaidSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game||Type==EWorldType::PIE;}
TStatId UHillsNightRaidSubsystem::GetStatId() const
{RETURN_QUICK_DECLARE_CYCLE_STAT(UHillsNightRaidSubsystem,STATGROUP_Tickables);}
void UHillsNightRaidSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    FWorldDelegates::OnWorldBeginTearDown.AddUObject(this,&UHillsNightRaidSubsystem::WorldTearingDown);
    GConfig->GetBool(Section,TEXT("Enabled"),bEnabled,GGameIni);
    GConfig->GetInt(Section,TEXT("MaxAlive"),MaxAlive,GGameIni);
    GConfig->GetInt(Section,TEXT("MaxPerNight"),MaxPerNight,GGameIni);
    GConfig->GetInt(Section,TEXT("WaveSize"),WaveSize,GGameIni);
    GConfig->GetFloat(Section,TEXT("NightStartHour"),NightStart,GGameIni);
    GConfig->GetFloat(Section,TEXT("NightEndHour"),NightEnd,GGameIni);
    GConfig->GetFloat(Section,TEXT("WaveIntervalSeconds"),WaveInterval,GGameIni);
    GConfig->GetFloat(Section,TEXT("WarmupSeconds"),WarmupSeconds,GGameIni);
    GConfig->GetFloat(Section,TEXT("ShrineDurability"),Durability,GGameIni);
    MaxAlive=FMath::Clamp(MaxAlive,1,24);MaxPerNight=FMath::Clamp(MaxPerNight,MaxAlive,120);
    WaveSize=FMath::Clamp(WaveSize,1,6);WaveInterval=FMath::Max(5.f,WaveInterval);WarmupSeconds=FMath::Max(8.f,WarmupSeconds);
}
int32 UHillsNightRaidSubsystem::LivingCount() const
{
    int32 Count=0;for(const auto& Raider:Raiders)if(Raider.IsValid()&&Raider->Health>0.f)++Count;return Count;
}
void UHillsNightRaidSubsystem::UpdateInvokers()
{
    Raiders.RemoveAll([](const auto& Raider){return !Raider.IsValid();});
    PlayerInvokers.RemoveAll([](const auto& Player){return !Player.IsValid();});
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=It->Get())if(APawn* Pawn=PC->GetPawn();Pawn&&!PlayerInvokers.Contains(Pawn))
        {
            UNavigationSystemV1::RegisterNavigationInvoker(*Pawn,6000,8000);PlayerInvokers.Add(Pawn);
        }
}
void UHillsNightRaidSubsystem::GetGroundPins(TArray<FVector>& Centers,FVector& Village,float& VillageRadius) const
{
    VillageRadius=0.f;
    if(!bEnabled||!Hills.IsValid()||GetWorld()->GetNetMode()==NM_Client)return;
    // Prewarm the connected village floor and its two approach roads before sunset.
    Village=Hills->GetVillageSite().Ground;VillageRadius=14000.f;
    if(bSiteChosen)Centers.Add(PortalSite);
    for(const auto& Raider:Raiders)if(Raider.IsValid())Centers.Add(Raider->GetActorLocation());
    if(PendingSave)for(int32 I=RestoreIndex;I<PendingSave->Raiders.Num();++I)
        Centers.Add(PendingSave->Raiders[I].Transform.GetLocation());
}
bool UHillsNightRaidSubsystem::IsPortalSpaceClear(const FVector& Ground) const
{
    TArray<FOverlapResult> Overlaps;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RaidPortalClear),false);
    GetWorld()->OverlapMultiByChannel(Overlaps,Ground+FVector(0,0,220),FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeBox(FVector(230,230,205)),Query);
    for(const FOverlapResult& Overlap:Overlaps)
    {
        // The box starts only 15 cm above its center ground. Gentle slopes can
        // enter it; ground support is not an obstacle. Keep trees/buildings/pawns.
        if(Overlap.bBlockingHit&&!IsRaidGround(Overlap.GetComponent(),Hills.Get()))return false;
    }
    return true;
}
bool UHillsNightRaidSubsystem::IsPlayerNear(const FVector& Point,float Distance) const
{
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=It->Get())if(APawn* Pawn=PC->GetPawn())
            if(FVector::DistSquared2D(Pawn->GetActorLocation(),Point)<FMath::Square(Distance))return true;
    return false;
}
bool UHillsNightRaidSubsystem::ChoosePortalSite()
{
    const auto& Site=Hills->GetVillageSite();
    if(!Site.bPlaced)return false;
    const double Half=Hills->SizeMeters*50.-800.;
    const bool Forest=Hills->IsForestVillage();
    const FBox2D Bounds=Forest ? ForestVillageMap::Bounds().ExpandBy(-800.) :
        FBox2D(FVector2D(-Half,-Half),FVector2D(Half,Half));
    TArray<FVector2D> RoadSites;
    if(Forest)
    {
        for(TActorIterator<AForestVillageRegion> It(GetWorld());It;++It)
            if(It->HasGround()){ForestRoadSites(Site,**It,RoadSites);break;}
    }
    int32 SurfaceRejected=0,PlayerRejected=0,ObstacleRejected=0;
    for(int32 Try=0;Try<8;++Try)
    {
        const double Side=Random.RandRange(0,1)?1.:-1.;
        const double ReservedApron=Site.PadHalfX-TemperateVillageLayout::HalfX;
        FVector2D Point;
        if(Forest && Try<6 && !RoadSites.IsEmpty())
        {
            const int32 Index=Random.RandRange(0,RoadSites.Num()-1);
            Point=RoadSites[Index];
            RoadSites.RemoveAtSwap(Index,1,EAllowShrinking::No);
        }
        else if(Forest)
        {
            // Try clear ground beyond either gate when road sites are occupied.
            Point=Site.World(Side*(Site.WallHalfSize().X+Random.FRandRange(2200.f,3800.f)),
                Site.GateY(Side)+Random.FRandRange(-480.f,480.f));
        }
        else
        {
            Point=Site.Approach(Side,ReservedApron+Site.Shoulder+Random.FRandRange(2200.f,3800.f),Hills->Seed);
        }
        if(!Bounds.IsInside(Point)||Hills->SurfaceNormal(Point.X,Point.Y).Z<.87
            ||Hills->SampleForestWater(Point.X,Point.Y).Wet||Hills->SampleRiver(Point.X,Point.Y).Wet>.01)
        {++SurfaceRejected;continue;}
        const double Height=Hills->Height(Point.X,Point.Y);
        bool Clear=true;
        for(const FVector2D Offset:{FVector2D(250,0),FVector2D(-250,0),FVector2D(0,250),FVector2D(0,-250)})
            if(FMath::Abs(Hills->Height(Point.X+Offset.X,Point.Y+Offset.Y)-Height)>75.){Clear=false;break;}
        if(!Clear){++SurfaceRejected;continue;}
        const FVector Ground(Point,Height);
        if(IsPlayerNear(Ground,3500.f)){++PlayerRejected;continue;}
        if(!IsPortalSpaceClear(Ground)){++ObstacleRejected;continue;}
        PortalSite=Ground;PortalFacing=(Shrine->GetActorLocation()-Ground).GetSafeNormal2D().Rotation();
        bSiteChosen=true;GroundWaitAttempts=0;return true;
    }
    if(GetWorld()->GetTimeSeconds()>=NextPlacementLog)
    {
        NextPlacementLog=GetWorld()->GetTimeSeconds()+30.;
        UE_LOG(LogTemp,Warning,TEXT("HILLS_RAID no clear site seed=%d surface=%d player=%d obstacle=%d"),
            Hills->Seed,SurfaceRejected,PlayerRejected,ObstacleRejected);
    }
    return false;
}
const TCHAR* UHillsNightRaidSubsystem::SpawnResultName(ESpawnResult Result)
{
    switch(Result)
    {
    case ESpawnResult::Spawned:return TEXT("spawned");
    case ESpawnResult::PlayerNearby:return TEXT("player_near_exit");
    case ESpawnResult::NavigationPending:return TEXT("navigation_building");
    case ESpawnResult::NoNavigation:return TEXT("no_agent_navigation");
    case ESpawnResult::NoSpawnFloor:return TEXT("no_exit_navigation");
    case ESpawnResult::NoShrineApproach:return TEXT("no_shrine_approach");
    case ESpawnResult::NoRoute:return TEXT("no_complete_route");
    case ESpawnResult::Occupied:return TEXT("exit_occupied");
    case ESpawnResult::SpawnRejected:return TEXT("spawn_rejected");
    case ESpawnResult::MissingController:return TEXT("missing_monster_controller");
    }
    return TEXT("unknown");
}
UHillsNightRaidSubsystem::ESpawnResult UHillsNightRaidSubsystem::SpawnOne()
{
    if(!Portal.IsValid()||MonsterClasses.Num()!=2)return ESpawnResult::SpawnRejected;
    const bool Heavy=SpawnedThisNight%3==2;
    UClass* Class=MonsterClasses[Heavy?1:0];const auto* Defaults=Class->GetDefaultObject<ANurseZombie>();
    const float Radius=Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius();
    const float HalfHeight=Defaults->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    FNavAgentProperties Agent=Defaults->GetNavAgentPropertiesRef();
    Agent.AgentRadius=Radius;Agent.AgentHeight=HalfHeight*2.f;
    // The existing larger Recast agent fits the fat zombie; keep Nurse on its native APS agent.
    if(Heavy){Agent.AgentRadius=62.f;Agent.AgentHeight=204.f;}
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto* Data=Nav?Nav->GetNavDataForProps(Agent,PortalSite):nullptr;
    if(!Data)return ESpawnResult::NoNavigation;
    // The shrine now includes a scaled, blocking stone pedestal. The old fixed
    // 175 cm destination can be inside it, rejecting every otherwise valid exit.
    const FVector ShrineFloor=Shrine->GetNavAgentLocation();
    const FBox ShrineBounds=Shrine->GetComponentsBoundingBox(true);
    const FVector ShrineExtent=(ShrineBounds.GetCenter()-ShrineFloor).GetAbs()+ShrineBounds.GetExtent();
    const double ApproachRadius=FMath::Max(175.,ShrineExtent.Size2D()+Agent.AgentRadius+50.);
    const FVector ApproachDirection=(PortalSite-ShrineFloor).GetSafeNormal2D();
    TArray<FNavLocation,TInlineAllocator<4>> Goals;
    for(const double Angle:{0.,90.,-90.,180.})
    {
        FNavLocation Goal;
        const FVector Desired=ShrineFloor+ApproachDirection.RotateAngleAxis(Angle,FVector::UpVector)*ApproachRadius;
        if(Nav->ProjectPointToNavigation(Desired,Goal,FVector(140,140,120),Data))Goals.Add(Goal);
    }
    const FVector Forward=Portal->GetActorForwardVector(),Right=Portal->GetActorRightVector();
    ESpawnResult Failure=ESpawnResult::NoSpawnFloor;bool PlayerAtValidExit=false;
    for(int32 Try=0;Try<3;++Try)
    {
        const FVector Probe=PortalSite+Forward*Random.FRandRange(180.f,330.f)+Right*Random.FRandRange(-90.f,90.f);
        FNavLocation Ground;
        if(!Nav->ProjectPointToNavigation(Probe,Ground,FVector(120,120,300),Data))
        {Failure=ESpawnResult::NoSpawnFloor;continue;}
        bool Connected=false;
        for(const FNavLocation& Goal:Goals)
        {
            FPathFindingQuery Route(nullptr,*Data,Ground.Location,Goal.Location);Route.SetAllowPartialPaths(false);
            if(Nav->TestPathSync(Route,EPathFindingMode::Regular)){Connected=true;break;}
        }
        if(!Connected)Connected=VillageDefenseCombat::HasRoute(GetWorld(),Ground.Location,Shrine->GetActorLocation(),Nav,Data);
        if(!Connected){Failure=Goals.IsEmpty()?ESpawnResult::NoShrineApproach:ESpawnResult::NoRoute;continue;}
        const FVector Center=Ground.Location+FVector(0,0,HalfHeight+4.);
        // Waiting for a player to leave is an intentional pause, not a bad portal.
        // Check before overlap so a player standing in the capsule is also a pause.
        if(IsPlayerNear(Center,600.f)){PlayerAtValidExit=true;continue;}
        FCollisionQueryParams Query(SCENE_QUERY_STAT(RaidEmergence),false);
        if(GetWorld()->OverlapBlockingTestByChannel(Center,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(Radius,HalfHeight),Query))
        {Failure=ESpawnResult::Occupied;continue;}
        const FTransform Transform(PortalFacing,Center);
        auto* Monster=CreateRaider(Heavy,Transform);
        if(!Monster){Failure=ESpawnResult::SpawnRejected;continue;}
        Raiders.Add(Monster);++SpawnedThisNight;
        return ESpawnResult::Spawned;
    }
    return PlayerAtValidExit?ESpawnResult::PlayerNearby:Failure;
}
void UHillsNightRaidSubsystem::Tick(float Delta)
{
    Super::Tick(Delta);auto* World=GetWorld();
    if(!bEnabled||!World)return;
    const double Now=World->GetTimeSeconds();if(Now<NextUpdate)return;NextUpdate=Now+1.;
    // Clients also need the first wave's class/mesh/animation dependencies. Do
    // this before terrain readiness and input release, including during late join.
    PrepareAssets();
    if(World->GetNetMode()==NM_Client)return;
    UpdateReplicationGates();
    if(!RestoreSession())return;
    if(auto* Load=World->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();Load&&Load->IsHoldingGameplayInput())return;
    UpdateInvokers();
    if(Now>=NextCheckpoint)Checkpoint();
    const bool RestorationReady=!bRestorePending||RestoreActors();
    const float Hour=Weather->NormalizedDayTime*24.f;
    const bool Night=Hour>=NightStart||Hour<NightEnd;
    if(!bClockInitialized){Shrine->SetRaidNight(false,Durability);bClockInitialized=true;}
    if(Night!=bNight)
    {
        bNight=Night;Shrine->SetRaidNight(Night,Durability);
        if(!Night)
        {
            if(Portal.IsValid())Portal->ClosePortal();Portal.Reset();bSiteChosen=false;WaveRemaining=0;
            if(PendingSave)PendingSave->PortalActive=false;
            // Survivors retain the shared AI and search for players; daytime shields the restored shrine.
        }
        Checkpoint();
    }
    if(!Night)return;
    const int32 Serial=Weather->GetScheduleDay()-(Hour<NightEnd?1:0);
    if(Serial!=NightSerial)
    {
        if(Portal.IsValid())Portal->ClosePortal();Portal.Reset();bSiteChosen=false;SpawnFailures=0;
        if(PendingSave)PendingSave->PortalActive=false;
        const int32 EventSeed=Hills->PlaythroughSeed ? Hills->PlaythroughSeed : Hills->Seed;
        NightSerial=Serial;Random.Initialize(int32(uint32(EventSeed)^(uint32(Serial)*196613u)^0x4e495447u));
        SpawnedThisNight=WaveRemaining=0;NextPortalAttempt=Now;NextWave=Now;
        NextPlacementLog=NextSpawnLog=Now;
        // Advancing directly to a later night may skip every daytime tick.
        // Restore the new night's ward just as an observed dawn would have done.
        Shrine->SetRaidNight(false,Durability);Shrine->SetRaidNight(true,Durability);
        UE_LOG(LogTemp,Display,TEXT("HILLS_RAID night begin day=%d hour=%.2f seed=%d"),Serial,Hour,Hills->Seed);
        Checkpoint();
    }
    if(!bAssetsReady||!RestorationReady)return;
    if(!Portal.IsValid())
    {
        if(Now<NextPortalAttempt||SpawnedThisNight>=MaxPerNight)return;
        NextPortalAttempt=Now+3.;
        if(!bSiteChosen&&!ChoosePortalSite())return;
        FHitResult Ground;FCollisionQueryParams Query(SCENE_QUERY_STAT(RaidPortalFloor),true);
        const bool HitFloor=World->LineTraceSingleByChannel(Ground,PortalSite+FVector(0,0,250),PortalSite-FVector(0,0,350),ECC_Visibility,Query);
        if(!HitFloor||!IsRaidGround(Ground.GetComponent(),Hills.Get())||FMath::Abs(Ground.ImpactPoint.Z-PortalSite.Z)>80.)
        {
            // Keep the pin while asynchronous terrain collision cooks, but do not
            // strand the whole night on one permanently obstructed/stale site.
            if(++GroundWaitAttempts>=6)bSiteChosen=false;
            if(Now>=NextPlacementLog)
            {
                NextPlacementLog=Now+30.;
                UE_LOG(LogTemp,Warning,TEXT("HILLS_RAID floor pending site=%s hit=%d component=%s attempt=%d reselect=%d"),
                    *PortalSite.ToString(),int32(HitFloor),*GetNameSafe(Ground.GetComponent()),GroundWaitAttempts,int32(!bSiteChosen));
            }
            return;
        }
        // Props and trunk collision can stream in after the candidate was chosen.
        if(IsPlayerNear(Ground.ImpactPoint,3500.f)||!IsPortalSpaceClear(Ground.ImpactPoint)){bSiteChosen=false;return;}
        PortalSite=Ground.ImpactPoint;
        const FTransform Placement(PortalFacing,Ground.ImpactPoint);
        auto* Door=World->SpawnActorDeferred<AHillsNightPortal>(AHillsNightPortal::StaticClass(),Placement,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Door)return;
        const auto* GS=World->GetGameState();Door->OpenedAt=GS?GS->GetServerWorldTimeSeconds():Now;
        UGameplayStatics::FinishSpawningActor(Door,Placement);Portal=Door;
        NextSpawn=Now+WarmupSeconds;
        NextWave=NextSpawn+(WaveRemaining>0?WaveInterval:0.f);
        Checkpoint();
        UE_LOG(LogTemp,Display,TEXT("HILLS_RAID portal night=%d seed=%d position=%s"),Serial,Hills->Seed,*Ground.ImpactPoint.ToString());
    }
    if(SpawnedThisNight>=MaxPerNight||LivingCount()>=MaxAlive){SpawnFailures=0;return;}
    if(WaveRemaining==0&&Now>=NextWave)
    {WaveRemaining=FMath::Min(WaveSize,MaxPerNight-SpawnedThisNight);NextWave=Now+WaveInterval;}
    if(WaveRemaining>0&&Now>=NextSpawn)
    {
        ESpawnResult Result=SpawnOne();
        const bool NavigationFailure=Result==ESpawnResult::NoNavigation||Result==ESpawnResult::NoSpawnFloor
            ||Result==ESpawnResult::NoShrineApproach||Result==ESpawnResult::NoRoute;
        if(NavigationFailure)
        {
            const auto* GS=World->GetGameState();const double ServerNow=GS?GS->GetServerWorldTimeSeconds():Now;
            // Do not repeatedly remove the invoker while its tiles are cooking.
            // Bound this grace period so unrelated navigation work cannot stall us forever.
            if(ServerNow-Portal->OpenedAt<90.&&UNavigationSystemV1::IsNavigationBeingBuiltOrLocked(World))
                Result=ESpawnResult::NavigationPending;
        }
        const bool Spawned=Result==ESpawnResult::Spawned;
        if(Spawned){--WaveRemaining;SpawnFailures=0;}
        else if(Result==ESpawnResult::PlayerNearby||Result==ESpawnResult::NavigationPending)SpawnFailures=0;
        else ++SpawnFailures;
        NextSpawn=Now+(Spawned?2.:3.);
        if(Spawned)Checkpoint();
        if(!Spawned&&Now>=NextSpawnLog)
        {
            NextSpawnLog=Now+30.;
            UE_LOG(LogTemp,Warning,TEXT("HILLS_RAID spawn waiting reason=%s next=%s failures=%d spawned=%d remaining=%d"),
                SpawnResultName(Result),SpawnedThisNight%3==2?TEXT("fat"):TEXT("nurse"),SpawnFailures,SpawnedThisNight,WaveRemaining);
        }
        // Recover after any blocked wave/species, not only before the first nurse.
        // Preserve the unfinished wave, monster order and this night's total budget.
        if(SpawnFailures>=10)
        {
            UE_LOG(LogTemp,Warning,TEXT("HILLS_RAID relocating reason=%s spawned=%d remaining=%d"),SpawnResultName(Result),SpawnedThisNight,WaveRemaining);
            Portal->ClosePortal();Portal.Reset();bSiteChosen=false;SpawnFailures=0;
            NextPortalAttempt=Now+5.;
            Checkpoint();
        }
    }
}
void UHillsNightRaidSubsystem::Deinitialize()
{
    ReleaseNetworkLoadingPolicy();
    ReplicationGates.Reset();
    FWorldDelegates::OnWorldBeginTearDown.RemoveAll(this);
    for(const auto& Player:PlayerInvokers)if(Player.IsValid())UNavigationSystemV1::UnregisterNavigationInvoker(*Player.Get());
    for(const auto& Raider:Raiders)if(Raider.IsValid())UNavigationSystemV1::UnregisterNavigationInvoker(*Raider.Get());
    if(Preload){Preload->CancelHandle();Preload.Reset();}
    Raiders.Reset();PlayerInvokers.Reset();Super::Deinitialize();
}
