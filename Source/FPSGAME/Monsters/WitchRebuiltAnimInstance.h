#pragma once
#include "CoreMinimal.h"
#include "WitchSpellAnimInstance.h"
#include "WitchRebuiltAnimInstance.generated.h"

/** Source contact curves drive foot support in locomotion, turns and spells. */
UCLASS(Transient)
class FPSGAME_API UWitchRebuiltAnimInstance : public UWitchSpellAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> TurnClip;
    float IdleTime = 0.f, WalkTime = 0.f, TurnTime = 0.f;
    float WalkAlpha = 0.f, TurnAlpha = 0.f, StrideScale = 1.f, GroundAlpha = 1.f;
    FVector StrideDirection = FVector::RightVector;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    bool bHasYaw = false;
    float PreviousYaw = 0.f;
};
