#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "FPSPlayerBodyTypes.h"
#include "FPSBodyReactionState.h"
#include "FPSPlayerBodyAnimInstance.generated.h"

/** Independent third-person graph. Explicit samples never execute gameplay notifies. */
UCLASS(Transient)
class FPSGAME_API UFPSPlayerBodyAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(Transient) TMap<FName, TObjectPtr<class UAnimSequence>> Clips;
    FFPSBodyState BodyState;
    FFPSBodyState UpperState;
    FFPSBodyState MotionState;
    FFPSBodyReactionState Reactions;
    FTransform LeftGripFromRight = FTransform::Identity;
    bool bHasLeftGrip = false;
    float Clock = 0.f;
    float Speed = 0.f;
    float Direction = 0.f;
    float VerticalSpeed = 0.f;
    bool bFalling = false;
    float CrouchAlpha = 0.f;
    float UpperAlpha = 0.f;
    float MotionAlpha = 0.f;
    float AimAlpha = 0.f;
    float SprintAlpha = 0.f;
    float AirAlpha = 0.f;
    float AirTime = 0.f;
    float LandTime = 1.f;
    bool bPreviouslyFalling = false;
    FVector PoseScale = FVector::OneVector;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    // Game-thread equipment adapter; the proxy copies these before evaluation.
    TArray<FTransform> EquipmentFingers;
    uint8 EquipmentGripHands = 0;
    bool bBowPose = false;
    FTransform BowHands[2];
    FQuat StaffHandRotation=FQuat::Identity;
    TArray<FTransform> ActionFingers;
    FTransform ActionHands[2];
    uint8 ActionFingerMask=0,ActionWristMask=0;
    bool bCoupledActionWrists=false;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
