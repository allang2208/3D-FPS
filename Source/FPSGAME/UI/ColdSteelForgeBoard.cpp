#include "ColdSteelForgeBoard.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/ForgingSystem.h"
#include "Engine/Texture2D.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Rendering/DrawElements.h"
#include "Input/Reply.h"

class SColdSteelForgeBoard : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelForgeBoard) {} SLATE_END_ARGS()
    void Construct(const FArguments&) {SetCanTick(false);}
    void Configure(UColdSteelForgingSystem* InSystem,UTexture2D* Texture)
    {
        System=InSystem;Mold.SetResourceObject(Texture);Mold.DrawAs=ESlateBrushDrawType::Image;
        Mold.ImageSize=Texture?FVector2D(Texture->GetSizeX(),Texture->GetSizeY()):FVector2D(384,768);
        Invalidate(EInvalidateWidgetReason::Paint);
    }
    virtual FVector2D ComputeDesiredSize(float) const override {return FVector2D(320,360);}
    FSlateRect MoldRect(const FGeometry& G) const
    {
        const FVector2D Size=G.GetLocalSize(),Space=Size-FVector2D(48,48);
        const double Fit=FMath::Max(.001,FMath::Min(Space.X/Mold.ImageSize.X,Space.Y/Mold.ImageSize.Y));
        const FVector2D Extent=Mold.ImageSize*Fit,Origin=(Size-Extent)*.5;
        return FSlateRect(Origin.X,Origin.Y,Origin.X+Extent.X,Origin.Y+Extent.Y);
    }
    virtual int32 OnPaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Clip,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool ParentEnabled) const override
    {
        const float Scale=FMath::Max(.1f,G.GetAccumulatedLayoutTransform().GetScale());
        const FLinearColor Tint=Style.GetColorAndOpacityTint();
        const FVector2D Size=G.GetLocalSize();
        const float Radius=ColdSteelUI::CardRadius/Scale;
        TArray<FSlateGradientStop> Stops;
        Stops.Reserve(3);
        Stops.Emplace(FVector2f(0,0),ColdSteelUI::Gray(42,238)*Tint);
        Stops.Emplace(FVector2f(0,Size.Y*.55f),ColdSteelUI::Gray(26,242)*Tint);
        Stops.Emplace(FVector2f(0,Size.Y),ColdSteelUI::Gray(12,248)*Tint);
        // Slate's orientation names describe the stop lines: horizontal lines vary along Y.
        FSlateDrawElement::MakeGradient(Out,Layer,G.ToPaintGeometry(),MoveTemp(Stops),Orient_Horizontal,ESlateDrawEffect::None,FVector4f(Radius));
        const FSlateBrush Edge=ColdSteelUI::RoundedBrush(FLinearColor::Transparent,Radius,ColdSteelUI::Border*Tint,1/Scale);
        // MakeBox does not apply Brush.TintColor; omitting InTint paints an opaque white fill.
        FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(),&Edge,ESlateDrawEffect::None,FLinearColor::Transparent);
        const FSlateRect Rect=MoldRect(G);const FVector2D Origin(Rect.Left,Rect.Top),Extent(Rect.Right-Rect.Left,Rect.Bottom-Rect.Top);
        if(Mold.GetResourceObject())
        {
            FSlateDrawElement::MakeBox(Out,Layer+2,G.ToPaintGeometry(Extent+FVector2D(6/Scale,6/Scale),FSlateLayoutTransform(Origin-FVector2D(3/Scale,1/Scale))),&Mold,ESlateDrawEffect::None,FLinearColor(.04,.04,.04,1)*Tint);
            FSlateDrawElement::MakeBox(Out,Layer+3,G.ToPaintGeometry(Extent,FSlateLayoutTransform(Origin)),&Mold,ESlateDrawEffect::None,Tint);
        }
        auto Ring=[&](FVector2D P,float Radius,FLinearColor Color,float Width)
        {
            TArray<FVector2D> Points;for(int32 N=0;N<=40;++N){const float A=N*2*PI/40;Points.Add(P+FVector2D(FMath::Cos(A),FMath::Sin(A))*Radius);}
            FSlateDrawElement::MakeLines(Out,Layer+4,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Color*Tint,true,Width/Scale);
        };
        const auto* S=System.Get();FVector2D UV;float Life=0;ShownIndex=INDEX_NONE;
        if(S&&IsEnabled()&&S->Target(UV,Life))
        {
            ShownIndex=S->TargetIndex();const FVector2D P=Origin+UV*Extent;const float R=20*Life/Scale;
            Ring(P,R,ColdSteelUI::Warning,2*Life);
            const float DotRadius=4*Life/Scale;
            const FSlateBrush Dot=ColdSteelUI::RoundedBrush(ColdSteelUI::Warning,DotRadius,FLinearColor::Transparent,0);
            FSlateDrawElement::MakeBox(Out,Layer+5,G.ToPaintGeometry(FVector2D(2*DotRadius),FSlateLayoutTransform(P-FVector2D(DotRadius))),&Dot,ESlateDrawEffect::None,ColdSteelUI::Warning*Tint);
        }
        const double Age=FPlatformTime::Seconds()-FeedbackAt;
        if(Age<.28)
        {
            const FVector2D P=Origin+FeedbackUV*Extent;FLinearColor Color=bHit?ColdSteelUI::Success:ColdSteelUI::Danger;Color.A*=1-Age/.28;
            Ring(P,(20+Age*80)/Scale,Color,2);
            if(bHit)for(int32 N=0;N<8;++N)
            {
                const float A=N*PI/4;const FVector2D D(FMath::Cos(A),FMath::Sin(A));
                FSlateDrawElement::MakeLines(Out,Layer+5,G.ToPaintGeometry(),TArray<FVector2D>{P+D*(24+Age*100)/Scale,P+D*(30+Age*120)/Scale},ESlateDrawEffect::None,Color*Tint,true,1.5/Scale);
            }
        }
        return Layer+6;
    }
    FReply StrikeAt(const FGeometry& G,const FPointerEvent& Event)
    {
        if(Event.GetEffectingButton()==EKeys::LeftMouseButton)
        {
            if(auto* S=System.Get();S&&S->Active()&&ShownIndex!=INDEX_NONE)
            {
                const FSlateRect R=MoldRect(G);const FVector2D Extent(R.Right-R.Left,R.Bottom-R.Top);
                const FVector2D P=G.AbsoluteToLocal(Event.GetScreenSpacePosition())-FVector2D(R.Left,R.Top);
                const float Radius=20/FMath::Max(.1f,G.GetAccumulatedLayoutTransform().GetScale());
                FeedbackUV=FVector2D(P.X/Extent.X,P.Y/Extent.Y);
                bHit=S->Strike(ShownIndex,FeedbackUV,FVector2D(Radius/Extent.X,Radius/Extent.Y));FeedbackAt=FPlatformTime::Seconds();
                Invalidate(EInvalidateWidgetReason::Paint);
            }
        }
        return FReply::Handled();
    }
    virtual FReply OnMouseButtonDown(const FGeometry& G,const FPointerEvent& Event) override {return StrikeAt(G,Event);}
    virtual FReply OnMouseButtonDoubleClick(const FGeometry& G,const FPointerEvent& Event) override {return StrikeAt(G,Event);}
    virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent&) override {return FReply::Handled();}
