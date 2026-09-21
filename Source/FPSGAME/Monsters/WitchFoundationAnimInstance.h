#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "WitchFoundationAnimInstance.generated.h"

class UAnimSequence;

UCLASS(Transient)
class FPSGAME_API UWitchFoundationAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkClip;
    float IdleTime = 0.f;
    float WalkTime = 0.f;
    float WalkAlpha = 0.f;
    float StrideScale = 1.f;
    float GroundAlpha = 1.f;
    FVector StrideDirection = FVector::RightVector;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
