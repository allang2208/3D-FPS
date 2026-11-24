#pragma once

#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "../Tasks/TaskTrackingSubsystem.h"
#include "ColdSteelQuestJournal.generated.h"

class SButton;
class SScrollBox;
class STextBlock;
class SVerticalBox;
class SWidgetSwitcher;

UCLASS()
class FPSGAME_API UColdSteelQuestJournal : public UUserWidget
{
    GENERATED_BODY()
public:
    void RefreshTracking();
    bool GoBack();
    void OpenList();

protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;

private:
    TSharedRef<STextBlock> Label(const FText& Text, float Pixels, FLinearColor Color, bool Medium = false, bool Wrap = false) const;
    TSharedRef<SWidget> Section(const FText& Title, TSharedRef<SWidget> Content) const;
    FReply OpenTask(FName Id);
    FReply ReturnClicked();
    FReply TrackClicked();
    void AnimatePage(bool Forward);
    void ClickSound() const;

    struct FListRow
    {
        FName Id;
        TSharedPtr<SButton> Button;
        TSharedPtr<STextBlock> Name, Tracking, StateLabel;
        ETrackedTaskState DisplayedState = ETrackedTaskState::NotStarted;
    };
    TArray<FListRow> Rows;
    TSharedPtr<SWidgetSwitcher> Pages;
    TSharedPtr<SVerticalBox> List, StepRows;
    TSharedPtr<SScrollBox> ListScroll, DetailScroll;
    TSharedPtr<SButton> ReturnButton;
    TSharedPtr<STextBlock> Title, Status, Introduction, Hint, Reward, TrackingCaption;
    FButtonStyle CardStyle, QuietStyle;
    FSlateBrush SectionBrush;
    FName OpenId;
    FString Instance;
    TArray<FTrackedObjectiveView> LastSteps;
    float RefreshAge = 0.f, Transition = 1.f, Direction = 1.f;
};
