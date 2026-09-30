#include "M4GunsmithWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "SMeleePartIcon.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Production/ProductionToolEnhance.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"

/**
 * 改造工作台第五栏「强化」（阶段 1-C）。
 *
 * 与另外四栏的区别：**强化不是改造槽**。它不进 `gunsmith_parts`、不进 `UGunsmithSystem::Slots()`／
 * `Calculate()`，也不参与 `Installed()`／`Normalize()`；它只是一个「金属材质档位」选择器，
 * 选中后把草稿等级交给 `UGunsmithSystem`，由模型在「应用」时和改造件同一次事务写进物品 Data 的
 * `tool_enhance_level`。
 *
 * 本阶段（1-C）不设消耗、不设强化数值：`cost`／`stats` 在目录里恒为空对象且加载器不暴露，
 * 详情区固定显示「待定」，总览只用「—」，绝不出现任何假数字或 0 值。
 */

namespace
{
    /** 档位卡片宽高沿用现有选项卡（工具工作台 288，与四栏一致）。 */
    constexpr float EnhanceCardWidth=288.f;
    constexpr float EnhanceCardHeight=142.f;
}

FString UM4GunsmithWidget::OptionsTitle() const
{
    if(SelectedCategory==TEXT("enhance"))return TEXT("强化 / 材质档位");
    return Model()->CategoryLabel(Model()->Definition(),SelectedCategory)+TEXT(" / 可选配件");
}

int32 UM4GunsmithWidget::OptionsCount() const
{
    if(SelectedCategory==TEXT("enhance"))return ColdSteelToolEnhance::Levels().Num();
    return OptionCards.Num();
}

bool UM4GunsmithWidget::EnhanceOptionsDirty() const
{
    const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance());
    if(!Item)return false;
    return EnhanceSignature!=FString::Printf(TEXT("%s|%d|%d"),*Item->InstanceId,ColdSteelToolEnhance::Level(*Item),Model()->DraftEnhanceLevel());
}

void UM4GunsmithWidget::ChooseEnhanceLevel(int32 Level)
{
    // 模型侧只接受「当前等级+1」：不可降级、不可跳级。其余点击在卡片上已禁用，这里再挡一次。
    if(!Model()->SetDraftEnhanceLevel(Level))return;
    PreviewMotion=1.f;
    RefreshPresentation();
}

void UM4GunsmithWidget::SyncEnhancePreview()
{
    if(!IsToolWorkbench())return;
    const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance());
    if(!Item)return;
    // 草稿等级为 0 时用实例等级；阶段 1-B 已把 override 并进预览 Key，切档位会重建一次网格。
    const int32 Draft=Model()->DraftEnhanceLevel();
    if(PreviewEnhanceLevel==Draft)return;
    PreviewEnhanceLevel=Draft;
    SetStandaloneToolItem(*Item,Draft);
}

