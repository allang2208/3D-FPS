#pragma once

#include "../Skills/FPSCastingMeshComponent.h"
#include "RuneSwordMeshComponent.generated.h"

/** Sword-only entry blend, evaluated before the final bone/socket publication. */
UCLASS()
class FPSGAME_API URuneSwordMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    void CaptureWhirlwindEntry();
    void SetWhirlwindEntryTime(float Seconds);
    void ClearWhirlwindEntry();
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> EntryMesh;
    TArray<FTransform> EntryPose;
    float EntryTime=0.f;
    static constexpr float EntrySeconds=.1f;
    void ApplyWhirlwindEntry();
};
