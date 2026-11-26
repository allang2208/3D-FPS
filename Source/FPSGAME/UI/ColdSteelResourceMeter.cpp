#include "ColdSteelResourceMeter.h"
#include "ColdSteelMeterPresentation.h"
#include "ColdSteelUIStyle.h"
#include "HAL/PlatformTime.h"
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElementTypes.h"

int32 ColdSteelUI::PaintResourceMeter(const FGeometry& G, FSlateWindowElementList& Out,
    int32 Layer, FVector2D Offset, FVector2D Size, float DisplayRatio,
    const FLinearColor& Fill, const FLinearColor& Deep, const FLinearColor& BorderColor,
    const FLinearColor& Tint, float GhostRatio, const FLinearColor& GhostColor,
    float PendingCostRatio, float ShieldRatio, float TickSpacingRatio)
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

    int32 CurLayer = Layer + 2;

    // 1. Ghost bar (trailing damage / mana cost lag)
    if (GhostRatio > DisplayRatio && GhostColor.A > 0.01f)
    {
        const FVector2D GhostSize(InnerSize.X * FMath::Clamp(GhostRatio, 0.f, 1.f), InnerSize.Y);
        if (GhostSize.X > 0.f && GhostSize.Y > 0.f)
        {
            const auto GhostBrush = RoundedBrush(FLinearColor::White, 2 * Unit, FLinearColor::Transparent, 0);
            FSlateDrawElement::MakeBox(Out, CurLayer,
                G.ToPaintGeometry(GhostSize, FSlateLayoutTransform(InnerAt)),
                &GhostBrush, ESlateDrawEffect::None, GhostColor * Tint);
        }
    }
    CurLayer++;

    // 2. Real resource bar (gradient fill)
    const float ClampedDisplay = FMath::Clamp(DisplayRatio, 0.f, 1.f);
    const FVector2D FillSize(InnerSize.X * ClampedDisplay, InnerSize.Y);
    if (FillSize.X > 0.f && FillSize.Y > 0.f)
    {
        TArray<FSlateGradientStop> Stops;
        Stops.Emplace(FVector2f(0, 0), Deep * Tint);
        Stops.Emplace(FVector2f(FillSize.X, 0), Fill * Tint);
        FSlateDrawElement::MakeGradient(Out, CurLayer,
            G.ToPaintGeometry(FillSize, FSlateLayoutTransform(InnerAt)), Stops,
            Orient_Vertical, ESlateDrawEffect::None, FVector4f(2 * Unit));
    }
    CurLayer++;

    // 3. Pending Cost anticipation preview (warm-gold strip)
    if (PendingCostRatio > 0.001f && ClampedDisplay > 0.f)
    {
        const float PreviewStart = FMath::Max(0.f, ClampedDisplay - PendingCostRatio);
        const float PreviewWidthRatio = ClampedDisplay - PreviewStart;
        if (PreviewWidthRatio > 0.001f)
        {
            const FVector2D CostOffset(InnerAt.X + InnerSize.X * PreviewStart, InnerAt.Y);
            const FVector2D CostSize(InnerSize.X * PreviewWidthRatio, InnerSize.Y);
            const auto CostBrush = RoundedBrush(FLinearColor::White, 1 * Unit, FLinearColor::Transparent, 0);
            const float Pulse = 0.55f + 0.35f * FMath::Sin(float(FPlatformTime::Seconds() * 6.0));
            const FLinearColor CostTint = HUDGoldLight * FLinearColor(1.f, 1.f, 1.f, Pulse) * Tint;
            FSlateDrawElement::MakeBox(Out, CurLayer,
                G.ToPaintGeometry(CostSize, FSlateLayoutTransform(CostOffset)),
                &CostBrush, ESlateDrawEffect::None, CostTint);
        }
    }
    CurLayer++;

    // 4. Overshield / Ward Overlay (cyan-silver ice armor bar)
    if (ShieldRatio > 0.001f)
    {
        const float ClampedShield = FMath::Clamp(ShieldRatio, 0.f, 1.f);
        const FVector2D ShieldSize(InnerSize.X * ClampedShield, InnerSize.Y);
        if (ShieldSize.X > 0.f)
        {
            TArray<FSlateGradientStop> ShieldStops;
            ShieldStops.Emplace(FVector2f(0, 0), FLinearColor(0.20f, 0.45f, 0.60f, 0.85f) * Tint);
            ShieldStops.Emplace(FVector2f(ShieldSize.X, 0), FLinearColor(0.37f, 0.75f, 0.88f, 0.70f) * Tint);
            FSlateDrawElement::MakeGradient(Out, CurLayer,
                G.ToPaintGeometry(ShieldSize, FSlateLayoutTransform(InnerAt)), ShieldStops,
                Orient_Vertical, ESlateDrawEffect::None, FVector4f(2 * Unit));
        }
    }
    CurLayer++;

    // 5. Pacing tick marks (every 100 points)
    if (TickSpacingRatio > 0.01f && TickSpacingRatio < 0.99f)
    {
        const auto TickBrush = RoundedBrush(FLinearColor::White, 0.f, FLinearColor::Transparent, 0);
        const FLinearColor TickColor = FLinearColor(1.f, 1.f, 1.f, 0.18f) * Tint;
        for (float T = TickSpacingRatio; T < 0.99f; T += TickSpacingRatio)
        {
            const FVector2D TickOffset(InnerAt.X + InnerSize.X * T, InnerAt.Y);
            FSlateDrawElement::MakeBox(Out, CurLayer,
                G.ToPaintGeometry(FVector2D(1.f, InnerSize.Y), FSlateLayoutTransform(TickOffset)),
                &TickBrush, ESlateDrawEffect::None, TickColor);
        }
    }

    return CurLayer + 1;
}

