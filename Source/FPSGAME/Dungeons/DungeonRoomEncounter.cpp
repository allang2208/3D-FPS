#include "DungeonRoomEncounter.h"
#include "Components/SceneComponent.h"

ADungeonRoomEncounter::ADungeonRoomEncounter()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("RetiredSpawnerRoot"));
    PrimaryActorTick.bCanEverTick=false;
}
