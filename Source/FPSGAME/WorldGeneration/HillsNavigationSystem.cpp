#include "HillsNavigationSystem.h"
#include "ForestVillageMap.h"
#include "AI/NavigationSystemConfig.h"
#include "GameFramework/WorldSettings.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "UObject/Package.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationData.h"
#include "ChapelShrine.h"
#include "HillsNightPortal.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../NPC/VillageArtisanMerchant.h"
#include "GameFramework/Pawn.h"
#if WITH_EDITOR
#include "Builders/CubeBuilder.h"
#include "Components/BrushComponent.h"
#include "Model.h"
#include "Engine/Polys.h"
#endif

UHillsNavigationSystem::UHillsNavigationSystem(const FObjectInitializer& Initializer):Super(Initializer)
{
    bGenerateNavigationOnlyAroundNavigationInvokers=true;
    bAutoCreateNavigationData=true;
    bAllowClientSideNavigation=false;
    ActiveTilesUpdateInterval=.5f;
    InvokersMaximumDistanceFromSeed=-1.;
}

void UHillsNavigationSystem::OnWorldInitDone(FNavigationSystemRunMode Mode)
{
    // Old saved Hills maps only enabled agents 0/1 on this bounds volume.
    // Repair before Super gathers bounds and creates dynamic navigation data;
    // this also reaches existing cooked maps without an editor resave.
    for(TActorIterator<ANavMeshBoundsVolume> It(GetWorld());It;++It)
        if(It->ActorHasTag(TEXT("HillsNightRaidNavigation")))
        {
            It->SupportedAgents=FNavAgentSelector();
            It->SupportedAgents.MarkInitialized();
        }
    Super::OnWorldInitDone(Mode);
    // Geometry gathering / completed-tile installation still run on the game
    // thread. The default wide launch batch multiplied across all agent profiles
    // cost 136-172 ms at entry. Bound submissions while keeping tile resolution,
    // invoker coverage and every supported agent unchanged.
    SetMaxSimultaneousTileGenerationJobsCount(2);
    UE_LOG(LogTemp,Display,TEXT("HILLS_NAV tile jobs per profile=2 profiles=%d"),NavDataSet.Num());
}

void UHillsNavigationSystem::RegisterInvoker(AActor& Invoker,float GenerationRadius,float RemovalRadius,
    const FNavAgentSelector& Agents,ENavigationInvokerPriority Priority)
{
    FNavAgentSelector Selected=Agents;
    if(Invoker.IsA<AChapelShrine>()||Invoker.IsA<AHillsNightPortal>())
    {
        // The 140-150 m raid pins still serve only the original raid bodies.
        // Enabling large agents must not multiply every village's tile workload.
        Selected.Empty();
        for(int32 Index:{0,1})if(Agents.Contains(Index))Selected.Set(Index);
    }
    else if(const auto* Pawn=Cast<APawn>(&Invoker);Pawn &&
        (Pawn->IsA<AVillageArtisanMerchant>() || Pawn->FindComponentByClass<UMonsterCombatComponent>()))
    {
        // Prefer the configured profile even before its dynamic data registers;
        // GetNavDataForProps can temporarily return a smaller fallback mesh.
        int32 Index=GetSupportedAgentIndex(Pawn->GetNavAgentPropertiesRef());
        if(Index==INDEX_NONE)
            if(const auto* Data=GetNavDataForProps(Pawn->GetNavAgentPropertiesRef(),Pawn->GetNavAgentLocation()))
                Index=GetSupportedAgentIndex(Data);
        if(Index!=INDEX_NONE)
        {Selected.Empty();if(Agents.Contains(Index))Selected.Set(Index);}
    }
    // Player invokers retain all profiles so an F6 spawn can find its own tiles
    // before the new monster exists. Monsters then maintain their own profile.
    Selected.MarkInitialized();
    Super::RegisterInvoker(Invoker,GenerationRadius,RemovalRadius,Selected,Priority);
}

bool UHillsNavigationSystem::InstallOnMap(UObject* Context)
{
#if WITH_EDITOR
    auto* World=GEngine->GetWorldFromContextObject(Context,EGetWorldErrorMode::ReturnNull);
    if(!World||(!ForestVillageMap::Is(World)&&World->GetPackage()->GetName()!=TEXT("/Game/GameMaps/L_TemperateHills_Initial")))return false;
    auto* Settings=World->GetWorldSettings();
    // The override is transient. Edit the map's serialized config, so the next game uses it too.
    if(Settings->GetNavigationSystemConfigOverride())return false;
    auto* Config=Settings->GetNavigationSystemConfig();
    if(!Config)return false;
    Config->Modify();
    Config->NavigationSystemClass=FSoftClassPath(UHillsNavigationSystem::StaticClass());
    Config->MarkPackageDirty();Settings->MarkPackageDirty();
    ANavMeshBoundsVolume* Bounds=nullptr;
    for(TActorIterator<ANavMeshBoundsVolume> It(World);It;++It)
        if(It->ActorHasTag(TEXT("HillsNightRaidNavigation"))){Bounds=*It;break;}
    if(!Bounds)Bounds=World->SpawnActor<ANavMeshBoundsVolume>();
    if(!Bounds)return false;
    Bounds->Tags.AddUnique(TEXT("HillsNightRaidNavigation"));Bounds->SetActorLabel(TEXT("Hills_NightRaid_Navigation"));
    Bounds->SupportedAgents=FNavAgentSelector();Bounds->SupportedAgents.MarkInitialized();
    if(!Bounds->Brush)
    {
        Bounds->Brush=NewObject<UModel>(Bounds,NAME_None,RF_Transactional);Bounds->Brush->Initialize(Bounds,false);
        Bounds->Brush->Polys=NewObject<UPolys>(Bounds->Brush,NAME_None,RF_Transactional);Bounds->GetBrushComponent()->Brush=Bounds->Brush;
    }
    auto* Cube=NewObject<UCubeBuilder>(Bounds);Cube->X=102400.;Cube->Y=102400.;Cube->Z=60000.;
    if(!Cube->Build(World,Bounds))return false;
    Bounds->GetBrushComponent()->BuildSimpleBrushCollision();Bounds->SetActorLocation(ForestVillageMap::Is(World)?FVector(ForestVillageMap::Bounds().GetCenter(),0.):FVector::ZeroVector);
    Bounds->ReregisterAllComponents();Bounds->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
