#pragma once

#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "ColdSteelWorldClock.generated.h"

/** Read-only 24-hour clock. The HUD supplies the same calendar used by event forecasts. */
UCLASS()
class FPSGAME_API UColdSteelWorldClock : public UWidget
{
    GENERATED_BODY()
public:
    void SetTime(int32 InDay, float InDayFraction, bool bInAvailable);
    void SetDisplayScale(float InScale);
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    int32 Day=0;
    float DayFraction=0, DisplayScale=1;
    bool bAvailable=false;
    TSharedPtr<class SColdSteelWorldClock> Clock;
};
