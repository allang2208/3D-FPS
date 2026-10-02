#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
class USkeletalMesh;

/** One complete left-arm gesture; the base weapon/gait is evaluated first. */
struct FDoorPushPoseLayer
{
    bool Capture(USkeletalMeshComponent& Mesh,const USkeletalMeshComponent& Source,
        const USkeletalMesh& FistRig,bool bNoNativeArms=false);
    bool Apply(USkeletalMeshComponent& Mesh,float Age);
    void Reset();
private:
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TWeakObjectPtr<const USkeletalMeshComponent> ExternalSource;
    TArray<FTransform> ExternalReference;
    TArray<int32> ExternalBoneMap;
    TArray<FTransform> Reference,EntryCamera,LastCamera,RecoveryCamera;
    TArray<FTransform> EntryLocal,SourcePose,AuthoredLocal;
    TArray<int32> Bones;
    int32 Clavicle=INDEX_NONE,Upper=INDEX_NONE,Lower=INDEX_NONE,Hand=INDEX_NONE;
    bool bRecovering=false;
    bool bSelfFallback=false;
};
