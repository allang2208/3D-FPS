#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
class AM66IncineratorMonster;
class USkeletalMesh;

/** Terrain support for the authored side-fall, before standing foot IK takes over. */
struct FM66RecoveryGroundNode : FAnimNode_SkeletalControlBase
{
    FM66RecoveryGroundNode(){Alpha=1.f;}
    void Prepare(const AM66IncineratorMonster* Owner,float Dt);
protected:
    virtual void InitializeBoneReferences(const FBoneContainer&) override {}
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer&) override {return true;}
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext&,TArray<FBoneTransform>&) override;
private:
    struct FInfluence {int32 Bone=0;FVector Point=FVector::ZeroVector;float Weight=0;};
    using FSample=TArray<FInfluence,TInlineAllocator<4>>;
    TArray<FSample> Samples;
    TArray<FTransform> SourceCS;
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    FTransform MeshWorld;
    FVector Pivot=FVector::ZeroVector;
    FQuat Tilt=FQuat::Identity;
    FQuat ReleaseTilt=FQuat::Identity;
    float Height=0,Weight=0,QueryAge=1;
    float ReleaseHeight=0;
    bool Enabled=false,WasAirborne=false,Release=false;
    void Cache(const AM66IncineratorMonster* Owner);
};
