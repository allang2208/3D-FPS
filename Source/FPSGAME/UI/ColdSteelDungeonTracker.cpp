#include "ColdSteelDungeonTracker.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDLayout.h"
#include "StatusEffectsHUD.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/World.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Rendering/DrawElementTypes.h"

namespace
{
UTextBlock* TrackerText(UWidgetTree* Tree, float Pixels, FLinearColor Color, bool Bold = false, bool Numeric = false)
{
    auto* Text = Tree->ConstructWidget<UTextBlock>();
    Text->SetFont(Numeric ? ColdSteelUI::NumberFont(Pixels * .75f, Bold) : ColdSteelUI::TextFont(Pixels * .75f, Bold));
    Text->SetColorAndOpacity(Color);
    Text->SetAutoWrapText(false);
    Text->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);
    Text->SetShadowColorAndOpacity(FLinearColor(0, 0, 0, .8f));
    Text->SetShadowOffset(FVector2D(1, 1));
    return Text;
}

void SetTrackerText(UTextBlock* Label, const FText& Value, bool Optional = false)
{
    if (!Label->GetText().EqualTo(Value)) { Label->SetText(Value); Label->SetToolTipText(Value); }
    const auto Visibility = Optional && Value.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::Visible;
    if (Label->GetVisibility() != Visibility) Label->SetVisibility(Visibility);
}
}

void UColdSteelTrackedObjectiveRow::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    auto* Body = WidgetTree->ConstructWidget<UVerticalBox>();
    WidgetTree->RootWidget = Body;
    auto* Line = WidgetTree->ConstructWidget<UHorizontalBox>();
    Body->AddChildToVerticalBox(Line);
    Label = TrackerText(WidgetTree, 14, ColdSteelUI::TextPrimary);
    Line->AddChildToHorizontalBox(Label)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Counter = TrackerText(WidgetTree, 14, ColdSteelUI::HUDGoldLight, true, true);
    Line->AddChildToHorizontalBox(Counter)->SetPadding(FMargin(14, 0, 0, 0));
    Hint = TrackerText(WidgetTree, 12, ColdSteelUI::TextPrimary);
    Hint->SetAutoWrapText(true);
    Body->AddChildToVerticalBox(Hint)->SetPadding(FMargin(0, 4, 0, 0));
}

void UColdSteelTrackedObjectiveRow::ApplyView(const FTrackedObjectiveView& View, bool bNewInstance)
{
    const bool Same = bInitialized && !bNewInstance && Id == View.Id;
    if (!Same || State != View.State)
    {
        StrikeProgress = TaskTracking::InitialStrike(Same, State, View.State);
        State = View.State;
        const bool Complete = State == ETrackedObjectiveState::Completed;
        Label->SetColorAndOpacity(Complete ? ColdSteelUI::HUDGoldLight
            : State == ETrackedObjectiveState::Failed ? ColdSteelUI::Danger : ColdSteelUI::TextPrimary);
        Label->SetRenderOpacity(Complete ? .72f : 1.f);
        if (const auto Widget = GetCachedWidget()) Widget->Invalidate(EInvalidateWidgetReason::Paint);
    }
    Id = View.Id;
    bInitialized = true;
    SetTrackerText(Label, View.Text);
    const FString Progress = State == ETrackedObjectiveState::Failed ? TEXT("未达成")
        : View.Target > 0 ? FString::Printf(TEXT("%d / %d"), FMath::Clamp(View.Current, 0, View.Target), View.Target) : FString();
    SetTrackerText(Counter, FText::FromString(Progress), true);
    SetTrackerText(Hint, View.Hint, true);
}

void UColdSteelTrackedObjectiveRow::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    if (State != ETrackedObjectiveState::Completed || StrikeProgress >= 1.f) return;
    StrikeProgress = FMath::Min(1.f, StrikeProgress + DeltaTime / .45f);
    if (const auto Widget = GetCachedWidget()) Widget->Invalidate(EInvalidateWidgetReason::Paint);
}

