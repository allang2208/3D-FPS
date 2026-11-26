#include "ColdSteelPlantingProgress.h"
#include "ColdSteelUIStyle.h"
#include "Rendering/DrawElementTypes.h"
#include "HAL/PlatformTime.h"

void SColdSteelPlantingProgress::Construct(const FArguments&)
{SetCanTick(false);SetClipping(EWidgetClipping::ClipToBoundsAlways);}
FVector2D SColdSteelPlantingProgress::ComputeDesiredSize(float) const
{return FVector2D(48.f,8.f)/Scale;}
void SColdSteelPlantingProgress::SetPixelScale(float InScale)
{
    const float Next=FMath::Max(.01f,InScale);
    if(FMath::IsNearlyEqual(Scale,Next))return;
    Scale=Next;Invalidate(EInvalidateWidgetReason::Layout);
}
void SColdSteelPlantingProgress::SetPlant(const FGuid& Id,float Ratio,bool bAnimate)
{
    const float Next=Id.IsValid()&&FMath::IsFinite(Ratio)?FMath::Clamp(Ratio,0.f,1.f):0.f;
    const bool NewPlant=PlantId!=Id;
    if(NewPlant||(Next>=1.f)!=(Transition.Target>=1.f)||!FMath::IsNearlyEqual(Next,Transition.Target,.00001f))
    {
        const double Now=FPlatformTime::Seconds();
        if(!NewPlant&&PlantId.IsValid()&&Transition.Target<1.f&&Next>=1.f)MatureFlashAt=Now;
        if(NewPlant)MatureFlashAt=-1.;
        PlantId=Id;Transition.SetTarget(Next,Now,NewPlant);
        Invalidate(EInvalidateWidgetReason::Paint);
    }
    SetEffectsEnabled(bAnimate);EnsureAnimation();
}
void SColdSteelPlantingProgress::SetEffectsEnabled(bool Enabled)
{
    if(bEffectsEnabled==Enabled)return;
    bEffectsEnabled=Enabled;
    if(!Enabled)
    {
        if(auto Timer=AnimationTimer.Pin())UnRegisterActiveTimer(Timer.ToSharedRef());
        AnimationTimer.Reset();
    }
    else EnsureAnimation();
    Invalidate(EInvalidateWidgetReason::Paint);
}
void SColdSteelPlantingProgress::EnsureAnimation()
{
    const double Now=FPlatformTime::Seconds();
    const bool Active=PlantId.IsValid()&&(Transition.Target<1.f||Transition.IsAnimating(Now)||(MatureFlashAt>=0&&Now-MatureFlashAt<.8));
    if(bEffectsEnabled&&Active&&!AnimationTimer.IsValid())
        AnimationTimer=RegisterActiveTimer(1.f/30.f,FWidgetActiveTimerDelegate::CreateSP(this,&SColdSteelPlantingProgress::Animate));
}
EActiveTimerReturnType SColdSteelPlantingProgress::Animate(double,float)
{
    const double Now=FPlatformTime::Seconds();Invalidate(EInvalidateWidgetReason::Paint);
    if(bEffectsEnabled&&PlantId.IsValid()&&(Transition.Target<1.f||Transition.IsAnimating(Now)||(MatureFlashAt>=0&&Now-MatureFlashAt<.8)))
        return EActiveTimerReturnType::Continue;
    AnimationTimer.Reset();return EActiveTimerReturnType::Stop;
}
int32 SColdSteelPlantingProgress::OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,
    int32 Layer,const FWidgetStyle& Style,bool) const
{
    const FVector2D Size=G.GetLocalSize();if(Size.X<=0||Size.Y<=0)return Layer;
    const float Unit=1.f/Scale;
    // The rail sits three physical pixels inside a six-pixel-radius tile.
    const float Radius=FMath::Min((ColdSteelUI::ButtonRadius-3.f)*Unit,float(FMath::Min(Size.X,Size.Y))*.5f);
    const auto Tint=Style.GetColorAndOpacityTint();
    const auto Track=ColdSteelUI::RoundedBrush(ColdSteelUI::Content,Radius);
    FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(),&Track,ESlateDrawEffect::None,Tint);
    const float Ratio=Transition.ValueAt(FPlatformTime::Seconds());
    const FVector2D InnerAt(Unit,Unit),InnerSize(FMath::Max(0.,Size.X-2*Unit),FMath::Max(0.,Size.Y-2*Unit));
    const FVector2D FillSize(InnerSize.X*FMath::Clamp(Ratio,0.f,1.f),InnerSize.Y);
    if(PlantId.IsValid()&&FillSize.X>0&&FillSize.Y>0)
    {
        const double Now=FPlatformTime::Seconds();
        const auto Fill=ColdSteelUI::ActionProgressColor(Ratio);
        const auto Deep=FMath::Lerp(ColdSteelUI::Content,Fill,.48f);
        const float Sweep=bEffectsEnabled&&Transition.Target<1.f?float(FMath::Fmod(Now+double(GetTypeHash(PlantId)%29)*.1,3.2)/3.2)*1.5f-.25f:-1.f;
        const float Flash=bEffectsEnabled&&MatureFlashAt>=0?FMath::Clamp(1.f-float(Now-MatureFlashAt)/.8f,0.f,1.f):0.f;
        TArray<float,TInlineAllocator<5>> Points={0.f,FMath::Clamp(Sweep-.13f,0.f,1.f),FMath::Clamp(Sweep,0.f,1.f),FMath::Clamp(Sweep+.13f,0.f,1.f),1.f};
        Points.Sort();TArray<FSlateGradientStop> Stops;Stops.Reserve(5);
        for(float P:Points)
        {
            const float Sheen=bEffectsEnabled&&Sweep>=-.13f?FMath::Max(0.f,1.f-FMath::Abs(P-Sweep)/.13f)*.24f:0.f;
            auto Color=FMath::Lerp(Deep,Fill,P*.65f+.35f);
            Color=FMath::Lerp(Color,ColdSteelUI::TextPrimary,FMath::Clamp(Sheen+Flash*.3f,0.f,.4f));
            Stops.Emplace(FVector2f(float(FillSize.X)*P,0),Color*Tint);
        }
        const float InnerRadius=FMath::Max(0.f,FMath::Min(Radius-Unit,float(FMath::Min(FillSize.X,FillSize.Y))*.5f));
        // Fill and sweep share one rounded gradient mesh; there is no rectangular glow to leak out.
        FSlateDrawElement::MakeGradient(Out,Layer+1,G.ToPaintGeometry(FillSize,FSlateLayoutTransform(InnerAt)),
            Stops,Orient_Vertical,ESlateDrawEffect::None,FVector4f(InnerRadius));
    }
    const auto Outline=ColdSteelUI::RoundedBrush(FLinearColor::Transparent,Radius,ColdSteelUI::Border.CopyWithNewOpacity(.45f*Tint.A),Unit);
    FSlateDrawElement::MakeBox(Out,Layer+2,G.ToPaintGeometry(),&Outline,ESlateDrawEffect::None,Tint);
    return Layer+2;
}
