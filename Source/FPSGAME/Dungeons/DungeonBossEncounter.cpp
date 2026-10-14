#include "DungeonBossEncounter.h"
#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "../SceneTestPortal.h"
#include "Engine/StaticMesh.h"
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
    PrimaryActorTick.bCanEverTick=false;
    Tags.Add(TEXT("DungeonTerminalFixtures"));
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
    Gate->SetRelativeLocation(DoorPoint+FVector(0,0,DoorSize.Y+16));
    GateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void ADungeonBossEncounter::ConfigureRewardExit(UStaticMesh* LeafMesh,const FVector& Position,
    const FVector& Travel,const FVector& ClearSize,AActor* Chest,ASceneTestPortal* ReturnPortal)
{
    // Preserve travel and walkable structure without pretending the old boss was killed.
    // The reward chest remains locked until new gameplay rules are authored.
    RewardGate->SetStaticMesh(LeafMesh);
    RewardGate->SetRelativeLocation(Position+Travel);
    RewardGateCollision->SetRelativeLocation(Position+Travel+FVector(0,0,ClearSize.Z*.5));
    RewardGateCollision->SetBoxExtent(ClearSize*.5);
    RewardGateCollision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(Chest)Chest->Tags.AddUnique(TEXT("DungeonReward.Locked"));
    if(ReturnPortal)ReturnPortal->Tags.Remove(TEXT("DungeonReward.Locked"));
}
