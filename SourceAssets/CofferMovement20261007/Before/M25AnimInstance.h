#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "M25AnimInstance.generated.h"

/** Independent idle clock and distance-driven crawl phase, blended over 0.25 s. */
UCLASS(Transient)
class FPSGAME_API UM25AnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UM25AnimInstance();
    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    float IdleTime = 0.f;
    float CrawlTime = 0.f;
    float LocomotionWeight = 0.f;
    float BiteTime = 0.f;
    float BiteWeight = 0.f;
    float HitTime = 0.f, HitWeight = 0.f;
    float DeathTime = 0.f, DeathWeight = 0.f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    bool bCrawling = false;
};
