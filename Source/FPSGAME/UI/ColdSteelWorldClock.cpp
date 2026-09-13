#include "ColdSteelWorldClock.h"
#include "ColdSteelUIStyle.h"
#include "Rendering/DrawElementTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
// Source SVG used a 48x48 viewBox. Keep its geometry independent of DPI.
class SColdSteelSunDial : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelSunDial) {} SLATE_END_ARGS()
    void Construct(const FArguments&) {}
    float Fraction=0;
    bool Available=false;
    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(52); }
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool) const override
    {
        const float Unit=FMath::Min(G.GetLocalSize().X,G.GetLocalSize().Y)/48.f;
        const FVector2f Origin((G.GetLocalSize().X-48*Unit)/2,(G.GetLocalSize().Y-48*Unit)/2);
        const auto Tint=Style.GetColorAndOpacityTint();
        auto Line=[&](const TArray<FVector2f>& Points,const FLinearColor& Color,float Width,int32 Z)
        {
            TArray<FVector2f> Scaled;Scaled.Reserve(Points.Num());for(const auto& P:Points)Scaled.Add(Origin+P*Unit);
            FSlateDrawElement::MakeLines(Out,Layer+Z,G.ToPaintGeometry(),Scaled,ESlateDrawEffect::None,Color*Tint,true,Width*Unit);
        };
        auto Disc=[&](FVector2f Center,float Radius,const FLinearColor& Color,int32 Z)
        {
            // Raw MakeBox uses its draw tint, unlike SBorder which applies the brush tint for us.
            const auto Brush=ColdSteelUI::RoundedBrush(FLinearColor::White,Radius*Unit,FLinearColor::Transparent,0);
            FSlateDrawElement::MakeBox(Out,Layer+Z,G.ToPaintGeometry(FVector2D(2*Radius*Unit),FSlateLayoutTransform(FVector2D(Origin+(Center-FVector2f(Radius))*Unit))),&Brush,ESlateDrawEffect::None,Color*Tint);
        };
        auto Arc=[&](float Start,float End,const FLinearColor& Color)
        {
            TArray<FVector2f> Points;for(int32 I=0;I<=32;++I){const float A=FMath::Lerp(Start,End,I/32.f);Points.Add(FVector2f(24+20*FMath::Cos(A),24+20*FMath::Sin(A)));}
            Line(Points,Color,2.8f,1);
        };
        const FLinearColor Face=ColdSteelUI::Content.CopyWithNewOpacity(1);
        Disc(FVector2f(24),22,Face,0);
        Arc(PI,2*PI,ColdSteelUI::Warning);
        Arc(0,PI,ColdSteelUI::Enchanted);
        Line({FVector2f(4,24),FVector2f(44,24)},ColdSteelUI::Border,.7f,1);
        for(int32 I=0;I<24;++I)
        {
            const bool Major=I%6==0;const float A=I*2*PI/24-PI/2;
            const FVector2f Direction(FMath::Cos(A),FMath::Sin(A));
            Line({FVector2f(24)+Direction*(Major?16.f:19.5f),FVector2f(24)+Direction*21.5f},Major?ColdSteelUI::Accent:ColdSteelUI::TextTertiary.CopyWithNewOpacity(.75f),Major?1.6f:.9f,2);
        }
        if(Available)
        {
            // Midnight down, 06:00 left, noon up, 18:00 right.
            const float A=Fraction*2*PI+PI/2;
            const FVector2f Direction(FMath::Cos(A),FMath::Sin(A));
            const FVector2f Tip=FVector2f(24)+Direction*15,Tail=FVector2f(24)-Direction*3;
            Line({Tail,Tip},Face,5.8f,3);
            Disc(Tip,4,Face,3);
            Line({Tail,Tip},ColdSteelUI::TextPrimary,3.2f,4);
            Disc(Tip,2.7f,ColdSteelUI::TextPrimary,5);
        }
        Disc(FVector2f(24),3.2f,Face,5);
        Disc(FVector2f(24),1.8f,ColdSteelUI::Accent,6);
        return Layer+6;
    }
};

