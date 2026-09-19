#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MonsterStairAudit.generated.h"
class ACharacter;
class ACameraActor;

/** Opt-in, rendered movement/path-following regression using the shipped monster blueprints. */
UCLASS()
class FPSGAME_API UMonsterStairAudit : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UMonsterStairAudit, STATGROUP_Tickables); }
private:
    void Setup();
    void Check(bool Pass, const TCHAR* Name);
    void FinishCase();
    void Finish();
    UPROPERTY() TObjectPtr<ACharacter> Monster;
    UPROPERTY() TObjectPtr<ACameraActor> Camera;
    UPROPERTY() TArray<TObjectPtr<AActor>> Fixture;
    FString Output, Samples;
    int32 Case = 0, Species = 0, Stage = 0, Frame = 0, Checks = 0, Failures = 0;
    float Time = 0, MaxVisualSpeed = 0, MaxHorizontalSpeed = 0, MaxOffset = 0;
    float BaselineMeshZ = 0, DeathOffset = 0;
    bool bAirborne = false, bStopped = false, bKilled = false, bFinished = false;
    bool bSingleCase = false;
    int32 CompletedCases = 0;
    FVector PreviousMesh, PreviousCapsule, Start, Goal;
};
