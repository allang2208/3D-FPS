#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
class AM10Mawcrawler;
class USkeletalMesh;
class UPhysicsAsset;

/** Eight bounded IK solves; copied frame data only on animation worker threads. */
struct FM10FootPlantNode : FAnimNode_SkeletalControlBase
{
    FM10FootPlantNode();
    void Prepare(const AM10Mawcrawler* Monster,float Phase,float Stance,float Weight,float Rate,float DeltaSeconds,bool Walking);
    FTransform RemoveGrounding(const FTransform& Bone) const;
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override;
private:
    struct FLeg
    {
        FBoneReference Upper,Lower,Foot,Body;
        float Offset=0.f,LastPhase=1.f,EmergencyTime=0.f;
        bool Locked=false,Emergency=false,UsedEarlyStep=false;
        FVector LockPosition=FVector::ZeroVector,EarlyStart=FVector::ZeroVector,EarlyEnd=FVector::ZeroVector;
        FVector PoleInBody=FVector::UpVector;
        FVector NeutralInBody=FVector::ZeroVector,OutwardInBody=FVector::RightVector;
        FVector ForwardInBody=FVector::ForwardVector;
        FQuat LockRotation=FQuat::Identity;
    };
    struct FSupport
    {
        FVector Point=FVector::ZeroVector,Normal=FVector::UpVector;
        FVector ReferenceFoot=FVector::ZeroVector;
        TArray<FVector,TInlineAllocator<32>> Sole;
        int32 Bone=INDEX_NONE;
        bool Valid=false;
    };
    FLeg Legs[8];
    FSupport Supports[8];
    TWeakObjectPtr<USkeletalMesh> PreparedMesh;
    TWeakObjectPtr<UPhysicsAsset> PreparedPhysics;
    FTransform Frame=FTransform::Identity,PreviousFrame=FTransform::Identity;
    FQuat GroundRotation=FQuat::Identity;
    float GroundHeight=0.f,BaseFloorZ=0.f,TraceElapsed=1.f;
    FQuat WantedGroundRotation=FQuat::Identity;
    FVector ReferenceForward=FVector::ForwardVector;
    float WantedGroundHeight=0.f;
    float CyclePhase=0.f,StanceFraction=.65f,PlantWeight=0.f,Dt=0.f,StepSeconds=.2f;
    uint64 Serial=0,LastEvaluated=0;
    bool Enabled=false,WasEnabled=false,Walking=false,GroundEnabled=false,PoseLiftAllowed=false;
    void CacheSupportGeometry(const AM10Mawcrawler* Monster);
    FTransform Grounded(const FTransform& Bone) const;
};
