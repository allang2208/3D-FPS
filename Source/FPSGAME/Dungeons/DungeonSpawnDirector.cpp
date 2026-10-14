#include "DungeonSpawnDirector.h"
#include "Components/SceneComponent.h"

ADungeonSpawnDirector::ADungeonSpawnDirector()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("RetiredSpawnerRoot"));
    PrimaryActorTick.bCanEverTick=false;
}
