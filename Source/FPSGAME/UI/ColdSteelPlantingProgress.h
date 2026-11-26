#pragma once
#include "CoreMinimal.h"
#include "Widgets/SLeafWidget.h"
#include "ColdSteelMeterPresentation.h"

/** A bounded, native rounded track. Cosmetic timing never changes the planting clock. */
class SColdSteelPlantingProgress : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelPlantingProgress) {} SLATE_END_ARGS()
    void Construct(const FArguments&);
    void SetPlant(const FGuid& Id,float Ratio,bool bAnimate);
    void SetEffectsEnabled(bool Enabled);
    void SetPixelScale(float InScale);
    virtual FVector2D ComputeDesiredSize(float) const override;
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
private:
    FGuid PlantId;
    FColdSteelMeterTransition Transition;
    TWeakPtr<FActiveTimerHandle> AnimationTimer;
    double MatureFlashAt=-1.;
    float Scale=1.f;
    bool bEffectsEnabled=false;
    void EnsureAnimation();
    EActiveTimerReturnType Animate(double,float);
};
