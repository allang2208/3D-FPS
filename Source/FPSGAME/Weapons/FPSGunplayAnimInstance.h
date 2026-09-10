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
    float BaseTime = 0.0f;
    float AimAlpha = 0.0f;
    float ActionTime = 0.0f;
    float ActionAlpha = 0.0f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
