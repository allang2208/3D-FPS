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
private:
    FWeaponGripComponentLayer GripLayer;
    TArray<FTransform> TransitionLocal;
    float TransitionAge=0.f,TransitionSeconds=0.f;
};
