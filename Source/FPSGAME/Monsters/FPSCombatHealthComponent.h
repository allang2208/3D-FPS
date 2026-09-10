#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSCombatHealthComponent.generated.h"

UCLASS(ClassGroup=(Combat), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSCombatHealthComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float MaxHealth = 100.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") float Health = 100.f;
    UFUNCTION(BlueprintPure, Category="Combat") bool IsDead() const { return Health <= 0.f; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UFUNCTION() void OnDamage(AActor* Actor, float Damage, const UDamageType* Type, AController* Instigator, AActor* Causer);
    void Respawn();
    FTimerHandle RespawnTimer;
};
