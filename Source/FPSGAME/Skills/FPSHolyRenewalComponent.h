#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSHolyRenewalComponent.generated.h"

UCLASS()
class FPSGAME_API UFPSHolyRenewalComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSHolyRenewalComponent();
    static void Apply(AActor* Target,int32 Stacks,float Seconds);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    int32 Count=0;
    float Remaining=0,UntilTick=1;
};
