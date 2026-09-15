#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSStairAudit.generated.h"

/** Opt-in real-player stair acceptance. Only created by -StairMovementAudit. */
UCLASS()
class UFPSStairAudit : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSStairAudit();
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    void SetupCase();
    void Key(FKey InputKey, bool bDown);
    void Check(bool bPass, const TCHAR* Message);
    UPROPERTY() TArray<TObjectPtr<AActor>> Fixture;
    int32 Case = 0, Stage = 0, Failures = 0, Checks = 0, Frame = 0;
    float Elapsed = 0, MaxViewDelta = 0, MaxHorizontalDelta = 0, MaxOffset = 0;
    float StartZ = 0, HighestZ = 0, JumpPressTime = 0;
    bool bAirborne = false, bJumpSent = false;
    FVector PreviousPosition = FVector::ZeroVector;
    float PreviousViewZ = 0;
    FString Samples, Output;
};
