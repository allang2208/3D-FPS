#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"

UColdSteelStatusModel* UColdSteelExpeditionWidget::Profile() const
{
    return GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}

void UColdSteelExpeditionWidget::SetDestinations(TArray<FColdSteelExpeditionDestination> Entries)
{
    Destinations = MoveTemp(Entries);
    Feedback = FText::GetEmpty();
    RefreshList();
}

const FColdSteelExpeditionDestination* UColdSteelExpeditionWidget::Selection() const
{
    return Destinations.FindByPredicate([this](const auto& Entry) { return Entry.Id == SelectedId; });
}

void UColdSteelExpeditionWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if (auto* Model = Profile())
        ProfileHandle = Model->OnChanged.AddUObject(this, &ThisClass::RefreshPreparation);
    RefreshList();
    RefreshPreparation();
}

void UColdSteelExpeditionWidget::NativeDestruct()
{
    if (auto* Model = Profile()) Model->OnChanged.Remove(ProfileHandle);
    ProfileHandle.Reset();
    OnDepartureRequested.Unbind();
    Super::NativeDestruct();
}

void UColdSteelExpeditionWidget::NativeTick(const FGeometry& Geometry, float Delta)
{
    Super::NativeTick(Geometry, Delta);
    UpdateLayout();
}

FReply UColdSteelExpeditionWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    // Preview catches Esc even while a search field or a tab owns keyboard focus.
    if (Event.GetKey() == EKeys::Escape) { Close(); return FReply::Handled(); }
    if (Event.IsControlDown() && Event.GetKey() == EKeys::F && Search.IsValid())
    { Search->SetText(FText::FromString(Query)); return FReply::Handled().SetUserFocus(Search.ToSharedRef()); }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}

void UColdSteelExpeditionWidget::Close()
{
    if (auto* Player = Cast<AFPSGAMEPlayerController>(GetOwningPlayer())) Player->CloseExpedition();
}

bool UColdSteelExpeditionWidget::CanConfirm() const
{
    const auto* Entry = Selection();
    return Entry && Entry->bCanDepart && OnDepartureRequested.IsBound();
}

FText UColdSteelExpeditionWidget::BlockMessage() const
{
    if (!Feedback.IsEmpty()) return Feedback;
    const auto* Entry = Selection();
    if (!Entry) return FText::FromString(TEXT("选择一个目的地，查看出征准备"));
    if (!Entry->bCanDepart)
        return FText::FromString(Entry->BlockReason.IsEmpty() ? TEXT("当前目的地暂未开放") : Entry->BlockReason);
    if (!OnDepartureRequested.IsBound()) return FText::FromString(TEXT("出征暂未开放"));
    return FText::FromString(TEXT("准备就绪，请确认本次目的地"));
}

void UColdSteelExpeditionWidget::ConfirmDeparture()
{
    if (!CanConfirm()) return;
    const FName RequestedId = SelectedId;
    // No saving, charging, travel or fabricated success in the view. The receiver returns feedback.
    Feedback = OnDepartureRequested.Execute(RequestedId);
}

void UColdSteelExpeditionWidget::SelectDestination(FName Id)
{
    SelectedId = Id;
    Feedback = FText::GetEmpty();
    RefreshDetail();
    RefreshPreparation();
    if (DetailScroll) DetailScroll->ScrollToStart();
    if (LayoutMode == 2) { CompactPage = 1; LayoutMode = -1; UpdateLayout(); }
}

void UColdSteelExpeditionWidget::UpdateSelectionStyles()
{
    for (auto& Button : CatalogButtons) Button.Value->SetButtonStyle(Button.Key == SelectedId ? &SelectedStyle : &NormalStyle);
    for (int32 Index = 0; Index < FilterButtons.Num(); ++Index) FilterButtons[Index]->SetButtonStyle(bAvailableOnly == (Index == 1) ? &SelectedStyle : &NormalStyle);
    for (int32 Index = 0; Index < DetailButtons.Num(); ++Index) DetailButtons[Index]->SetButtonStyle(DetailTab == Index ? &SelectedStyle : &NormalStyle);
    for (int32 Index = 0; Index < CompactButtons.Num(); ++Index) CompactButtons[Index]->SetButtonStyle(CompactPage == Index ? &SelectedStyle : &NormalStyle);
}

