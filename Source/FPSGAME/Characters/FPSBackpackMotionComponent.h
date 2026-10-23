#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSBackpackHangingMotion.h"
#include "FPSBackpackMotionComponent.generated.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;
class FJsonObject;

/** Cosmetic inertial pack motion. The sewn harness is pinned by an authored vertex mask. */
UCLASS()
class FPSGAME_API UFPSBackpackMotionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSBackpackMotionComponent();
    void Clear();
    void Configure(USkeletalMeshComponent* InBody,USkeletalMeshComponent* InPack,const TSharedPtr<FJsonObject>& Settings,FName Shirt=NAME_None);
    void AttachRigidBody(UStaticMeshComponent* InRigid,const FTransform& ReferencePose);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    friend int32 RunBackpackMotionDiagnostic(const FString& Params);
    friend int32 RunBackpackLifecycleDiagnostic(const FString& Params);
    TWeakObjectPtr<USkeletalMeshComponent> Body,Pack;
    TWeakObjectPtr<UStaticMeshComponent> RigidBody;
    FTransform RigidReference=FTransform::Identity;
    int32 Spine=INDEX_NONE;
    FTransform InverseBind=FTransform::Identity;
    FVector Pivot=FVector(0,-15,134),BoundsMin=FVector(-25,-40,95),BoundsMax=FVector(25,-10,155);
    FVector LastPosition=FVector::ZeroVector,LastVelocity=FVector::ZeroVector;
    FVector LastAnchor=FVector::ZeroVector,AnchorVelocity=FVector::ZeroVector,FrameAngularVelocity=FVector::ZeroVector;
    FQuat LastFrame=FQuat::Identity;
    FVector Angles=FVector::ZeroVector,AngularVelocity=FVector::ZeroVector;
    FVector Offset=FVector::ZeroVector,OffsetVelocity=FVector::ZeroVector;
    float Frequency=3.5f,Damping=.85f,MaxAngle=2.5f,MaxBounce=.35f,ResponseScale=1.f,MaxDisplacement=0.f;
    bool bInitialized=false,bSent=false;
    float PreviousField[15]={},LastSent[30]={};
    FFPSHangingPack Hanging;
    void ConfigureHanging(const TSharedPtr<FJsonObject>& Settings,FName Shirt);
    void UpdateHanging(const FTransform& Frame,float Delta,float Gain,bool Reset);
    void ResetMotion();
    void Push(const FTransform& Frame,const FQuat& Rotation,const FVector& Translation,bool bResetPrevious=false);
};
