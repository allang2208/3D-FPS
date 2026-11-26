#include "ColdSteelTextToolTip.h"
#include "ColdSteelUIStyle.h"
#include "Widgets/SDeferredToolTip.h"
#include "Widgets/SToolTip.h"

namespace
{
    TSharedRef<SToolTip> BuildTextTip(const TAttribute<FText>& Text)
    {
        return SNew(SToolTip).Text(Text).Font(ColdSteelUI::TextFont(14.f * .75f));
    }
}

TAttribute<TSharedPtr<IToolTip>> ColdSteelToolTip::Make(const TAttribute<FText>& Text)
{
    if (!Text.IsSet() || (!Text.IsBound() && Text.Get().IsEmptyOrWhitespace())) return {};
    TSharedPtr<IToolTip> Tip = MakeShared<SDeferredToolTip>(
        FOnGetDeferredToolTip::CreateLambda([Text]() -> TSharedPtr<IToolTip> { return BuildTextTip(Text); }));
    return Tip;
}

void ColdSteelToolTip::Set(SWidget& Target, const TAttribute<FText>& Text)
{
    Target.SetToolTip(Make(Text));
}

void ColdSteelToolTip::Set(UWidget& Target, const FText& Text)
{
    auto* Tip = Cast<UColdSteelTextToolTip>(Target.GetToolTip());
    if (Text.IsEmptyOrWhitespace())
    {
        if (Target.GetToolTip() || !Target.GetToolTipText().IsEmpty())
        {
            Target.SetToolTipText(FText::GetEmpty());
            Target.SetToolTip(nullptr);
        }
        return;
    }
    if (Tip && Target.GetToolTipText().EqualTo(Text)) return;
    // SetToolTipText also updates the reflected text and notifies its observers.
    // Set the custom presenter afterwards, since that setter installs a stock Slate tip.
    Target.SetToolTipText(Text);
    Target.SetToolTip(Tip ? Tip : NewObject<UColdSteelTextToolTip>(&Target));
}

TSharedRef<SWidget> UColdSteelTextToolTip::RebuildWidget()
{
    auto* Target = CastChecked<UWidget>(GetOuter());
    return BuildTextTip(TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateUObject(Target, &UWidget::GetToolTipText)));
}
