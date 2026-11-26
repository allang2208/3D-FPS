#pragma once

#include "Components/Widget.h"
#include "ColdSteelInventoryTypes.h"
#include "Input/Reply.h"
#include "Styling/SlateTypes.h"
#include "DevelopmentItemPicker.generated.h"

class SComboButton;
class STextBlock;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDevelopmentItemSelected, const FString&, Definition);

/** F6 与打铁共用的分组下拉：标题只展示，只有子项能选择真实条目 ID。 */
UCLASS()
class FPSGAME_API UDevelopmentItemPicker : public UWidget
{
    GENERATED_BODY()
public:
    void SetOptions(const TArray<FColdSteelCatalogEntry>& Entries, const FString& Selected, bool bCenterCaption = false);
    void SetSelectedOption(const FString& Selected);
    void SetPixelScale(float Scale);
    /** Workbenches use the same physical 14/16 px type sizes as their other controls. */
    void SetPhysicalFontSizes(bool bEnabled){bPhysicalFontSizes=bEnabled;SetPixelScale(PixelScale);}
    void CloseMenu();
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;

    UPROPERTY() FDevelopmentItemSelected OnSelectionChanged;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    TSharedRef<SWidget> BuildMenu();
    FReply ChooseItem(FString Definition);
    void RefreshCaption();
    FSlateFontInfo OptionFont(float Size,bool bMedium=false) const;

    TArray<FColdSteelCatalogEntry> Options;
    FString SelectedDefinition;
    bool bCenteredCaption = false;
    bool bPhysicalFontSizes = false;
    float PixelScale = 1.f;
    FComboButtonStyle ComboStyle;
    FButtonStyle RowStyle;
    FButtonStyle SelectedRowStyle;
    TSharedPtr<SComboButton> Choice;
    TSharedPtr<STextBlock> Caption;
};
