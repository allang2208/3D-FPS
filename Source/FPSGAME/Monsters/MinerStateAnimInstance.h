#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/PoseSnapshot.h"
#include "MinerStateAnimInstance.generated.h"

class UAnimSequence;

// Presentation only. Attacks keep the existing authoritative combat clock.
UCLASS(Transient)
class FPSGAME_API UMinerStateAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    void StartClip(UAnimSequence* Clip,bool bLoop,const FPoseSnapshot& FromPose);
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentClip;
    UPROPERTY(Transient) FPoseSnapshot PreviousPose;
    float ClipTime=0.f;
    float PlayRate=1.f;
    float BlendAlpha=1.f;
private:
    bool bLooping=false;
    float BlendElapsed=.16f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