class SColdSteelResourceMeter : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelResourceMeter) {} SLATE_END_ARGS()
    void Construct(const FArguments&) {}
    FColdSteelMeterTransition Transition;
    FColdSteelGhostTransition GhostTransition;
    bool bMana = false;
    bool bStamina = false;
    bool bSemantic = false;
    bool bWarnOnLowFill = true;
    FLinearColor SemanticFill = FLinearColor::White, SemanticDeep = FLinearColor::White;
    float PendingCostRatio = 0.f;
    float ShieldRatio = 0.f;
    float MaxPoints = 0.f;

    void SetTarget(float Ratio, bool bSnap = false)
    {
        const double Now = FPlatformTime::Seconds();
        const float PreviousTarget = Transition.Target;
        Transition.SetTarget(Ratio, Now, bSnap);
        GhostTransition.SetTarget(Ratio, PreviousTarget, Now, bSnap);
        Invalidate(EInvalidateWidgetReason::Paint);
        if ((Transition.IsAnimating(Now) || GhostTransition.IsAnimating(Now)) && !AnimationTimer.IsValid())
            AnimationTimer = RegisterActiveTimer(0.f,
                FWidgetActiveTimerDelegate::CreateSP(this, &SColdSteelResourceMeter::Animate));
    }

    void SetPendingCost(float InRatio)
    {
        const float Next = FMath::Clamp(InRatio, 0.f, 1.f);
        if (PendingCostRatio != Next)
        {
            PendingCostRatio = Next;
            Invalidate(EInvalidateWidgetReason::Paint);
        }
    }

    void SetShield(float InRatio)
    {
        const float Next = FMath::Clamp(InRatio, 0.f, 1.f);
        if (ShieldRatio != Next)
        {
            ShieldRatio = Next;
            Invalidate(EInvalidateWidgetReason::Paint);
        }
    }

    void SetPoints(float InPoints)
    {
        if (MaxPoints != InPoints)
        {
            MaxPoints = InPoints;
            Invalidate(EInvalidateWidgetReason::Paint);
        }
    }

    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(160, 13); }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&,
        FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool) const override
    {
        const double Now = FPlatformTime::Seconds();
        const float Ratio = Transition.Target;
        const auto Deep = bSemantic ? SemanticDeep : bStamina ? ColdSteelUI::StaminaDeep : bMana ? ColdSteelUI::ManaDeep : ColdSteelUI::HealthDeep;
        const auto Light = bSemantic ? (bWarnOnLowFill && Ratio <= .25f ? ColdSteelUI::Warning : SemanticFill) :
            bStamina ? (Ratio <= .25f ? ColdSteelUI::Warning : ColdSteelUI::Stamina) : bMana ? ColdSteelUI::Mana : ColdSteelUI::Health;

        const float DisplayRatio = Transition.ValueAt(Now);
        const float GhostRatio = GhostTransition.ValueAt(Now);
        const FLinearColor GhostColor = bMana ? (ColdSteelUI::HUDGoldLight * FLinearColor(1.f, 1.f, 1.f, 0.40f)) :
            (!bStamina && !bSemantic ? FLinearColor(0.85f, 0.28f, 0.32f, 0.50f) : FLinearColor::Transparent);

        const float TickSpacing = MaxPoints > 50.f ? (100.f / MaxPoints) : 0.f;

        return ColdSteelUI::PaintResourceMeter(G, Out, Layer, FVector2D::ZeroVector, G.GetLocalSize(),
            DisplayRatio, Light, Deep,
            !bMana && Ratio <= .25f ? ColdSteelUI::Danger : ColdSteelUI::Border,
            Style.GetColorAndOpacityTint(),
            GhostRatio, GhostColor, PendingCostRatio, ShieldRatio, TickSpacing);
    }

