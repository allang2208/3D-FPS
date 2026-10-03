#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

class ANurseZombie;
class USkeletalMesh;
class UPhysicsAsset;

/** Final whole-body floor alignment for the existing standard rise clips. */
struct FMonsterRecoveryGroundNode : FAnimNode_SkeletalControlBase
{
    FMonsterRecoveryGroundNode() { Alpha=0.f; }
    void Prepare(const ANurseZombie* Monster);
protected:
    virtual void InitializeBoneReferences(const FBoneContainer&) override {}
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer&) override { return !Samples.IsEmpty(); }
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override;
private:
    struct FContact { int32 Bone; FVector Point; };
    TArray<FContact> Samples;
    TWeakObjectPtr<USkeletalMesh> PreparedMesh;
    TWeakObjectPtr<UPhysicsAsset> PreparedPhysics;
    FVector FloorPoint=FVector::ZeroVector,FloorNormal=FVector::UpVector,WorldUp=FVector::UpVector;
    float Scale=1.f;
};
