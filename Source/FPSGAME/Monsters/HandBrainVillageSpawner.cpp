#include "HandBrainVillageSpawner.h"
#include "HandBrainMonster.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "TimerManager.h"
AHandBrainVillageSpawner::AHandBrainVillageSpawner(){RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("SpawnPoint"));PrimaryActorTick.bCanEverTick=false;}
void AHandBrainVillageSpawner::BeginPlay(){Super::BeginPlay();if(HasAuthority()&&bEnabled)GetWorldTimerManager().SetTimer(Timer,this,&AHandBrainVillageSpawner::SpawnMonster,1.f,false);}
void AHandBrainVillageSpawner::SpawnMonster()
{
 if(!HasAuthority()||!bEnabled||IsValid(LiveMonster)||!MonsterClass)return;
 FActorSpawnParameters P;P.Owner=this;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
 LiveMonster=GetWorld()->SpawnActor<AHandBrainMonster>(MonsterClass,GetActorLocation(),GetActorRotation(),P);
 if(LiveMonster){++SpawnCount;LiveMonster->OnDestroyed.AddDynamic(this,&AHandBrainVillageSpawner::MonsterDestroyed);UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_VILLAGE_SPAWN count=%d position=%s"),SpawnCount,*LiveMonster->GetActorLocation().ToString());}
 else GetWorldTimerManager().SetTimer(Timer,this,&AHandBrainVillageSpawner::SpawnMonster,10.f,false);
}
void AHandBrainVillageSpawner::MonsterDestroyed(AActor*){LiveMonster=nullptr;if(bEnabled&&!IsActorBeingDestroyed())GetWorldTimerManager().SetTimer(Timer,this,&AHandBrainVillageSpawner::SpawnMonster,FMath::Max(1.f,RespawnSeconds),false);}
void AHandBrainVillageSpawner::EndPlay(const EEndPlayReason::Type Reason){GetWorldTimerManager().ClearTimer(Timer);if(IsValid(LiveMonster))LiveMonster->OnDestroyed.RemoveDynamic(this,&AHandBrainVillageSpawner::MonsterDestroyed);Super::EndPlay(Reason);}