void UColdSteelExpeditionWidget::RefreshList()
{
    VisibleIds.Reset();
    for (const auto& Entry : Destinations)
    {
        if (Entry.Id.IsNone() || (bAvailableOnly && !Entry.bCanDepart)) continue;
        if (!Query.IsEmpty() && !Entry.Name.Contains(Query) && !Entry.Category.Contains(Query)) continue;
        VisibleIds.AddUnique(Entry.Id);
    }
    if (!VisibleIds.Contains(SelectedId)) SelectedId = VisibleIds.IsEmpty() ? NAME_None : VisibleIds[0];
    Feedback = FText::GetEmpty();
    if (!CatalogRows) { RefreshDetail(); RefreshPreparation(); return; }
    CatalogRows->ClearChildren();
    CatalogButtons.Reset();
    for (const FName Id : VisibleIds)
    {
        const auto* Entry = Destinations.FindByPredicate([Id](const auto& Item) { return Item.Id == Id; });
        if (!Entry) continue;
        const FString Status = Entry->bCanDepart ? TEXT("可出征") : TEXT("待开放");
        TSharedPtr<SButton> Button;
        CatalogRows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)
        [SAssignNew(Button, SButton).ButtonStyle(SelectedId == Id ? &SelectedStyle : &NormalStyle)
            .ContentPadding(14).HAlign(HAlign_Fill)
            .OnClicked_Lambda([this, Id]() { SelectDestination(Id); return FReply::Handled(); })
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(Entry->Category, 12, ColdSteelUI::TextTertiary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 12)[Label(Entry->Name, 16, ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight()[Label(Status, 12, Entry->bCanDepart ? ColdSteelUI::Success : ColdSteelUI::TextSecondary)]]];
        CatalogButtons.Add(Id, Button);
    }
    if (VisibleIds.IsEmpty())
    {
        CatalogRows->AddSlot().AutoHeight().Padding(0, 20)
            [Label(Destinations.IsEmpty() ? TEXT("暂无目的地") : TEXT("没有符合条件的目的地"), 16, ColdSteelUI::TextSecondary)];
        CatalogRows->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
            [Label(Destinations.IsEmpty() ? TEXT("新的目的地开放后将在这里显示。") : TEXT("尝试其他名称，或查看全部目的地。"), 12, ColdSteelUI::TextTertiary)];
        if (!Destinations.IsEmpty())
            CatalogRows->AddSlot().AutoHeight()[Action(TEXT("重置筛选"), [this]() {
                bAvailableOnly = false; Query.Reset();
                if (Search) Search->SetText(FText::GetEmpty());
                RefreshList();
            })];
    }
    RefreshDetail();
    RefreshPreparation();
}

