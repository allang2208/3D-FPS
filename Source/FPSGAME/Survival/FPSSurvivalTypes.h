#pragma once
#include "CoreMinimal.h"
#include "GameFramework/DamageType.h"
#include "FPSSurvivalTypes.generated.h"

/** All three resources count down from full to empty. Missing legacy save fields stay full. */
USTRUCT(BlueprintType)
struct FFPSSurvivalState
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Survival") float Hunger=100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Survival") float Hydration=100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Survival") float Sanity=100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Survival") float MaxHunger=100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Survival") float MaxHydration=100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Survival") float MaxSanity=100.f;
    /** Persist the partial empty-resource second across saves and level travel. */
    UPROPERTY() float DeprivationSeconds=0.f;
    void Normalize();
    bool IsDeprived() const { return Hunger<=0.f || Hydration<=0.f; }
    bool IsSanityDepleted() const { return Sanity<=0.f; }
    float AttributeMultiplier() const { return IsSanityDepleted()?.5f:1.f; }
    static constexpr float FountainBlessingDuration=720.f;
    /** Remaining gameplay seconds; survives travel/save, offline time is not consumed. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Survival") float FountainBlessingSeconds=0.f;
};

/** Physiological loss uses the existing death/respawn path, bypassing combat avoidance. */
UCLASS()
class FPSGAME_API UFPSSurvivalDamage : public UDamageType
{
    GENERATED_BODY()
};
