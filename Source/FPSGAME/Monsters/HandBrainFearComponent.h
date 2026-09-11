#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HandBrainFearComponent.generated.h"
class AController;
UCLASS(ClassGroup=(Combat),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UHandBrainFearComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UHandBrainFearComponent();
 void Apply(AActor* Source);
 virtual void TickComponent(float Dt,ELevelTick TickType,FActorComponentTickFunction* Tick) override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Fear") int32 Stacks=0;
private:
 void Release();
 TWeakObjectPtr<AActor> Threat;
 TWeakObjectPtr<AController> LockedController;
 TArray<double> Expirations;
 float RestoreSpeed=0;
};
