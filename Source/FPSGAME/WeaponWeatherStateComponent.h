#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WeaponWeatherStateComponent.generated.h"

/** Cosmetic state belongs to the item, not to the observer's camera or material. */
USTRUCT()
struct FWeaponWeatherSnapshot
{
    GENERATED_BODY()
    UPROPERTY() FString MainInstance;
    UPROPERTY() FString OffhandInstance;
    UPROPERTY() uint8 MainWetness=0;
    UPROPERTY() uint8 OffhandWetness=0;
    UPROPERTY() uint8 TorchBurnRate=1;
};

/** Server integrates each player's held items; clients only present the snapshot.
    No material assets, combat values or client RPCs live in this component. */
UCLASS()
class FPSGAME_API UWeaponWeatherStateComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWeaponWeatherStateComponent();
    virtual void BeginPlay() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    float GetWetness(uint8 Hand,const FString& Instance) const;
    int32 TorchBurnRate(const FString& Instance) const
    {
        return !Instance.IsEmpty() && (Instance==Snapshot.MainInstance || Instance==Snapshot.OffhandInstance)
            ? Snapshot.TorchBurnRate : 1;
    }
private:
    UPROPERTY(Replicated) FWeaponWeatherSnapshot Snapshot;
    TWeakObjectPtr<class AFPSWeatherManager> Weather;
    TMap<FString,float> ItemWetness;
    float WeatherSearchLeft=0.f,ShelterCheckLeft=0.f;
    float ExposedRain=0.f,ExposedRainTarget=0.f;
};
