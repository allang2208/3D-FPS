#include "DungeonBossEncounter.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "../SceneTestPortal.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "UObject/ConstructorHelpers.h"

ADungeonBossEncounter::ADungeonBossEncounter()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("EncounterRoot"));
    Gate=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("SteelGrille"));
    Gate->SetupAttachment(RootComponent);Gate->SetMobility(EComponentMobility::Movable);
    Gate->SetCollisionEnabled(ECollisionEnabled::NoCollision);Gate->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if(Cube.Succeeded())Gate->SetStaticMesh(Cube.Object);
    GateCollision=CreateDefaultSubobject<UBoxComponent>(TEXT("EncounterDoor"));
    GateCollision->SetupAttachment(RootComponent);GateCollision->SetCollisionProfileName(TEXT("BlockAll"));
    GateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GateCollision->SetCanEverAffectNavigation(false);
    RewardGate=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FinalRewardMechanicalGate"));
    RewardGate->SetupAttachment(RootComponent);RewardGate->SetMobility(EComponentMobility::Movable);
    RewardGate->SetCollisionEnabled(ECollisionEnabled::NoCollision);RewardGate->SetCanEverAffectNavigation(false);
    RewardGateCollision=CreateDefaultSubobject<UBoxComponent>(TEXT("FinalRewardGateBlocker"));
    RewardGateCollision->SetupAttachment(RootComponent);
    RewardGateCollision->SetCollisionProfileName(TEXT("BlockAll"));
    RewardGateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RewardGateCollision->SetGenerateOverlapEvents(false);RewardGateCollision->SetCanEverAffectNavigation(false);
    // Microscopic grating triangles are a poor rasterization/capsule support
    // surface. Fill only each authored tread/deck's thickness and footprint.
    // Rails, columns and machinery still export their real blocking geometry.
    auto AddWalkSurface=[this](FName Name,const FVector& Center,const FVector& Extent)
    {
        auto* Surface=CreateDefaultSubobject<UBoxComponent>(Name);
        Surface->SetupAttachment(RootComponent);
        Surface->SetRelativeLocation(Center);Surface->InitBoxExtent(Extent);
        Surface->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Surface->SetCollisionObjectType(ECC_WorldStatic);
        Surface->SetCollisionResponseToAllChannels(ECR_Ignore);
        Surface->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
        // GroundPoint uses WorldStatic traces to place the slam on this storey.
        // Visibility/weapon traces still see the original open grating.
        Surface->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
        Surface->SetGenerateOverlapEvents(false);Surface->SetCanEverAffectNavigation(true);
        Surface->SetVisibility(false);Surface->SetHiddenInGame(true);
        Surface->ComponentTags.Add(TEXT("DungeonBossWalkSurface"));
    };
#include "DungeonBossWalkSurfaces.inl"
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickInterval=.05f;
    Tags.Add(TEXT("DungeonBossEncounter"));
}

void ADungeonBossEncounter::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);Gate->ClearInstances();
    if(GateMaterial)Gate->SetMaterial(0,GateMaterial);
    auto Bar=[this](FVector Center,FVector Size){Gate->AddInstance(FTransform(FQuat::Identity,Center,Size/100.));};
    const float W=DoorSize.X,H=DoorSize.Y;
    for(float X:{-W*.5f+5,W*.5f-5})Bar(FVector(X,0,H*.5f),FVector(10,12,H));
    for(float Z:{5.f,H*.5f,H-5})Bar(FVector(0,0,Z),FVector(W,10,10));
    for(float X=-W*.5f+22;X<W*.5f-12;X+=22)Bar(FVector(X,0,H*.5f),FVector(4,6,H-16));
    GateCollision->SetRelativeLocation(DoorPoint+FVector(0,0,H*.5f));
    GateCollision->SetBoxExtent(FVector(W*.5f,8,H*.5f));
    UpdateGate();
}

void ADungeonBossEncounter::BeginPlay()
{
    Super::BeginPlay();GateOpen=1;GateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);UpdateGate();
    // Saved preview actors never start an encounter while the old layout is being replaced.
    SetActorTickEnabled(false);
}

void ADungeonBossEncounter::ActivateEncounter()
{
    if(!GetWorld()->IsGameWorld()||!HasAuthority()||bArmed)return;
    bArmed=true;SetActorTickEnabled(true);
}

