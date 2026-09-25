#pragma once

#include "Components/SkeletalMeshComponent.h"
#include "BowArmsMeshComponent.generated.h"

/** Bow-only local-pose handoff. Contact markers are children of their hands. */
UCLASS()
class FPSGAME_API UBowArmsMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    void CaptureEntry(float Seconds);
    void AdvanceEntry(float Delta);
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> EntryMesh;
    TArray<FTransform> EntryPose;
    float EntryAge = 0.f, EntryDuration = 0.f;
};
