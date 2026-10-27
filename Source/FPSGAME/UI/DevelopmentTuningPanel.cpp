#include "DevelopmentPanelWidget.h"
#include "DevelopmentItemPicker.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDWidget.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "GameFramework/PlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"

void UDevelopmentPanelWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if (auto* Previous = BoundTuning.Get()) Previous->OnChanged.Remove(TuningChangedHandle);
    BoundTuning = UDevelopmentTuningSubsystem::Find(this);
    if (auto* Tuning = BoundTuning.Get())
        TuningChangedHandle = Tuning->OnChanged.AddUObject(this, &ThisClass::RefreshTuning);
    RefreshTuning();
}

void UDevelopmentPanelWidget::NativeDestruct()
{
    if (ItemChoice) ItemChoice->CloseMenu();
    ++PerformanceExportGeneration;
    bPerformanceExporting = false;
    if (PerformanceExportButton) PerformanceExportButton->SetIsEnabled(true);
    // 面板被销毁时收回动画不会跑完，HUD 让位必须在这里直接解除。
    if (bHudYielded)
    {
        bHudYielded = false;
        if (auto* HUD = ResolveHUD()) HUD->SetExternalDrawerOpen(false);
    }
    if (auto* Tuning = BoundTuning.Get()) Tuning->OnChanged.Remove(TuningChangedHandle);
    TuningChangedHandle.Reset();
    BoundTuning.Reset();
    Super::NativeDestruct();
}

