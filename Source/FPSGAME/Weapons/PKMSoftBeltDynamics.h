#pragma once
#include "CoreMinimal.h"

class USkeletalMesh;
class USkeletalMeshComponent;

struct FPKMSoftChainSettings
{
    double VelocityDamping=3.6;
    double Guidance=42.;
    double GravityScale=.65;
};

namespace PKMBeltProfiles
{
// Accepted incoming Belt08 authoring values, in seconds and viewmodel cm.
// The loose PKM outlet retains the solver's original default profile.
inline constexpr FPKMSoftChainSettings Incoming{13.,1050.,1.};
inline constexpr double IncomingCorridor=.4;
}

// World-space cosmetic particles with fixed link lengths. No gameplay bodies.
struct FPKMSoftChain
{
    void Solve(const TArray<FVector>& Guide, const FTransform& Component, double Now,
        double Gravity, int32 PinnedStart, bool PinEnd, double Strength,
        double Corridor, TArray<FVector>& Result);
    void Solve(const TArray<FVector>& Guide, const FTransform& Component, double Now,
        double Gravity, int32 PinnedStart, bool PinEnd, double Strength,
        double Corridor, TArray<FVector>& Result,
        const FPKMSoftChainSettings& Settings);
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
