#include "ColdSteelQuestJournal.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDWidget.h"
#include "SExpeditionButton.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
void UpdateText(const TSharedPtr<STextBlock>& Label, const FText& Value)
{
    if (!Label->GetText().EqualTo(Value)) Label->SetText(Value);
}

bool SameSteps(const TArray<FTrackedObjectiveView>& A, const TArray<FTrackedObjectiveView>& B)
{
    if (A.Num() != B.Num()) return false;
    for (int32 I = 0; I < A.Num(); ++I)
    {
        const auto& L = A[I]; const auto& R = B[I];
        if (L.Id != R.Id || L.State != R.State || L.Current != R.Current || L.Target != R.Target ||
            !L.Text.EqualTo(R.Text) || !L.Hint.EqualTo(R.Hint)) return false;
    }
    return true;
}
}

TSharedRef<STextBlock> UColdSteelQuestJournal::Label(const FText& Text, float Pixels, FLinearColor Color, bool Medium, bool Wrap) const
{
    return SNew(STextBlock).Text(Text).Font(ColdSteelUI::TextFont(.75f * Pixels, Medium))
        .ColorAndOpacity(Color).AutoWrapText(Wrap);
}

TSharedRef<SWidget> UColdSteelQuestJournal::Section(const FText& Caption, TSharedRef<SWidget> Body) const
{
    return SNew(SBorder).BorderImage(&SectionBrush).Padding(FMargin(18,14))[
        SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[Label(Caption, 16, ColdSteelUI::HUDGoldLight, true)]
        + SVerticalBox::Slot().AutoHeight()[Body]
    ];
}

TSharedRef<SWidget> UColdSteelQuestJournal::RebuildWidget()
{
    CardStyle = ColdSteelUI::ButtonStyle();
    CardStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius));
    CardStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::CardRadius, ColdSteelUI::Accent));
    CardStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed, ColdSteelUI::CardRadius, ColdSteelUI::TextPrimary));
    QuietStyle = ColdSteelUI::ButtonStyle();
    SectionBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius);
    Rows.Reset();
    Instance.Reset();
    LastSteps.Reset();
    Title = Label(FText(), 23, ColdSteelUI::HUDGoldLight, true, true);
    Status = Label(FText(), 14, ColdSteelUI::TextSecondary, false, true);
    Introduction = Label(FText(), 16, ColdSteelUI::TextPrimary, false, true);
    Hint = Label(FText(), 14, ColdSteelUI::TextSecondary, false, true);
    Reward = Label(FText(), 16, ColdSteelUI::TextPrimary, false, true);
    TrackingCaption = Label(FText(), 14, ColdSteelUI::TextPrimary, true);

    auto Toolbar = SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth()[
            SAssignNew(ReturnButton,SExpeditionButton).ButtonStyle(&QuietStyle).ContentPadding(FMargin(14,8))
            .OnClicked_UObject(this,&ThisClass::ReturnClicked)[Label(INVTEXT("‹  任务列表"),14,ColdSteelUI::TextPrimary)]]
        + SHorizontalBox::Slot().FillWidth(1)[SNullWidget::NullWidget]
        + SHorizontalBox::Slot().AutoWidth()[
            SNew(SExpeditionButton).ButtonStyle(&QuietStyle).ContentPadding(FMargin(16,8))
            .OnClicked_UObject(this,&ThisClass::TrackClicked)[TrackingCaption.ToSharedRef()]];
    auto Detail = SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,14)[SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight)[Toolbar]]
        + SVerticalBox::Slot().FillHeight(1)[
            SAssignNew(DetailScroll,SScrollBox)
            + SScrollBox::Slot().Padding(2,0,8,4)[Title.ToSharedRef()]
            + SScrollBox::Slot().Padding(2,0,8,12)[Status.ToSharedRef()]
            + SScrollBox::Slot().Padding(0,0,6,8)[Section(INVTEXT("任务详情"),Introduction.ToSharedRef())]
            + SScrollBox::Slot().Padding(0,0,6,8)[Section(INVTEXT("任务步骤"),
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[SAssignNew(StepRows,SVerticalBox)]
                + SVerticalBox::Slot().AutoHeight()[Hint.ToSharedRef()])]
            + SScrollBox::Slot().Padding(0,0,6,4)[Section(INVTEXT("任务奖励"),Reward.ToSharedRef())]];
    return SNew(SDPIScaler).DPIScale_Lambda([this]{return 1.f / FMath::Max(.1f,UWidgetLayoutLibrary::GetViewportScale(this));})[
        SNew(SBox).Padding(FMargin(16,12))[
            SAssignNew(Pages,SWidgetSwitcher)
            + SWidgetSwitcher::Slot()[SAssignNew(ListScroll,SScrollBox)
                + SScrollBox::Slot().Padding(0,0,6,0)[SAssignNew(List,SVerticalBox)]]
            + SWidgetSwitcher::Slot()[Detail]]];
}

