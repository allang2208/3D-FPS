#include "ColdSteelAmmoReadout.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/Texture2D.h"
#include "Misc/Paths.h"

namespace ColdSteelStaffReadoutUI
{
void Set(UTextBlock* Block,const FString& Value)
{
    if(Block->GetText().ToString()!=Value)Block->SetText(FText::FromString(Value));
}
}

void UColdSteelAmmoReadout::BuildStaffDetails(UVerticalBox* Parent)
{
    StaffDetails=WidgetTree->ConstructWidget<UHorizontalBox>();Parent->AddChildToVerticalBox(StaffDetails);
    auto* Left=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* Right=WidgetTree->ConstructWidget<UVerticalBox>();
    StaffDetails->AddChildToHorizontalBox(Left)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    StaffDetails->AddChildToHorizontalBox(Right)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    auto Text=[&](UVerticalBox* Column,bool bRight)
    {
        auto* Block=WidgetTree->ConstructWidget<UTextBlock>();Block->SetAutoWrapText(false);
        Block->SetJustification(bRight?ETextJustify::Right:ETextJustify::Left);
        Block->SetColorAndOpacity(ColdSteelUI::TextSecondary);Column->AddChildToVerticalBox(Block);return Block;
    };
    CooldownLabel=Text(Left,false);CooldownValue=Text(Left,false);
    RecoveryLabel=Text(Right,true);RecoveryValue=Text(Right,true);
    CooldownLabel->SetText(FText::FromString(TEXT("魔法技能冷却缩减")));
    RecoveryLabel->SetText(FText::FromString(TEXT("魔法回满时间")));
    StaffDetails->SetVisibility(ESlateVisibility::Collapsed);
    BuildStaffMagicReadout(Parent);
}

void UColdSteelAmmoReadout::BuildStaffMagicReadout(UVerticalBox* Parent)
{
    StaffMagicRow=WidgetTree->ConstructWidget<UHorizontalBox>();Parent->AddChildToVerticalBox(StaffMagicRow);
    StaffMagicIcon=WidgetTree->ConstructWidget<UImage>();
    StaffMagicRow->AddChildToHorizontalBox(StaffMagicIcon)->SetVerticalAlignment(VAlign_Center);
    StaffMagicIcon->SetVisibility(ESlateVisibility::Collapsed);
    StaffMagicName=WidgetTree->ConstructWidget<UTextBlock>();StaffMagicName->SetAutoWrapText(false);
    StaffMagicName->SetText(FText::FromString(TEXT("未选择魔法")));StaffMagicName->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    auto* NameSlot=StaffMagicRow->AddChildToHorizontalBox(StaffMagicName);
    NameSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));NameSlot->SetVerticalAlignment(VAlign_Center);
    auto* CooldownColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    StaffMagicRow->AddChildToHorizontalBox(CooldownColumn)->SetVerticalAlignment(VAlign_Center);
    StaffMagicCooldownLabel=WidgetTree->ConstructWidget<UTextBlock>();
    StaffMagicCooldownLabel->SetText(FText::FromString(TEXT("剩余冷却")));
    StaffMagicCooldownLabel->SetAutoWrapText(false);StaffMagicCooldownLabel->SetJustification(ETextJustify::Right);
    StaffMagicCooldownLabel->SetColorAndOpacity(ColdSteelUI::TextSecondary);CooldownColumn->AddChildToVerticalBox(StaffMagicCooldownLabel);
    StaffMagicCooldown=WidgetTree->ConstructWidget<UTextBlock>();
    StaffMagicCooldown->SetAutoWrapText(false);StaffMagicCooldown->SetJustification(ETextJustify::Right);
    CooldownColumn->AddChildToVerticalBox(StaffMagicCooldown);
    StaffMagicRow->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelAmmoReadout::UpdateStaffMagicLayout(float Scale)
{
    StaffMagicIcon->SetDesiredSizeOverride(FVector2D(36.f/Scale));
    StaffMagicName->SetFont(ColdSteelUI::TextFont(16*.75f/Scale,true));
    StaffMagicCooldownLabel->SetFont(ColdSteelUI::TextFont(12*.75f/Scale));
    StaffMagicCooldown->SetFont(ColdSteelUI::NumberFont(20*.75f/Scale));
    Cast<UVerticalBoxSlot>(StaffMagicRow->Slot)->SetPadding(FMargin(0,12/Scale,0,0));
    Cast<UHorizontalBoxSlot>(StaffMagicIcon->Slot)->SetPadding(FMargin(0,0,8/Scale,0));
    Cast<UHorizontalBoxSlot>(StaffMagicName->Slot)->SetPadding(FMargin(0,0,12/Scale,0));
    Cast<UVerticalBoxSlot>(StaffMagicCooldown->Slot)->SetPadding(FMargin(0,2/Scale,0,0));
}

