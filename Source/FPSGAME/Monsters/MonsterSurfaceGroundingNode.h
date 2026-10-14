#pragma once
#include "CoreMinimal.h"
#include "Animation/PoseSnapshot.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

class ACharacter;
class USkeletalMesh;

/** Terrain overlay for the existing M03/04/05/07/27, M14 and M25 rigs.
 * Authoring, locomotion phase and combat clocks remain owned by their players. */
struct FMonsterSurfaceGroundingNode : FAnimNode_SkeletalControlBase
{
    explicit FMonsterSurfaceGroundingNode(UAnimInstance* Instance);
    void Prepare(const ACharacter* Owner, float DeltaSeconds);
    FPoseSnapshot UncorrectedPose;
    bool IsGrounding() const { return Enabled; }
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& Out) override;
private:
    enum class ERig : uint8 { None, Biped, RootFan, Tendrils, Tripod };
    struct FLimb
    {
        FBoneReference Upper, Lower, Foot;
        int32 EndMeshIndex=INDEX_NONE;
        bool VirtualEnd=false, Valid=false;
        FVector EndLocal=FVector::ZeroVector, Sole[2], ReferencePole=FVector::ForwardVector;
        FVector Contact=FVector::ZeroVector, Normal=FVector::UpVector;
        FVector SmoothNormal=FVector::UpVector;
        float Correction=0.f;
    };
    ERig Rig=ERig::None;
    TArray<FLimb> Limbs;
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    FTransform Frame=FTransform::Identity;
    FVector PivotCS=FVector::ZeroVector, ForwardCS=FVector::ForwardVector;
    FQuat Tilt=FQuat::Identity, WantedTilt=FQuat::Identity;
    float Height=0.f, WantedHeight=0.f, MinimumHeight=-70.f, QueryAge=1.f, Dt=0.f;
    bool Enabled=false, ReferenceReady=false, ResetPose=true;
    uint64 PreparedFrame=0, EvaluatedFrame=MAX_uint64;
    void Configure(const ACharacter* Owner);
    void CacheReference(const ACharacter* Owner);
    FTransform Grounded(const FTransform& Bone, float Compression=0.f) const;
};
