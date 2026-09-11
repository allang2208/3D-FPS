#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "NurseZombieAudit.generated.h"
class ANurseZombie;
class ACharacter;
UCLASS()
class FPSGAME_API UNurseZombieAudit : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
private:
    void Step();
    void Check(const TCHAR* Name, bool Passed);
    void Capture(const TCHAR* Name);
    void PlaceForMelee();
    FTimerHandle Timer;
    TWeakObjectPtr<ANurseZombie> Nurse;
    TWeakObjectPtr<ACharacter> Player;
    FVector Start,PlayerStart;
    int32 Stage=0,Failures=0;
    float Clock=0,StageClock=0,BeforeHealth=0,ExpectedContactDamage=0;
    bool SawAttack=false;
};
