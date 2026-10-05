#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
class ALurkerM08Monster;
class UQuadrupedTemplateAnimInstance;
class USkeletalMesh;
class UPrimitiveComponent;

/** Bonehead-inspired stepping. World queries and step state stay in PreUpdate;
 * animation evaluation consumes component-space goals only. */
struct FLurkerM08ContactNode : FAnimNode_SkeletalControlBase
{
    FLurkerM08ContactNode();
    void Prepare(const ALurkerM08Monster* Monster, const UQuadrupedTemplateAnimInstance* Anim, float Dt);
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& Out) override;
private:
    struct FFoot
    {
        FVector Reference = FVector::ZeroVector, Pole = FVector::UpVector, Hock = -FVector::UpVector;
        FQuat ReferenceRotation = FQuat::Identity;
        float Height = 0.f;
        FVector Position = FVector::ZeroVector, Normal = FVector::UpVector;
        FQuat Rotation = FQuat::Identity;
        FVector Start = FVector::ZeroVector, End = FVector::ZeroVector, StartNormal = FVector::UpVector, EndNormal = FVector::UpVector;
        FQuat StartRotation = FQuat::Identity, EndRotation = FQuat::Identity;
        FVector Candidate = FVector::ZeroVector, CandidateNormal = FVector::UpVector;
        FQuat CandidateRotation = FQuat::Identity;
        TWeakObjectPtr<UPrimitiveComponent> Base, CandidateBase, LandingBase;
        FVector BasePoint = FVector::ZeroVector, BaseNormal = FVector::UpVector;
        FQuat BaseRotation = FQuat::Identity;
        float Time = 0.f, Duration = .22f, Lift = 8.f;
        bool Planted = false, Swing = false, Valid = false;
        FVector GoalCS = FVector::ZeroVector;
        FQuat RotationCS = FQuat::Identity;
        float Curl = 0.f, ContactAge = 1.f, Load = 0.f;
    };
    FFoot Feet[4]; // front L/R, rear L/R; diagonal pairs (0,3), (1,2)
    struct FMouthSample
    {
        FName Bones[4];
        FVector Local[4];
        float Weights[4] = {};
        int32 Count = 0;
    };
    TArray<FMouthSample,TInlineAllocator<12>> MouthSamples;
    FVector MouthProbeCS = FVector::ZeroVector;
    struct FMouthPlane
    {
        FVector Point = FVector::ZeroVector, Normal = FVector::UpVector;
        bool Valid = false;
    };
    FMouthPlane MouthPlanes[3];
    bool CannonSupport = false;
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<int32> Parents;
    TMap<FName, int32> Indices;
    FVector BodyOffset = FVector::ZeroVector, BodyVelocity = FVector::ZeroVector;
    // Contact-driven sway / reach / compression, with progressively slower
    // followers. Prepared on the game thread; evaluation only reads them.
    FVector StepMotion = FVector::ZeroVector, StepVelocity = FVector::ZeroVector;
    FVector NeckMotion = FVector::ZeroVector, NeckVelocity = FVector::ZeroVector;
    FVector HeadMotion = FVector::ZeroVector, HeadVelocity = FVector::ZeroVector;
    FVector ArchMotion = FVector::ZeroVector, ArchVelocity = FVector::ZeroVector;
    float MoveWeight = 0.f;
    FVector UpCS = FVector::UpVector, ForwardCS = FVector::ForwardVector, RightCS = FVector::RightVector;
    FVector LastLocation = FVector::ZeroVector, LastForward = FVector::ForwardVector;
    FQuat LastRotation = FQuat::Identity;
    float QueryAge = 1.f, Turn = 0.f, Pitch = 0.f;
    int32 NextPair = 0;
    bool Enabled = false, WasEnabled = false, ReferenceReady = false;
    bool ActionSupport = false, FlightOnly = false;
    float ActionTime = 0.f, FlightPitch = 0.f, CorrectionWeight = 1.f;
    void CacheReference(const ALurkerM08Monster* Monster);
    void ResetLocomotionMotion();
};
