#pragma once

#include "Components/Widget.h"
#include "ColdSteelTextToolTip.generated.h"

class IToolTip;

namespace ColdSteelToolTip
{
    TAttribute<TSharedPtr<IToolTip>> Make(const TAttribute<FText>& Text);
    void Set(SWidget& Target, const TAttribute<FText>& Text);
    void Set(UWidget& Target, const FText& Text);
}

/** UMG keeps this widget across Slate rebuilds. Its outer holds the tooltip text. */
UCLASS(Transient, NotBlueprintable)
class UColdSteelTextToolTip : public UWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
};
