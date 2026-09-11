#include "M4GunsmithWidget.h"
#include "SM4PreviewSurface.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"

namespace {
TSharedRef<STextBlock> Label(const FString& Text,int32 Size=16,FLinearColor Color=ColdSteelUI::TextPrimary)
{return SNew(STextBlock).Text(FText::FromString(Text)).Font(ColdSteelUI::TextFont(Size)).ColorAndOpacity(Color).AutoWrapText(true);}
}
TSharedRef<SWidget> UM4GunsmithWidget::BuildWorkbench()
{
    OptionsSignature.Reset();OptionsCategory.Reset();OptionCards.Reset();
    PanelBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,8);
    RowBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,4,ColdSteelUI::Border,.5f);
    NormalButton=FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("Button");
    NormalButton.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal,5));
    NormalButton.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,5,ColdSteelUI::Accent));
    NormalButton.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,5));
    NormalButton.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,5));
    SelectedButton=NormalButton;SelectedButton.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,5,ColdSteelUI::Accent,2));
    PrimaryButton=NormalButton;PrimaryButton.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,5));
    PrimaryButton.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary,5));
    BackgroundTexture=LoadObject<UTexture2D>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_WorkshopBackground.T_WorkshopBackground"));
    BackgroundBrush.SetResourceObject(BackgroundTexture);BackgroundBrush.ImageSize=FVector2D(1672,941);BackgroundBrush.DrawAs=ESlateBrushDrawType::Image;
    InitializePreview();
    auto Button=[this](const FString& Text,TFunction<void()> Fn,bool Primary=false){return SNew(SButton).ButtonStyle(Primary?&PrimaryButton:&NormalButton).ContentPadding(FMargin(14,9)).OnClicked_Lambda([Fn](){Fn();return FReply::Handled();})[SNew(STextBlock).Text(FText::FromString(Text)).Font(ColdSteelUI::TextFont(16)).ColorAndOpacity(Primary?FLinearColor(.025f,.035f,.045f,1):ColdSteelUI::TextPrimary)];};
    auto Rail=SNew(SVerticalBox);
    const auto* W=Model()->Weapon(Model()->Definition());
    for(int32 I=0;I<Model()->Slots().Num();++I)
    {
        const FString Key=Model()->Slots()[I],Name=Model()->Categories()[I];const bool Enabled=W&&W->Allowed.Contains(Key);
        Rail->AddSlot().AutoHeight().Padding(0,0,0,6)
        [SNew(SBorder).Padding(2).BorderImage_Lambda([this,Key]()->const FSlateBrush*{return SelectedCategory==Key?&SelectedButton.Normal:FCoreStyle::Get().GetBrush("NoBrush");})
        [SNew(SButton).ButtonStyle(&NormalButton).ForegroundColor_Lambda([this,Key](){return SelectedCategory==Key?ColdSteelUI::Accent:ColdSteelUI::TextPrimary;}).IsEnabled(Enabled).ContentPadding(FMargin(10,8))
            .OnClicked_Lambda([this,Key](){SelectCategory(Key);return FReply::Handled();})
            [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Name)).Font(ColdSteelUI::TextFont(17)).ColorAndOpacity_Lambda([this,Key](){return SelectedCategory==Key?ColdSteelUI::Accent:ColdSteelUI::TextPrimary;})]+SVerticalBox::Slot().AutoHeight().Padding(0,3,0,0)[Label(Enabled?TEXT("选择部件"):TEXT("待扩展"),11,ColdSteelUI::TextTertiary)]]]];
    }
    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1)[SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Label(TEXT("装备改造  /  装配工作台"),26)]+SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[Label(TEXT("M4A1   ·   5.56 mm   /   选择配件预览，应用后保存"),14,ColdSteelUI::TextSecondary)]]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Button(TEXT("Esc  返回"),[this](){if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->CloseGunsmith();})];
    auto Stage=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&BackgroundBrush)]]
        +SOverlay::Slot().Padding(8,8,8,20)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(&PreviewBrush).Visibility_Lambda([this](){auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance()?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]
        +SOverlay::Slot().VAlign(VAlign_Top).HAlign(HAlign_Left).Padding(20)[SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()[Label(TEXT("M4A1"),28)]
            +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("左键拖动旋转 · 双击复位"))).Font(ColdSteelUI::TextFont(14)).ColorAndOpacity(ColdSteelUI::TextSecondary)]]
        +SOverlay::Slot().VAlign(VAlign_Bottom).HAlign(HAlign_Right).Padding(16)
        [SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)[Button(TEXT("水平复位"),[this](){SetSidePreview(true);})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("瞄准预览"),[this](){SetAimPreview(true);})]]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(STextBlock).Text(FText::FromString(TEXT("该枪械尚未装备\n应用配置后装备查看"))).Font(ColdSteelUI::TextFont(20)).ColorAndOpacity(ColdSteelUI::TextPrimary)
            .Visibility_Lambda([this](){auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance()?EVisibility::Collapsed:EVisibility::Visible;})];
    auto Surface=SNew(SM4PreviewSurface).CanRotate_Lambda([this](){auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance();})
        .OnOrbit_Lambda([this](FVector2D Delta){RotatePreview(Delta);}).OnReset_Lambda([this](){SetSidePreview(true);})[Stage];
    PreviewSurface=Surface;
    auto Center=SNew(SVerticalBox)
        +SVerticalBox::Slot().FillHeight(1)[Surface]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(SBorder).BorderImage(&PanelBrush).Padding(14)
            [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([this](){const int32 Index=Model()->Slots().IndexOfByKey(SelectedCategory);const FString Category=Model()->Categories().IsValidIndex(Index)?Model()->Categories()[Index]:TEXT("配件");return FText::FromString(Category+TEXT(" / 可选配件"));}).Font(ColdSteelUI::TextFont(18)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("%d 项  ·  %s"),OptionCards.Num(),OptionCards.Num()>2?TEXT("滚轮浏览"):TEXT("点击选择")));}).Font(ColdSteelUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextTertiary)]]
                +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(140)
                    [SAssignNew(OptionScroll,SScrollBox).Orientation(Orient_Horizontal).ScrollBarAlwaysVisible(false).AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::Always).WheelScrollMultiplier(2.f).AnimateWheelScrolling(false)]]]];
    auto CompareButton=[this](bool Factory)
    {
        return SNew(SBorder).Padding(2).BorderImage_Lambda([this,Factory]()->const FSlateBrush*{return bCompareFactory==Factory?&SelectedButton.Normal:FCoreStyle::Get().GetBrush("NoBrush");})
            [SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(8,7)).OnClicked_Lambda([this,Factory](){SetCompareFactory(Factory);return FReply::Handled();})
                [Label(Factory?TEXT("对比原厂"):TEXT("对比当前"),14)]];
    };
    auto Inspector=SNew(SBorder).BorderImage(&PanelBrush).Padding(16)
        [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[Label(TEXT("改造项目"),19)]
            +SVerticalBox::Slot().AutoHeight()[SNew(SBox).MaxDesiredHeight(148)[SNew(SScrollBox).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                +SScrollBox::Slot()[SAssignNew(ModificationList,SVerticalBox)]]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,14,0,5)[Label(TEXT("整枪数值总览"),20)]
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,4,0)[CompareButton(false)]
                +SHorizontalBox::Slot().FillWidth(1).Padding(4,0,0,0)[CompareButton(true)]]
            +SVerticalBox::Slot().FillHeight(1)[SNew(SScrollBox).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                +SScrollBox::Slot()[SAssignNew(OverviewList,SVerticalBox)]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Label(TEXT("绿色：增强  ·  红色：削弱  ·  灰色：不变\n后坐力越低越好；枪械稳定性越高越好。"),11,ColdSteelUI::TextTertiary)]];
    FLinearColor Shell=ColdSteelUI::GlassTint;Shell.A=1;
    return SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Shell).Padding(0)
        [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SBox).WidthOverride(1600).HeightOverride(900)
        [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(22,16,22,14)[Header]
            +SVerticalBox::Slot().FillHeight(1).Padding(20,0,20,0)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(112)[SNew(SScrollBox)+SScrollBox::Slot()[Rail]]]
                +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,16,0)[Center]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(520)[Inspector]]]
            +SVerticalBox::Slot().AutoHeight().Padding(20,14,20,16)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,16,0)[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(StatusText);}).Font(ColdSteelUI::TextFont(14)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[Button(TEXT("撤销更改"),[this](){Model()->Undo();Choose(Model()->Draft().FindRef(TEXT("optic"))==TEXT("holographic"));ChooseDrum(Model()->Draft().FindRef(TEXT("magazine"))==TEXT("large_drum"));})]
                +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("应用并保存"),[this](){ApplyDraft();},true)]]]]];
}

