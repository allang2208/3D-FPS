#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "InfectedMinerAudit.generated.h"
class AInfectedMiner;
class AInfectedMinerSpawner;
class ACharacter;
class AActor;
class UPrimitiveComponent;

UCLASS()
class FPSGAME_API UInfectedMinerAudit : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
private:
    void Step();
    void Check(const TCHAR* Name,bool Passed);
    void Capture(const TCHAR* Name);
    void Place(float Distance);
    void Next(int32 Value);
    void Finish();
    FTimerHandle Timer;
    TWeakObjectPtr<AInfectedMiner> Miner;
    TWeakObjectPtr<AInfectedMinerSpawner> Spawner;
    TWeakObjectPtr<ACharacter> Player;
    TWeakObjectPtr<AActor> Wall;
    TWeakObjectPtr<UPrimitiveComponent> DeathFloor;
    FVector PlayerStart,Start,Forward;
    int32 Stage=0,Failures=0,BeforeHits=0,BeforeKills=0;
    float Clock=0,StageClock=0,BeforeHealth=0,ExpectedDamage=0,CalfLengthBefore=0,LastStepTime=-1;
    bool Started=false;
    TArray<TPair<FString,bool>> Checks;
};
