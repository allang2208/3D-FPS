#include "ColdSteelMountGearPanel.h"
#include "ColdSteelUIStyle.h"
#include "SHorseMarketPlate.h"
#include "../Movement/StableHorseGear.h"
#include "Widgets/Input/SComboButton.h"
#include "Brushes/SlateNoResource.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SUniformWrapPanel.h"
#include "Widgets/Layout/SWrapBox.h"
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

TSharedRef<SWidget> Section(const TCHAR* Title,TSharedRef<SWidget> SectionBody,TSharedPtr<STextBlock>* Counter=nullptr,const TCHAR* RightHint=nullptr)
{
    static const FSlateBrush Frame=RoundedBrush(Gray(120,9),10,Gray(220,22),1);
    static const FSlateBrush AccentRule=RoundedBrush(HUDGold,1,FLinearColor::Transparent,0);
    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(2.5f).HeightOverride(14)[SNew(SImage).Image(&AccentRule)]]
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,0,0,0)[Text(Title,13,TextPrimary,true)];
    if(RightHint && *RightHint)
        Header->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(6,0,Counter?8:0,0)
            [SNew(STextBlock).Text(FText::FromString(RightHint)).Font(TextFont(9.5f)).ColorAndOpacity(TextTertiary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)];
    if(Counter)
        Header->AddSlot().AutoWidth().VAlign(VAlign_Center)
            [SAssignNew(*Counter,STextBlock).Font(NumberFont(11,true)).ColorAndOpacity(HUDGoldLight)];
    return SNew(SBorder).BorderImage(&Frame).Padding(FMargin(12,10,12,12))
        [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Header]
        +SVerticalBox::Slot().AutoHeight().Padding(0,9,0,0)[SectionBody]];
}

TSharedRef<SWidget> Meter(TSharedPtr<SProgressBar>& Bar,const FLinearColor& Ink,float Height)
{
    static const FProgressBarStyle Style=[]
    {
        FProgressBarStyle S;
        S.SetBackgroundImage(RoundedBrush(Gray(255,20),2,FLinearColor::Transparent,0));
        S.SetFillImage(RoundedBrush(FLinearColor::White,2,FLinearColor::Transparent,0));
        return S;
    }();
    return SNew(SBox).HeightOverride(Height)[SAssignNew(Bar,SProgressBar).Style(&Style).Percent(0.f)
        .BarFillStyle(EProgressBarFillStyle::Scale).BorderPadding(FVector2D::ZeroVector).FillColorAndOpacity(Ink)];
}

TSharedRef<SWidget> Vital(const TCHAR* Title,FLinearColor Ink,TSharedPtr<STextBlock>& Value,TSharedPtr<SProgressBar>& Bar)
{
    static const FSlateBrush VitalCard=RoundedBrush(Gray(14,224),6,Gray(222,26),1);
    return SNew(SBorder).BorderImage(&VitalCard).Padding(FMargin(11,8,11,9))
        [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Text(Title,11,TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SAssignNew(Value,STextBlock).Font(NumberFont(12.5f,true)).ColorAndOpacity(TextPrimary)]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[Meter(Bar,Ink,6.5f)]];
}
}

