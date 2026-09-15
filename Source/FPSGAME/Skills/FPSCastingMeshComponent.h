#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "FPSCastingMeshComponent.generated.h"

class UFPSFireballComponent;

// Apply the shared cast after the weapon/tool/traversal animation is evaluated.
// Only the left arm is modified; weapon bones and the right arm keep their pose.
UCLASS()
class FPSGAME_API UFPSCastingMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    bool bApplyLeftHandCast=true;
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> PoseMesh;
    TArray<FTransform> ReferencePose, SourcePose, GoalPose, EntryLocal;
    TArray<int32> LeftBones;
    int32 CastClavicleIndex=INDEX_NONE,CastUpperIndex=INDEX_NONE,CastLowerIndex=INDEX_NONE,CastHandIndex=INDEX_NONE;
    uint32 EntrySerial=0;
    FQuat ReferencePalm=FQuat::Identity;
    void CacheCastSkeleton();
    void ApplyCastPose(UFPSFireballComponent* Magic);
};
