#pragma once
#include "Widgets/SLeafWidget.h"

/** Read-only ritual decoration. Animation is advanced only by the host's success feedback. */
class SColdSteelArcaneSeal : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelArcaneSeal) {} SLATE_END_ARGS()
    void Construct(const FArguments&);
    void SetRitualState(bool Enchant,bool Ready);
    void SetPulse(float Progress);
    virtual FVector2D ComputeDesiredSize(float)const override{return FVector2D(160,160);}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool)const override;
private:
    bool bEnchant=false,bReady=false;
    float Pulse=-1.f;
};
