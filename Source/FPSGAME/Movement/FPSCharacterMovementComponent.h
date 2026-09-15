#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "FPSCharacterMovementComponent.generated.h"

/** Native swept walking, with local first-person compensation for discrete stair corrections. */
UCLASS()
class FPSGAME_API UFPSCharacterMovementComponent : public UCharacterMovementComponent
{
    GENERATED_BODY()
public:
    UFPSCharacterMovementComponent();
    virtual float GetMaxSpeed() const override;
    void SetStairVisualRoot(USceneComponent* InRoot) { StairVisualRoot = InRoot; }

    // Local single-player dodge. Direction is captured at activation, in world XY.
    bool StartDodge(const FVector& Direction, float DistanceCM, float DurationSeconds);
    void CancelDodge();
    bool IsDodging() const;
    float GetDodgeProgress() const;
    FVector GetDodgeDirection() const { return DodgeDirection; }

    // One grounded capsule sweep, with no residual velocity. Returns actual displacement.
    FVector ApplyMeleeLungeStep(const FVector& Direction, float DistanceCM);

    // Centimetres per second; constant interpolation has no spring or exponential tail.
    UPROPERTY(EditDefaultsOnly, Category="Movement|Stairs", meta=(ClampMin="1", Units="cm/s"))
    float StairVisualSpeed = 220.f;

    UPROPERTY(EditDefaultsOnly, Category="Movement|Stairs", meta=(ClampMin="0"))
    float StairSpeedToWalkSpeed = .75f;

    float GetStairVisualOffset() const { return StairVisualOffset; }
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual bool StepUp(const FVector& GravDir, const FVector& Delta, const FHitResult& Hit, FStepDownResult* OutStepDownResult = nullptr) override;
    virtual void AdjustFloorHeight() override;
    virtual void OnTeleported() override;
    virtual bool DoJump(bool bReplayingMoves, float DeltaTime) override;
    virtual bool IsValidLandingSpot(const FVector& CapsuleLocation, const FHitResult& Hit) const override;

protected:
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    // Accepted native corrections only, also used by third-person monster presentation.
    float GetFrameStairDisplacement() const { return FrameStairDisplacement; }

private:
    void UpdateDodgeState();
    uint16 DodgeRootMotionId = 0;
    double DodgeStartedAt = 0.0;
    float ActiveDodgeDuration = .3f;
    FVector DodgeDirection = FVector::ZeroVector;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> StairVisualRoot;
    float StairVisualOffset = 0.f;
    float FrameStairDisplacement = 0.f;
    bool bCaptureStairs = false;
    bool bLastFrameSteppedUp = false;
    bool bLeavingStairJump = false;
};