void UDevelopmentPanelWidget::BuildTuningPage(UVerticalBox* Page)
{
    const float Scale = ColdSteelUI::PixelScale(this);
    TuningStatus = CreatePanelText(TEXT("正在读取调参状态"), 14, ColdSteelUI::TextSecondary);
    Page->AddChildToVerticalBox(TuningStatus)->SetPadding(FMargin(0,0,0,8.f / Scale));
    Page->AddChildToVerticalBox(CreatePanelText(
        TEXT("开关立即生效，关闭面板后保持；结束本次游戏后重置。"), 12, ColdSteelUI::TextTertiary))
        ->SetPadding(FMargin(0,0,0,12.f / Scale));
    Page->AddChildToVerticalBox(CreatePanelText(TEXT("会话开关"), 16, ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0,0,0,8.f / Scale));

    struct FOptionCopy { EDevelopmentTuningOption Option; const TCHAR* Title; const TCHAR* Help; const TCHAR* Name; };
    const FOptionCopy Options[] = {
        {EDevelopmentTuningOption::ThirdPersonView, TEXT("玩家视角"), TEXT("点击切换第一人称／第三人称；第三人称显示全身，镜头遇墙自动拉近。"), TEXT("DevelopmentThirdPersonView")},
        {EDevelopmentTuningOption::FixedThirdPersonView, TEXT("第三人称固定视角"), TEXT("开启后固定第三人称镜头的位置与朝向。关闭面板后照常移动、攻击和施法；关闭此项恢复跟随，再次开启可固定新位置。"), TEXT("DevelopmentFixedThirdPersonView")},
        {EDevelopmentTuningOption::Invincible, TEXT("无敌"), TEXT("免疫受到的伤害，生命值不再因受击降低。"), TEXT("DevelopmentInvincible")},
        {EDevelopmentTuningOption::OneHitKill, TEXT("秒杀"), TEXT("玩家有效命中即可击杀敌方怪物，照常结算掉落与经验。"), TEXT("DevelopmentOneHitKill")},
        {EDevelopmentTuningOption::InfiniteReserveAmmo, TEXT("无限备弹"), TEXT("换弹不消耗背包弹药，弹匣打空后仍需换弹。"), TEXT("DevelopmentInfiniteAmmo")},
        {EDevelopmentTuningOption::InfiniteMana, TEXT("无限魔法值"), TEXT("魔法值保持可用上限，施法不扣蓝；关闭后恢复原有数值。"), TEXT("DevelopmentInfiniteMana")},
        {EDevelopmentTuningOption::NoAbilityCooldown, TEXT("魔法／技能无 CD"), TEXT("清除现有冷却，施放后不再等待 CD；保留施法动作与飞行过程。"), TEXT("DevelopmentNoCooldown")},
        {EDevelopmentTuningOption::FreeBuilding, TEXT("建造不消耗资源"), TEXT("放置体素块不扣背包／仓库体块；拆除回收仍按原规则发放。"), TEXT("DevelopmentFreeBuilding")},
        {EDevelopmentTuningOption::FreeCrafting, TEXT("制作不消耗材料"), TEXT("打铁、制药、木工、枪械／弹药制造免材料；篝火只免食材，木材照常消耗。小游戏与加工时间照常，免费工件和未加工食材不退料。"), TEXT("DevelopmentFreeCrafting")}
    };
    for (const auto& Option : Options)
    {
        FTuningRow Row;
        Row.Option = Option.Option;
        auto* Card = WidgetTree->ConstructWidget<UBorder>(); Row.Card = Card;
        Page->AddChildToVerticalBox(Card)->SetPadding(FMargin(0,0,0,8.f / Scale));
        auto* Grid = WidgetTree->ConstructWidget<UGridPanel>(); Row.Grid = Grid;
        Grid->SetColumnFill(0,1.f); Card->SetContent(Grid);
        auto* Copy = WidgetTree->ConstructWidget<UVerticalBox>(); Row.Copy = Copy;
        auto* Title = CreatePanelText(Option.Title,16,ColdSteelUI::TextPrimary);
        Copy->AddChildToVerticalBox(Title)->SetPadding(FMargin(0,0,0,6.f / Scale));
        Copy->AddChildToVerticalBox(CreatePanelText(Option.Help,12,ColdSteelUI::TextSecondary));
        Grid->AddChildToGrid(Copy,0,0);
        auto* SwitchBox = WidgetTree->ConstructWidget<USizeBox>(); Row.SwitchBox = SwitchBox;
        auto* Button = CreatePanelButton(TEXT("已关闭"),FName(Option.Name)); Row.Button = Button;
        if (auto* Label = Cast<UTextBlock>(Button->GetContent()))
        {
            Label->SetAutoWrapText(false);
            if (auto* LabelSlot = Cast<UButtonSlot>(Label->Slot))
            { LabelSlot->SetHorizontalAlignment(HAlign_Center); LabelSlot->SetVerticalAlignment(VAlign_Center); }
        }
        SwitchBox->SetContent(Button); Grid->AddChildToGrid(SwitchBox,0,1);
        switch (Option.Option)
        {
        case EDevelopmentTuningOption::Invincible: Button->OnClicked.AddDynamic(this,&ThisClass::InvincibleClicked); break;
        case EDevelopmentTuningOption::OneHitKill: Button->OnClicked.AddDynamic(this,&ThisClass::OneHitKillClicked); break;
        case EDevelopmentTuningOption::InfiniteReserveAmmo: Button->OnClicked.AddDynamic(this,&ThisClass::InfiniteAmmoClicked); break;
        case EDevelopmentTuningOption::InfiniteMana: Button->OnClicked.AddDynamic(this,&ThisClass::InfiniteManaClicked); break;
        case EDevelopmentTuningOption::NoAbilityCooldown: Button->OnClicked.AddDynamic(this,&ThisClass::NoCooldownClicked); break;
        case EDevelopmentTuningOption::FreeBuilding: Button->OnClicked.AddDynamic(this,&ThisClass::FreeBuildingClicked); break;
        case EDevelopmentTuningOption::FreeCrafting: Button->OnClicked.AddDynamic(this,&ThisClass::FreeCraftingClicked); break;
        case EDevelopmentTuningOption::ThirdPersonView: Button->OnClicked.AddDynamic(this,&ThisClass::ThirdPersonViewClicked); break;
        case EDevelopmentTuningOption::FixedThirdPersonView: Button->OnClicked.AddDynamic(this,&ThisClass::FixedThirdPersonViewClicked); break;
        }
        TuningRows.Add(Row);
    }
    BuildFeatureRows(Page);
    Page->AddChildToVerticalBox(CreatePanelText(TEXT("角色外观"),16,ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0,12.f/Scale,0,8.f/Scale));
    BodyTypeButton=AddButton(Page,TEXT("切换女性角色"),TEXT("DevelopmentBodyType"));
    BodyTypeButton->OnClicked.AddDynamic(this,&ThisClass::BodyTypeClicked);
    if(auto* Label=Cast<UTextBlock>(BodyTypeButton->GetContent()))Label->SetAutoWrapText(false);
    BodyTypeStatus=CreatePanelText(TEXT("角色外观选择随当前档案保存。"),12,ColdSteelUI::TextSecondary);
    Page->AddChildToVerticalBox(BodyTypeStatus)->SetPadding(FMargin(0,6.f/Scale,0,0));
    RefreshBodyTypeButton();
}

