#pragma once
#include "Components/SkeletalMeshComponent.h"
#include "../Weapons/WeaponGripComponentLayer.h"
#include "FPSBodyWeaponMeshComponent.generated.h"

/** World weapon consumes the same authored hold correction as its viewmodel. */
UCLASS()
class UFPSBodyWeaponMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    UPROPERTY(Transient) TObjectPtr<class UWeaponGripProfile> GripProfile;
    virtual void FinalizeBoneTransform() override;
    void CaptureHoldTransition(float Seconds);
    void AdvanceHoldTransition(float Delta);
    bool IsHoldTransitionActive() const {return TransitionAge<TransitionSeconds;}
    void PublishMechanicalPose(const TArray<FTransform>& Pose);
    uint64 GetUnchangedPoseSkipCount() const { return UnchangedPoseSkipCount; }
private:
    FWeaponGripComponentLayer GripLayer;
    TArray<FTransform> TransitionLocal;
    float TransitionAge=0.f,TransitionSeconds=0.f;
    TWeakObjectPtr<USkeletalMesh> LastPublishedMesh;
    const FSkeletalMeshObject* LastPublishedObject=nullptr;
    uint32 LastPublishedRevision=0;
    uint64 LastPublishedFrame=MAX_uint64,UnchangedPoseSkipCount=0;
    int32 LastPublishedLOD=INDEX_NONE;
    bool bPoseHistorySettled=false;
};
