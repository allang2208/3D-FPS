#pragma once
#include "CoreMinimal.h"
#include "GameFramework/RootMotionSource.h"
#include "FPSLeapRootMotionSource.generated.h"

// Replicated launch/velocity state for native Falling. This source never seeks
// an absolute position or replaces the gravity/collision result each frame.
USTRUCT()
struct FPSGAME_API FRootMotionSource_FPSLeap : public FRootMotionSource_MoveToForce
{
    GENERATED_BODY()
    FRootMotionSource_FPSLeap();
    virtual FRootMotionSource* Clone() const override;
    virtual UScriptStruct* GetScriptStruct() const override;
    UPROPERTY() uint32 CastSerial=0;
    UPROPERTY() FVector LinearVelocity=FVector::ZeroVector;
    UPROPERTY() bool bLaunched=false;
    bool bRestoreVelocity=false;
    // Local first-step duration, including a launch partway through a server move.
    float InitialStepSeconds=-1.f;
    virtual bool Matches(const FRootMotionSource* Other) const override;
    virtual bool MatchesAndHasSameState(const FRootMotionSource* Other) const override;
    virtual bool UpdateStateFrom(const FRootMotionSource* Other,bool SimulatedCatchup=false) override;
    virtual bool NetSerialize(FArchive& Ar,UPackageMap* Map,bool& Success) override;
    virtual void PrepareRootMotion(float SimulationTime,float MovementTickTime,
        const ACharacter& Character,const UCharacterMovementComponent& MoveComponent) override;
};
template<> struct TStructOpsTypeTraits<FRootMotionSource_FPSLeap> : TStructOpsTypeTraitsBase2<FRootMotionSource_FPSLeap>
{enum {WithNetSerializer=true,WithCopy=true};};