void UColdSteelExpeditionWidget::RefreshDetail()
{
    UpdateSelectionStyles();
    if (!DetailRows) return;
    DetailRows->ClearChildren();
    const auto* Entry = Selection();
    if (!Entry)
    {
        DetailRows->AddSlot().AutoHeight().Padding(0, 24)[Label(TEXT("尚未选择目的地"), 20, ColdSteelUI::TextPrimary)];
        DetailRows->AddSlot().AutoHeight()[Label(TEXT("从目的地列表中选择一项，查看任务情报。"), 14, ColdSteelUI::TextSecondary)];
        return;
    }
    if (DetailTab == 0)
    {
        DetailRows->AddSlot().AutoHeight().Padding(0, 0, 0, 18)
            [Label(Entry->Description.IsEmpty() ? TEXT("暂无目的地描述") : Entry->Description, 14, ColdSteelUI::TextSecondary)];
        DetailRows->AddSlot().AutoHeight().Padding(0, 0, 0, 10)[Label(TEXT("任务概况"), 16, ColdSteelUI::TextPrimary)];
        DetailRows->AddSlot().AutoHeight()[Row(TEXT("推荐等级"), Entry->RecommendedLevel.IsEmpty() ? TEXT("待公布") : Entry->RecommendedLevel)];
        DetailRows->AddSlot().AutoHeight()[Row(TEXT("探索规模"), Entry->Scale.IsEmpty() ? TEXT("暂无情报") : Entry->Scale)];
        DetailRows->AddSlot().AutoHeight()[Row(TEXT("威胁情报"), Entry->Threat.IsEmpty() ? TEXT("暂无情报") : Entry->Threat)];
        DetailRows->AddSlot().AutoHeight()[Row(TEXT("进入消耗"), Entry->EntryCost.IsEmpty() ? TEXT("待公布") : Entry->EntryCost)];
        DetailRows->AddSlot().AutoHeight().Padding(0, 18, 0, 6)[Label(TEXT("行动提示"), 16, ColdSteelUI::TextPrimary)];
        DetailRows->AddSlot().AutoHeight()[Label(TEXT("出发前确认装备与补给；可在奖励和规则页查看目的地的详细说明。"), 14, ColdSteelUI::TextSecondary)];
    }
    else
    {
        const auto& Lines = DetailTab == 1 ? Entry->Rewards : Entry->Rules;
        DetailRows->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
            [Label(DetailTab == 1 ? TEXT("奖励情报") : TEXT("出征规则"), 16, ColdSteelUI::TextPrimary)];
        for (int32 Index = 0; Index < Lines.Num(); ++Index)
            DetailRows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)
                [Card(SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)[Label(FString::Printf(TEXT("%02d"), Index + 1), 12, ColdSteelUI::TextTertiary, true)]
                    +SVerticalBox::Slot().AutoHeight()[Label(Lines[Index], 14, ColdSteelUI::TextSecondary)])];
        if (Lines.IsEmpty())
            DetailRows->AddSlot().AutoHeight()[Card(Label(DetailTab == 1 ? TEXT("奖励情报待公布") : TEXT("进入条件与结算规则待公布"), 14, ColdSteelUI::TextSecondary), 20)];
    }
}

void UColdSteelExpeditionWidget::RefreshPreparation()
{
    if (!PreparationRows) return;
    PreparationRows->ClearChildren();
    auto* Model = Profile();
    auto Identity = SNew(SVerticalBox);
    Identity->AddSlot().AutoHeight()[Label(Model ? Model->CharacterName : TEXT("角色信息暂不可用"), 16, ColdSteelUI::TextPrimary)];
    if (Model)
    {
        Identity->AddSlot().AutoHeight().Padding(0, 6, 0, 12)[Label(Model->CharacterClass, 12, ColdSteelUI::TextSecondary)];
        Identity->AddSlot().AutoHeight()[Row(TEXT("等级"), FString::FromInt(Model->Level), true)];
        const auto* Weapon = Model->Equipped();
        Identity->AddSlot().AutoHeight()[Row(TEXT("当前武器"), Weapon ? ColdSteelInventory::Text(*Weapon, TEXT("name")) : TEXT("未装备"))];
    }
    PreparationRows->AddSlot().AutoHeight().Padding(0, 0, 0, 16)[Card(Identity)];
    PreparationRows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)[Label(TEXT("同行成员"), 16, ColdSteelUI::TextPrimary)];
    PreparationRows->AddSlot().AutoHeight().Padding(0, 0, 0, 18)
        [Card(Label(TEXT("队伍编成暂未开放"), 12, ColdSteelUI::TextTertiary))];
    PreparationRows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)[Label(TEXT("进入条件"), 16, ColdSteelUI::TextPrimary)];
    const auto* Entry = Selection();
    PreparationRows->AddSlot().AutoHeight()[Row(TEXT("目的地"), Entry ? Entry->Name : TEXT("尚未选择"))];
    PreparationRows->AddSlot().AutoHeight()[Row(TEXT("消耗"), Entry && !Entry->EntryCost.IsEmpty() ? Entry->EntryCost : TEXT("待公布"))];
    PreparationRows->AddSlot().AutoHeight().Padding(0, 12, 0, 0)
        [Label(Entry && !Entry->BlockReason.IsEmpty() ? Entry->BlockReason : TEXT("请在出发前查看任务情报。"), 12, ColdSteelUI::TextSecondary)];
}
