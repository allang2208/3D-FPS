#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSSurvivalTypes.h"
#include "FPSSurvivalComponent.generated.h"

/** Server-owned survival resources. 4 Hz integration; HUD reads the replicated state. */
UCLASS(ClassGroup=(Survival), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSSurvivalComponent : public UActorComponent
{
    GENERATED_BODY()
    friend class ULargeLambMealAuditCommandlet;
    friend class USurvivalClockAuditCommandlet;
public:
    UFPSSurvivalComponent();
    UFUNCTION(BlueprintPure, Category="Survival") FFPSSurvivalState GetState() const;
    float SausageRecoveryRemaining() const;
    float LargeLambMealRemaining() const;
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Survival") void RestoreState(const FFPSSurvivalState& Saved);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Survival") void RestoreResources(float Food,float Water,float Sanity);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Survival") void ApplySanityDamage(float BaseLoss,float Coefficient=1.f);
    /** Refill water and refresh one 12-minute, 10% food/water conservation blessing. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Survival") bool DrinkBlessedWater();
    /** Called only after an accepted combat hit. Untuned monster tags/classes cost zero. */
    void ApplySanityAttack(AActor* Attacker);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction) override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_State) FFPSSurvivalState State;
    // Runtime server-clock deadline only; saves contain remaining gameplay seconds.
    UPROPERTY(ReplicatedUsing=OnRep_SausageRecoveryClock) double SausageRecoveryEndsAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_LargeLambMealClock) double LargeLambMealEndsAt=0.;
    double ServerTime() const;
    float FoodRecoveryRemaining(float SavedSeconds,double EndsAt,float Duration) const;
    UFUNCTION() void OnRep_SausageRecoveryClock();
    UFUNCTION() void OnRep_LargeLambMealClock();
    // Reference rates: scaled by actual authority calendar progress at runtime.
    float HungerPerSecond=100.f/2160.f,HydrationPerSecond=100.f/1080.f,DungeonSanityPerSecond=.02f;
    float BedRestSanityPerSecond=5.f;
    TWeakObjectPtr<class AFPSWeatherManager> NaturalClock;
    double LastNaturalDays=0.,ClockResolveAfter=0.;
    float NaturalConsumptionSeconds(float DeltaTime);
    // Preserve sub-float integration error between 4 Hz steps; not a gameplay effect or save field.
    double HungerIntegrationRemainder=0.,HydrationIntegrationRemainder=0.;
    float MonsterSanityMultiplier=1.f;
    TMap<FName,float> MonsterSanityLossByTag,MonsterSanityLossByClass;
    void LoadTuning();
    void NotifySanityChange(bool bWasDepleted);
    UFUNCTION() void OnRep_State(const FFPSSurvivalState& Previous);
};
