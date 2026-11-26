#pragma once

#include "../Skills/FPSCastingMeshComponent.h"
#include "WeaponGripComponentLayer.h"
#include "SwordGripClearance.h"
#include "RuneSwordMeshComponent.generated.h"

class UWeaponGripProfile;
struct FColdSteelItem;
/** Sword entry/recovery blends, evaluated before the final bone/socket publication. */
UCLASS()
class FPSGAME_API URuneSwordMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    UWeaponGripProfile* GetGripProfile() const {return GripProfile;}
    void SetGripProfile(UWeaponGripProfile* Profile) {GripProfile=Profile;}
    void SetGripClearance(const FColdSteelItem* Item);
    void CaptureWhirlwindEntry();
    void SetWhirlwindEntryTime(float Seconds);
    void ClearWhirlwindEntry();
    void CaptureLocomotionEntry(float Seconds=.1f,bool bPreserveShaftGrip=false,bool bFromWrists=false);
    void LimitLocomotionEntry(float Seconds);
    void AdvanceLocomotionEntry(float Delta);
    void CacheQuickCombatIdlePose();
    void SetQuickCombatRecoveryWeight(float Weight);
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> EntryMesh;
    TArray<FTransform> EntryPose;
    TArray<FTransform> EntryTargetPose;
    float EntryTime=0.f;
    static constexpr float EntrySeconds=.1f;
    void ApplyWhirlwindEntry();
    void BlendRidgeEntry(float Alpha);
    void ApplyQuickCombatRecovery();
    void BlendSupportedPoses(const TArray<FTransform>& From,const TArray<FTransform>& To,
        float Alpha,bool bPreserveBoneLengths,bool bPreserveShaftGrip=false);
    TWeakObjectPtr<USkeletalMesh> RecoveryMesh;
    TArray<FTransform> RecoveryIdlePose;
    float RecoveryWeight=0.f;
    bool bCaptureRecoveryIdle=false;
    float EntryDuration=EntrySeconds;
    bool bEntryShaftGrip=false;
    bool bEntryFromWrists=false;
    UPROPERTY(Transient) TObjectPtr<class UWeaponGripProfile> GripProfile;
    FWeaponGripComponentLayer GripLayer;
    FSwordGripClearance GripClearance;
    FString GripFitDefinition,GripFitData;
    bool bRefreshGripIdle=false;
};