class SColdSteelTimeSymbol : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelTimeSymbol) {} SLATE_END_ARGS()
    void Construct(const FArguments&) {}
    int32 Period=-1; // 0 dawn, 1 day, 2 dusk, 3 night
    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(16); }
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool) const override
    {
        if(Period<0)return Layer;
        const float U=FMath::Min(G.GetLocalSize().X,G.GetLocalSize().Y)/16.f;
        const FLinearColor Color=(Period==3?ColdSteelUI::Enchanted:ColdSteelUI::Warning)*Style.GetColorAndOpacityTint();
        auto Line=[&](TArray<FVector2f> Points){for(auto& P:Points)P*=U;FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Color,true,U);};
        if(Period==3)
        {
            TArray<FVector2f> Crescent;
            for(int32 I=0;I<=20;++I){const float A=FMath::Lerp(-PI/2,PI/2,I/20.f);Crescent.Add(FVector2f(8-5*FMath::Cos(A),8+5*FMath::Sin(A)));}
            for(int32 I=20;I>=0;--I){const float A=FMath::Lerp(-PI/2,PI/2,I/20.f);Crescent.Add(FVector2f(8-2*FMath::Cos(A),8+5*FMath::Sin(A)));}
            Line(Crescent);
        }
        else
        {
            const bool Horizon=Period!=1;const FVector2f Center(8,Horizon?10:8);
            TArray<FVector2f> Circle;for(int32 I=0;I<=24;++I){const float A=(Horizon?PI:0)+I/24.f*(Horizon?PI:2*PI);Circle.Add(Center+FVector2f(FMath::Cos(A),FMath::Sin(A))*3);}
            Line(Circle);
            for(int32 I=0;I<8;++I){const float A=I*PI/4;if(Horizon&&FMath::Sin(A)>.01f)continue;const FVector2f D(FMath::Cos(A),FMath::Sin(A));Line({Center+D*5,Center+D*6.5f});}
            if(Horizon)Line({FVector2f(2,12),FVector2f(14,12)});
        }
        return Layer;
    }
};
}

