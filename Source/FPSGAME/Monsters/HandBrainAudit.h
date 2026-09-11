#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "HandBrainAudit.generated.h"
class AHandBrainMonster;class AHandBrainVillageSpawner;class ACharacter;class UFPSCombatHealthComponent;
UCLASS()
class FPSGAME_API UHandBrainAudit : public UWorldSubsystem
{
 GENERATED_BODY()
public:
 virtual void OnWorldBeginPlay(UWorld& World) override;
 virtual void Deinitialize() override;
private:
 void Step();void Check(const FString& Name,bool Pass);void Capture(const FString& Name);void PlacePlayer(float Distance);void Finish();
 FTimerHandle Timer;int32 Stage=0;float Clock=0,StageClock=0;int32 BeforeHits=0,BeforeHowl=0,BeforeKills=0;float BeforeHealth=0;
 FVector Start,PlayerBefore;TArray<FString> Passed,Failed;
 bool bGunReleased=false;int32 BeforeAmmo=0;
 TWeakObjectPtr<AHandBrainMonster> Brain;TWeakObjectPtr<AHandBrainVillageSpawner> Spawner;TWeakObjectPtr<ACharacter> Player;TWeakObjectPtr<UFPSCombatHealthComponent> Health;TWeakObjectPtr<AActor> Wall;
 TWeakObjectPtr<class UPrimitiveComponent> DeathFloor;
};
