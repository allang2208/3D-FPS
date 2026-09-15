#include "ColdSteelDisclosureIndicator.h"
#include "ColdSteelUIStyle.h"
#include "Components/ExpandableArea.h"
#include "Widgets/SLeafWidget.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"

class SColdSteelDisclosureIndicator : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelDisclosureIndicator) : _Scale(1.f),_Expanded(false),_Intro(false) {}
        SLATE_ARGUMENT(float,Scale)
        SLATE_ARGUMENT(bool,Expanded)
        SLATE_ARGUMENT(bool,Intro)
        SLATE_ARGUMENT(TWeakObjectPtr<UExpandableArea>,Header)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {Scale=Args._Scale;bExpanded=Args._Expanded;Header=Args._Header;IntroRemaining=Args._Intro?3.6f:0.f;bPlaying=!bExpanded&&IntroRemaining>0;SetVisibility(EVisibility::HitTestInvisible);SetCanTick(true);}
    void SetExpanded(bool Expanded)
    {
        if(bExpanded==Expanded)return;
        bExpanded=Expanded;Elapsed=0.f;if(Expanded){IntroRemaining=0.f;bPlaying=false;}Invalidate(EInvalidateWidgetReason::PaintAndVolatility);
    }
    virtual FVector2D ComputeDesiredSize(float)const override{return FVector2D(24.f/Scale);}
    virtual bool ComputeVolatility()const override{return bPlaying;}
    virtual void Tick(const FGeometry& Geometry,double Time,float Delta)override
    {
        SLeafWidget::Tick(Geometry,Time,Delta);
        const bool Highlighted=Header.IsValid()&&(Header->IsHovered()||Header->HasAnyUserFocus()||Header->HasFocusedDescendants());
        IntroRemaining=FMath::Max(0.f,IntroRemaining-Delta);
        const bool Playing=!bExpanded&&(IntroRemaining>0||Highlighted);
        if(Playing!=bPlaying){bPlaying=Playing;Elapsed=0.f;Invalidate(EInvalidateWidgetReason::PaintAndVolatility);}
        if(bPlaying){Elapsed=FMath::Fmod(Elapsed+Delta,1.8f);Invalidate(EInvalidateWidgetReason::Paint);}
    }
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,
        FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool ParentEnabled)const override
    {
        // Keep a fully opaque solid core. Only its highlight and surrounding halo pulse.
        const float Pulse=!bPlaying||!ParentEnabled?0.f:FMath::Pow(.5f-.5f*FMath::Cos(2.f*PI*Elapsed/1.8f),4.f);
        const FVector2f Center=FVector2f(Geometry.GetLocalSize())*.5f;
        const FVector2f Points[]={FVector2f(-4.5f,-7.f),FVector2f(7.f,0.f),FVector2f(-4.5f,7.f)};
        const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
        auto Triangle=[&](float Extent,FLinearColor Color,int32 Z)
        {
            TArray<FSlateVertex> Vertices;Vertices.Reserve(3);
            Color*=Style.GetColorAndOpacityTint();if(!ParentEnabled)Color.A*=.45f;
            for(FVector2f Point:Points)
            {
                if(bExpanded)Point=FVector2f(-Point.Y,Point.X);
                const FVector2f Position=Center+Point*(Extent/Scale);
                Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Geometry.GetAccumulatedRenderTransform(),Position,FVector2f(.5f,.5f),Color.ToFColor(true)));
            }
            const TArray<SlateIndex> Indices={0,1,2};
            FSlateDrawElement::MakeCustomVerts(Elements,Layer+Z,Resource,Vertices,Indices,nullptr,0,0);
        };
        if(Pulse>0)
        {
            for(int32 Ring=3;Ring>=1;--Ring)
            {
                FLinearColor Halo=ColdSteelUI::ItemTooltipDisclosureFlash;Halo.A=Pulse*.045f;
                Triangle(1.f+Ring*.12f,Halo,0);
            }
        }
        Triangle(1.12f,ColdSteelUI::ItemTooltipDisclosureOutline,1);
        Triangle(1.f,FMath::Lerp(ColdSteelUI::ItemTooltipDisclosure,ColdSteelUI::ItemTooltipDisclosureFlash,Pulse*.6f),2);
        return Layer+2;
    }
private:
    float Scale=1.f,Elapsed=0.f,IntroRemaining=0.f;
    TWeakObjectPtr<UExpandableArea> Header;
    bool bExpanded=false,bPlaying=false;
};

void UColdSteelDisclosureIndicator::Configure(float PixelScale,bool Expanded,UExpandableArea* InHeader,bool Intro)
{Scale=PixelScale;bExpanded=Expanded;Header=InHeader;bIntro=Intro;SetVisibility(ESlateVisibility::HitTestInvisible);if(Indicator)Indicator->SetExpanded(Expanded);}
void UColdSteelDisclosureIndicator::SetExpanded(bool Expanded)
{bExpanded=Expanded;if(Indicator)Indicator->SetExpanded(Expanded);}
TSharedRef<SWidget> UColdSteelDisclosureIndicator::RebuildWidget()
{return SAssignNew(Indicator,SColdSteelDisclosureIndicator).Scale(Scale).Expanded(bExpanded).Header(Header).Intro(bIntro);}
void UColdSteelDisclosureIndicator::ReleaseSlateResources(bool ReleaseChildren)
{Super::ReleaseSlateResources(ReleaseChildren);Indicator.Reset();}
