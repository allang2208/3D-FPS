#include "ColdSteelSkillPage.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/Text/STextBlock.h"
#include "Framework/Application/SlateApplication.h"

TSharedRef<SWidget> UColdSteelSkillPage::RebuildWidget()
{
    Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if (Model && !IconTexture)
    {
        TArray<uint8> Bytes;
        if (FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->RifleDefinition().Icon)))
            IconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if (IconTexture) { IconBrush.SetResourceObject(IconTexture); IconBrush.DrawAs=ESlateBrushDrawType::Image; }
    }
    SAssignNew(Root,SBox); RefreshLayout(); return Root.ToSharedRef();
}
void UColdSteelSkillPage::ReleaseSlateResources(bool bReleaseChildren)
{ Super::ReleaseSlateResources(bReleaseChildren); Scroll.Reset(); Root.Reset(); DetailButton.Reset(); BackButton.Reset(); FilterButtons.Reset(); }
void UColdSteelSkillPage::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    if (!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this))) RefreshLayout();
}
void UColdSteelSkillPage::RefreshLayout()
{
    const float Offset=Scroll?Scroll->GetScrollOffset():0;
    Scale=ColdSteelUI::PixelScale(this); ActionStyle=ColdSteelUI::ButtonStyle(Scale);
    CardBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale);
    IconBrush.ImageSize=FVector2D(48/Scale);
    if (Root) { Root->SetContent(BuildPage()); if(Scroll) Scroll->SetScrollOffset(Offset); }
}
TSharedRef<SWidget> UColdSteelSkillPage::Label(const FString& Value,float Pixels,const FLinearColor& Color,bool bNumeric) const
{
    return SNew(STextBlock).Text(FText::FromString(Value)).Font(bNumeric?ColdSteelUI::NumberFont(Pixels*.75f/Scale):ColdSteelUI::TextFont(Pixels*.75f/Scale))
        .ColorAndOpacity(Color).AutoWrapText(true);
}
TSharedRef<SWidget> UColdSteelSkillPage::Overview(bool bCompact)
{
    const auto& D=Model->RifleDefinition();
    return SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12/Scale,0)
                [SNew(SBox).WidthOverride(48/Scale).HeightOverride(48/Scale)[SNew(SImage).Image(&IconBrush)]]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(D.Name,20,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Label(TEXT("步枪  /  远程  /  被动"),12,ColdSteelUI::TextSecondary)]]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8/Scale,0)
                [SNew(STextBlock).Text_Lambda([this]{return FText::FromString(FString::Printf(TEXT("Lv.%d / %d"),Model->RifleProgress().Level,Model->RifleDefinition().MaxLevel));})
                    .Font(ColdSteelUI::NumberFont(16*.75f/Scale,true)).ColorAndOpacity(ColdSteelUI::Accent)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12/Scale,0,0)[SNew(STextBlock)
            .Text_Lambda([this]{const auto P=Model->RifleProgress();const int32 Need=ColdSteelSkills::ExperienceRequired(Model->RifleDefinition(),P.Level);
                return FText::FromString(Need?FString::Printf(TEXT("修炼    %d / %d"),P.Experience,Need):TEXT("修炼完成 · 已达最高等级"));})
            .Font(ColdSteelUI::NumberFont(12*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6/Scale,0,0)[SNew(SBox).HeightOverride(4/Scale)
            [SNew(SProgressBar).Percent_Lambda([this]()->TOptional<float>{const auto P=Model->RifleProgress();const int32 Need=ColdSteelSkills::ExperienceRequired(Model->RifleDefinition(),P.Level);return Need?FMath::Clamp(float(P.Experience)/Need,0.f,1.f):1.f;})
                .FillColorAndOpacity(ColdSteelUI::Accent)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12/Scale,0,0)[Label(bCompact?TEXT("在实战中修炼 · 查看技能详情"):D.Description,14,ColdSteelUI::TextSecondary)];
}
FString UColdSteelSkillPage::EffectValue(int32 Index,bool bNext) const
{
    if (bNext && Model->RifleProgress().Level>=Model->RifleDefinition().MaxLevel) return TEXT("MAX");
    const auto E=Model->RifleEffect(Model->RifleProgress().Level+(bNext?1:0));
    if(Index==0)return FString::Printf(TEXT("+%.0f%%"),E.DamagePercent*100);
    if(Index==1)return FString::Printf(TEXT("+%.0f"),E.FlatDamage);
    if(Index==2)return FString::Printf(TEXT("+%d"),E.Wisdom);
    return FString::Printf(TEXT("+%.0f%%"),E.WeakpointPercent*100);
}
TSharedRef<SWidget> UColdSteelSkillPage::EffectRow(const FString& Caption,int32 Index)
{
    return SNew(SBorder).BorderImage(&CardBrush).Padding(FMargin(12/Scale,10/Scale))
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(Caption,14,ColdSteelUI::TextSecondary)]
            +SHorizontalBox::Slot().FillWidth(.5f).HAlign(HAlign_Right)[SNew(STextBlock)
                .Text_Lambda([this,Index]{return FText::FromString(EffectValue(Index,false));}).Font(ColdSteelUI::NumberFont(16*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().FillWidth(.5f).HAlign(HAlign_Right)[SNew(STextBlock)
                .Text_Lambda([this,Index]{return FText::FromString(EffectValue(Index,true));}).Font(ColdSteelUI::NumberFont(16*.75f/Scale)).ColorAndOpacity(ColdSteelUI::Success)]];
}
TSharedRef<SWidget> UColdSteelSkillPage::BuildPage()
{
    Scroll.Reset();
    DetailButton.Reset();BackButton.Reset();FilterButtons.Reset();
    if (!Model) return Label(TEXT("技能数据暂不可用"),14,ColdSteelUI::TextSecondary);
    auto Column=SNew(SVerticalBox);
    if (!bDetail)
    {
        auto Filters=SNew(SHorizontalBox);
        const TCHAR* Captions[]={TEXT("全部"),TEXT("被动"),TEXT("主动"),TEXT("魔法")};
        FilterButtons.SetNum(4);
        for(int32 I=0;I<4;++I) Filters->AddSlot().FillWidth(1).Padding(I?4/Scale:0,0,0,0)
            [SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight/Scale)[SAssignNew(FilterButtons[I],SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_UObject(this,&ThisClass::SelectCategory,I)[Label(Captions[I],14,Category==I?ColdSteelUI::TextPrimary:ColdSteelUI::TextTertiary)]]];
        Column->AddSlot().AutoHeight().Padding(16/Scale,12/Scale)[Filters];
        SAssignNew(Scroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No);
        if(Category<=1) Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(DetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail)[Overview(true)]];
        else Scroll->AddSlot().Padding(16/Scale,24/Scale)
            [Label(Category==2?TEXT("尚未学习主动技能"):TEXT("尚未学习魔法技能"),16,ColdSteelUI::TextSecondary)];
        Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
        Column->AddSlot().AutoHeight().Padding(16/Scale,8/Scale)[Label(TEXT("被动技能学习后自动生效，无需放入快捷栏。"),12,ColdSteelUI::TextTertiary)];
    }
    else
    {
        Column->AddSlot().AutoHeight().Padding(16/Scale,12/Scale)[SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight/Scale)
            [SAssignNew(BackButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_Lambda([this]{GoBack();return FReply::Handled();})[Label(TEXT("返回技能列表"),14,ColdSteelUI::TextPrimary)]]];
        SAssignNew(Scroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No);
        Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Overview(false)]];
        Scroll->AddSlot().Padding(28/Scale,4/Scale)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("技能收益"),16,ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().FillWidth(.5f).HAlign(HAlign_Right)[Label(TEXT("当前等级"),12,ColdSteelUI::TextSecondary)]
            +SHorizontalBox::Slot().FillWidth(.5f).HAlign(HAlign_Right)[Label(TEXT("下一等级"),12,ColdSteelUI::Success)]];
        const TCHAR* Rows[]={TEXT("步枪伤害倍率"),TEXT("步枪附加伤害"),TEXT("精神"),TEXT("步枪要害伤害")};
        for(int32 I=0;I<4;++I) Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
        Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,4/Scale)[Label(TEXT("修炼方式"),16,ColdSteelUI::TextPrimary)];
        const auto& D=Model->RifleDefinition();
        Scroll->AddSlot().Padding(16/Scale,4/Scale)[Label(FString::Printf(TEXT("步枪击杀 +%d · 有效要害命中 +%d · 要害击杀可叠加\n普通命中不增加修炼值；满级后停止积累。"),D.KillExperience,D.CriticalExperience),14,ColdSteelUI::TextSecondary)];
        Scroll->AddSlot().Padding(16/Scale,12/Scale)[SNew(STextBlock).AutoWrapText(true)
            .Text_Lambda([this]{return FText::FromString(ColdSteelSkills::IsRifle(Model->Equipped())?TEXT("当前已装备步枪 · 全部收益生效"):TEXT("当前未装备步枪 · 精神加成常驻，武器收益在装备步枪后生效"));})
            .Font(ColdSteelUI::TextFont(14*.75f/Scale)).ColorAndOpacity(ColdSteelUI::Success)];
        Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Label(TEXT("伤害倍率只作用于武器贡献，角色攻击另加。要害加成依实际命中部位判定。"),12,ColdSteelUI::TextTertiary)];
        Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
    }
    return Column;
}
FReply UColdSteelSkillPage::SelectCategory(int32 Index)
{ Category=Index; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); return FReply::Handled().SetUserFocus(FilterButtons[Index].ToSharedRef(),EFocusCause::Navigation); }
FReply UColdSteelSkillPage::OpenDetail()
{ bDetail=true; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); return FReply::Handled().SetUserFocus(BackButton.ToSharedRef(),EFocusCause::Navigation); }
bool UColdSteelSkillPage::GoBack()
{ if(!bDetail)return false; bDetail=false; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); if(DetailButton)FSlateApplication::Get().SetKeyboardFocus(DetailButton,EFocusCause::Navigation); return true; }
