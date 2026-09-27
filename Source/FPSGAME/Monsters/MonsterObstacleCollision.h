#pragma once
#include "CoreMinimal.h"

class ACharacter;
class USkeletalMeshComponent;

// Small, conservative samples of the existing Physics Asset. No additional bodies
// or collision channels are installed in the world.
struct FMonsterObstacleProbe
{
    FName Bone;
    FVector Center;
    float Radius = 1.f;
};
struct FMonsterObstacleSphere
{
    FVector Center;
    float Radius = 1.f;
};
using FMonsterObstaclePose = TArray<FMonsterObstacleSphere>;

namespace MonsterObstacleCollision
{
void BuildProbes(const USkeletalMeshComponent* Mesh, TArray<FMonsterObstacleProbe>& Out);
FMonsterObstacleSphere TransformProbe(const FMonsterObstacleProbe& Probe, const FTransform& Bone);
void WorldPose(const USkeletalMeshComponent* Mesh, const TArray<FMonsterObstacleProbe>& Probes, FMonsterObstaclePose& Out);
// Scene responses remain authoritative: NoCollision dressing is never promoted
// to an obstacle; Pawns are left to the normal movement capsule.
bool PoseFits(const ACharacter* Owner, const FMonsterObstaclePose& Pose, float FloorZ);
bool PathFits(const ACharacter* Owner, const FMonsterObstaclePose& From, const FMonsterObstaclePose& To, float FloorZ);
float LimitPush(const ACharacter* Owner, const FVector& Delta);
}