TSharedRef<SWidget> UM4GunsmithWidget::BuildEnhanceCard(int32 Level)
{
    const FToolEnhanceLevel* Row=ColdSteelToolEnhance::Find(Level);
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile->FindItem(Model()->Instance());
    const int32 Current=Item?ColdSteelToolEnhance::Level(*Item):1;
    int32 Next=0;
    const bool bHasNext=Item&&ColdSteelToolEnhance::CanEnhance(*Item,Next);
    const int32 Draft=Model()->DraftEnhanceLevel();
    // 只有「当前+1」这一档可点：当前档是已装备、更高档需先逐级强化。
    const bool bSelectable=bHasNext&&Level==Next;
    const bool bSelected=bSelectable&&Draft==Level;
    const FString Name=Row?Row->Name:FString();
    const FString Description=Row?Row->Description:FString();
    // 角标只有三种：当前档「已装备」、当前+1 档「可强化／已选 · 待应用」、更高档「需先强化到 Lv.N」。
    // 卡片在草稿变化时会整体重建（见 EnhanceOptionsDirty），所以这里按当前草稿定稿即可。
    const FString Caption=Level==Current?TEXT("已装备"):Level==Next?(bSelected?TEXT("已选 · 待应用"):TEXT("可强化"))
        :FString::Printf(TEXT("需先强化到 Lv.%d"),Level-1);
    auto Frame=[bSelectable,bSelected]()
    {
        if(!bSelectable)return FLinearColor::Transparent;
        auto Color=ColdSteelUI::Success;Color.A=bSelected?.32f:.18f;
        return Color;
    };
    auto CaptionColor=[bSelectable,bSelected,Level,Current]()
    {
        if(Level==Current)return GunsmithUI::Secondary;
        return bSelectable?(bSelected?ColdSteelUI::Success:GunsmithUI::Silver):GunsmithUI::Muted;
    };
    return SNew(SBox).WidthOverride(EnhanceCardWidth).HeightOverride(EnhanceCardHeight)
        [SNew(SOverlay)
            +SOverlay::Slot()
            [SNew(SBorder).Padding(2).BorderImage(&OptionFrameBrush).BorderBackgroundColor_Lambda(Frame)
                [SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(10,8))
                    .IsEnabled(bSelectable)
                    .ToolTipText(FText::FromString(Name+TEXT("  Lv.")+FString::FromInt(Level)+TEXT("\n")+Description))
                    .OnClicked_Lambda([this,Level](){ChooseEnhanceLevel(Level);return FReply::Handled();})
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()
                        [SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,6,0)
                            [SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("Lv.%d"),Level)))
                                .Font(GunsmithUI::NumberFont(13,true)).ColorAndOpacity(bSelectable?GunsmithUI::Silver:GunsmithUI::Muted)]
                            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                            [SNew(STextBlock).Text(FText::FromString(Name)).Font(GunsmithUI::TextFont(16,true))
                                .ColorAndOpacity(bSelectable?GunsmithUI::Text:GunsmithUI::Muted).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]
                        +SVerticalBox::Slot().FillHeight(1).Padding(0,5,0,5)
                        [SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,10,0)
                            [SNew(SBox).WidthOverride(64).HeightOverride(64)
                                [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
                                    [SNew(SImage).Image(CategoryBrushes.Contains(TEXT("enhance"))?CategoryBrushes.FindChecked(TEXT("enhance")).Get():FCoreStyle::Get().GetBrush("NoBrush"))
                                        .ColorAndOpacity(bSelectable?FLinearColor::White:GunsmithUI::Muted)]]]
                            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                            [SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)
                                [SNew(STextBlock).Text(FText::FromString(Description)).Font(GunsmithUI::TextFont(12))
                                    .ColorAndOpacity(GunsmithUI::Secondary).AutoWrapText(true)]]]
                        +SVerticalBox::Slot().AutoHeight()
                        [SNew(SOverlay)
                            +SOverlay::Slot()[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush"))
                                .ColorAndOpacity_Lambda([bSelected](){auto C=ColdSteelUI::Success;C.A=bSelected?.08f:0.f;return C;})
                                .Visibility(EVisibility::HitTestInvisible)]
                            +SOverlay::Slot().Padding(6,2)
                            [SNew(STextBlock).Text(FText::FromString(Caption)).Font(GunsmithUI::TextFont(12,true))
                                .ColorAndOpacity_Lambda(CaptionColor)
                                .ShadowOffset(FVector2D(0,1)).ShadowColorAndOpacity(FLinearColor(0,0,0,.4f))]]]]]];
}

