#pragma once
#include "CoreMinimal.h"
class AFPSGAMECharacter;
class UFPSFootstepAudioComponent;

/** One shared carry pose for the staff, closed right hand and supporting arm chain. */
struct FStaffLocomotion
{
    void Reset();
    void Update(const AFPSGAMECharacter& Pawn,const UFPSFootstepAudioComponent* Footsteps,float Delta,bool bAction);
    FVector Offset=FVector::ZeroVector;
    FQuat Rotation=FQuat::Identity;
    FVector RightShoulder=FVector::ZeroVector,RightElbow=FVector::ZeroVector;
    FVector LeftShoulder=FVector::ZeroVector,LeftElbow=FVector::ZeroVector;
    FTransform LeftHand=FTransform::Identity;
    float RunWeight()const{return RunBlend;}
    float StridePhase()const{return Phase;}
    float MoveWeight()const{return MoveBlend;}
    float MotionTime()const{return IdleTime;}
private:
    float Phase=0,MoveBlend=0,RunBlend=0,IdleTime=0;
    FVector LaggedVelocity=FVector::ZeroVector;
    FRotator PreviousView=FRotator::ZeroRotator;
    bool bInitialized=false;
};
