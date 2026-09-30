#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "FPSGunplayAnimInstance.generated.h"

class UAnimSequence;

// Local first-person presentation. Gameplay owns the clock; the graph only blends poses.
UCLASS(Transient)
class FPSGAME_API UFPSGunplayAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AimClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActionClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SprintClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SprintLoopClip;
    float SprintTime = 0.0f;
    float SprintAlpha = 0.0f;
    float SprintLoopTime = 0.0f;
    float SprintLoopAlpha = 0.0f;
    float BaseTime = 0.0f;
    float AimAlpha = 0.0f;
    float ActionTime = 0.0f;
    float ActionAlpha = 0.0f;
    bool bRevolver = false;
    int32 RevolverLiveRounds = 6;
    int32 RevolverCartridges = 6;
    bool bDualPistolAim=false;
    int32 DualPistolSide=0;
    float DualPistolAimAlpha=0.f;
    FVector DualPistolAimTargetWorld=FVector::ZeroVector;
    // GripLayer56 (GripPoseLayer.h): per-channel grip layer and its reference pairs.
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripIdleBase;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripIdleFamily;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripAimBase;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripAimFamily;
    bool bGripIdle=false,bGripAim=false,bGripSprint=false,bGripAction=false,bGripActionAim=false;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
