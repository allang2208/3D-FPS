#pragma once

#include "CoreMinimal.h"
#include "UObject/StrongObjectPtr.h"

class ANurseZombie;
class ABellowSacLobber;
class ACharacter;
class USkeletalMesh;
class UAnimSequence;
class UQuadrupedAnimationSet;
class USkeletalMeshComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
struct FFacilityWarmupCompletion;

/** Warm the SAME deferred staff/Bellow body used at activation. No gameplay clock. */
class FFacilityMonsterGpuWarmup
{
public:
    explicit FFacilityMonsterGpuWarmup(ANurseZombie* Monster);
    explicit FFacilityMonsterGpuWarmup(ABellowSacLobber* Monster);
    ~FFacilityMonsterGpuWarmup();
    /** Returns true only when this call submits a capture. */
    bool Tick(bool bAllowSubmission);
    bool IsReady() const;
    FName Stage() const;
    void Cancel();
    void RestoreForActivation();

private:
    void Initialize(ACharacter* Monster, USkeletalMesh* VisualMesh, UAnimSequence* IdleClip,
        UQuadrupedAnimationSet* QuadrupedSet = nullptr);
    void ReleaseCapture();
    TWeakObjectPtr<USkeletalMeshComponent> Body;
    TStrongObjectPtr<USceneCaptureComponent2D> Capture;
    TStrongObjectPtr<UTextureRenderTarget2D> Target;
    TSharedPtr<FFacilityWarmupCompletion, ESPMode::ThreadSafe> Completion;
    FTransform OriginalRelativeTransform;
    FName WaitReason = TEXT("waiting_for_admission");
    int32 OriginalForcedLOD = 0;
    bool bOriginalCastShadow = false, bOriginalAffectLighting = false, bOriginalRayTracing = false;
    bool bOriginalCaptureOnly = false, bOriginalHidden = false, bOriginalVisible = true;
    bool bOriginalTick = false;
    bool bSubmitted = false, bRestored = false;
};
