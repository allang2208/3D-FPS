#pragma once

#include "CoreMinimal.h"
#include "WolfMonster.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "InfectedDogMonster.generated.h"

/** Hairless green canine using the established wolf animation and combat clock. */
UCLASS(Blueprintable)
class FPSGAME_API AInfectedDogMonster : public AWolfMonster
{
    GENERATED_BODY()
public:
    AInfectedDogMonster(const FObjectInitializer& ObjectInitializer=FObjectInitializer::Get());
    virtual void BeginPlay() override;
    CoreCombatFormula::Attributes BaseAttributes() const;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Attributes", meta=(ClampMin="0")) float Strength=24.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Attributes", meta=(ClampMin="0")) float Dexterity=32.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Attributes", meta=(ClampMin="0")) float Intelligence=4.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Attributes", meta=(ClampMin="0")) float Constitution=18.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Attributes", meta=(ClampMin="0")) float Wisdom=10.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Attributes", meta=(ClampMin="0")) float Luck=6.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Infection") FInfectionTuning Infection;
protected:
    virtual void OnAttackLanded(APawn* Victim) override;
};
