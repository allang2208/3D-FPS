#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Combat/CoreCombatFormula.h"
#include "VillageArtisanVitalsComponent.generated.h"

class APawn;
class UDamageType;

UCLASS()
class FPSGAME_API UVillageArtisanVitalsComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillageArtisanVitalsComponent();
    bool IsDowned() const { return Health <= 0.f; }
    const CoreCombatFormula::Attributes& Attributes() const;
    float MaxHealth() const;
    float WeaponDamage() const;
    float ReceiveMonsterDamage(float Amount, const UDamageType* Type, AController* Instigator, AActor* Causer);
    bool ReviveFromFirstAid(APawn* Rescuer);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;

protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(VisibleInstanceOnly, ReplicatedUsing=OnRep_Health) float Health = 100.f;
    UFUNCTION() void OnRep_Health(float Previous);
    void SetHealth(float NewHealth);
};
