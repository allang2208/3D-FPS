#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
class UPrimitiveComponent;
class UFPSPlayerBodyAnimInstance;

/** Pre-IK observations from the previous completed evaluation, in mesh space. */
struct FFPSBodyFootSeed
{
    FTransform Ankle=FTransform::Identity;
    FVector Hip=FVector::ZeroVector;
    FVector Toe=FVector::ZeroVector;
    FVector SoleUpLocal=FVector::UpVector;
    float SoleHeight=9.f;
    float GaitPhase=0.f;
    float ReachLimit=0.f;
    bool bValid=false;
};

/** Value-only snapshot copied on the game thread, read on the animation worker. */
struct FFPSBodyGroundPose
{
    FVector FootOffset[2]={FVector::ZeroVector,FVector::ZeroVector};
    FQuat FootTilt[2]={FQuat::Identity,FQuat::Identity};
    float Weight[2]={0.f,0.f};
    float SolePlant[2]={0.f,0.f};
    float PelvisZ=0.f;
    float LowerYaw=0.f;
    float TurnLift[2]={0.f,0.f};
    float TurnAlpha=0.f;
};

/** Six bounded support traces at 30 Hz nearby / 10 Hz at distance, never on a worker. */
struct FFPSBodyGrounding
{
    FFPSBodyGroundPose Pose;
    void Update(USkeletalMeshComponent& Mesh,const UFPSPlayerBodyAnimInstance& Anim,
        const FFPSBodyFootSeed (&Feet)[2],float WalkWeight,float Delta);
    void Reset();
private:
    struct FContact
    {
        TWeakObjectPtr<UPrimitiveComponent> Surface;
        FVector LocalPoint=FVector::ZeroVector,LocalNormal=FVector::UpVector;
        FVector PlantLocal=FVector::ZeroVector;
        bool bValid=false,bPlanted=false;
    };
    FContact Contacts[2];
    TWeakObjectPtr<class USkinnedAsset> Asset;
    FVector LastLocation=FVector::ZeroVector;
    float FeetYaw=0.f,TurnFrom=0.f,TurnDelta=0.f,TurnAge=1.f,ProbeCountdown=0.f;
    bool bInitialized=false,bTurning=false;
};