private:
    TWeakPtr<FActiveTimerHandle> AnimationTimer;
    EActiveTimerReturnType Animate(double, float)
    {
        Invalidate(EInvalidateWidgetReason::Paint);
        const double Now = FPlatformTime::Seconds();
        if (Transition.IsAnimating(Now) || GhostTransition.IsAnimating(Now)) return EActiveTimerReturnType::Continue;
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
    Meter->bWarnOnLowFill = bWarnOnLowFill;
    Meter->SemanticFill = SemanticFill;
    Meter->SemanticDeep = SemanticDeep;
    Meter->PendingCostRatio = PendingCostRatio;
    Meter->ShieldRatio = ShieldRatio;
    Meter->MaxPoints = MaxPoints;
    if (bHasValue) Meter->SetTarget(Value, true);
    return Meter.ToSharedRef();
}

void UColdSteelResourceMeter::SetPendingCostRatio(float InRatio)
{
    const float Next = FMath::Clamp(InRatio, 0.f, 1.f);
    if (PendingCostRatio == Next) return;
    PendingCostRatio = Next;
    if (Meter) Meter->SetPendingCost(PendingCostRatio);
}

void UColdSteelResourceMeter::SetShieldRatio(float InRatio)
{
    const float Next = FMath::Clamp(InRatio, 0.f, 1.f);
    if (ShieldRatio == Next) return;
    ShieldRatio = Next;
    if (Meter) Meter->SetShield(ShieldRatio);
}

void UColdSteelResourceMeter::SetMaxPoints(float InMaxPoints)
{
    if (MaxPoints == InMaxPoints) return;
    MaxPoints = InMaxPoints;
    if (Meter) Meter->SetPoints(MaxPoints);
}

void UColdSteelResourceMeter::SetSemanticValue(float InRatio, const FLinearColor& Fill, const FLinearColor& Deep, bool bInWarnOnLowFill)
{
    const float Next = FMath::IsFinite(InRatio) ? FMath::Clamp(InRatio, 0.f, 1.f) : 0.f;
    if (bHasValue && bSemantic && Value == Next && SemanticFill == Fill && SemanticDeep == Deep && bWarnOnLowFill == bInWarnOnLowFill) return;
    const bool bSnap = !bHasValue;
    bHasValue = true;
    bSemantic = true;
    bWarnOnLowFill = bInWarnOnLowFill;
    bMana = bStamina = false;
    Value = Next;
    SemanticFill = Fill;
    SemanticDeep = Deep;
    if (Meter)
    {
        Meter->bMana = Meter->bStamina = false;
        Meter->bSemantic = true;
        Meter->bWarnOnLowFill = bWarnOnLowFill;
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
    if (Meter)
    {
        Meter->Transition = FColdSteelMeterTransition{};
        Meter->GhostTransition = FColdSteelGhostTransition{};
    }
}

void UColdSteelResourceMeter::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    Meter.Reset();
}