TSharedRef<SWidget> UM4GunsmithWidget::BuildOption(const FString& SlotKey,const FString& Id)
{
    const auto* O=Model()->Option(Model()->Definition(),SlotKey,Id);if(!O)return SNew(SBox);
    FString Summary=O->Description.Replace(TEXT("\r"),TEXT(" ")).Replace(TEXT("\n"),TEXT(" "));
    if(Summary.Len()>32)Summary=Summary.Left(32)+TEXT("…");
    auto Selected=[this,SlotKey,Id](){return Model()->Draft().FindRef(SlotKey)==Id||(Id==TEXT("false")&&!Model()->Draft().Contains(SlotKey));};
    return SNew(SBox).WidthOverride(310).HeightOverride(122)
        [SNew(SBorder).Padding(2).BorderImage_Lambda([this,Selected]()->const FSlateBrush*{return Selected()?&SelectedButton.Normal:FCoreStyle::Get().GetBrush("NoBrush");})
        [SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(12,8)).ToolTipText(FText::FromString(O->Name+TEXT("\n")+O->Description))
            .OnClicked_Lambda([this,SlotKey,Id](){ChooseOption(SlotKey,Id);return FReply::Handled();})
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(O->Name)).Font(ColdSteelUI::TextFont(17)).ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().FillHeight(1).Padding(0,5,0,4)[SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[Label(Summary,12,ColdSteelUI::TextSecondary)]]
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([Selected](){return FText::FromString(Selected()?TEXT("已选择"):TEXT("选择配件"));}).Font(ColdSteelUI::TextFont(12)).ColorAndOpacity_Lambda([Selected](){return Selected()?ColdSteelUI::Accent:ColdSteelUI::TextTertiary;})]]]];
}