class SColdSteelWorldClock : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelWorldClock) {} SLATE_END_ARGS()
    void Construct(const FArguments&)
    {
        const auto TimeRow=SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(TimeText,STextBlock).ColorAndOpacity(ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SAssignNew(DayText,STextBlock).ColorAndOpacity(ColdSteelUI::TextSecondary)];
        const auto PeriodRow=SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SAssignNew(SymbolBox,SBox)[SAssignNew(Symbol,SColdSteelTimeSymbol)]]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(PeriodText,STextBlock).ColorAndOpacity(ColdSteelUI::TextSecondary)];
        const auto Readout=SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()[TimeRow]
            +SVerticalBox::Slot().AutoHeight()
            [SAssignNew(PeriodPadding,SBorder).BorderImage(FCoreStyle::Get().GetBrush("NoBrush"))[PeriodRow]];
        const auto ContentRow=SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SAssignNew(DialBox,SBox)[SAssignNew(Dial,SColdSteelSunDial)]]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(TextPadding,SBorder).BorderImage(FCoreStyle::Get().GetBrush("NoBrush"))[Readout]];
        ChildSlot
        [SAssignNew(Blur,SBackgroundBlur).Padding(0).BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius)
            [SAssignNew(Surface,SBorder).BorderImage(&GlassBrush)[ContentRow]]];
        SetScale(1);SetTime(0,0,false);
    }
    void SetScale(float S)
    {
        GlassBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S);
        FallbackBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/S);
        Blur->SetCornerRadius(FVector4(10/S));Blur->SetLowQualityBackgroundBrush(&FallbackBrush);
        Surface->SetPadding(FMargin(12/S,9/S));TextPadding->SetPadding(FMargin(10/S,0,0,0));PeriodPadding->SetPadding(FMargin(0,2/S,0,0));
        DialBox->SetWidthOverride(52/S);DialBox->SetHeightOverride(52/S);SymbolBox->SetWidthOverride(22/S);SymbolBox->SetHeightOverride(16/S);
        TimeText->SetFont(ColdSteelUI::NumberFont(20*.75f/S,true));DayText->SetFont(ColdSteelUI::NumberFont(14*.75f/S));PeriodText->SetFont(ColdSteelUI::TextFont(12*.75f/S));
        Invalidate(EInvalidateWidgetReason::Layout|EInvalidateWidgetReason::Paint);
    }
    void SetTime(int32 Day,float Fraction,bool Available)
    {
        if(Dial->Fraction!=Fraction||Dial->Available!=Available){Dial->Fraction=Fraction;Dial->Available=Available;Dial->Invalidate(EInvalidateWidgetReason::Paint);}
        const int32 Minutes=Available?FMath::Clamp(FMath::FloorToInt(Fraction*1440.f),0,1439):-1;
        if(Minutes==LastMinute&&Day==LastDay&&Available==LastAvailable)return;
        LastMinute=Minutes;LastDay=Day;LastAvailable=Available;
        const int32 Hour=Minutes/60;
        const int32 Period=!Available?-1:Hour>=5&&Hour<8?0:Hour>=8&&Hour<17?1:Hour>=17&&Hour<20?2:3;
        static const TCHAR* Names[]={TEXT("晨曦"),TEXT("白昼"),TEXT("黄昏"),TEXT("深夜")};
        TimeText->SetText(FText::FromString(Available?FString::Printf(TEXT("%02d:%02d"),Hour,Minutes%60):TEXT("--:--")));
        DayText->SetText(FText::FromString(Available?FString::Printf(TEXT("第%d日"),Day):TEXT("—")));
        PeriodText->SetText(FText::FromString(Available?Names[Period]:TEXT("时间未接入")));
        PeriodText->SetColorAndOpacity(Available?(Period==3?ColdSteelUI::Enchanted:ColdSteelUI::Warning):ColdSteelUI::TextSecondary);
        Symbol->Period=Period;Symbol->Invalidate(EInvalidateWidgetReason::Paint);
    }
private:
    FSlateBrush GlassBrush,FallbackBrush;
    TSharedPtr<SBackgroundBlur> Blur;
    TSharedPtr<SBorder> Surface,TextPadding,PeriodPadding;
    TSharedPtr<SBox> DialBox,SymbolBox;
    TSharedPtr<SColdSteelSunDial> Dial;
    TSharedPtr<SColdSteelTimeSymbol> Symbol;
    TSharedPtr<STextBlock> TimeText,DayText,PeriodText;
    int32 LastMinute=INDEX_NONE-1,LastDay=INDEX_NONE;
    bool LastAvailable=false;
};

TSharedRef<SWidget> UColdSteelWorldClock::RebuildWidget()
{
    SAssignNew(Clock,SColdSteelWorldClock);Clock->SetScale(DisplayScale);Clock->SetTime(Day,DayFraction,bAvailable);return Clock.ToSharedRef();
}
void UColdSteelWorldClock::SetTime(int32 InDay,float InDayFraction,bool bInAvailable)
{
    bAvailable=bInAvailable&&FMath::IsFinite(InDayFraction);Day=InDay;DayFraction=bAvailable?FMath::Clamp(InDayFraction,0.f,.999999f):0;
    if(Clock)Clock->SetTime(Day,DayFraction,bAvailable);
}
void UColdSteelWorldClock::SetDisplayScale(float InScale)
{
    const float S=FMath::Max(.01f,InScale);if(FMath::IsNearlyEqual(DisplayScale,S,.0001f))return;DisplayScale=S;if(Clock)Clock->SetScale(S);
}
void UColdSteelWorldClock::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);Clock.Reset();
}
