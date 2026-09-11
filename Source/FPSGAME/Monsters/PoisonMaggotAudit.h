#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "PoisonMaggotAudit.generated.h"
class APoisonMaggotMonster;class APoisonMaggotSpawner;class ACharacter;class ACameraActor;class AStaticMeshActor;class UPrimitiveComponent;
UCLASS()
class FPSGAME_API UPoisonMaggotAudit : public UWorldSubsystem
{
 GENERATED_BODY()
public:virtual void OnWorldBeginPlay(UWorld& World) override;virtual void Deinitialize() override;
private:
 void Step();void VillageStep();void FrameVillageCamera();void Check(const FString& Name,bool Pass);void Finish();void Capture(const FString& Name);void Next();void Arena();
 TWeakObjectPtr<UPrimitiveComponent> VillageGround;
 bool bVillage=false;float LastNavLog=-100;
 FTimerHandle Timer;TWeakObjectPtr<APoisonMaggotMonster> Monster;TWeakObjectPtr<APoisonMaggotSpawner> Spawner;TWeakObjectPtr<ACharacter> Player;TWeakObjectPtr<ACameraActor> Camera;TWeakObjectPtr<AStaticMeshActor> Wall;
 int32 Stage=0,BeforeShots=0,BeforeHits=0;float StartTime=0,StageStart=0,MaxSide=0,BeforeHealth=0,BeforeMonsterHP=0,BeforeYaw=0;bool Flag=false;FVector BeforeLocation;
 TArray<FString> Passed,Failed;
};
