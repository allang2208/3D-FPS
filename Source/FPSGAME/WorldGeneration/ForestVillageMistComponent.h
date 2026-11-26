#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ForestVillageMistComponent.generated.h"

class AFPSWeatherManager;
class ULocalFogVolumeComponent;

UCLASS()
class UForestVillageMistComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UForestVillageMistComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* TickFunction) override;

private:
    UPROPERTY(Transient) TArray<TObjectPtr<ULocalFogVolumeComponent>> Pockets;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    float LocalStrength=-1.f;
};