int32 UColdSteelTrackedObjectiveRow::NativePaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Clip,
    FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool Enabled) const
{
    const int32 Result = Super::NativePaint(Args, Geometry, Clip, Out, Layer, Style, Enabled);
    if (State != ETrackedObjectiveState::Completed || StrikeProgress <= 0.f || !Label) return Result;
    const FGeometry& TextGeometry = Label->GetCachedGeometry();
    const FVector2D Size = TextGeometry.GetLocalSize();
    const double Width = FMath::Min(Size.X, Label->GetDesiredSize().X);
    if (Width <= 0 || Size.Y <= 0) return Result;
    const float Reveal = FMath::SmoothStep(0.f, 1.f, StrikeProgress);
    const TArray<FVector2D> Points = { FVector2D(0, Size.Y * .52), FVector2D(Width * Reveal, Size.Y * .52) };
    FSlateDrawElement::MakeLines(Out, Result + 1, TextGeometry.ToPaintGeometry(), Points, ESlateDrawEffect::None,
        ColdSteelUI::HUDGoldLight * Style.GetColorAndOpacityTint(), true, 1.25f);
    return Result + 1;
}

void UColdSteelTrackedTaskCard::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    auto* Column = WidgetTree->ConstructWidget<UHorizontalBox>();
    WidgetTree->RootWidget = Column;
    auto* RuleSize = WidgetTree->ConstructWidget<USizeBox>();
    RuleSize->SetWidthOverride(2);
    auto* Rule = WidgetTree->ConstructWidget<UBorder>();
    Rule->SetBrushColor(ColdSteelUI::HUDGold);
    RuleSize->SetContent(Rule);
    Column->AddChildToHorizontalBox(RuleSize)->SetPadding(FMargin(0, 3, 12, 0));
    auto* Body = WidgetTree->ConstructWidget<UVerticalBox>();
    Column->AddChildToHorizontalBox(Body)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Title = TrackerText(WidgetTree, 20, ColdSteelUI::HUDGoldLight, true);
    Body->AddChildToVerticalBox(Title);
    Area = TrackerText(WidgetTree, 16, ColdSteelUI::TextPrimary, true);
    Body->AddChildToVerticalBox(Area)->SetPadding(FMargin(0, 5, 0, 0));
    Stage = TrackerText(WidgetTree, 12, ColdSteelUI::HUDGold);
    Body->AddChildToVerticalBox(Stage)->SetPadding(FMargin(0, 3, 0, 0));
    Objectives = WidgetTree->ConstructWidget<UVerticalBox>();
    Body->AddChildToVerticalBox(Objectives)->SetPadding(FMargin(0, 2, 0, 0));
    Hint = TrackerText(WidgetTree, 12, ColdSteelUI::TextPrimary);
    Hint->SetAutoWrapText(true);
    Body->AddChildToVerticalBox(Hint)->SetPadding(FMargin(0, 6, 0, 0));
}

void UColdSteelTrackedTaskCard::ApplyView(const FTrackedTaskView& View)
{
    const bool NewInstance = Id != View.Id || InstanceId != View.InstanceId;
    Id = View.Id;
    InstanceId = View.InstanceId;
    SetTrackerText(Title, View.Title);
    SetTrackerText(Area, View.Area, true);
    SetTrackerText(Stage, View.Stage, true);
    SetTrackerText(Hint, View.Hint, true);
    TArray<TObjectPtr<UColdSteelTrackedObjectiveRow>> Next;
    for (const auto& Objective : View.Objectives)
    {
        const auto* Existing = Rows.FindByPredicate([&Objective](const auto& Row) { return Row->ObjectiveId() == Objective.Id; });
        auto* Row = Existing ? Existing->Get() : CreateWidget<UColdSteelTrackedObjectiveRow>(GetOwningPlayer());
        Row->ApplyView(Objective, NewInstance);
        Next.Add(Row);
    }
    if (Rows != Next)
    {
        Objectives->ClearChildren();
        for (auto& Row : Next) Objectives->AddChildToVerticalBox(Row)->SetPadding(FMargin(0, 8, 0, 0));
        Rows = MoveTemp(Next);
    }
}

