#pragma once
#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "ColdSteelResourceMeter.generated.h"

/** Cold-steel resource track with a short visual transition toward the current value. */
UCLASS()
class FPSGAME_API UColdSteelResourceMeter : public UWidget
{
    GENERATED_BODY()
public:
    void SetValue(float InRatio, bool bInMana);
    void SetStaminaValue(float InRatio);
    void SetSemanticValue(float InRatio,const FLinearColor& Fill,const FLinearColor& Deep, bool bWarnOnLowFill=true);
    void SetPendingCostRatio(float InRatio);
    void SetShieldRatio(float InRatio);
    void SetMaxPoints(float InMaxPoints);
    float Ratio() const { return Value; }
    void ResetAnimation();
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    float Value=0;
    bool bHasValue=false;
    bool bMana=false;
    bool bStamina=false;
    TSharedPtr<class SColdSteelResourceMeter> Meter;
    bool bSemantic=false;
    bool bWarnOnLowFill=true;
    FLinearColor SemanticFill=FLinearColor::White,SemanticDeep=FLinearColor::White;
    float PendingCostRatio=0.f;
    float ShieldRatio=0.f;
    float MaxPoints=0.f;
};
