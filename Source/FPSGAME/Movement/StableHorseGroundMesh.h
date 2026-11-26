#pragma once
#include "Components/SkeletalMeshComponent.h"
#include "StableHorseGroundMesh.generated.h"

UCLASS()
class UStableHorseGroundMesh : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    void SetTailShape(float Length,float Width,float SweepCm);
    FQuat SurfaceTilt() const { return LastTilt; }
    FVector SurfaceOffset() const { return LastOffset; }
    void FinalizeBoneTransform() override;
private:
#if WITH_EDITOR
    friend class UHorseGroundContactReviewCommandlet;
    bool bMeasureGroundFit=false;
    double LastGroundFitUs=0.;
#endif
    struct FLeg
    {
        int32 Hip=INDEX_NONE,Knee=INDEX_NONE,Ankle=INDEX_NONE,Toe=INDEX_NONE;
        FVector RestSole=FVector::ZeroVector;
        TArray<int32> Children;
        TArray<FVector> Pads;
    };
    FLeg Legs[4];
    struct FCachedSupport
    {
        FVector Query=FVector::ZeroVector,Point=FVector::ZeroVector,Normal=FVector::UpVector;
        double Until=-1.;
        TWeakObjectPtr<UPrimitiveComponent> Base;
    };
    // Centre, four supports, two probes per shoe and two per skinned guard.
    FCachedSupport ParkedSamples[23];
    TArray<int32> GuardIndices, TailBranch;
    TArray<FTransform> GuardInverseBind;
    int32 TailRoot=INDEX_NONE,TailLengthAxis=0;
    float TailLength=1.f,TailWidth=1.f,TailSweepCm=0.f;
    void ShapeTail(TArray<FTransform>& Pose,const FVector& Side) const;
    TWeakObjectPtr<USkeletalMesh> Rig;
    bool bRigReady=false;
    FQuat LastTilt=FQuat::Identity;
    FVector LastOffset=FVector::ZeroVector;
    bool bHaveGroundState=false;
    FVector PrevOrigin=FVector::ZeroVector;
    double SmoothedWorldZ=0.;
    FQuat SmoothedTilt=FQuat::Identity;
    bool CacheRig();
    void FitToGround(class AStableRidingHorse& Horse,TArray<FTransform>& Pose);
};