void UDevelopmentPanelWidget::RefreshBodyTypeButton()
{
    if(!BodyTypeButton)return;
    const auto* Player=GetOwningPlayer();
    const auto* Body=Player&&Player->GetPawn()?Player->GetPawn()->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    const bool Female=Body&&Body->GetBodyType()==TEXT("kaitlin");
    const FName Target=Female?TEXT("jason"):TEXT("kaitlin");
    const bool Loading=Body&&Body->IsAppearanceLoading();
    BodyTypeButton->SetIsEnabled(Body&&Body->CanUseBodyType(Target));
    if(auto* Label=Cast<UTextBlock>(BodyTypeButton->GetContent()))
        Label->SetText(FText::FromString(Loading?TEXT("正在切换角色…"):Female?TEXT("切换男性角色"):TEXT("切换女性角色")));
    if(BodyTypeStatus)BodyTypeStatus->SetText(FText::FromString(!Body?TEXT("控制角色后可切换外观。"):
        Loading?TEXT("正在加载身体与装备。"):
        !Body->CanUseBodyType(Target)?TEXT("角色暂不可切换，或对应外观资源尚未接入。"):
        Female?TEXT("当前：女性 Kaitlin · 选择随档案保存"):
        TEXT("当前：男性 Jason · 选择随档案保存")));
}

void UDevelopmentPanelWidget::BodyTypeClicked()
{
    auto* Player=GetOwningPlayer();
    auto* Body=Player&&Player->GetPawn()?Player->GetPawn()->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(Body&&!Body->SetBodyType(Body->GetBodyType()==TEXT("kaitlin")?FName(TEXT("jason")):FName(TEXT("kaitlin"))))
    {
        if(BodyTypeStatus)BodyTypeStatus->SetText(FText::FromString(TEXT("角色切换未完成，请稍后重试。")));
        return;
    }
    RefreshBodyTypeButton();
}

void UDevelopmentPanelWidget::UpdateTuningLayout(float ContentWidth, float Scale)
{
    const bool bStackSwitch = ContentWidth < 360.f;
    for (auto& Row : TuningRows)
    {
        if (!Row.Card.IsValid() || !Row.Grid.IsValid() || !Row.Copy.IsValid() || !Row.SwitchBox.IsValid()) continue;
        Row.Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius / Scale));
        Row.Card->SetPadding(FMargin(12.f / Scale));
        if (auto* CardSlot = Cast<UVerticalBoxSlot>(Row.Card->Slot)) CardSlot->SetPadding(FMargin(0,0,0,8.f / Scale));
        Row.SwitchBox->SetWidthOverride(88.f / Scale);
        Row.SwitchBox->SetHeightOverride(ColdSteelUI::ActionHeight / Scale);
        if (auto* CopySlot = Cast<UGridSlot>(Row.Copy->Slot))
        {
            CopySlot->SetColumnSpan(bStackSwitch ? 2 : 1);
            CopySlot->SetPadding(FMargin(0,0,bStackSwitch ? 0 : 12.f / Scale,0));
        }
        if (auto* SwitchSlot = Cast<UGridSlot>(Row.SwitchBox->Slot))
        {
            SwitchSlot->SetRow(bStackSwitch ? 1 : 0); SwitchSlot->SetColumn(bStackSwitch ? 0 : 1);
            SwitchSlot->SetColumnSpan(bStackSwitch ? 2 : 1);
            SwitchSlot->SetHorizontalAlignment(HAlign_Right); SwitchSlot->SetVerticalAlignment(VAlign_Center);
            SwitchSlot->SetPadding(FMargin(0,bStackSwitch ? 10.f / Scale : 0,0,0));
        }
    }
}