TSharedRef<SWidget> UColdSteelMountGearPanel::RebuildWidget()
{
    using namespace ColdSteelUI;
    static const FSlateBrush HeroFrame=RoundedBrush(Gray(12,240),7,FLinearColor(HUDGold.R,HUDGold.G,HUDGold.B,.36f),1);
    static const FSlateBrush PillDark=RoundedBrush(Gray(15,212),4,Gray(222,56),1);
    static const FSlateBrush TraitNormal=RoundedBrush(Gray(255,9),5,Gray(222,24),1);
    static const FSlateBrush TeleCard=RoundedBrush(Gray(14,205),5,Gray(222,20),1);

    // Full-width framed Hero Portrait Banner + flush XP rail + Vitals pair
    const auto HeroBanner=SNew(SBorder).BorderImage(&HeroFrame).Padding(1)
    [
        SNew(SOverlay)
        +SOverlay::Slot()
        [SAssignNew(HeroPlate,SHorseMarketPlate).Sharp(&PortraitBrush).PreferredHeight(184.f).CornerRadius(6.f).ShowScrim(true).CornerBrackets(true)]
        // Top overlay pills
        +SOverlay::Slot().VAlign(VAlign_Top).Padding(11,10)
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SAssignNew(StateBadge,SBorder).BorderImage(&PillDark).Padding(FMargin(8,3))
                [SAssignNew(StateText,STextBlock).Font(TextFont(10.5f,true)).ColorAndOpacity(HUDGoldLight).AutoWrapText(false)]
            ]
            +SHorizontalBox::Slot().FillWidth(1)[SNew(SSpacer)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SNew(SBorder).BorderImage(&PillDark).Padding(FMargin(8,3))
                [SAssignNew(TotalRatingText,STextBlock).Font(NumberFont(10.5f,true)).ColorAndOpacity(TextPrimary)]
            ]
        ]
        // Bottom overlay identity & level
        +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(14,0,14,12)
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Bottom)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [SAssignNew(NameText,STextBlock).Font(TextFont(21,true)).ColorAndOpacity(FLinearColor(.96f,.96f,.97f,1.f))
                    .ShadowOffset(FVector2D(0,1.5f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.88f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,2,0,0)
                [SAssignNew(CoatText,STextBlock).Font(TextFont(11)).ColorAndOpacity(FLinearColor(.78f,.78f,.81f,1.f))
                    .ShadowOffset(FVector2D(0,1.f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.90f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().AutoHeight()
                [SAssignNew(HairText,STextBlock).Font(TextFont(10)).ColorAndOpacity(FLinearColor(.64f,.64f,.68f,1.f))
                    .ShadowOffset(FVector2D(0,1.f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.90f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
            ]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom).Padding(10,0,0,0)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
                [SAssignNew(LevelText,STextBlock).Font(NumberFont(19,true)).ColorAndOpacity(HUDGoldLight)
                    .ShadowOffset(FVector2D(0,1.5f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.88f))]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right).Padding(0,2,0,0)
                [SAssignNew(ExperienceText,STextBlock).Font(NumberFont(10.5f)).ColorAndOpacity(TextSecondary)
                    .ShadowOffset(FVector2D(0,1.f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.90f))]
            ]
        ]
        // Flush XP progress rail hugging bottom edge of banner
        +SOverlay::Slot().VAlign(VAlign_Bottom)
        [Meter(ExperienceBar,HUDGold,3.5f)]
    ];

    const auto VitalsRow=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,5,0)[Vital(TEXT("生命"),Health,HealthText,HealthBar)]
        +SHorizontalBox::Slot().FillWidth(1).Padding(5,0,0,0)[Vital(TEXT("耐力"),MountStamina,StaminaText,StaminaBar)];

    // 4-Slot Horse Tack Assembly (mirrors right-side real backpack 随身装备 grammar!)
    const auto Gear=SNew(SUniformWrapPanel).HAlign(HAlign_Fill).EvenRowDistribution(true)
        .MinDesiredSlotWidth(178).MaxDesiredSlotWidth(460).SlotPadding(FMargin(4));
    Buttons.SetNum(StableHorseGear::Count);
    Captions.SetNum(StableHorseGear::Count);
    GearSubLabels.SetNum(StableHorseGear::Count);
    GearImages.SetNum(StableHorseGear::Count);
    GearAccentBars.SetNum(StableHorseGear::Count);
    GearArtFrames.SetNum(StableHorseGear::Count);
    Brushes.SetNum(StableHorseGear::Count);
    CellBrushes.SetNum(StableHorseGear::Count);
    GearAccentBrushes.SetNum(StableHorseGear::Count);
    GearArtFrameBrushes.SetNum(StableHorseGear::Count);
    EmptyMarks.SetNum(StableHorseGear::Count);

    static const FButtonStyle Bare=FButtonStyle().SetNormal(FSlateNoResource()).SetHovered(FSlateNoResource())
        .SetPressed(FSlateNoResource()).SetDisabled(FSlateNoResource()).SetNormalPadding(0).SetPressedPadding(0);
    static const FSlateBrush Hover=RoundedBrush(FLinearColor::FromSRGBColor(FColor(38,35,28,236)),6,HUDGold,1.2f);
    static const FSlateBrush Accept=RoundedBrush(FLinearColor::FromSRGBColor(FColor(46,40,26,245)),6,HUDGoldLight,2.f);
    static const FSlateBrush Reject=RoundedBrush(FLinearColor::FromSRGBColor(FColor(52,24,28,245)),6,Warning,2.f);

    for(int32 I=0;I<StableHorseGear::Count;++I)
    {
        GearAccentBrushes[I]=RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0);
        GearArtFrameBrushes[I]=RoundedBrush(Gray(10,235),5,Gray(222,32),1);
        Gear->AddSlot()[SAssignNew(Buttons[I],SComboButton).ButtonStyle(&Bare).HasDownArrow(false)
            .ContentPadding(0).HAlign(HAlign_Fill).OnGetMenuContent_UObject(this,&ThisClass::Choices,I)
            .ButtonContent()
            [
                SNew(SBorder).BorderImage_Lambda([this,I]() -> const FSlateBrush*
                {
                    if(DropIndex==I)return bDropAllowed?&Accept:&Reject;
                    if(Editable && Buttons[I] && (Buttons[I]->IsHovered() || Buttons[I]->HasKeyboardFocus() || Buttons[I]->HasFocusedDescendants() || Buttons[I]->IsOpen()))return &Hover;
                    return &CellBrushes[I];
                }).Padding(FMargin(0,0,10,0))
                [
                    SNew(SBox).HeightOverride(76)
                    [
                        SNew(SHorizontalBox)
                        // Inset vertical rarity indicator so all four outer rounded corners stay completely intact
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Fill).Padding(5.f,11.f,0.f,11.f)
                        [SNew(SBox).WidthOverride(2.5f)[SAssignNew(GearAccentBars[I],SBorder).BorderImage(&GearAccentBrushes[I])]]
                        // Middle text stack
                        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,4,8,4)
                        [
                            SNew(SVerticalBox)
                            +SVerticalBox::Slot().AutoHeight()[Text(StableHorseGear::Labels[I],10.f,TextTertiary)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,1,0,0)
                            [SAssignNew(Captions[I],STextBlock).Font(TextFont(12.5f,true)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,1,0,0)
                            [SAssignNew(GearSubLabels[I],STextBlock).Font(TextFont(9.5f)).ColorAndOpacity(TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                        ]
                        // Right 52x52 framed icon (monochrome watermark when empty, full-color when equipped!)
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                        [
                            SNew(SBox).WidthOverride(52).HeightOverride(52)
                            [
                                SAssignNew(GearArtFrames[I],SBorder).BorderImage(&GearArtFrameBrushes[I]).Padding(4)
                                [
                                    SNew(SOverlay)
                                    +SOverlay::Slot().HAlign(HAlign_Fill).VAlign(VAlign_Fill)
                                    [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SAssignNew(GearImages[I],SImage)]]
                                    +SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(0,0,1,0)
                                    [SAssignNew(EmptyMarks[I],STextBlock).Font(NumberFont(12.5f,true)).ColorAndOpacity(Gray(220,110))]
                                ]
                            ]
                        ]
                    ]
                ]
            ]];
    }

    // Bar-Backed 6-Stat Matrix
    const TCHAR* Stats[]={TEXT("力量"),TEXT("敏捷"),TEXT("智力"),TEXT("体质"),TEXT("精神"),TEXT("幸运")};
    const auto Traits=SNew(SUniformWrapPanel).HAlign(HAlign_Fill).EvenRowDistribution(true)
        .MinDesiredSlotWidth(112).MaxDesiredSlotWidth(290).SlotPadding(FMargin(3.5f));
    Values.SetNum(6);GrowthValues.SetNum(6);TraitCards.SetNum(6);TraitBars.SetNum(6);TraitRanks.SetNum(6);
    for(int32 I=0;I<6;++I)
    {
        Traits->AddSlot()[SAssignNew(TraitCards[I],SBorder).BorderImage(&TraitNormal).Padding(FMargin(10,7,10,8))
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Text(Stats[I],11,TextSecondary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SAssignNew(GrowthValues[I],STextBlock).Font(NumberFont(10)).ColorAndOpacity(Success)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(2,0,0,0)[Text(TEXT("/级"),9.5f,TextTertiary)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0,2,0,0)
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Bottom)[SAssignNew(Values[I],STextBlock).Font(NumberFont(16,true)).ColorAndOpacity(TextPrimary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)[SAssignNew(TraitRanks[I],STextBlock).Font(TextFont(9.5f,true)).ColorAndOpacity(TextTertiary)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[Meter(TraitBars[I],FLinearColor(.80f,.82f,.86f,.75f),3.f)]
            ]];
    }

    // Riding Performance Telemetry (clean 3x2 grid including Mounted Damage Reduction from tack)
    const TCHAR* Labels[]={TEXT("疾驰速度"),TEXT("跳跃高度"),TEXT("转向速度"),TEXT("体力恢复"),TEXT("静养回血"),TEXT("骑乘减伤")};
    const TCHAR* Units[]={TEXT("米/秒"),TEXT("米"),TEXT("°/秒"),TEXT("%"),TEXT("/秒"),TEXT("%")};
    const auto PerformanceGrid=SNew(SUniformWrapPanel).HAlign(HAlign_Fill).EvenRowDistribution(true)
        .MinDesiredSlotWidth(178).MaxDesiredSlotWidth(290).SlotPadding(FMargin(3.5f));
    Performance.SetNum(UE_ARRAY_COUNT(Labels));
    PerformanceDeltas.SetNum(UE_ARRAY_COUNT(Labels));
    for(int32 I=0;I<Performance.Num();++I)
    {
        PerformanceGrid->AddSlot()[SNew(SBorder).BorderImage(&TeleCard).Padding(FMargin(10,6))
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Text(Labels[I],11,TextTertiary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SAssignNew(Performance[I],STextBlock).Font(NumberFont(12,true)).ColorAndOpacity(TextPrimary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(2,0,6,0)[Text(Units[I],9.5f,TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SAssignNew(PerformanceDeltas[I],STextBlock).Font(NumberFont(10,true)).ColorAndOpacity(Success)]
            ]];
    }

    const auto AffixHost=SAssignNew(AffixWrap,SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(6.f,6.f));

    return SNew(SDPIScaler).DPIScale_Lambda([Weak=TWeakObjectPtr<UColdSteelMountGearPanel>(this)]{
        return Weak.IsValid()?1.f/FMath::Max(.1f,ColdSteelUI::PixelScale(Weak.Get())):1.f;})
    [
        SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[HeroBanner]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[VitalsRow]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[Section(TEXT("马匹装备"),Gear,&CountText)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[Section(TEXT("六维属性与成长"),Traits)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[Section(TEXT("实测骑乘性能"),PerformanceGrid)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[Section(TEXT("马匹词条"),AffixHost,&AffixCountText)]
    ];
}