void ADungeonBossEncounter::ConfigureRewardExit(UStaticMesh* LeafMesh,const FVector& Position,
    const FVector& Travel,const FVector& ClearSize,AActor* Chest,ASceneTestPortal* ReturnPortal)
{
    RewardGate->SetStaticMesh(LeafMesh);RewardDoorPoint=Position;RewardDoorTravel=Travel;
    RewardGateOpen=0;bRewardsUnlocked=false;RewardChest=Chest;RewardPortal=ReturnPortal;
    RewardGate->SetRelativeLocation(Position);
    RewardGateCollision->SetRelativeLocation(Position+FVector(0,0,ClearSize.Z*.5));
    RewardGateCollision->SetBoxExtent(ClearSize*.5);
    RewardGateCollision->SetCollisionEnabled(LeafMesh?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
    if(Chest)Chest->Tags.AddUnique(TEXT("DungeonReward.Locked"));
    if(ReturnPortal)ReturnPortal->Tags.AddUnique(TEXT("DungeonReward.Locked"));
}

void ADungeonBossEncounter::UpdateRewardExit(float DeltaSeconds)
{
    if(!RewardGate->GetStaticMesh())return;
    if(bEncounterComplete)RewardGateOpen=FMath::Min(1.f,RewardGateOpen+DeltaSeconds/2.8f);
    const float Lift=FMath::SmoothStep(0.f,1.f,RewardGateOpen);
    RewardGate->SetRelativeLocation(RewardDoorPoint+RewardDoorTravel*Lift);
    if(bEncounterComplete&&RewardGateOpen>=1.f&&!bRewardsUnlocked)
    {
        // Collision and interaction are released together after the complete lift.
        RewardGateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if(auto* Chest=RewardChest.Get())Chest->Tags.Remove(TEXT("DungeonReward.Locked"));
        if(auto* Portal=RewardPortal.Get())Portal->Tags.Remove(TEXT("DungeonReward.Locked"));
        bRewardsUnlocked=true;Tags.AddUnique(TEXT("DungeonReward.Ready"));
    }
}

bool ADungeonBossEncounter::Contains(const APawn* Pawn) const
{
    if(!IsValid(Pawn))return false;
    const FVector P=GetActorTransform().InverseTransformPosition(Pawn->GetActorLocation());
    return P.X>ArenaMin.X&&P.X<ArenaMax.X&&P.Y>ArenaMin.Y&&P.Y<ArenaMax.Y&&P.Z>ArenaMin.Z&&P.Z<ArenaMax.Z;
}

bool ADungeonBossEncounter::SpawnBoss(APawn* Player)
{
    if(!BossClass||IsValid(LiveBoss))return false;
    const auto* Defaults=BossClass->GetDefaultObject<AHandBrainMonster>();
    if(!Defaults||!Defaults->VisualMesh||!Defaults->IdleClip||!Defaults->MoveClip||!Defaults->SlamClip||!Defaults->HowlClip||!Defaults->DeathClip)return false;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FVector Ground=GetActorTransform().TransformPosition(SpawnPoint);
    const auto* Movement=Defaults->GetCharacterMovement();
    const auto* Capsule=Defaults->GetCapsuleComponent();
    FNavAgentProperties Agent=Movement->GetNavAgentPropertiesRef();
    const bool FromCapsule=Movement->ShouldUpdateNavAgentWithOwnersCollision();
    Agent.AgentRadius=FromCapsule?Capsule->GetScaledCapsuleRadius():FMath::Max(Agent.AgentRadius,Capsule->GetScaledCapsuleRadius());
    Agent.AgentHeight=FromCapsule?Capsule->GetScaledCapsuleHalfHeight()*2:FMath::Max(Agent.AgentHeight,Capsule->GetScaledCapsuleHalfHeight()*2);
    const auto* NavData=Nav?Nav->GetNavDataForProps(Agent,Ground):nullptr;
    FNavLocation Location;
    if(!NavData||!Nav->ProjectPointToNavigation(Ground,Location,FVector(150,150,100),NavData))return false;
    if(NavData->GetConfig().AgentRadius+KINDA_SMALL_NUMBER<Agent.AgentRadius||NavData->GetConfig().AgentHeight+KINDA_SMALL_NUMBER<Agent.AgentHeight)return false;
    // Never let projection move the boss to an upper platform or into another room.
    if(FMath::Abs(Location.Location.Z-Ground.Z)>55||(Location.Location-Ground).Size2D()>150)return false;
    const float HalfHeight=Defaults->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const FVector Position=Location.Location+FVector(0,0,HalfHeight+3);
    const FRotator Facing=(Player->GetActorLocation()-Position).Rotation();
    const FTransform Transform(FRotator(0,Facing.Yaw,0),Position);
    auto* Boss=GetWorld()->SpawnActorDeferred<AHandBrainMonster>(BossClass,Transform,this,nullptr,
        ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding);
    if(!Boss)return false;
    // Same health, attacks and rewards as the accepted boss. Only perception/leash cover this arena.
    Boss->AggroRadius=FMath::Max(Boss->AggroRadius,3500.f);Boss->LeashRadius=FMath::Max(Boss->LeashRadius,3600.f);
    Boss->Tags.Add(TEXT("DungeonTerminalBoss"));Boss->FinishSpawning(Transform);
    if(!IsValid(Boss)||!Boss->IsActorTickEnabled()||!Boss->GetMesh()->GetPhysicsAsset())
    {if(IsValid(Boss))Boss->Destroy();return false;}
    if(!Boss->GetController())Boss->SpawnDefaultController();
    auto* Controller=Cast<AMonsterAIController>(Boss->GetController());
    if(!Controller||!Controller->Behavior){Boss->Destroy();return false;}
    LiveBoss=Boss;Entrant=Player;bActive=true;
    Controller->SetEncounterTarget(Player);
    GateCollision->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Tags.AddUnique(TEXT("DungeonBoss.Active"));
    UE_LOG(LogTemp,Display,TEXT("DUNGEON_BOSS_STARTED %s"),*Boss->GetPathName());
    return true;
}

void ADungeonBossEncounter::UpdateGate()
{
    Gate->SetRelativeLocation(DoorPoint+FVector(0,0,GateOpen*(DoorSize.Y+16)));
}

void ADungeonBossEncounter::ResetEncounter()
{
    bActive=false;bAwaitExit=true;Entrant.Reset();
    if(IsValid(LiveBoss))LiveBoss->Destroy();LiveBoss=nullptr;
    Tags.Remove(TEXT("DungeonBoss.Active"));GateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void ADungeonBossEncounter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!bArmed||!HasAuthority())return;
    if(bActive)
    {
        if(IsValid(LiveBoss)&&LiveBoss->Health<=0)
        {
            bActive=false;bEncounterComplete=true;Tags.Remove(TEXT("DungeonBoss.Active"));Tags.AddUnique(TEXT("DungeonBoss.Cleared"));
            GateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            // Full-rate motion is needed only for the short reward-door opening.
            if(RewardGate->GetStaticMesh())SetActorTickInterval(0.f);
            UE_LOG(LogTemp,Display,TEXT("DUNGEON_BOSS_CLEARED %s"),*GetPathName());
            // The monster grants its existing kill reward once and owns its corpse lifetime.
        }
        else
        {
            auto* Player=Entrant.Get();auto* Health=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
            if(!IsValid(LiveBoss)||!Player||(Health&&Health->IsDead())||!Contains(Player))ResetEncounter();
        }
    }
    else if(!bEncounterComplete)
    {
        APawn* Inside=nullptr;
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        {
            APawn* Player=It->Get()?It->Get()->GetPawn():nullptr;
            auto* Health=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
            if(Contains(Player)&&GetActorTransform().InverseTransformPosition(Player->GetActorLocation()).Y<DoorPoint.Y-180
                &&(!Health||!Health->IsDead())){Inside=Player;break;}
        }
        if(bAwaitExit){if(!Inside)bAwaitExit=false;}
        else if(Inside&&!SpawnBoss(Inside))
        {
            // Keep the door open on missing nav/assets or an obstructed spawn. Re-enter to retry.
            bAwaitExit=true;UE_LOG(LogTemp,Warning,TEXT("DUNGEON_BOSS_SPAWN_DEFERRED: leave/re-enter the arena to retry"));
        }
    }
    GateOpen=FMath::FInterpConstantTo(GateOpen,bActive?0.f:1.f,DeltaSeconds,2.f);UpdateGate();
    UpdateRewardExit(DeltaSeconds);
    if(bEncounterComplete&&GateOpen>=1&&(!RewardGate->GetStaticMesh()||bRewardsUnlocked))SetActorTickEnabled(false);
}

void ADungeonBossEncounter::EndPlay(const EEndPlayReason::Type Reason)
{
    if(IsValid(LiveBoss))LiveBoss->Destroy();LiveBoss=nullptr;
    Super::EndPlay(Reason);
}
