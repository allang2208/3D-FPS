#pragma once

#include "CoreMinimal.h"

class UAnimSequence;
class UWeaponGripProfile;

// A camera-space framing contract for rifles, independent of their skeleton origins.
// Only samples an authored idle on weapon/grip changes; never follows the live bones.
struct FRifleHipFraming
{
    void Initialize(const FString& Definition, UAnimSequence* Idle, const FVector& Anchor,
        const FRotator& BaseRotation, const FVector& Scale, bool bMeasuredAKMSights);
    void SelectIdle(UAnimSequence* Idle,UWeaponGripProfile* Profile=nullptr);
    bool IsReady() const { return bReady; }
    FVector Location(const FVector& Fallback) const { return bReady ? HipLocation : Fallback; }
    FQuat Rotation(const FQuat& Fallback) const { return bReady ? HipRotation : Fallback; }

private:
    bool bReferenceReady = false;
    bool bReady = false;
    bool bAKMSights = false;
    TWeakObjectPtr<UAnimSequence> SampledIdle;
    TWeakObjectPtr<UWeaponGripProfile> SampledProfile;
    FVector MeshScale = FVector::OneVector;
    FVector TargetHand = FVector::ZeroVector;
    FQuat TargetAxis = FQuat::Identity;
    FVector HipLocation = FVector::ZeroVector;
    FQuat HipRotation = FQuat::Identity;
};
