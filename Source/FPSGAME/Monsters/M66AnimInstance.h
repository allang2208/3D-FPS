#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "M66AnimInstance.generated.h"
class UAnimSequence;
UCLASS(Transient)
class FPSGAME_API UM66AnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Idle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Move;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Left;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Right;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Reaction;
    float ReactionTime=0.f;
    uint32 ReactionVersion=0;
    uint32 AttackVersion=0;
    bool bReaction=false,bLoopReaction=false;
    bool bHoldKnockdownDeath=false;
    double LifeSeconds=0.;
    float LifeWeight=0.f;
    float Phase=0,IdleTime=0,Activity=0,TurnWeight=0,RightWeight=.5f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    FVector PreviousLocation=FVector::ZeroVector;
    FVector SupportCentreLocal=FVector::ZeroVector;
    float PreviousYaw=0;
    bool bHaveTransform=false;
};
