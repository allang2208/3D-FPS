#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
class USkeletalMeshComponent;
class USkeletalMesh;

/** Keeps walking and the standard rise within the original long-robe silhouette. */
struct FWitchRecoveryLegNode : FAnimNode_SkeletalControlBase
{
    FWitchRecoveryLegNode();
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,
        TArray<FBoneTransform>& Out) override;
    // PreUpdate/game-thread only. The worker sees copied geometry and a plane.
    void PrepareSupportSamples(USkeletalMeshComponent* CharacterMesh);
    bool bWalkingPose = false;
    bool bGroundRecovery = false;
    FVector FloorPoint = FVector::ZeroVector, FloorNormal = FVector::UpVector;
    FVector WorldUp = FVector::UpVector;
    float ContactClearance = .5f;
private:
    struct FSupportWeight { int32 MeshBone; FVector BonePoint; float Weight; };
    struct FSupportSample { TArray<FSupportWeight, TInlineAllocator<8>> Weights; };
    TArray<FSupportSample> SupportSamples;
    const USkeletalMesh* SupportMesh = nullptr;
    FBoneReference Hip, Upper[2], Knee[2], Foot[2], Toe[2];
    FVector DownLocal=FVector::DownVector, AcrossLocal=FVector::RightVector, ForwardLocal=FVector::ForwardVector;
    float LegLength=0.f, HalfWidth=0.f;
};
