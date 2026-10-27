#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FoodSpoilage.h"
#include "FoodSpoilageClock.generated.h"

/** An accounting view of the existing weather clock; never advances the sun. */
UCLASS()
class UFoodSpoilageClock : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UFoodSpoilageClock,STATGROUP_Tickables);}
    virtual bool IsTickableWhenPaused() const override {return false;}
    virtual void Deinitialize() override;
    FFoodClockSample Sample();
private:
    TWeakObjectPtr<class AFPSWeatherManager> Weather;
    FFoodClockSample Current;
    double LastNatural=0.,SearchAfter=0.;
    float SettlementSeconds=0.f;
    bool bSeeded=false,bHadWeather=false;
};
