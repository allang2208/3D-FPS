#pragma once
#include "CoreMinimal.h"
#include "ProductionTreeFallPlan.generated.h"
struct FProductionResource;

// Shared by the cosmetic fall and the saved drop transaction.
USTRUCT()
struct FProductionTreeFallPlan
{
    GENERATED_BODY()
    UPROPERTY() FVector Pivot=FVector::ZeroVector;
    UPROPERTY() FVector Axis=FVector::RightVector;
    UPROPERTY() FVector Direction=FVector::ForwardVector;
    UPROPERTY() FVector LocalHinge=FVector(0,0,42);
    UPROPERTY() FVector TrunkContact=FVector::ZeroVector;
    UPROPERTY() FVector CrownContact=FVector::ZeroVector;
    UPROPERTY() float LandingAngle=90;
    UPROPERTY() float CrownAngle=86;
    UPROPERTY() float FallSeconds=2.6f;
    UPROPERTY() float LocalHeight=3000;
    static constexpr float CutHeight=42.f, AnticipationSeconds=.42f, SettleSeconds=.75f, FadeSeconds=.7f;
    float ReleaseSeconds() const { return AnticipationSeconds+FallSeconds+SettleSeconds; }
    static FProductionTreeFallPlan Make(const FProductionResource& Resource);
};
