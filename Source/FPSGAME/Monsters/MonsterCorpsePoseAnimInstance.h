#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/PoseSnapshot.h"
#include "MonsterCorpsePoseAnimInstance.generated.h"

/** Immutable corpse pose, independent of humanoid or quadruped animation graphs. */
UCLASS(Transient)
class FPSGAME_API UMonsterCorpsePoseAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    void HoldPose(const FPoseSnapshot& Pose) { FrozenPose = Pose; }
    UPROPERTY(Transient) FPoseSnapshot FrozenPose;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