void UDevelopmentPanelWidget::RefreshTuning()
{
    if (!TuningStatus) return;
    const auto* Tuning = UDevelopmentTuningSubsystem::Find(this);
    bTuningAvailable = Tuning && Tuning->CanEdit(GetOwningPlayer());
    const float Scale = ColdSteelUI::PixelScale(this);
    int32 Enabled = 0;
    for (const auto& Row : TuningRows)
    {
        auto* Button = Row.Button.Get(); if (!Button) continue;
        const bool bEnabled = Tuning && Tuning->IsEnabled(Row.Option);
        if (bEnabled) ++Enabled;
        Button->SetIsEnabled(bTuningAvailable);
        auto Style = ColdSteelUI::ButtonStyle(1.f / Scale);
        if (bEnabled) Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius / Scale,ColdSteelUI::Accent));
        Button->SetStyle(Style);
        if (auto* Label = Cast<UTextBlock>(Button->GetContent()))
        {
            const bool bViewSwitch = Row.Option == EDevelopmentTuningOption::ThirdPersonView;
            const bool bFixedViewSwitch = Row.Option == EDevelopmentTuningOption::FixedThirdPersonView;
            Label->SetText(FText::FromString(bViewSwitch
                ? (bEnabled ? TEXT("第三人称") : TEXT("第一人称"))
                : bFixedViewSwitch ? (bEnabled ? TEXT("已固定") : TEXT("未固定"))
                : (bEnabled ? TEXT("已开启") : TEXT("已关闭"))));
            Label->SetColorAndOpacity(bEnabled ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary);
        }
    }
    TuningStatus->SetText(FText::FromString(bTuningAvailable
        ? FString::Printf(TEXT("当前已开启 %d / %d 项"),Enabled,TuningRows.Num())
        : TEXT("进入单机游戏并控制角色后，可使用基本调参。")));
    TuningStatus->SetColorAndOpacity(bTuningAvailable ? ColdSteelUI::TextSecondary : ColdSteelUI::Warning);
    if (DisableTuningButton) DisableTuningButton->SetIsEnabled(bTuningAvailable && Enabled > 0);
}

void UDevelopmentPanelWidget::ToggleTuning(EDevelopmentTuningOption Option)
{
    if (auto* Tuning = UDevelopmentTuningSubsystem::Find(this))
        Tuning->SetEnabled(Option,!Tuning->IsEnabled(Option),GetOwningPlayer());
    if (auto* Player = GetOwningPlayer(); Player && Player->GetPawn())
        if (auto* Body = Player->GetPawn()->FindComponentByClass<UFPSPlayerBodyComponent>()) Body->RefreshViewMode();
}

void UDevelopmentPanelWidget::InvincibleClicked() { ToggleTuning(EDevelopmentTuningOption::Invincible); }
void UDevelopmentPanelWidget::OneHitKillClicked() { ToggleTuning(EDevelopmentTuningOption::OneHitKill); }
void UDevelopmentPanelWidget::InfiniteAmmoClicked() { ToggleTuning(EDevelopmentTuningOption::InfiniteReserveAmmo); }
void UDevelopmentPanelWidget::InfiniteManaClicked() { ToggleTuning(EDevelopmentTuningOption::InfiniteMana); }
void UDevelopmentPanelWidget::NoCooldownClicked() { ToggleTuning(EDevelopmentTuningOption::NoAbilityCooldown); }
void UDevelopmentPanelWidget::FreeBuildingClicked() { ToggleTuning(EDevelopmentTuningOption::FreeBuilding); }
void UDevelopmentPanelWidget::FreeCraftingClicked() { ToggleTuning(EDevelopmentTuningOption::FreeCrafting); }
void UDevelopmentPanelWidget::ThirdPersonViewClicked() { ToggleTuning(EDevelopmentTuningOption::ThirdPersonView); }
void UDevelopmentPanelWidget::FixedThirdPersonViewClicked() { ToggleTuning(EDevelopmentTuningOption::FixedThirdPersonView); }
void UDevelopmentPanelWidget::DisableTuningClicked()
{
    if (auto* Tuning = UDevelopmentTuningSubsystem::Find(this)) Tuning->DisableAll(GetOwningPlayer());
    if (auto* Player = GetOwningPlayer(); Player && Player->GetPawn())
        if (auto* Body = Player->GetPawn()->FindComponentByClass<UFPSPlayerBodyComponent>()) Body->RefreshViewMode();
}
