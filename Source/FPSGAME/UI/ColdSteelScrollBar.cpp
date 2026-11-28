#include "ColdSteelScrollBar.h"
#include "ColdSteelUIStyle.h"
#include "Brushes/SlateNoResource.h"
#include "Containers/Ticker.h"
#include "HAL/PlatformTime.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Styling/SlateTypes.h"
#include "Widgets/Layout/SScrollBar.h"
#include "Widgets/SWidget.h"

namespace
{
struct FGoldScrollAnimator
{
    FScrollBarStyle BarStyle;
    FScrollBoxStyle BoxStyle;
    TArray<TWeakPtr<SScrollBox>> Registered;
    FTSTicker::FDelegateHandle TickerHandle;
    bool bInitialized = false;
    double StartTime = 0.0;

    static FGoldScrollAnimator& Get()
    {
        static FGoldScrollAnimator Instance;
        return Instance;
    }

    void EnsureInit()
    {
        if (bInitialized) return;
        bInitialized = true;
        StartTime = FPlatformTime::Seconds();

        using namespace ColdSteelUI;
        const FSlateBrush TrackBg = RoundedBrush(
            Gray(14, 165), 3.f, FLinearColor(HUDGold.R, HUDGold.G, HUDGold.B, 0.28f), 0.75f);
        const FSlateBrush GoldThumb = RoundedBrush(
            HUDGoldLight, 3.f, HUDGoldLight, 1.25f);
        const FSlateBrush GoldHover = RoundedBrush(
            FLinearColor::FromSRGBColor(FColor(255, 236, 170, 255)), 3.f,
            FLinearColor::FromSRGBColor(FColor(255, 248, 218, 255)), 1.35f);
        const FSlateBrush GoldDrag = RoundedBrush(
            FLinearColor::FromSRGBColor(FColor(255, 244, 198, 255)), 3.f,
            FLinearColor::White, 1.5f);

        BarStyle = FScrollBarStyle()
            .SetVerticalBackgroundImage(TrackBg)
            .SetHorizontalBackgroundImage(TrackBg)
            .SetVerticalTopSlotImage(FSlateNoResource())
            .SetVerticalBottomSlotImage(FSlateNoResource())
            .SetHorizontalTopSlotImage(FSlateNoResource())
            .SetHorizontalBottomSlotImage(FSlateNoResource())
            .SetNormalThumbImage(GoldThumb)
            .SetHoveredThumbImage(GoldHover)
            .SetDraggedThumbImage(GoldDrag);
        BarStyle.Thickness = 5.5f;

        BoxStyle = FScrollBoxStyle()
            .SetTopShadowBrush(FSlateNoResource())
            .SetBottomShadowBrush(FSlateNoResource())
            .SetLeftShadowBrush(FSlateNoResource())
            .SetRightShadowBrush(FSlateNoResource());

        // Start at peak radiance (cos(0) == 1) so first-frame / headless captures gleam immediately.
        ApplyPulseColors(1.f);
    }

    void ApplyPulseColors(float Pulse)
    {
        using namespace ColdSteelUI;
        static const FLinearColor ThumbLow = FLinearColor::FromSRGBColor(FColor(178, 138, 66, 205));
        static const FLinearColor ThumbHigh = FLinearColor::FromSRGBColor(FColor(255, 234, 158, 255));
        static const FLinearColor RimLow(HUDGold.R, HUDGold.G, HUDGold.B, 0.45f);
        static const FLinearColor RimHigh = FLinearColor::FromSRGBColor(FColor(255, 246, 204, 255));

        const FLinearColor ThumbColor = FMath::Lerp(ThumbLow, ThumbHigh, Pulse);
        const FLinearColor RimColor = FMath::Lerp(RimLow, RimHigh, Pulse);
        const FLinearColor TrackRim(HUDGold.R, HUDGold.G, HUDGold.B, FMath::Lerp(0.18f, 0.55f, Pulse));

        BarStyle.NormalThumbImage.TintColor = ThumbColor;
        BarStyle.NormalThumbImage.OutlineSettings.Color = RimColor;
        BarStyle.VerticalBackgroundImage.OutlineSettings.Color = TrackRim;
        BarStyle.HorizontalBackgroundImage.OutlineSettings.Color = TrackRim;
    }

    static void InvalidateScrollBarPaint(SWidget& Node, int32 Depth = 0)
    {
        if (Depth > 4) return;
        const FName Type = Node.GetType();
        if (Type == TEXT("SScrollPanel")) return;
        if (Type == TEXT("SScrollBar") || Depth > 0)
        {
            Node.Invalidate(EInvalidateWidgetReason::Paint);
        }
        FChildren* Children = Node.GetChildren();
        for (int32 I = 0; Children && I < Children->Num(); ++I)
        {
            InvalidateScrollBarPaint(Children->GetChildAt(I).Get(), Depth + 1);
        }
    }

    void EnsureTicker()
    {
        if (TickerHandle.IsValid() || IsEngineExitRequested() || !FApp::CanEverRender()) return;
        TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateRaw(this, &FGoldScrollAnimator::OnTick), 0.033f);
    }

    static bool IsEffectivelyVisible(const TSharedPtr<SScrollBox>& Box)
    {
        if (!Box.IsValid()) return false;
        if (Box->GetTickSpaceGeometry().GetLocalSize().GetMin() <= 1.f) return false;
        for (const SWidget* Cur = Box.Get(); Cur; Cur = Cur->GetParentWidget().Get())
        {
            if (!Cur->GetVisibility().IsVisible()) return false;
        }
        return true;
    }

