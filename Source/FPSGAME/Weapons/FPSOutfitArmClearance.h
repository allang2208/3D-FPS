#pragma once

#include "CoreMinimal.h"

class UCameraComponent;
class UFPSModularOutfitComponent;
class USkeletalMesh;
class USkeletalMeshComponent;

/** Camera-space support for thick first-person sleeves; hands remain authored. */
struct FFPSOutfitArmClearance
{
    void Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose);

private:
    struct FArm
    {
        int32 Upper = INDEX_NONE, Lower = INDEX_NONE, Hand = INDEX_NONE;
        TArray<int32> UpperBones, LowerBones;
    };
    FArm Arms[2];
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TWeakObjectPtr<UCameraComponent> Camera;
    TWeakObjectPtr<UFPSModularOutfitComponent> Outfit;
    void Cache(USkeletalMeshComponent& Mesh);
};
