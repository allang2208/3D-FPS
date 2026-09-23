#include "DungeonStorageCabinet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
ADungeonStorageCabinet::ADungeonStorageCabinet()
{
    Tags.Add(TEXT("DungeonStorageCabinet"));
    Mesh->SetVisibility(false);Mesh->SetHiddenInGame(true);
    if(auto* Box=FindComponentByClass<UBoxComponent>())Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CabinetMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CabinetMesh"));CabinetMesh->SetupAttachment(RootComponent);
    CabinetMesh->SetCollisionProfileName(TEXT("BlockAll"));
}