void UColdSteelAmmoReadout::UpdateStaffMagicIcon(FName Skill,const FString& RelativeIcon)
{
    if(StaffMagicIconSkill==Skill)return;
    StaffMagicIconSkill=Skill;
    if(StaffMagicIconLoad)StaffMagicIconLoad->CancelHandle();StaffMagicIconLoad.Reset();
    StaffMagicIcon->SetBrushFromTexture(nullptr);
    StaffMagicIcon->SetVisibility(Skill.IsNone()?ESlateVisibility::Collapsed:ESlateVisibility::Hidden);
    if(Skill.IsNone())return;
    if(const auto* Cached=StaffMagicIcons.Find(Skill))
    {
        StaffMagicIcon->SetBrushFromTexture(Cached->Get());StaffMagicIcon->SetVisibility(ESlateVisibility::HitTestInvisible);return;
    }
    if(RelativeIcon.IsEmpty())return;
    const FString Package=TEXT("/Game/ColdSteelData/")+FPaths::GetPath(RelativeIcon)/FPaths::GetBaseFilename(RelativeIcon);
    const FSoftObjectPath Path(Package+TEXT(".")+FPaths::GetBaseFilename(Package));
    // One request per selection; the finite spell catalog bounds the retained icon cache.
    StaffMagicIconLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,FStreamableDelegate::CreateWeakLambda(this,[this,Skill,Path]()
    {
        if(StaffMagicIconSkill!=Skill)return;
        if(auto* Texture=Cast<UTexture2D>(Path.ResolveObject()))
        {
            StaffMagicIcons.Add(Skill,Texture);StaffMagicIcon->SetBrushFromTexture(Texture);
            StaffMagicIcon->SetVisibility(ESlateVisibility::HitTestInvisible);
        }
    }));
}

void UColdSteelAmmoReadout::NativeDestruct()
{
    // A cached widget can be attached again after the selection changed while detached.
    // Clear the image together with its request key, not just the key.
    UpdateStaffMagicIcon(NAME_None,FString());
    Super::NativeDestruct();
}

void UColdSteelAmmoReadout::SetStaffVisible(bool Visible)
{
    if(LastStaffVisible.IsSet()&&LastStaffVisible.GetValue()==Visible)return;
    LastStaffVisible=Visible;
    StaffDetails->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    StaffMagicRow->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if(!Visible)UpdateStaffMagicIcon(NAME_None,FString());
}

