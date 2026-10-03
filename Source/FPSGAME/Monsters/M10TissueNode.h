#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

/** Tissue follows the final solved limb/jaw pose, including foot-plant correction. */
struct FM10TissueNode : FAnimNode_SkeletalControlBase
{
    FM10TissueNode();
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override;
private:
    struct FSocket {FBoneReference Upper,Tissue,Body;FTransform Rest;};
    FSocket Sockets[8];
    FBoneReference Jaw,Head;
    FTransform JawRest;
};
