#pragma once
#include "CoreMinimal.h"
class USkeletalMeshComponent;
class USkeletalMesh;
struct FPotionUseMotion;

/** Per-use cache; the shared V7 surface stays on each weapon's native binding. */
struct FPotionArmPose
{
    void Reset();
    bool Apply(USkeletalMeshComponent& Mesh,const FPotionUseMotion& Motion,float Age,FTransform& OutPalmWorld);
private:
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<FTransform> Rest,Source,Goal;
    TArray<int32> Bones;
    int32 Clavicle=INDEX_NONE,Upper=INDEX_NONE,Lower=INDEX_NONE,Hand=INDEX_NONE;
    FQuat PalmReference=FQuat::Identity;
};