void UM4GunsmithWidget::RefreshEnhanceOptions()
{
    if(!OptionScroll)return;
    const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance());
    if(!Item)return;
    EnhanceSignature=FString::Printf(TEXT("%s|%d|%d"),*Item->InstanceId,ColdSteelToolEnhance::Level(*Item),Model()->DraftEnhanceLevel());
    OptionScroll->ClearChildren();OptionCards.Reset();
    if(ColdSteelToolEnhance::Levels().IsEmpty())
    {
        OptionScroll->AddSlot().Padding(0,0,10,4)
            [SNew(SBox).WidthOverride(EnhanceCardWidth).HeightOverride(EnhanceCardHeight)
                [SNew(SBorder).BorderImage(&OptionFrameBrush).Padding(12)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("强化工具目录不可用"))).Font(GunsmithUI::TextFont(14))
                        .ColorAndOpacity(GunsmithUI::Secondary).AutoWrapText(true)]]];
        return;
    }
    const int32 Current=ColdSteelToolEnhance::Level(*Item);
    int32 Next=0;
    const bool bHasNext=ColdSteelToolEnhance::CanEnhance(*Item,Next);
    // 默认定位「当前+1」档；已满级则停在当前档。滚动在卡片全部加入之后再做一次，
    // 与 SelectCategory 的做法一致（同一帧内刚 AddSlot 的子控件还没进入滚动树，先滚会无效）。
    const int32 Focus=(bHasNext?Next:Current);
    TSharedPtr<SWidget> FocusCard;
    for(const auto& Entry:ColdSteelToolEnhance::Levels())
    {
        auto Card=BuildEnhanceCard(Entry.Level);
        OptionCards.Add(FString::FromInt(Entry.Level),Card);
        OptionScroll->AddSlot().Padding(0,0,10,4)[Card];
        if(Entry.Level==Focus)FocusCard=Card;
    }
    if(FocusCard.IsValid())OptionScroll->ScrollDescendantIntoView(FocusCard.ToSharedRef(),false);
}

void UM4GunsmithWidget::AppendEnhanceDetails(int32 Level)
{
    const FToolEnhanceLevel* Row=ColdSteelToolEnhance::Find(Level);
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile->FindItem(Model()->Instance());
    const int32 Current=Item?ColdSteelToolEnhance::Level(*Item):1;
    auto Paragraph=[this](const FString& Caption,int32 Pixels,FLinearColor Color,bool Medium=false)
    {
        return SNew(STextBlock).Text(FText::FromString(Caption)).Font(GunsmithUI::TextFont(Pixels,Medium))
            .ColorAndOpacity(Color).WrapTextAt_Lambda([this](){return SelectedDetailsWidth();});
    };
    ModificationList->AddSlot().AutoHeight()
        [Paragraph(Row?FString::Printf(TEXT("%s  Lv.%d"),*Row->Name,Level):TEXT("强化档位"),16,GunsmithUI::Text,true)];
    ModificationList->AddSlot().AutoHeight().Padding(0,5,0,12)
        [Paragraph(Level==Current?TEXT("已装备"):Level==Model()->DraftEnhanceLevel()?TEXT("已选 · 待应用"):TEXT("未装备"),12,
            Level==Current?GunsmithUI::Muted:GunsmithUI::Silver)];
    if(Row&&!Row->Description.IsEmpty())ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
        [Paragraph(Row->Description,12,GunsmithUI::Secondary)];
    // 本阶段不设消耗与数值：如实写「待定」，不填假数字、不显示 0。
    auto Line=[this,&Paragraph](const TCHAR* Name,const TCHAR* Value)
    {
        ModificationList->AddSlot().AutoHeight().Padding(0,0,0,4)
            [SNew(SBorder).BorderImage(&RowBrush).Padding(8,6)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                    [SNew(STextBlock).Text(FText::FromString(Name)).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(GunsmithUI::Secondary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SNew(STextBlock).Text(FText::FromString(Value)).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(GunsmithUI::Text)]]];
    };
    Line(TEXT("消耗"),TEXT("待定"));
    Line(TEXT("数值"),TEXT("本次不影响"));
    ModificationList->AddSlot().AutoHeight().Padding(0,10,0,6)[Paragraph(TEXT("等级规则"),12,GunsmithUI::Muted)];
    ModificationList->AddSlot().AutoHeight()
        [Paragraph(TEXT("逐级 +1，不可降级、不可跳级：只有当前等级的下一档可以点选，更高档需先强化到前一档。"),14,GunsmithUI::Secondary)];
    ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
        [Paragraph(TEXT("强化只更换金属部位的材质实例，木柄、绑带与皮革保持原装；采集产出、所需有效命中与自卫数值均不受影响。"),12,GunsmithUI::Muted)];
    ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
        [Paragraph(TEXT("外观资产尚未接入：材质资产在阶段 2 制作，当前预览保持现有材质，不报错、不阻断改造栏。"),12,GunsmithUI::Muted)];
    ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
        [Paragraph(TEXT("强化消耗与数值尚未开放。"),12,GunsmithUI::Muted)];
}
