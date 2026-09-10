#include "ColdSteelResourceMeter.h"
#include "ColdSteelUIStyle.h"
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElementTypes.h"

class SColdSteelResourceMeter : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelResourceMeter) {} SLATE_END_ARGS()
    void Construct(const FArguments&) {}
    float Ratio=0;
    bool bMana=false;
    virtual FVector2D ComputeDesiredSize(float) const override {return FVector2D(160,9);}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool) const override
    {
        const FLinearColor Tint=Style.GetColorAndOpacityTint();
        const float Unit=G.GetLocalSize().Y/9.f;
        const auto Track=ColdSteelUI::RoundedBrush(FLinearColor::White,3*Unit,FLinearColor::Transparent,0);
        FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(),&Track,ESlateDrawEffect::None,(!bMana&&Ratio<=.25f?ColdSteelUI::Danger:ColdSteelUI::Border)*Tint);
        const auto Inner=ColdSteelUI::RoundedBrush(FLinearColor::White,2*Unit,FLinearColor::Transparent,0);
        const FVector2D InnerSize=G.GetLocalSize()-FVector2D(2*Unit);
        FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(InnerSize,FSlateLayoutTransform(FVector2D(Unit))),&Inner,ESlateDrawEffect::None,FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("080B0EFF")))*Tint);
        const FVector2D Size(FMath::Max(0.f,float(G.GetLocalSize().X-2*Unit))*Ratio,FMath::Max(0.f,float(G.GetLocalSize().Y-2*Unit)));
        if(Size.X>0&&Size.Y>0){
            const auto Deep=FLinearColor::FromSRGBColor(FColor::FromHex(bMana?TEXT("36566E"):TEXT("763B43")));
            const auto Light=FLinearColor::FromSRGBColor(FColor::FromHex(bMana?TEXT("7194AC"):TEXT("BD626D")));
            TArray<FSlateGradientStop> Stops;Stops.Emplace(FVector2f(0,0),Deep*Tint);Stops.Emplace(FVector2f(Size.X,0),Light*Tint);
            FSlateDrawElement::MakeGradient(Out,Layer+2,G.ToPaintGeometry(Size,FSlateLayoutTransform(FVector2D(Unit))),Stops,Orient_Vertical,ESlateDrawEffect::None,FVector4f(2*Unit));
        }
        return Layer+2;
    }
};
TSharedRef<SWidget> UColdSteelResourceMeter::RebuildWidget(){SAssignNew(Meter,SColdSteelResourceMeter);Meter->Ratio=Value;Meter->bMana=bMana;return Meter.ToSharedRef();}
void UColdSteelResourceMeter::SetValue(float InRatio,bool bInMana){const float Next=FMath::IsFinite(InRatio)?FMath::Clamp(InRatio,0.f,1.f):0.f;if(Value==Next&&bMana==bInMana)return;Value=Next;bMana=bInMana;if(Meter){Meter->Ratio=Value;Meter->bMana=bMana;Meter->Invalidate(EInvalidateWidgetReason::Paint);}}
void UColdSteelResourceMeter::ReleaseSlateResources(bool bReleaseChildren){Super::ReleaseSlateResources(bReleaseChildren);Meter.Reset();}