private:
    TWeakObjectPtr<UColdSteelForgingSystem> System;
    FSlateBrush Mold;
    mutable int32 ShownIndex=INDEX_NONE;
    FVector2D FeedbackUV;
    double FeedbackAt=-100;
    bool bHit=false;
};
void UColdSteelForgeBoard::Configure(UColdSteelForgingSystem* InSystem,UTexture2D* InTexture)
{System=InSystem;Texture=InTexture;if(Board)Board->Configure(System,Texture);}
TSharedRef<SWidget> UColdSteelForgeBoard::RebuildWidget()
{
    SAssignNew(Board,SColdSteelForgeBoard);Board->Configure(System,Texture);
    const TWeakPtr<SColdSteelForgeBoard> WeakBoard=Board;
    // Blur only the scenery behind the preview; the weapon and any feedback stay sharp.
    // If blur is disabled, the same near-opaque gradient still supplies the dark surface.
    return SNew(SBackgroundBlur).Padding(0)
        .BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius)
        .CornerRadius_Lambda([WeakBoard]
        {
            const auto Preview=WeakBoard.Pin();
            const float Scale=Preview.IsValid()?FMath::Max(.1f,Preview->GetCachedGeometry().GetAccumulatedLayoutTransform().GetScale()):1.f;
            return FVector4(ColdSteelUI::CardRadius/Scale);
        })
        [Board.ToSharedRef()];
}
void UColdSteelForgeBoard::RefreshPaint(){if(Board)Board->Invalidate(EInvalidateWidgetReason::Paint);}
void UColdSteelForgeBoard::ReleaseSlateResources(bool bReleaseChildren)
{Super::ReleaseSlateResources(bReleaseChildren);Board.Reset();}