void UColdSteelAmmoReadout::PresentStaff(const FColdSteelItem& Staff,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character,bool bHasOffhand)
{
    const auto Readout=Model.StaffManaReadout(Character);
    const FName SelectedSkill=Model.SelectedMagicSkill();
    const auto* Definition=Model.QuickSkillDefinition(SelectedSkill);
    const float Remaining=FMath::Max(0.f,Model.MagicCooldownRemaining(SelectedSkill));
    SetTextIfChanged(StaffMagicName,Definition?Definition->Name:TEXT("未选择魔法"));
    SetTextIfChanged(StaffMagicCooldown,Definition?FString::Printf(TEXT("%.1f s"),FMath::CeilToDouble(double(Remaining)*10.)/10.):TEXT("—"));
    SetColorIfChanged(StaffMagicCooldown,Remaining>0.f?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    UpdateStaffMagicIcon(Definition?SelectedSkill:NAME_None,Definition?Definition->Icon:FString());
    SetReserveStatusText(false);
    SetTextIfChanged(Weapon,(bHasOffhand?FString(TEXT("主手 · ")):FString())+ColdSteelInventory::Text(Staff,TEXT("name")));
    SetTextIfChanged(Calibre,SelectedSkill.IsNone()?TEXT("左键挥杖 · 长按 R 选择魔法"):TEXT("左键施法 · 长按 R 切换魔法"));
    SetTextIfChanged(MagazineLabel,TEXT("魔法"));SetTextIfChanged(ReserveLabel,TEXT("每秒恢复"));
    SetTextIfChanged(Current,Readout.bInfinite?TEXT("∞ / ∞"):FString::Printf(TEXT("%.0f / %.0f"),FMath::FloorToDouble(Readout.Current),Readout.Maximum));
    SetColorIfChanged(Current,Readout.bInfinite?ColdSteelUI::TextPrimary:Readout.Current<=0.f?ColdSteelUI::Danger:
        Readout.Current<=Readout.Maximum*.2f?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    SetTextIfChanged(Spare,FString::Printf(TEXT("%.2f"),Readout.RecoveryPerSecond));
    SetColorIfChanged(Spare,ColdSteelUI::TextSecondary);
    SetTextIfChanged(CooldownValue,FString::Printf(TEXT("%.1f%%"),Readout.CooldownReductionPercent));
    SetColorIfChanged(CooldownValue,ColdSteelUI::TextPrimary);
    const bool StatusText=Readout.bRecoveryPaused||Readout.bRecoveryDisabled;
    if(bRecoveryStatusText!=StatusText)
    {
        bRecoveryStatusText=StatusText;
        const float S=ColdSteelUI::PixelScale(this);
        RecoveryValue->SetFont(StatusText?ColdSteelUI::TextFont(16*.75f/S):ColdSteelUI::NumberFont(24*.75f/S));
    }
    if(Readout.bRecoveryPaused)SetTextIfChanged(RecoveryValue,TEXT("暂停恢复"));
    else if(Readout.bRecoveryDisabled)SetTextIfChanged(RecoveryValue,TEXT("不恢复"));
    else SetTextIfChanged(RecoveryValue,FString::Printf(TEXT("%.1f s"),FMath::CeilToDouble(double(Readout.FullRecoverySeconds)*10.)/10.));
    SetColorIfChanged(RecoveryValue,Readout.bRecoveryDisabled?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

void UColdSteelAmmoReadout::PresentSpellbook(const FColdSteelItem& Book,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character)
{
    const auto Readout=Model.SpellbookReadout(Character);
    const bool Empowered=Readout.State==EColdSteelFocusReadout::Empowered;
    SetTextIfChanged(OffhandName,TEXT("副手 · ")+ColdSteelInventory::Text(Book,TEXT("name")));
    FString Status;
    switch(Readout.State)
    {
        case EColdSteelFocusReadout::Opening:Status=TEXT("正在进入专注 · 完成后生效");break;
        case EColdSteelFocusReadout::Empowered:Status=TEXT("专注中 · 右键退出");break;
        case EColdSteelFocusReadout::Closing:Status=TEXT("正在退出专注 · 效果已结束");break;
        case EColdSteelFocusReadout::Interrupted:Status=TEXT("专注已中断 · 效果已结束");break;
        default:Status=TEXT("右键进入专注 · 专注效果预览");break;
    }
    SetTextIfChanged(OffhandCalibre,Status);
    SetColorIfChanged(OffhandCalibre,Empowered?ColdSteelUI::HUDGold:ColdSteelUI::TextSecondary);
    SetTextIfChanged(OffhandMagazineLabel,TEXT("专注施法速度"));SetTextIfChanged(OffhandReserveLabel,TEXT("专注魔法消耗"));
    SetTextIfChanged(OffhandAmmo,FString::Printf(TEXT("%.2f×"),Readout.CastSpeedMultiplier));
    SetTextIfChanged(OffhandSpare,FString::Printf(TEXT("%.0f%%"),Readout.ManaCostMultiplier*100.f));
    SetColorIfChanged(OffhandAmmo,Empowered?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary);
    SetColorIfChanged(OffhandSpare,Empowered?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary);
    SetTextIfChanged(FocusEffects,FString::Printf(TEXT("移动速度为 %.0f%%\n受击中断并失去 %.0f%% 最大魔法"),
        Readout.MovementMultiplier*100.f,Readout.InterruptMaxManaFraction*100.f));
}
