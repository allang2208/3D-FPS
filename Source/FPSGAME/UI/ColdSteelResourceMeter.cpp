#include "ColdSteelResourceMeter.h"
#include "ColdSteelMeterPresentation.h"
#include "ColdSteelUIStyle.h"
#include "HAL/PlatformTime.h"
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElementTypes.h"

int32 ColdSteelUI::PaintResourceMeter(const FGeometry& G, FSlateWindowElementList& Out,
    int32 Layer, FVector2D Offset, FVector2D Size, float DisplayRatio,
    const FLinearColor& Fill, const FLinearColor& Deep, const FLinearColor& BorderColor,
    const FLinearColor& Tint)
{
    if (Size.X <= 0.f || Size.Y <= 0.f) return Layer;
    const float Unit = Size.Y / 9.f;
    const auto Track = RoundedBrush(FLinearColor::White, 3 * Unit, FLinearColor::Transparent, 0);
    FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(Size, FSlateLayoutTransform(Offset)),
        &Track, ESlateDrawEffect::None, BorderColor * Tint);
    const auto Inner = RoundedBrush(FLinearColor::White, 2 * Unit, FLinearColor::Transparent, 0);
    const FVector2D InnerSize(FMath::Max(0., Size.X - 2 * Unit), FMath::Max(0., Size.Y - 2 * Unit));
    const FVector2D InnerAt = Offset + FVector2D(Unit);
    FSlateDrawElement::MakeBox(Out, Layer + 1, G.ToPaintGeometry(InnerSize, FSlateLayoutTransform(InnerAt)),
        &Inner, ESlateDrawEffect::None, Content * Tint);
    const FVector2D FillSize(InnerSize.X * FMath::Clamp(DisplayRatio, 0.f, 1.f), InnerSize.Y);
    if (FillSize.X > 0.f && FillSize.Y > 0.f)
    {
        TArray<FSlateGradientStop> Stops;
        Stops.Emplace(FVector2f(0, 0), Deep * Tint);
        Stops.Emplace(FVector2f(FillSize.X, 0), Fill * Tint);
        FSlateDrawElement::MakeGradient(Out, Layer + 2,
            G.ToPaintGeometry(FillSize, FSlateLayoutTransform(InnerAt)), Stops,
            Orient_Vertical, ESlateDrawEffect::None, FVector4f(2 * Unit));
    }
    return Layer + 2;
}

class SColdSteelResourceMeter : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelResourceMeter) {} SLATE_END_ARGS()
    void Construct(const FArguments&) {}
    FColdSteelMeterTransition Transition;
    bool bMana = false;
    bool bStamina = false;
    bool bSemantic = false;
    FLinearColor SemanticFill = FLinearColor::White, SemanticDeep = FLinearColor::White;

    void SetTarget(float Ratio, bool bSnap = false)
    {
        const double Now = FPlatformTime::Seconds();
        Transition.SetTarget(Ratio, Now, bSnap);
        Invalidate(EInvalidateWidgetReason::Paint);
        if (Transition.IsAnimating(Now) && !AnimationTimer.IsValid())
            AnimationTimer = RegisterActiveTimer(0.f,
                FWidgetActiveTimerDelegate::CreateSP(this, &SColdSteelResourceMeter::Animate));
    }

    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(160, 9); }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&,
        FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool) const override
    {
        const float Ratio = Transition.Target;
        const auto Deep = bSemantic ? SemanticDeep : bStamina ? ColdSteelUI::StaminaDeep : bMana ? ColdSteelUI::ManaDeep : ColdSteelUI::HealthDeep;
        const auto Light = bSemantic ? (Ratio <= .25f ? ColdSteelUI::Warning : SemanticFill) :
            bStamina ? (Ratio <= .25f ? ColdSteelUI::Warning : ColdSteelUI::Stamina) : bMana ? ColdSteelUI::Mana : ColdSteelUI::Health;
        return ColdSteelUI::PaintResourceMeter(G, Out, Layer, FVector2D::ZeroVector, G.GetLocalSize(),
            Transition.ValueAt(FPlatformTime::Seconds()), Light, Deep,
            !bMana && Ratio <= .25f ? ColdSteelUI::Danger : ColdSteelUI::Border,
            Style.GetColorAndOpacityTint());
    }

private:
    TWeakPtr<FActiveTimerHandle> AnimationTimer;
    EActiveTimerReturnType Animate(double, float)
    {
        Invalidate(EInvalidateWidgetReason::Paint);
        if (Transition.IsAnimating(FPlatformTime::Seconds())) return EActiveTimerReturnType::Continue;
        AnimationTimer.Reset();
        return EActiveTimerReturnType::Stop;
    }
};

TSharedRef<SWidget> UColdSteelResourceMeter::RebuildWidget()
{
    SAssignNew(Meter, SColdSteelResourceMeter);
    Meter->bMana = bMana;
    Meter->bStamina = bStamina;
    Meter->bSemantic = bSemantic;
    Meter->SemanticFill = SemanticFill;
    Meter->SemanticDeep = SemanticDeep;
    if (bHasValue) Meter->SetTarget(Value, true);
    return Meter.ToSharedRef();
}

void UColdSteelResourceMeter::SetSemanticValue(float InRatio, const FLinearColor& Fill, const FLinearColor& Deep)
{
    const float Next = FMath::IsFinite(InRatio) ? FMath::Clamp(InRatio, 0.f, 1.f) : 0.f;
    if (bHasValue && bSemantic && Value == Next && SemanticFill == Fill && SemanticDeep == Deep) return;
    const bool bSnap = !bHasValue;
    bHasValue = true;
    bSemantic = true;
    bMana = bStamina = false;
    Value = Next;
    SemanticFill = Fill;
    SemanticDeep = Deep;
    if (Meter)
    {
        Meter->bMana = Meter->bStamina = false;
        Meter->bSemantic = true;
        Meter->SemanticFill = Fill;
        Meter->SemanticDeep = Deep;
        Meter->SetTarget(Value, bSnap);
    }
}

void UColdSteelResourceMeter::SetStaminaValue(float InRatio)
{
    const bool bChanged = !bStamina;
    SetValue(InRatio, false);
    bStamina = true;
    if (Meter)
    {
        Meter->bStamina = true;
        if (bChanged) Meter->Invalidate(EInvalidateWidgetReason::Paint);
    }
}

void UColdSteelResourceMeter::SetValue(float InRatio, bool bInMana)
{
    const float Next = FMath::IsFinite(InRatio) ? FMath::Clamp(InRatio, 0.f, 1.f) : 0.f;
    if (bHasValue && !bSemantic && Value == Next && bMana == bInMana) return;
    const bool bSnap = !bHasValue;
    bHasValue = true;
    Value = Next;
    bMana = bInMana;
    bSemantic = false;
    if (Meter)
    {
        Meter->bMana = bMana;
        Meter->bStamina = bStamina;
        Meter->bSemantic = false;
        Meter->SetTarget(Value, bSnap);
    }
}

void UColdSteelResourceMeter::ResetAnimation()
{
    bHasValue = false;
    if (Meter) Meter->Transition = FColdSteelMeterTransition{};
}

void UColdSteelResourceMeter::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    Meter.Reset();
}
