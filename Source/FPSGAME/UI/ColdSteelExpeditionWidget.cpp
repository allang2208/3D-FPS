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
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SGridPanel.h"
#include "Widgets/Text/STextBlock.h"

UColdSteelStatusModel* UColdSteelExpeditionWidget::Profile() const
{
    return GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}

void UColdSteelExpeditionWidget::SetDestinations(TArray<FColdSteelExpeditionDestination> Entries)
{
    Destinations = MoveTemp(Entries);
    if(Destinations.Num()<=1){Query.Reset();bAvailableOnly=false;}
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
    bClosing=false;
    RefreshPreparationData();
    if (auto* Model = Profile())
        ProfileHandle = Model->OnChanged.AddUObject(this, &ThisClass::RefreshPreparationData);
    RefreshList();
    RefreshPreparation();
}

void UColdSteelExpeditionWidget::NativeDestruct()
{
    bClosing=true;
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
    if (Destinations.Num()>1 && Event.IsControlDown() && Event.GetKey() == EKeys::F && Search.IsValid())
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
    return FText::FromString(TEXT("满足进入条件"));
}

void UColdSteelExpeditionWidget::ConfirmDeparture()
{
    if (!CanConfirm()) return;
    const FName RequestedId = SelectedId;
    Feedback = OnDepartureRequested.Execute(RequestedId);
    // Travel closes the panel before OpenLevel; the widget may already be torn down.
    if (!IsValid(this)) return;
    if (Feedback.IsEmpty()) Close();
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
