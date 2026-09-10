#pragma once
#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "ColdSteelResourceMeter.generated.h"

/** Thin cold-steel resource track. Its fill always represents the current value. */
UCLASS()
class FPSGAME_API UColdSteelResourceMeter : public UWidget
{
    GENERATED_BODY()
public:
    void SetValue(float InRatio, bool bInMana);
    float Ratio() const { return Value; }
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    float Value=0;
    bool bMana=false;
    TSharedPtr<class SColdSteelResourceMeter> Meter;
};
