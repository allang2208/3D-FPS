#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

class ABellowSacLobber;
class UQuadrupedTemplateAnimInstance;
class USkeletalMesh;

/** M-09's original three/four-segment limbs, with independent scene support.
 * Traces and reference caching stay on the game thread; evaluation uses copied data. */
struct FBellowGroundingNode : FAnimNode_SkeletalControlBase
{
    FBellowGroundingNode();
    void Prepare(const ABellowSacLobber* Monster, const UQuadrupedTemplateAnimInstance* Anim, float DeltaSeconds);
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& Out) override;
private:
    struct FLeg
    {
        FBoneReference Chain[5];
        int32 Count = 0, FootMeshIndex = INDEX_NONE;
        FName ToeName;
        FVector Sole[2] = {FVector::ZeroVector, FVector::ZeroVector};
        FVector Point = FVector::ZeroVector, Normal = FVector::UpVector;
        float PhaseOffset = 0.f;
        bool Valid = false;
    };
    FLeg Legs[4];
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    FTransform Frame = FTransform::Identity;
    FVector PivotCS = FVector::ZeroVector;
    FQuat Tilt = FQuat::Identity, WantedTilt = FQuat::Identity;
    float Height = 0.f, WantedHeight = 0.f, QueryAge = 1.f, Phase = 0.f, MoveWeight = 0.f;
    bool Enabled = false, Walking = false, ReferenceReady = false;
    void CacheReference(const ABellowSacLobber* Monster);
    FTransform Grounded(const FTransform& Bone) const;
};
