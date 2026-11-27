#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "LumberjackAnimInstance.generated.h"

class UAnimSequence;

UENUM()
enum class ELumberjackAnimState : uint8
{
    Idle = 0,
    Walk,
    ChopTree,
    SplitLog,
    SawLog,
    CarryLogWalk,
    DriveWagon,
    SitTavern,
};

/**
 * Lightweight native C++ AnimInstance for the 3 restored Lumber Mill workers (SK_Smith_Body / Jason rig).
 * Crossfades smoothly between standing breath, distance-synced walk, and the 5 dedicated R52 3P clips.
 */
UCLASS(Transient)
class FPSGAME_API ULumberjackAnimInstance : public UAnimInstance
{
    GENERATED_BODY()

public:
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ChopTreeClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SplitLogClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SawLogClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CarryLogWalkClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> DriveWagonClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SitTavernClip;

    void SetAnimInputs(ELumberjackAnimState InState, float InSpeedCmPerSec, float InRateScale = 1.f);
    float GetActiveNormalizedPhase() const { return ActiveNormalizedPhase; }
    ELumberjackAnimState GetActiveState() const { return TargetState; }

protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;

private:
    ELumberjackAnimState TargetState = ELumberjackAnimState::Idle;
    float MoveSpeedCmPerSec = 0.f;
    float ActionRateScale = 1.f;
    float ActiveNormalizedPhase = 0.f;

    friend struct FLumberjackAnimProxy;
};
