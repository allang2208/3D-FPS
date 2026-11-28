#pragma once

#include "CoreMinimal.h"
#include "Components/ScrollBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "ColdSteelScrollBar.generated.h"

namespace ColdSteelUI
{
    FPSGAME_API const FScrollBarStyle& GoldScrollBarStyle();
    FPSGAME_API const FScrollBoxStyle& GoldScrollBoxStyle();
    FPSGAME_API void RegisterGoldScrollBox(const TSharedPtr<SScrollBox>& ScrollBox);

    FPSGAME_API TSharedRef<SScrollBox> ApplyGoldScroll(
        const TSharedRef<SScrollBox>& ScrollBox,
        FVector2D Thickness = FVector2D(5.5f, 5.5f),
        FMargin Padding = FMargin(4.f, 0.f, 0.f, 0.f),
        bool bEnsureVisible = false);

    FPSGAME_API void ConfigureGoldScrollBox(
        UScrollBox* ScrollBox,
        float Thickness = 5.5f,
        FMargin Padding = FMargin(4.f, 0.f, 0.f, 0.f),
        bool bEnsureVisible = false);
}

/**
 * Cold Steel scrollable container with synchronized gold pulsing scrollbar hint.
 */
UCLASS(MinimalAPI)
class UColdSteelScrollBox : public UScrollBox
{
    GENERATED_BODY()

public:
    UColdSteelScrollBox(const FObjectInitializer& ObjectInitializer);

    virtual void SynchronizeProperties() override;

protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
};
