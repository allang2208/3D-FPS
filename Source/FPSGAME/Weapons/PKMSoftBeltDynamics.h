#pragma once
#include "CoreMinimal.h"

class USkeletalMesh;
class USkeletalMeshComponent;

// World-space cosmetic particles with fixed link lengths. No gameplay bodies.
struct FPKMSoftChain
{
    void Solve(const TArray<FVector>& Guide, const FTransform& Component, double Now,
        double Gravity, int32 PinnedStart, bool PinEnd, double Strength,
        double Corridor, TArray<FVector>& Result);
    void Reset() { LastTime=-1.; }
private:
    double LastTime=-1.;
    TArray<FVector> Positions, Velocities, PreviousGuide;
    TArray<double> Lengths;
};

struct FPKMSoftBeltDynamics
{
    void Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose,
        bool Reloading, bool Empty, float SourceTime, bool OldVisible, bool NewVisible);
private:
    TWeakObjectPtr<USkeletalMesh> SourceMesh;
    int32 BoneCount=0;
    TArray<int32> Rounds[2], Links[2];
    FPKMSoftChain Chains[2];
};
