#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/PoseSnapshot.h"
#include "NightWardenAnimInstance.generated.h"
class UAnimSequence;

UCLASS(Transient)
class FPSGAME_API UNightWardenAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AttackClip;
    UPROPERTY(Transient) FPoseSnapshot EntryPose;
    float IdleTime = 0.f, WalkTime = 0.f, WalkAlpha = 0.f;
    float AttackTime = 0.f, AttackAlpha = 0.f, EntryAlpha = 1.f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    uint32 LastAttackSerial = 0;
    bool bWasAttacking = false;
};
