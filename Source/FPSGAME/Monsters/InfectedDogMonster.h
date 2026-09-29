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
    // 2026-09-28 随怪物端六维剔除常量化：数值为原六维 {24,32,4,18,10,6} 的派生烤入值
    // （HP=100+5体、咬=atk、扑=round(atk×1.65)、防/抗=公式），CDO 已核验无 BP 覆盖。
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Infected Dog|Infection") FInfectionTuning Infection;
protected:
    virtual void OnAttackLanded(APawn* Victim) override;
};
