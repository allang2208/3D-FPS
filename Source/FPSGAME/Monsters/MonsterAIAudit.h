#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MonsterAIAudit.generated.h"
class ANurseZombie;class ACharacter;
UCLASS()
class FPSGAME_API UMonsterAIAudit:public UWorldSubsystem
{
 GENERATED_BODY()
public:virtual void OnWorldBeginPlay(UWorld& World) override;virtual void Deinitialize() override;
private:
 void Step();void Check(const FString& Name,bool Pass);void Finish();void Capture(const FString& Name);
 FTimerHandle Timer;TWeakObjectPtr<ANurseZombie> Nurse;TWeakObjectPtr<ACharacter> Player;
 int32 Stage=0;float Time=0,StageTime=0,MaxSide=0,Before=0;bool SawChase=false,FollowupHit=false;TArray<FString> Passed,Failed;
};