    bool OnTick(float)
    {
        if (IsEngineExitRequested() || !FApp::CanEverRender())
        {
            TickerHandle.Reset();
            Registered.Reset();
            return false;
        }
        EnsureInit();

        TArray<TSharedPtr<SScrollBox>, TInlineAllocator<16>> ActiveBoxes;
        for (int32 I = Registered.Num() - 1; I >= 0; --I)
        {
            const TSharedPtr<SScrollBox> Box = Registered[I].Pin();
            if (!Box.IsValid())
            {
                Registered.RemoveAtSwap(I);
                continue;
            }
            if (IsEffectivelyVisible(Box) && Box->GetScrollOffsetOfEnd() > 0.5f)
            {
                ActiveBoxes.Add(Box);
            }
        }

        if (!ActiveBoxes.IsEmpty())
        {
            const double Elapsed = FPlatformTime::Seconds() - StartTime;
            const float Pulse = 0.5f + 0.5f * FMath::Cos(float(Elapsed) * (2.f * UE_PI / 1.55f));
            ApplyPulseColors(Pulse);
            for (const TSharedPtr<SScrollBox>& Box : ActiveBoxes)
            {
                InvalidateScrollBarPaint(*Box, 0);
            }
        }

        if (Registered.IsEmpty())
        {
            TickerHandle.Reset();
            return false;
        }
        return true;
    }

    void Register(const TSharedPtr<SScrollBox>& ScrollBox)
    {
        if (!ScrollBox.IsValid() || !FApp::CanEverRender()) return;
        EnsureInit();
        for (int32 I = Registered.Num() - 1; I >= 0; --I)
        {
            const TSharedPtr<SScrollBox> Existing = Registered[I].Pin();
            if (!Existing.IsValid())
            {
                Registered.RemoveAtSwap(I);
            }
            else if (Existing == ScrollBox)
            {
                EnsureTicker();
                return;
            }
        }
        Registered.Add(ScrollBox);
        EnsureTicker();
    }
};
} // namespace

const FScrollBarStyle& ColdSteelUI::GoldScrollBarStyle()
{
    auto& Anim = FGoldScrollAnimator::Get();
    Anim.EnsureInit();
    return Anim.BarStyle;
}

const FScrollBoxStyle& ColdSteelUI::GoldScrollBoxStyle()
{
    auto& Anim = FGoldScrollAnimator::Get();
    Anim.EnsureInit();
    return Anim.BoxStyle;
}

void ColdSteelUI::RegisterGoldScrollBox(const TSharedPtr<SScrollBox>& ScrollBox)
{
    FGoldScrollAnimator::Get().Register(ScrollBox);
}

TSharedRef<SScrollBox> ColdSteelUI::ApplyGoldScroll(
    const TSharedRef<SScrollBox>& ScrollBox,
    FVector2D Thickness,
    FMargin Padding,
    bool bEnsureVisible)
{
    ScrollBox->SetScrollBarStyle(&GoldScrollBarStyle());
    ScrollBox->SetScrollBarThickness(Thickness);
    ScrollBox->SetScrollBarPadding(Padding);
    if (bEnsureVisible)
    {
        ScrollBox->SetScrollBarVisibility(EVisibility::Visible);
    }
    RegisterGoldScrollBox(ScrollBox);
    return ScrollBox;
}

void ColdSteelUI::ConfigureGoldScrollBox(
    UScrollBox* ScrollBox,
    float Thickness,
    FMargin Padding,
    bool bEnsureVisible)
{
    if (!ScrollBox) return;
    ScrollBox->SetWidgetBarStyle(GoldScrollBarStyle());
    ScrollBox->SetScrollbarThickness(FVector2D(Thickness, Thickness));
    ScrollBox->SetScrollbarPadding(Padding);
    if (bEnsureVisible)
    {
        ScrollBox->SetScrollBarVisibility(ESlateVisibility::Visible);
    }
    if (const TSharedPtr<SWidget> Cached = ScrollBox->GetCachedWidget())
    {
        if (Cached->GetType() == TEXT("SScrollBox"))
        {
            const TSharedPtr<SScrollBox> SlateBox = StaticCastSharedPtr<SScrollBox>(Cached);
            SlateBox->SetScrollBarStyle(&GoldScrollBarStyle());
            RegisterGoldScrollBox(SlateBox);
        }
    }
}

UColdSteelScrollBox::UColdSteelScrollBox(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    SetWidgetBarStyle(ColdSteelUI::GoldScrollBarStyle());
    SetScrollbarThickness(FVector2D(5.5f, 5.5f));
    SetScrollbarPadding(FMargin(4.f, 0.f, 0.f, 0.f));
}

TSharedRef<SWidget> UColdSteelScrollBox::RebuildWidget()
{
    TSharedRef<SWidget> Widget = Super::RebuildWidget();
    if (MyScrollBox.IsValid())
    {
        MyScrollBox->SetScrollBarStyle(&ColdSteelUI::GoldScrollBarStyle());
        ColdSteelUI::RegisterGoldScrollBox(MyScrollBox);
    }
    return Widget;
}

void UColdSteelScrollBox::SynchronizeProperties()
{
    Super::SynchronizeProperties();
    if (MyScrollBox.IsValid())
    {
        MyScrollBox->SetScrollBarStyle(&ColdSteelUI::GoldScrollBarStyle());
        ColdSteelUI::RegisterGoldScrollBox(MyScrollBox);
    }
}
