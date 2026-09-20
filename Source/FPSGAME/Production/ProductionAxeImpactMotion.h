#pragma once
#include "CoreMinimal.h"

/** Authored local camera offsets. Timings also drive the Blender hit animation. */
struct FProductionAxeCameraKey
{
    float Time=0.f;
    FVector Angles=FVector::ZeroVector; // Pitch, yaw, roll in degrees.
    FVector Position=FVector::ZeroVector; // Forward, right, up in cm.
};

struct FProductionAxeImpactMotion
{
    float SwingSeconds=1.1f, ContactSeconds=.48f, SwingSoundSeconds=.405f;
    float HitRecoverSeconds=.92f, PryEndSeconds=.43f;
    float PryCameraPitch=-.16f, PryCameraUp=-.045f;
    TArray<FProductionAxeCameraKey> SwingCamera, HitCamera, ImpactCamera, ExtractCamera;
    TArray<FVector2D> PryKeys;

    void Load();
    void Sample(float AttackSeconds,bool bConfirmedHit,FVector& Location,FRotator& Rotation) const;
};
