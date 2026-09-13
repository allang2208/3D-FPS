#pragma once
#include "CoreMinimal.h"
struct FProductionResource;

// Shared by the cosmetic fall and the saved drop transaction.
struct FProductionTreeFallPlan
{
    FVector Pivot=FVector::ZeroVector, Axis=FVector::RightVector, Direction=FVector::ForwardVector;
    FVector TrunkContact=FVector::ZeroVector, CrownContact=FVector::ZeroVector;
    float LandingAngle=90, CrownAngle=86, FallSeconds=2.6f, LocalHeight=3000;
    static constexpr float CutHeight=42.f, AnticipationSeconds=.42f, SettleSeconds=.75f, FadeSeconds=.7f;
    float ReleaseSeconds() const { return AnticipationSeconds+FallSeconds+SettleSeconds; }
    static FProductionTreeFallPlan Make(const FProductionResource& Resource);
};
