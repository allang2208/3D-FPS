#pragma once

#include "../Skills/FPSCastingMeshComponent.h"
#include "RuneSwordMeshComponent.generated.h"

/** Sword entry/recovery blends, evaluated before the final bone/socket publication. */
UCLASS()
class FPSGAME_API URuneSwordMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    void CaptureWhirlwindEntry();
    void SetWhirlwindEntryTime(float Seconds);
    void ClearWhirlwindEntry();
    void CaptureLocomotionEntry();
    void LimitLocomotionEntry(float Seconds);
    void AdvanceLocomotionEntry(float Delta);
    void CacheQuickCombatIdlePose();
    void SetQuickCombatRecoveryWeight(float Weight);
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> EntryMesh;
    TArray<FTransform> EntryPose;
    float EntryTime=0.f;
    static constexpr float EntrySeconds=.1f;
    void ApplyWhirlwindEntry();
    void ApplyQuickCombatRecovery();
    void BlendSupportedPoses(const TArray<FTransform>& From,const TArray<FTransform>& To,
        float Alpha,bool bPreserveBoneLengths);
    TWeakObjectPtr<USkeletalMesh> RecoveryMesh;
    TArray<FTransform> RecoveryIdlePose;
    float RecoveryWeight=0.f;
    bool bCaptureRecoveryIdle=false;
    float EntryDuration=EntrySeconds;
};
