#pragma once

#include "Components/SkeletalMeshComponent.h"
#include "BowArmsMeshComponent.generated.h"

class UAnimSequence;

/** Bow-only local-pose handoff. Contact markers are children of their hands. */
UCLASS()
class FPSGAME_API UBowArmsMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    void CaptureEntry(float Seconds);
    /** Preserve the incoming pickup motion while fading the previous-pose offset. */
    void CaptureCarry(float Seconds);
    /** Carry the current draw into release, then remove its offset during recovery. */
    void CaptureRelease(float Seconds);
    void AdvanceEntry(float Delta);
    /** Speed-driven loops share one phase; the action pose remains the base. */
    void SetLocomotion(UAnimSequence* Walk, UAnimSequence* Run, float Phase,
        float Weight, float Sprint, bool bKeepBraceContact, const FVector& Brace);
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> EntryMesh;
    TArray<FTransform> EntryPose;
    float EntryAge = 0.f, EntryDuration = 0.f;
    TArray<FTransform> ReleaseReference;
    bool bReleaseHandoff = false;
    bool bCarryHandoff = false;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkCycle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> RunCycle;
    TWeakObjectPtr<USkeletalMesh> LocomotionMesh;
    TArray<int32> LocomotionBoneMap;
    float GaitPhase = 0.f, GaitWeight = 0.f, SprintWeight = 0.f;
    bool bBraceContact = false;
    FVector BraceContact = FVector::ZeroVector;
    void BlendLocomotion();
    void PreserveBraceContact();
};
