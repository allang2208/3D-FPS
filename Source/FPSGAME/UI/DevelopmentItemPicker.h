#pragma once

#include "Components/Widget.h"
#include "ColdSteelInventoryTypes.h"
#include "Input/Reply.h"
#include "Styling/SlateTypes.h"
#include "DevelopmentItemPicker.generated.h"

class SComboButton;
class STextBlock;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDevelopmentItemSelected, const FString&, Definition);

/** F6 专用目录下拉：标题只展示，只有物品行能选择真实 Definition。 */
UCLASS()
class FPSGAME_API UDevelopmentItemPicker : public UWidget
{
    GENERATED_BODY()
public:
    void SetOptions(const TArray<FColdSteelCatalogEntry>& Entries, const FString& Selected);
    void SetPixelScale(float Scale);
    void CloseMenu();
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;

    UPROPERTY() FDevelopmentItemSelected OnSelectionChanged;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    TSharedRef<SWidget> BuildMenu();
    FReply ChooseItem(FString Definition);
    void RefreshCaption();

    TArray<FColdSteelCatalogEntry> Options;
    FString SelectedDefinition;
    float PixelScale = 1.f;
    FComboButtonStyle ComboStyle;
    FButtonStyle RowStyle;
    FButtonStyle SelectedRowStyle;
    TSharedPtr<SComboButton> Choice;
    TSharedPtr<STextBlock> Caption;
};
