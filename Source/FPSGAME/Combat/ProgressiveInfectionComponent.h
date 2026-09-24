#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ProgressiveInfectionComponent.generated.h"

UENUM(BlueprintType)
enum class EInfectionStage : uint8 { None, Early, Middle, Late };

/** Ratios are fractions, not percentage points. Timings use online game seconds. */
USTRUCT(BlueprintType)
struct FInfectionTuning
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infection", meta=(ClampMin="1")) float MiddleAtSeconds = 60.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infection", meta=(ClampMin="2")) float LateAtSeconds = 180.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infection") FVector AttributeReduction = FVector(.05, .30, .50);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infection") FVector MaxHealthLossPerSecond = FVector(.002, .005, .01);
};

/** Stored with the player profile; offline time never advances the disease. */
USTRUCT(BlueprintType)
struct FInfectionState
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Infection") bool bActive = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Infection") float ElapsedSeconds = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infection") FInfectionTuning Tuning;

    EInfectionStage Stage() const;
    float AttributeMultiplier() const;
    float HealthLossRatio() const;
};

/** One infection per victim. Repeated hits do not stack, postpone ticks or reset progression. */
UCLASS(ClassGroup=(Combat), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UProgressiveInfectionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UProgressiveInfectionComponent();
    static UProgressiveInfectionComponent* GetOrAdd(AActor* Target);
    static float AttributeMultiplier(const AActor* Target);
    UFUNCTION(BlueprintCallable, Category="Infection") bool Infect(AActor* Source, const FInfectionTuning& Tuning);
    UFUNCTION(BlueprintCallable, Category="Infection") void Cure();
    UFUNCTION(BlueprintPure, Category="Infection") EInfectionStage GetStage() const { return State.Stage(); }
    const FInfectionState& GetState() const { return State; }
    void Restore(const FInfectionState& SavedState);
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Function) override;
private:
    void Publish(bool bStageChanged);
    UPROPERTY(VisibleAnywhere, Category="Infection") FInfectionState State;
    TWeakObjectPtr<AActor> InfectionSource;
};
