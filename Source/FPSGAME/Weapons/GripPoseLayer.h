#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimNodeBase.h"

class UAnimSequence;
class USkeletalMesh;

// GripLayer56: PKM / 201 grip families share the base (handguard) clips. While the base left
// hand holds the handguard, the layer moves the shoulder girdle, elbow swivel, hand and finger
// grasp onto the selected grip (read from the family's reference pose: idle, or aim for ADS)
// and re-solves the left arm with the ArmHinge55 anatomical construction. Away from the
// handguard (reload, inspect) it fades to the base clip unchanged.
// Offline reference and study: SourceAssets/PKMLowpoly20260922/GripLayer56/evaluate.py
struct FGripPoseLayer
{
    // fps.Weapon.GripLayer: 0 = authored family clips; 1 = idle, aim, fire, aim_fire through the
    // layer (offline identical to the family clips); 2 = also sprint, equip, reloads (preview).
    static int32 Mode();
    // Local: mesh-indexed local pose (in/out). Returns the applied weight (0 = untouched).
    float Apply(const FReferenceSkeleton& Ref,const USkeletalMesh* Mesh,const UAnimSequence* BaseRef,
        const UAnimSequence* FamilyRef,TArray<FTransform>& Local,float DeltaSeconds);
    void ResetState(){bHasState=false;}
private:
    enum { Clavicle, Upper, UpperTwist1, UpperTwist2, Lower, LowerTwist2, LowerTwist1, Hand, ArmCount };
    bool CacheRig(const FReferenceSkeleton& Ref);
    bool CacheGrips(const FReferenceSkeleton& Ref);
    FQuat Anatomical(const FVector& U,const FVector& F) const;
    double PalmTotal(const FQuat& HandRotation,const FVector& A,const FVector& E,const FVector& H) const;
    void SolveArm(FQuat* R,FVector* P,const FQuat& HandTarget,const FVector& HandGoal,double Swivel,
        const FVector& SwivelAxisRef,double TotalShift) const;
    bool bRig=false,bGrips=false,bHasState=false;
    float State=0.f;
    const USkeletalMesh* RigMesh=nullptr;
    const UAnimSequence* GripBase=nullptr;
    const UAnimSequence* GripFamily=nullptr;
    int32 Root=INDEX_NONE;
    int32 Arm[ArmCount]={};
    FQuat BindRotation[ArmCount];
    FVector Offset[ArmCount];
    double Station[ArmCount]={};
    FVector U0=FVector::ZeroVector,F0=FVector::ZeroVector;
    FQuat BindForearmFrame=FQuat::Identity;
    TArray<int32> Fingers;
    TArray<FQuat> FamilyFingers;
    FQuat BaseGripRotation=FQuat::Identity,GripOffsetRotation=FQuat::Identity,ClavicleDelta=FQuat::Identity;
    FVector BaseGripLocation=FVector::ZeroVector,GripOffsetLocation=FVector::ZeroVector,ClavicleShift=FVector::ZeroVector;
    double SwivelShift=0.0,TotalShift=0.0;
    TArray<FTransform> Space;
};

// One gunplay channel (idle, aim, sprint or action) before it is blended with the others, so a
// family clip that is still authored per grip blends against the matching layered pose.
struct FGripPoseLayerNode : FAnimNode_Base
{
    FPoseLink Source;
    bool bEnabled=false;
    const UAnimSequence* BaseRef=nullptr;
    const UAnimSequence* FamilyRef=nullptr;
    const UAnimSequence* Clip=nullptr;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override { Source.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override { Source.CacheBones(Context); }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override;
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;
private:
    FGripPoseLayer Layer;
    float DeltaSeconds=0.f;
    const UAnimSequence* LastClip=nullptr;
    TArray<FTransform> Local;
};
