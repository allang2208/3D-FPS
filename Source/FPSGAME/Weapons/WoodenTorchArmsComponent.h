#pragma once

#include "../Skills/FPSCastingMeshComponent.h"
#include "WoodenTorchArmsComponent.generated.h"

UCLASS()
class FPSGAME_API UWoodenTorchArmsComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    // Native V7 pose and the torch grip relative to an unscaled wrist in centimetres.
    static FTransform BuildStaffCarry(USkeletalMesh& Mesh, int32 Side, TArray<FTransform>& Pose, int32 SwingKey=INDEX_NONE);
    static FTransform MirrorContact(const FTransform& Contact);
    FTransform ConfigureCarry(USkeletalMesh& Mesh, int32 Side);
    FTransform AuthoredSwingContact(const struct FStaffCastPose& Motion) const;
    virtual void FinalizeBoneTransform() override;
private:
    TArray<FTransform> CarryPose;
    TArray<FTransform> CarryLocal, Reference;
    TArray<int32> LeftChain;
    TArray<FTransform> LeftSwingLocal[5];
    FTransform WristInGrip;
    void ApplyOffhandSwing(const struct FStaffCastPose& Motion, TArray<FTransform>& Pose) const;
    int32 LeftRoot=INDEX_NONE,LeftWrist=INDEX_NONE;
};
