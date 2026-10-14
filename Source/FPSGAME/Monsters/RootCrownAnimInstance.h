#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "RootCrownAnimInstance.generated.h"
class UAnimSequence;

/** Presentation follows replicated motion. It never selects targets or moves the actor. */
UCLASS(Transient)
class FPSGAME_API URootCrownAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Idle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Move;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Left;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Right;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Slash;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Reaction;
    float ReactionTime=0.f;
    bool bReaction=false,bLoopReaction=false,bDeathHandoffSample=false;
    uint32 ReactionVersion=0;
    float SlashTime=0.f,SlashBlend=0.f;
    float Phase=0.f,IdleTime=0.f,Activity=0.f,TurnWeight=0.f,RightWeight=.5f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    FVector PreviousLocation=FVector::ZeroVector;
    float PreviousYaw=0.f;
    bool bHaveTransform=false;
    uint32 PreviousSlashSerial=0;
};
