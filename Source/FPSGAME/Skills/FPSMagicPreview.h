#pragma once

#include "CoreMinimal.h"

class AActor;
class APawn;
class ULineBatchComponent;

/**
 * Shared trajectory preview for projectile spells ("hold the key to see where it goes").
 *
 * Every magic skill behaves the same way: a press while its projectile hovers starts the
 * preview, the release fires it. Both the fireball and the ice spike draw one arc per
 * projectile from its current position to the predicted contact, using the same camera trace,
 * the same ballistic integration and the same sweep rule as the flight itself.
 */
namespace FPSMagicPreview
{
    constexpr float LineThickness=1.6f;
    /** Preview sampling: fixed step, so the drawn arc matches the flight's own integration. */
    constexpr float StepSeconds=1.f/60.f;
    constexpr int32 MaxPathPoints=48;
    /** Fraction of the path over which the line fades in from the spell, hiding the attachment. */
    constexpr float FadeInFraction=.32f;

    /**
     * Full-strength red. Only the end touching the spell is softened (see DrawPath); the rest of
     * the arc stays one crisp line. Alpha is written for paths that honour it, but the engine's
     * batched lines are composited additively, where the colour value alone decides strength.
     */
    FLinearColor LineColor();
    /** Live multiplier on the configured spell gravity (`fps.Magic.GravityScale`, 1 = as set). */
    float GravityScale();

    /** Aim point both spells launch at: the camera ray's first blocking hit. */
    FVector AimPoint(const APawn* Shooter,const AActor* Ignore);
    /** Sweeps one segment; returns true and fills OutEnd when something blocks it. Corpses are skipped. */
    bool SweepSegment(const APawn* Shooter,const AActor* Ignore,const FVector& Start,const FVector& End,
        float SweepRadius,FVector& OutEnd);
    /**
     * Samples the ballistic path the flight actually flies: constant launch velocity plus gravity,
     * fixed time steps, stopping at MaxDistance along the path or at the first blocking contact.
     * OutPoints always starts at Start and ends at the contact/limit, so it can be drawn directly.
     */
    void SamplePath(const APawn* Shooter,const AActor* Ignore,const FVector& Start,const FVector& LaunchVelocity,
        float Gravity,float MaxDistance,float SweepRadius,TArray<FVector>& OutPoints);

    /**
     * Starts one frame of preview: lazily creates Owner's line batcher and drops the previous
     * frame's segments. Lines are persistent until then, so fast camera motion cannot pile up
     * several frames of stale segments into a smear.
     */
    void BeginRefresh(TObjectPtr<ULineBatchComponent>& Lines,AActor* Owner);
    /**
     * Draws one projectile's arc as a dashed red line: the rhythm runs along the whole path
     * (`fps.Magic.PreviewDashCM` / `PreviewGapCM`), and the end touching the spell fades in from
     * invisible and is thinner there, so the attachment reads as a soft lead-in.
     */
    void DrawPath(TObjectPtr<ULineBatchComponent>& Lines,const TArray<FVector>& Points);
    /** Stops drawing immediately: pending segments are dropped. */
    void Clear(ULineBatchComponent* Lines);
}