void UColdSteelDungeonTracker::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    Root = WidgetTree->ConstructWidget<UCanvasPanel>();
    WidgetTree->RootWidget = Root;
    ListSize = WidgetTree->ConstructWidget<USizeBox>();
    ListSlot = Root->AddChildToCanvas(ListSize);
    ListSlot->SetAutoSize(true);
    ListSize->SetWidthOverride(384);
    ListSize->SetMaxDesiredHeight(400);
    ListSize->SetVisibility(ESlateVisibility::Collapsed);
    Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetAllowOverscroll(false);
    Scroll->SetAnimateWheelScrolling(true);
    Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible);
    Scroll->SetScrollBarVisibility(ESlateVisibility::Visible);
    Scroll->SetClipping(EWidgetClipping::ClipToBounds);
    ListSize->SetContent(Scroll);
    TaskList = WidgetTree->ConstructWidget<UVerticalBox>();
    Scroll->AddChild(TaskList);
}

TSharedRef<SWidget> UColdSteelDungeonTracker::RebuildWidget()
{
    return SNew(SDPIScaler).DPIScale_Lambda([this]
    { return 1.f / FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(this)); })[Super::RebuildWidget()];
}

void UColdSteelDungeonTracker::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    RefreshAge += DeltaTime;
    if (RefreshAge < .2f) return;
    RefreshAge = 0.f;
    RefreshTracking();
    if (!Cards.IsEmpty()) UpdatePlacement();
}

void UColdSteelDungeonTracker::RefreshTracking()
{
    TArray<FTrackedTaskView> Views;
    if (auto* Tracking = GetWorld()->GetSubsystem<UTaskTrackingSubsystem>()) Tracking->CollectTasks(GetOwningPlayerPawn(), Views);
    TArray<TObjectPtr<UColdSteelTrackedTaskCard>> Next;
    for (const auto& View : Views)
    {
        const auto* Existing = Cards.FindByPredicate([&View](const auto& Card) { return Card->TaskId() == View.Id; });
        auto* Card = Existing ? Existing->Get() : CreateWidget<UColdSteelTrackedTaskCard>(GetOwningPlayer());
        Card->ApplyView(View);
        Next.Add(Card);
    }
    if (Cards != Next)
    {
        const float PreviousOffset = Scroll->GetScrollOffset();
        TaskList->ClearChildren();
        for (auto& Card : Next) TaskList->AddChildToVerticalBox(Card)->SetPadding(FMargin(0, 0, 6, 18));
        Cards = MoveTemp(Next);
        Scroll->SetScrollOffset(Cards.IsEmpty() ? 0.f : PreviousOffset);
    }
    const auto ListVisibility = Cards.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::SelfHitTestInvisible;
    if (ListSize->GetVisibility() != ListVisibility) ListSize->SetVisibility(ListVisibility);
}

void UColdSteelDungeonTracker::UpdatePlacement()
{
    const FVector2D Viewport = UWidgetLayoutLibrary::GetViewportSize(this);
    const float Width = FMath::Min(384.f, FMath::Max(1.f, float(Viewport.X) - 24.f));
    float Top = 68.f;
    if (const auto* Status = GetWorld()->GetSubsystem<UStatusEffectsHUDSubsystem>())
        if (const auto* HUD = Status->GetHUD()) Top = FMath::Max(Top, HUD->OccupiedBottomPixels() + 12.f);
    const FColdSteelHUDLayout Layout(Viewport.X);
    const float CompassLeft = (Viewport.X - Layout.CompassWidth) * .5f;
    if (12.f + Width > CompassLeft && Top < Layout.TargetTop + 60.f && Top + 144.f > Layout.CompassTop)
        Top = Layout.TargetTop + 60.f;
    const float Height = FMath::Max(32.f, FMath::Min3(float(Viewport.Y) * .45f, float(Viewport.Y) - Top - 220.f,BottomBoundaryPixels-Top));
    const FVector2D Position(12, Top), Bounds(Width, Height);
    if (!LastPosition.Equals(Position, .1)) { ListSlot->SetPosition(Position); LastPosition = Position; }
    if (!LastBounds.Equals(Bounds, .1))
    {
        ListSize->SetWidthOverride(Width);
        ListSize->SetMaxDesiredHeight(Height);
        LastBounds = Bounds;
    }
}
