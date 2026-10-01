#pragma once
#include "CoreMinimal.h"

class UWeaponGripProfile;
class UAnimSequence;
class USkeletalMesh;
class USkeletalMeshComponent;
struct FWeaponGripClip;

// Single-node weapons apply the same authored differences before their existing
// entry/recovery/casting layers and before sockets publish the contact pose.
struct FWeaponGripComponentLayer
{
    void Apply(const UWeaponGripProfile* Profile,const UAnimSequence* Clip,float Time,USkeletalMeshComponent& Mesh);
private:
    const UWeaponGripProfile* CachedProfile=nullptr;
    const UAnimSequence* CachedClip=nullptr;
    const USkeletalMesh* CachedMesh=nullptr;
    const FWeaponGripClip* Layer=nullptr;
    TArray<int32> TrackBones;
    TArray<FTransform> Local;
};