void UColdSteelQuestJournal::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    Rows.Reset(); Pages.Reset(); List.Reset(); StepRows.Reset(); ListScroll.Reset(); DetailScroll.Reset();
    ReturnButton.Reset(); Title.Reset(); Status.Reset(); Introduction.Reset(); Hint.Reset(); Reward.Reset(); TrackingCaption.Reset();
}

void UColdSteelQuestJournal::NativeConstruct()
{
    Super::NativeConstruct();
    if (auto* Source = GetWorld()->GetSubsystem<UTaskTrackingSubsystem>())
        Source->OnSelectionChanged.AddUObject(this, &ThisClass::RefreshTracking);
    OpenList();
}

void UColdSteelQuestJournal::NativeDestruct()
{
    if (auto* World = GetWorld())
        if (auto* Source = World->GetSubsystem<UTaskTrackingSubsystem>()) Source->OnSelectionChanged.RemoveAll(this);
    Super::NativeDestruct();
}

void UColdSteelQuestJournal::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    if (Transition < 1.f)
    {
        Transition = FMath::Min(1.f,Transition + Delta / .18f);
        const float Ease = ColdSteelUI::EaseSmooth(Transition);
        SetRenderOpacity(.65f + .35f * Ease);
        SetRenderTranslation(FVector2D(Direction * 12.f * (1.f-Ease) / ColdSteelUI::PixelScale(this),0));
    }
    RefreshAge += Delta;
    if (RefreshAge >= .2f) { RefreshAge = 0.f; RefreshTracking(); }
}

void UColdSteelQuestJournal::ClickSound() const
{
    if (const auto* PC = Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))
        if (auto* HUD = PC->GetColdSteelHUD()) HUD->PlayButtonClick();
}

void UColdSteelQuestJournal::AnimatePage(bool Forward)
{
    Transition = 0.f; Direction = Forward ? 1.f : -1.f;
    SetRenderOpacity(.65f);
    SetRenderTranslation(FVector2D(Direction * 12.f / ColdSteelUI::PixelScale(this),0));
}

void UColdSteelQuestJournal::OpenList()
{
    OpenId = NAME_None;
    if (!Pages) return;
    Pages->SetActiveWidgetIndex(0);
    Transition = 1.f; SetRenderOpacity(1); SetRenderTranslation(FVector2D::ZeroVector);
    RefreshTracking();
}

FReply UColdSteelQuestJournal::OpenTask(FName Id)
{
    OpenId = Id; Instance.Reset();
    RefreshTracking();
    if (OpenId.IsNone()) return FReply::Handled();
    Pages->SetActiveWidgetIndex(1);
    DetailScroll->ScrollToStart();
    ClickSound(); AnimatePage(true);
    return FReply::Handled().SetUserFocus(ReturnButton.ToSharedRef(),EFocusCause::SetDirectly);
}

bool UColdSteelQuestJournal::GoBack()
{
    if (OpenId.IsNone() || !Pages) return false;
    const FName Previous = OpenId;
    OpenList();
    ClickSound(); AnimatePage(false);
    for (const auto& Row : Rows)
        if (Row.Id == Previous)
        {
            ListScroll->ScrollDescendantIntoView(Row.Button,false,EDescendantScrollDestination::IntoView);
            FSlateApplication::Get().SetKeyboardFocus(Row.Button,EFocusCause::SetDirectly);
            break;
        }
    return true;
}

FReply UColdSteelQuestJournal::ReturnClicked(){ GoBack(); return FReply::Handled(); }

FReply UColdSteelQuestJournal::TrackClicked()
{
    if (!OpenId.IsNone())
        if (auto* Source = GetWorld()->GetSubsystem<UTaskTrackingSubsystem>())
        {
            ClickSound();
            Source->ToggleTask(OpenId);
        }
    return FReply::Handled();
}

