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
public:
    UFPSSurvivalComponent();
    UFUNCTION(BlueprintPure, Category="Survival") FFPSSurvivalState GetState() const { return State; }
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
    float HungerPerSecond=.05f,HydrationPerSecond=.075f,DungeonSanityPerSecond=.02f;
    float MonsterSanityMultiplier=1.f;
    TMap<FName,float> MonsterSanityLossByTag,MonsterSanityLossByClass;
    void LoadTuning();
    void NotifySanityChange(bool bWasDepleted);
    UFUNCTION() void OnRep_State(const FFPSSurvivalState& Previous);
};
