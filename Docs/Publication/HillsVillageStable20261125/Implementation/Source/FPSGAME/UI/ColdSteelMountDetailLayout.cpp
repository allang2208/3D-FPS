#include "ColdSteelMountGearPanel.h"
#include "ColdSteelUIStyle.h"
#include "../Movement/StableHorseGear.h"
#include "Widgets/Input/SComboButton.h"
#include "Brushes/SlateNoResource.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SUniformWrapPanel.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
using namespace ColdSteelUI;
TSharedRef<STextBlock> Text(const TCHAR* Value,float Size,FLinearColor Color,bool Bold=false)
{
    return SNew(STextBlock).Text(FText::FromString(Value)).Font(TextFont(Size,Bold)).ColorAndOpacity(Color);
}
TSharedRef<SWidget> Section(const TCHAR* Title,TSharedRef<SWidget> SectionBody,TSharedPtr<STextBlock>* Counter=nullptr)
{
    static const FSlateBrush Frame=RoundedBrush(Gray(120,9),10,Gray(220,22),1);
    static const FSlateBrush AccentRule=RoundedBrush(Accent,0,FLinearColor::Transparent,0);
    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(2).HeightOverride(16)[SNew(SImage).Image(&AccentRule)]]
        +SHorizontalBox::Slot().FillWidth(1).Padding(9,0,0,0)[Text(Title,13,TextPrimary,true)];
    if(Counter) Header->AddSlot().AutoWidth().VAlign(VAlign_Center)
        [SAssignNew(*Counter,STextBlock).Font(NumberFont(11,true)).ColorAndOpacity(TextSecondary)];
    return SNew(SBorder).BorderImage(&Frame).Padding(12)
        [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Header]
        +SVerticalBox::Slot().AutoHeight().Padding(0,9,0,0)[SectionBody]];
}
TSharedRef<SWidget> Meter(TSharedPtr<SProgressBar>& Bar,const FLinearColor& Ink,float Height)
{
    static const FProgressBarStyle Style=[]
    {
        FProgressBarStyle S;
        S.SetBackgroundImage(RoundedBrush(Gray(59),2,FLinearColor::Transparent,0));
        S.SetFillImage(RoundedBrush(FLinearColor::White,2,FLinearColor::Transparent,0));
        return S;
    }();
    return SNew(SBox).HeightOverride(Height)[SAssignNew(Bar,SProgressBar).Style(&Style).Percent(0.f)
        .BarFillStyle(EProgressBarFillStyle::Scale).BorderPadding(FVector2D::ZeroVector).FillColorAndOpacity(Ink)];
}
TSharedRef<SWidget> Vital(const TCHAR* Title,FLinearColor Ink,TSharedPtr<STextBlock>& Value,TSharedPtr<SProgressBar>& Bar)
{
    return SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()
        [SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1)[Text(Title,11,TextSecondary)]
        +SHorizontalBox::Slot().AutoWidth()[SAssignNew(Value,STextBlock).Font(NumberFont(12,true)).ColorAndOpacity(TextPrimary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[Meter(Bar,Ink,5)];
}
}

TSharedRef<SWidget> UColdSteelMountGearPanel::RebuildWidget()
{
    using namespace ColdSteelUI;
    static const FSlateBrush IdentityFrame=RoundedBrush(Content,8,Border,1);
    static const FSlateBrush TraitFrame=RoundedBrush(Gray(18,130),InventoryItemRadius,Gray(220,28),1);
    static const FSlateBrush Line=RoundedBrush(Border,0,FLinearColor::Transparent,0);
    const auto Summary=SNew(SBorder).BorderImage(&IdentityFrame).Padding(12)
    [
        SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(.40f).VAlign(VAlign_Fill)
            [SNew(SBox).HeightOverride(100).Clipping(EWidgetClipping::ClipToBounds)
                [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SAssignNew(Portrait,SImage).Image(&PortraitBrush)]]]
            +SHorizontalBox::Slot().FillWidth(.60f).Padding(12,0,0,0).VAlign(VAlign_Center)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth()[SAssignNew(LevelText,STextBlock).Font(TextFont(11,true)).ColorAndOpacity(HUDGoldLight)]
                    +SHorizontalBox::Slot().FillWidth(1).Padding(8,0,0,0)[SAssignNew(StateText,STextBlock).Font(TextFont(10)).ColorAndOpacity(TextSecondary).AutoWrapText(true)]]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,3)[SAssignNew(NameText,STextBlock).Font(TextFont(22,true)).ColorAndOpacity(TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().AutoHeight()[SAssignNew(CoatText,STextBlock).AutoWrapText(true).Font(TextFont(11)).ColorAndOpacity(TextSecondary)]
                +SVerticalBox::Slot().AutoHeight()[SAssignNew(HairText,STextBlock).Font(TextFont(10)).ColorAndOpacity(TextTertiary)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,6)
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Text(TEXT("经验"),10,TextSecondary)]
            +SHorizontalBox::Slot().AutoWidth()[SAssignNew(ExperienceText,STextBlock).Font(NumberFont(11)).ColorAndOpacity(HUDGoldLight)]]
        +SVerticalBox::Slot().AutoHeight()[Meter(ExperienceBar,HUDGoldDim,3)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,1)
        [SNew(SUniformWrapPanel).HAlign(HAlign_Fill).MinDesiredSlotWidth(143).MaxDesiredSlotWidth(143).SlotPadding(FMargin(3,2))
            +SUniformWrapPanel::Slot()[Vital(TEXT("生命"),FLinearColor::FromSRGBColor(FColor(169,77,78)),HealthText,HealthBar)]
            +SUniformWrapPanel::Slot()[Vital(TEXT("体力"),FLinearColor::FromSRGBColor(FColor(84,148,207)),StaminaText,StaminaBar)]]
    ];

    const auto Gear=SNew(SUniformWrapPanel).HAlign(HAlign_Fill).EvenRowDistribution(true).MinDesiredSlotWidth(170).MaxDesiredSlotWidth(170).SlotPadding(FMargin(3));
    Buttons.SetNum(StableHorseGear::Count);Captions.SetNum(StableHorseGear::Count);GearImages.SetNum(StableHorseGear::Count);
    Brushes.SetNum(StableHorseGear::Count);CellBrushes.SetNum(StableHorseGear::Count);EmptyMarks.SetNum(StableHorseGear::Count);
    static const FButtonStyle Bare=FButtonStyle().SetNormal(FSlateNoResource()).SetHovered(FSlateNoResource())
        .SetPressed(FSlateNoResource()).SetDisabled(FSlateNoResource()).SetNormalPadding(0).SetPressedPadding(0);
    static const FSlateBrush Hover=RoundedBrush(Gray(65,120),InventoryItemRadius,Gray(230,95),1);
    static const FSlateBrush Accept=RoundedBrush(Gray(65,145),InventoryItemRadius,HUDGoldLight,2);
    static const FSlateBrush Reject=RoundedBrush(Gray(34,145),InventoryItemRadius,Warning,2);
    for(int32 I=0;I<StableHorseGear::Count;++I)
    {
        Gear->AddSlot()[SAssignNew(Buttons[I],SComboButton).ButtonStyle(&Bare).HasDownArrow(false)
            .ContentPadding(0).HAlign(HAlign_Fill).OnGetMenuContent_UObject(this,&ThisClass::Choices,I)
            .ButtonContent()
            [SNew(SBorder).BorderImage_Lambda([this,I]() -> const FSlateBrush*
                {
                    if(DropIndex==I)return bDropAllowed?&Accept:&Reject;
                    if(Editable && Buttons[I] && (Buttons[I]->IsHovered() || Buttons[I]->HasKeyboardFocus() || Buttons[I]->HasFocusedDescendants() || Buttons[I]->IsOpen()))return &Hover;
                    return &CellBrushes[I];
                }).Padding(FMargin(11,4))
                [SNew(SBox).HeightOverride(58)
                    [SNew(SHorizontalBox)
                        +SHorizontalBox::Slot().FillWidth(.52f).VAlign(VAlign_Center)
                        [SNew(SVerticalBox)
                            +SVerticalBox::Slot().AutoHeight()[Text(StableHorseGear::Labels[I],12,TextSecondary)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[SAssignNew(Captions[I],STextBlock).Font(TextFont(11)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]
                        +SHorizontalBox::Slot().FillWidth(.48f).VAlign(VAlign_Fill)
                        [SNew(SOverlay)
                            +SOverlay::Slot().Padding(3)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SAssignNew(GearImages[I],SImage)]]
                            +SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Center)
                            [SAssignNew(EmptyMarks[I],STextBlock).Font(NumberFont(16,true)).ColorAndOpacity(TextTertiary)]]]]]];
    }

    const TCHAR* Stats[]={TEXT("力量"),TEXT("敏捷"),TEXT("智力"),TEXT("体质"),TEXT("精神"),TEXT("幸运")};
    const auto Traits=SNew(SUniformWrapPanel).HAlign(HAlign_Fill).EvenRowDistribution(true).MinDesiredSlotWidth(108).MaxDesiredSlotWidth(108).SlotPadding(FMargin(3));
    Values.SetNum(6);GrowthValues.SetNum(6);
    for(int32 I=0;I<6;++I)
        Traits->AddSlot()[SNew(SBorder).BorderImage(&TraitFrame).Padding(FMargin(10,6))
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Text(Stats[I],11,TextSecondary)]
                    +SHorizontalBox::Slot().AutoWidth()[SAssignNew(Values[I],STextBlock).Font(NumberFont(15,true)).ColorAndOpacity(TextPrimary)]]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth()[SAssignNew(GrowthValues[I],STextBlock).Font(NumberFont(10)).ColorAndOpacity(HUDGoldLight)]
                    +SHorizontalBox::Slot().AutoWidth().Padding(3,0,0,0)[Text(TEXT("/ 级"),10,TextTertiary)]]]];

    const TCHAR* Labels[]={TEXT("疾驰速度"),TEXT("跳跃高度"),TEXT("转向速度"),TEXT("体力恢复"),TEXT("静养回血")};
    const TCHAR* Units[]={TEXT("米/秒"),TEXT("米"),TEXT("°/秒"),TEXT("%"),TEXT("/ 秒")};
    const auto PerformanceGrid=SNew(SUniformWrapPanel).HAlign(HAlign_Fill).EvenRowDistribution(true).MinDesiredSlotWidth(155).MaxDesiredSlotWidth(155).SlotPadding(FMargin(5,3));
    Performance.SetNum(UE_ARRAY_COUNT(Labels));
    for(int32 I=0;I<Performance.Num();++I)
        PerformanceGrid->AddSlot()[SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Text(Labels[I],11,TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SAssignNew(Performance[I],STextBlock).Font(NumberFont(12,true)).ColorAndOpacity(TextPrimary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(3,0,0,0)[Text(Units[I],10,TextSecondary)]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Line)]]];
    return SNew(SDPIScaler).DPIScale_Lambda([Weak=TWeakObjectPtr<UColdSteelMountGearPanel>(this)]{
        return Weak.IsValid()?1.f/FMath::Max(.1f,ColdSteelUI::PixelScale(Weak.Get())):1.f;})
    [SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[Summary]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Section(TEXT("马匹装备"),Gear,&CountText)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Section(TEXT("六维属性"),Traits)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Section(TEXT("骑乘能力"),PerformanceGrid)]];
}
