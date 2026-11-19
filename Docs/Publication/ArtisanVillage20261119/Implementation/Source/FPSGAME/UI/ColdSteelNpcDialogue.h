#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "SColdSteelSkillTreeCanvas.h"
#include "ColdSteelTreePanel.h"
#include "ColdSteelNpcDialogue.generated.h"
class UChapelDialogueComponent;
class SBox;
class SButton;
class STextBlock;
class SColdSteelNpcSpeech;
namespace ColdSteelMerchantDialogue { struct FSpeaker; }

/** Cold Steel conversation, shared village construction tree and trainer page. */
UCLASS()
class FPSGAME_API UColdSteelNpcDialogue : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UChapelDialogueComponent* Owner);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void ReleaseSlateResources(bool ReleaseChildren) override;
    virtual FReply NativeOnFocusReceived(const FGeometry& Geometry, const FFocusEvent& Event) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply NativeOnMouseButtonDoubleClick(const FGeometry& Geometry, const FPointerEvent& Event) override;
private:
    TWeakObjectPtr<UChapelDialogueComponent> Conversation;
    FDelegateHandle Changed;
    ColdSteelTreePanel::FStyle TreeStyle;
    UPROPERTY(Transient) TMap<FName,FSlateBrush> VillageIcons;
    TSharedPtr<SBox> FrameHost,Content,Detail;
    TSharedPtr<SColdSteelSkillTreeCanvas> Tree;
    TSharedPtr<SColdSteelNpcSpeech> Speech;
    TSharedPtr<SButton> DefaultChoice, LessonButton, ReturnButton, TrainingRetry;
    TSharedPtr<STextBlock> FeedbackText, LessonReason, LessonLabel, TrainingProgress;
    int32 Page=0;
    bool bHeardNunIntro=false;
    int32 LastTopic=1;
    int32 MerchantTopicIndex=0;
    int32 LastMerchantChoice=1;
    FName Selected=TEXT("wall");
    FName Group;
    FString Query;
    void Refresh();
    void ShowPage(int32 NewPage);
    void ChooseMerchantAction(int32 Choice);
    void ChooseMerchantTopic(int32 Index);
    void RequestArtisanTraining();
    void ReturnToParentPage();
    void ResetPageWidgets();
    void FocusPage();
    TSharedRef<SWidget> Dialogue();
    TSharedRef<SWidget> DialogueFrame();
    TSharedRef<SWidget> MerchantDialogue(const ColdSteelMerchantDialogue::FSpeaker& Speaker);
    TSharedRef<SWidget> ArtisanLesson();
    void RefreshArtisanLesson();
    TSharedRef<SWidget> Village();
    TSharedRef<SWidget> VillageHeader();
    TSharedRef<SWidget> VillageDetail();
    void RelayoutVillage();
    TSharedRef<SWidget> Magic();
    SColdSteelSkillTreeCanvas::FSource VillageSource() const;
};