void UColdSteelQuestJournal::RefreshTracking()
{
    if (!Pages || !IsVisible()) return;
    auto* Source = GetWorld()->GetSubsystem<UTaskTrackingSubsystem>();
    const auto* Pawn = GetOwningPlayerPawn();
    TArray<FTrackedTaskView> Views;
    if (Source) Source->CollectTasks(Pawn,Views,ETaskViewPurpose::Journal);
    const FName Tracked = Source ? Source->SelectedTask() : NAME_None;
    bool ListChanged = Rows.Num() != Views.Num();
    for (int32 I=0; !ListChanged && I<Rows.Num(); ++I) ListChanged = Rows[I].Id != Views[I].Id;
    if (ListChanged || (Views.IsEmpty() && List->NumSlots()==0))
    {
        List->ClearChildren(); Rows.Reset();
        if (Views.IsEmpty()) List->AddSlot().AutoHeight()[Label(INVTEXT("暂无任务记录"),14,ColdSteelUI::TextSecondary)];
        for (const auto& View : Views)
        {
            auto& Row = Rows.AddDefaulted_GetRef(); Row.Id = View.Id;
            Row.Name = Label(View.Title,19,ColdSteelUI::HUDGoldLight,true,true);
            Row.Tracking = Label(INVTEXT("追踪中"),13,ColdSteelUI::TextSecondary);
            Row.StateLabel = Label(FText(),13,ColdSteelUI::TextSecondary,true);
            List->AddSlot().AutoHeight().Padding(0,0,0,8)[
                SNew(SBox).MinDesiredHeight(60)[
                    SAssignNew(Row.Button,SExpeditionButton).ButtonStyle(&CardStyle).ContentPadding(FMargin(18,12)).HAlign(HAlign_Fill)
                    .OnClicked_UObject(this,&ThisClass::OpenTask,View.Id)[
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Row.Name.ToSharedRef()]
                        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8,0)[Row.Tracking.ToSharedRef()]
                        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,8,0)[Row.StateLabel.ToSharedRef()]
                        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(INVTEXT("›"),22,ColdSteelUI::TextSecondary)]]]];
        }
    }
    for (int32 I=0; I<Rows.Num(); ++I)
    {
        auto& Row = Rows[I];
        const auto& Task = Views[I];
        UpdateText(Row.Name,Task.Title);
        const auto TrackingVisibility = Row.Id == Tracked ? EVisibility::HitTestInvisible : EVisibility::Collapsed;
        if (Row.Tracking->GetVisibility()!=TrackingVisibility) Row.Tracking->SetVisibility(TrackingVisibility);
        if (Row.DisplayedState != Task.State)
        {
            Row.DisplayedState = Task.State;
            const bool Completed = Task.State == ETrackedTaskState::Completed;
            const FText Caption = Completed ? INVTEXT("已完成") :
                Task.State == ETrackedTaskState::InProgress ? INVTEXT("进行中") : FText();
            Row.StateLabel->SetText(Caption);
            Row.StateLabel->SetColorAndOpacity(Completed ? ColdSteelUI::Success : ColdSteelUI::HUDGoldLight);
            Row.Name->SetColorAndOpacity(Completed ? ColdSteelUI::TextSecondary : ColdSteelUI::HUDGoldLight);
            Row.Name->SetStrikeBrush(Completed ? FCoreStyle::Get().GetBrush("DefaultTextUnderline") : FStyleDefaults::GetNoBrush());
        }
    }
    if (OpenId.IsNone()) return;
    const auto* View = Views.FindByPredicate([this](const auto& V){return V.Id==OpenId;});
    if (!View) { OpenId = NAME_None; Pages->SetActiveWidgetIndex(0); return; }
    const auto Details = Source->JournalDetails(Pawn,*View);
    UpdateText(Title,View->Title);
    UpdateText(Status,FText::Format(INVTEXT("{0}  ·  {1}"),View->Area,View->Stage));
    UpdateText(Introduction,Details.Introduction.IsEmpty()?View->Title:Details.Introduction);
    UpdateText(Hint,View->Hint);
    Hint->SetVisibility(View->Hint.IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible);
    UpdateText(Reward,Details.Reward.IsEmpty()?INVTEXT("无固定任务奖励"):Details.Reward);
    UpdateText(TrackingCaption,Tracked==OpenId?INVTEXT("取消追踪"):INVTEXT("追踪任务"));
    if (Instance == View->InstanceId && SameSteps(LastSteps,Details.Steps)) return;
    Instance = View->InstanceId;
    LastSteps = Details.Steps;
    StepRows->ClearChildren();
    for (const auto& Step : LastSteps)
    {
        const bool Active = Step.State == ETrackedObjectiveState::Active;
        FText State = INVTEXT("待进行");
        FLinearColor Color = ColdSteelUI::TextTertiary;
        switch (Step.State)
        {
        case ETrackedObjectiveState::Active: State=INVTEXT("进行中"); Color=ColdSteelUI::HUDGoldLight; break;
        case ETrackedObjectiveState::Completed: State=INVTEXT("已完成"); Color=ColdSteelUI::Success; break;
        case ETrackedObjectiveState::Skipped: State=INVTEXT("已跳过"); break;
        case ETrackedObjectiveState::Failed: State=INVTEXT("未达成"); Color=ColdSteelUI::Danger; break;
        default: break;
        }
        const auto StepName = Label(Step.Text, 15, Active ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary, Active, true);
        if (Step.State == ETrackedObjectiveState::Completed)
            StepName->SetStrikeBrush(FCoreStyle::Get().GetBrush("DefaultTextUnderline"));

        const bool HasCounter = Step.Target > 0;
        const FText Counter = HasCounter ? FText::Format(INVTEXT("{0}/{1}"), Step.Current, Step.Target) : FText();
        StepRows->AddSlot().AutoHeight().Padding(0,2,0,8)[
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Top)[StepName]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Top).Padding(HasCounter ? 8.f : 0.f,0,0,0)[Label(Counter,14,Color)]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Top).Padding(12,0,0,0)[Label(State,13,Color,true)]];
        if (Active && !Step.Hint.IsEmpty() && !Step.Hint.EqualTo(View->Hint))
            StepRows->AddSlot().AutoHeight().Padding(0,0,0,10)[Label(Step.Hint,13,ColdSteelUI::TextSecondary,false,true)];
    }
}
