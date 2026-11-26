#include "ColdSteelNpcDialogue.h"
#include "ColdSteelTextToolTip.h"
#include "SSiegeWorkshopMarket.h"
#include "ColdSteelNpcDialogueArtisans.h"
#include "ColdSteelNpcDialogueSpeech.h"
#include "ColdSteelUIStyle.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../Tasks/BlacksmithLessonText.h"
#include "../Tasks/CarpenterLessonText.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "InputCoreTypes.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

using namespace ColdSteelUI;

namespace
{
constexpr int32 MainPage = 0, VillagePage = 1, HolyLightPage = 2;
constexpr int32 MerchantTopicsPage = 3, MerchantStoryPage = 4, ArtisanLessonPage = 5;
constexpr int32 MerchantFollowUpPage = 6, WorkshopPage = 7;

using ColdSteelMerchantDialogue::FSpeaker;
constexpr int32 MerchantTopicCount = FSpeaker::TopicCount;

const FSpeaker* MerchantSpeaker(const UChapelDialogueComponent* Conversation)
{
    if (Conversation && Conversation->IsMasterArtisan()) return &ColdSteelMerchantDialogue::MasterArtisan;
    if (Conversation && Conversation->IsBlacksmith()) return &ColdSteelMerchantDialogue::Blacksmith;
    if (Conversation && Conversation->IsCarpenter()) return &ColdSteelMerchantDialogue::Carpenter;
    if (Conversation && Conversation->IsBaker()) return &ColdSteelMerchantDialogue::Baker;
    if (Conversation && Conversation->IsMillKeeper()) return &ColdSteelMerchantDialogue::MillKeeper;
    if (Conversation && Conversation->IsTavernKeeper()) return &ColdSteelMerchantDialogue::TavernKeeper;
    if (Conversation && Conversation->IsHerbalist()) return &ColdSteelMerchantDialogue::Herbalist;
    return nullptr;
}

const TCHAR* const Lines[] = {
    TEXT("你也看见那些空屋了吧。这里曾经住着许多人，傍晚能听见铁锤声，也能闻到面包的香气。如今围墙塌了，炉火熄了，年轻人带着家人陆续离开，留下的也越来越少。"),
    TEXT("我守着这座教堂，并不是在等过去回来。只要还有人愿意修好一段墙、点亮一盏灯，这里就还有重新成为家园的机会。先让村庄安全起来，再让铁匠铺开工，离开的人才会愿意回来。"),
    TEXT("如果你愿意帮忙，我们就从修复围墙和铁匠铺开始。你也可以向我学习圣光——它能救助受伤的人，也能让你在黑暗中多一分守护他人的力量。你想从哪里开始？")
};

TSharedRef<STextBlock> Label(const FString& Value, float Px, const FLinearColor& Color, bool Medium = false, bool Wrap = false)
{
    return SNew(STextBlock)
        .Text(FText::FromString(Value)).Font(TextFont(Px * .75f, Medium))
        .ColorAndOpacity(Color).AutoWrapText(Wrap).LineHeightPercentage(Wrap ? 1.35f : 1.f);
}

TSharedRef<SWidget> Rule(const FLinearColor& Color)
{
    return SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(Color).Padding(0).Visibility(EVisibility::HitTestInvisible);
}

TSharedRef<SButton> DialogueButton(const FButtonStyle& Style, TSharedRef<STextBlock> Caption,
    const FString& Shortcut, TFunction<void()> OnClick, bool bShortcutFirst = false)
{
    auto Button = SNew(SButton).ButtonStyle(&Style).HAlign(HAlign_Fill).ContentPadding(0)
        .OnClicked_Lambda([Click = MoveTemp(OnClick)] { Click(); return FReply::Handled(); });
    // Revealing a sentence can uncover this button between the two presses.
    // Slate normally treats the double-click as another button down.
    Button->SetOnMouseDoubleClick(FPointerEventHandler::CreateLambda([](const FGeometry&, const FPointerEvent& Event)
    {
        return Event.GetEffectingButton() == EKeys::LeftMouseButton ? FReply::Handled() : FReply::Unhandled();
    }));
    const TWeakPtr<SButton> WeakButton = Button;
    auto ButtonContent = SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Fill).Padding(2, 6, 0, 6)
        [SNew(SBox).WidthOverride(2).Visibility_Lambda([WeakButton]
            {
                const auto Target = WeakButton.Pin();
                return Target && Target->HasAnyUserFocus() ? EVisibility::HitTestInvisible : EVisibility::Hidden;
            })[Rule(HUDGoldLight)]];
    if (bShortcutFirst)
    {
        ButtonContent->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(10, 0, 0, 0)
            [SNew(STextBlock).Text(FText::FromString(Shortcut)).Font(NumberFont(14 * .75f)).ColorAndOpacity(HUDGoldLight)];
    }
    ButtonContent->AddSlot().FillWidth(1).VAlign(VAlign_Center).Padding(bShortcutFirst ? 8 : 10, 0, 12, 0)[Caption];
    if (!bShortcutFirst && !Shortcut.IsEmpty())
    {
        ButtonContent->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
            [SNew(STextBlock).Text(FText::FromString(Shortcut)).Font(NumberFont(12 * .75f)).ColorAndOpacity(HUDGoldLight)];
    }
    Button->SetContent(SNew(SBox).MinDesiredHeight(ActionHeight)[ButtonContent]);
    return Button;
}

int32 NumberChoice(const FKey& Key)
{
    if (Key == EKeys::One || Key == EKeys::NumPadOne) return 1;
    if (Key == EKeys::Two || Key == EKeys::NumPadTwo) return 2;
    if (Key == EKeys::Three || Key == EKeys::NumPadThree) return 3;
    if (Key == EKeys::Four || Key == EKeys::NumPadFour) return 4;
    return 0;
}

TSharedRef<SWidget> Footer(TSharedRef<SWidget> Actions)
{
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(1)[Rule(Border)]]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 0)[Actions];
}

TSharedRef<SWidget> ForgeAimExample(bool Aligned)
{
    // The forge renders a shrinking blue target and a smaller, pale player-controlled ring.
    static const FSlateBrush TargetRing=RoundedBrush(FLinearColor::Transparent,14.f,FLinearColor(.015f,.65f,1.f),2.f);
    static const FSlateBrush AimRing=RoundedBrush(FLinearColor::Transparent,6.f,FLinearColor(.88f,.94f,1.f),1.5f);
    return SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [SNew(SBox).WidthOverride(64).HeightOverride(36)
            [SNew(SOverlay)
                + SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Center).Padding(0,0,8,0)
                [SNew(SBox).WidthOverride(28).HeightOverride(28)[SNew(SBorder).BorderImage(&TargetRing)]]
                + SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Center).Padding(0,0,Aligned?16.f:45.f,0)
                [SNew(SBox).WidthOverride(12).HeightOverride(12)[SNew(SBorder).BorderImage(&AimRing)]]]]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [Label(Aligned?TEXT("两圈对准，单击左键"):TEXT("移动白圈，对准蓝色热区"),14,TextSecondary)];
}
}

void UColdSteelNpcDialogue::Configure(UChapelDialogueComponent* Owner)
{
    Conversation = Owner;
    SetIsFocusable(true);
}

void UColdSteelNpcDialogue::NativeConstruct()
{
    Super::NativeConstruct();
    if (Conversation.IsValid())
    {
        Changed = Conversation->OnChanged.AddUObject(this, &UColdSteelNpcDialogue::Refresh);
    }
}

void UColdSteelNpcDialogue::NativeDestruct()
{
    if (Speech) Speech->Stop();
    if (Conversation.IsValid()) Conversation->OnChanged.Remove(Changed);
    Changed.Reset();
    Super::NativeDestruct();
}

void UColdSteelNpcDialogue::ResetPageWidgets()
{
    if (Speech) Speech->Stop();
    Speech.Reset();
    Content.Reset();
    Detail.Reset();
    Tree.Reset();
    DefaultChoice.Reset();
    LessonButton.Reset();
    ReturnButton.Reset();
    FeedbackText.Reset();
    LessonReason.Reset();
    LessonLabel.Reset();
    TrainingRetry.Reset();
    TrainingProgress.Reset();
    WorkshopMarket.Reset();
}

void UColdSteelNpcDialogue::ReleaseSlateResources(bool ReleaseChildren)
{
    ResetPageWidgets();
    FrameHost.Reset();
    Super::ReleaseSlateResources(ReleaseChildren);
}

TSharedRef<SWidget> UColdSteelNpcDialogue::RebuildWidget()
{
    TreeStyle.Initialize();
    auto Root = SAssignNew(FrameHost, SBox);
    Refresh();
    return Root;
}

TSharedRef<SWidget> UColdSteelNpcDialogue::DialogueFrame()
{
    const FSpeaker* Speaker = MerchantSpeaker(Conversation.Get());
    const TCHAR* Subject = Speaker ? Speaker->Workshop : TEXT("留下的人");
    if (Page == HolyLightPage) Subject = TEXT("圣光传授");
    else if (Page == MerchantTopicsPage) Subject = TEXT("闲聊");
    else if (Page == MerchantStoryPage && Speaker) Subject = Speaker->Topics[MerchantTopicIndex].Title;
    else if (Page == MerchantFollowUpPage && Speaker) Subject = Speaker->Topics[MerchantTopicIndex].FollowUp;
    else if (Page == ArtisanLessonPage && Speaker) Subject = Speaker->Lesson;
    const auto Exit = DialogueButton(TreeStyle.Quiet, Label(TEXT("离开"), 14, TextSecondary),
        Page == MainPage ? TEXT("Esc") : TEXT(""), [this] { if (Conversation.IsValid()) Conversation->Close(); });
    const auto Body = Speaker ? (Page == ArtisanLessonPage ? ArtisanLesson() : MerchantDialogue(*Speaker))
        : (Page == HolyLightPage ? Magic() : Dialogue());

    auto Card = SNew(SBackgroundBlur)
        .BlurStrength(GlassBlurStrength).BlurRadius(GlassBlurRadius)
        .CornerRadius(FVector4(PanelRadius)).LowQualityFallbackBrush(&TreeStyle.FallbackBrush)
        [SNew(SBorder).BorderImage(&TreeStyle.GlassBrush).Padding(FMargin(22, 10, 22, 14))
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)
                    [SNew(SBox).WidthOverride(3).HeightOverride(20)[Rule(HUDGold)]]
                    + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [Label(Speaker ? Speaker->Name : TEXT("教堂修女"), 24, HUDGoldLight, true)]
                    + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(14, 0)
                    [SNew(SBox).WidthOverride(1).HeightOverride(14)[Rule(Border)]]
                    + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                    [Label(Subject, 14, TextSecondary)]
                    + SHorizontalBox::Slot().AutoWidth()[Exit]]
                + SVerticalBox::Slot().FillHeight(1).Padding(0, 6, 0, 0)
                [SAssignNew(Content, SBox)[Body]]]];

    const TWeakObjectPtr<UColdSteelNpcDialogue> WeakOwner(this);
    const bool bLesson = Page == ArtisanLessonPage || Page == HolyLightPage;
    return SNew(SDPIScaler).DPIScale_Lambda([WeakOwner]
        {
            if (!WeakOwner.IsValid()) return 1.f;
            const FVector2D Size = UWidgetLayoutLibrary::GetViewportSize(WeakOwner.Get());
            // Keep the usual text size; scale the whole conversation together in very small windows.
            const float CompactScale = Size.X > 0 && Size.Y > 0
                ? FMath::Min3(1.f, float(Size.X / 640.f), float(Size.Y / 420.f)) : 1.f;
            return CompactScale / FMath::Max(.1f, PixelScale(WeakOwner.Get()));
        })
        [SNew(SOverlay).Visibility(EVisibility::Visible)
            + SOverlay::Slot().HAlign(HAlign_Fill).VAlign(VAlign_Bottom)
            [SNew(SBox).MinDesiredHeight_Lambda([WeakOwner, bLesson]
                {
                    const float ViewHeight = WeakOwner.IsValid() ? UWidgetLayoutLibrary::GetViewportSize(WeakOwner.Get()).Y : 0.f;
                    const float Height = ViewHeight > 0.f ? ViewHeight : 900.f;
                    return FOptionalSize(bLesson ? FMath::Clamp(Height * .37f, 285.f, 400.f)
                        : FMath::Clamp(Height * .31f, 245.f, 335.f));
                })[Card]]
            // During reveal, both normal clicks and Slate's separate double-click route
            // hit this surface. Buttons underneath never get a down/up pair from a skip.
            + SOverlay::Slot()[SNew(SBox).Visibility_Lambda([WeakSpeech = TWeakPtr<SColdSteelNpcSpeech>(Speech)]
                {
                    const auto Active = WeakSpeech.Pin();
                    return Active && Active->IsRevealing() ? EVisibility::Visible : EVisibility::Collapsed;
                })]];
}

void UColdSteelNpcDialogue::ShowPage(int32 NewPage)
{
    if ((Page == VillagePage || Page == HolyLightPage) && NewPage == MainPage) LastTopic = Page;
    Page = NewPage;
    ResetPageWidgets();
    Query.Reset();
    Group = NAME_None;
    Refresh();
    FocusPage();
}

void UColdSteelNpcDialogue::Refresh()
{
    if (!FrameHost) return;
    if (Page == WorkshopPage)
    {
        if(WorkshopMarket)WorkshopMarket->Refresh();
        else FrameHost->SetContent(Workshop());
        return;
    }
    if (Page == VillagePage)
    {
        if (Tree && Detail)
        {
            Tree->SetSource(VillageSource());
            Detail->SetContent(VillageDetail());
        }
        else FrameHost->SetContent(Village());
        return;
    }
    const bool AdvanceSmithLesson = Content && Page == ArtisanLessonPage && Conversation.IsValid()
        && !Conversation->IsCarpenter() && PresentedSmithStep != Conversation->SmithTrainingStage();
    if (AdvanceSmithLesson) ResetPageWidgets();
    if (!Content) FrameHost->SetContent(DialogueFrame());
    if (AdvanceSmithLesson) FocusPage();

    if (FeedbackText)
    {
        const FString Feedback = !Conversation.IsValid() ? FString()
            : Page == ArtisanLessonPage ? Conversation->Message
            : Page == HolyLightPage ? Conversation->NunActionMessage(TEXT("holyLight")) : FString();
        FeedbackText->SetText(FText::FromString(Feedback));
        FeedbackText->SetVisibility(Feedback.IsEmpty() ? EVisibility::Collapsed : EVisibility::HitTestInvisible);
    }
    if (Page == ArtisanLessonPage)
    {
        RefreshArtisanLesson();
        return;
    }
    if (LessonButton)
    {
        FString Reason;
        const bool bEligible = Conversation.IsValid() && Conversation->CanLearnHolyLight(Reason);
        const bool bLearned = Conversation.IsValid() && Conversation->HolyLightLearned();
        const bool bPending = Conversation.IsValid() && Conversation->IsPending();
        const bool bEnabled = bEligible && !bPending && !bLearned;
        const bool bMoveFocus = !bEnabled && LessonButton->HasAnyUserFocus();
        LessonReason->SetText(FText::FromString(Reason));
        LessonLabel->SetText(FText::FromString(bLearned ? TEXT("已习得圣光") : bPending ? TEXT("正在确认…") : TEXT("接受圣光传授")));
        LessonButton->SetEnabled(bEnabled);
        DefaultChoice = bEnabled ? LessonButton : ReturnButton;
        if (bMoveFocus) FocusPage();
    }
}

TSharedRef<SWidget> UColdSteelNpcDialogue::Dialogue()
{
    TArray<FColdSteelSpokenPassage> Passages;
    if (bHeardNunIntro) Passages.Add({TEXT("你想从哪里开始？")});
    else for (const TCHAR* Text : Lines) Passages.Add({Text});

    const auto First = DialogueButton(TreeStyle.Muted, Label(TEXT("建设村庄"), 16, TextPrimary, true), TEXT("1"),
        [this] { ShowPage(VillagePage); });
    const auto Second = DialogueButton(TreeStyle.Muted, Label(TEXT("学习魔法"), 16, TextPrimary, true), TEXT("2"),
        [this] { ShowPage(HolyLightPage); });
    DefaultChoice = LastTopic == HolyLightPage ? Second : First;
    const auto Actions = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(ActionGap, ActionGap))
        .Visibility(bHeardNunIntro ? EVisibility::Visible : EVisibility::Collapsed)
        + SWrapBox::Slot()[SNew(SBox).WidthOverride(194)[First]]
        + SWrapBox::Slot()[SNew(SBox).WidthOverride(194)[Second]];

    return SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1).Padding(0, 0, 0, 6)
        [SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[SAssignNew(Speech, SColdSteelNpcSpeech).Passages(MoveTemp(Passages))
                .OnFinished(FSimpleDelegate::CreateWeakLambda(this, [this, WeakActions = TWeakPtr<SWrapBox>(Actions)]
                {
                    if (bHeardNunIntro) return;
                    bHeardNunIntro = true;
                    if (const auto Choices = WeakActions.Pin()) Choices->SetVisibility(EVisibility::Visible);
                    FocusPage();
                }))]
            + SVerticalBox::Slot().AutoHeight()
            [SAssignNew(FeedbackText, STextBlock).Font(TextFont(14 * .75f)).AutoWrapText(true).ColorAndOpacity(HUDGoldLight)]]
        + SVerticalBox::Slot().AutoHeight()[Footer(Actions)];
}

TSharedRef<SWidget> UColdSteelNpcDialogue::Workshop()
{
    const TWeakObjectPtr<UColdSteelNpcDialogue> Owner(this);
    return SNew(SDPIScaler).DPIScale_Lambda([Owner]
        {
            // Keep text readable on small screens, retaining native enlargement above 1080p.
            return Owner.IsValid()?1.f/FMath::Clamp(PixelScale(Owner.Get()),.1f,1.f):1.f;
        })
        [SAssignNew(WorkshopMarket,SSiegeWorkshopMarket).Conversation(Conversation.Get())
            .OnBack(FSimpleDelegate::CreateWeakLambda(this,[this]
            {
                if(Page!=WorkshopPage)return;
                bResumeWorkshopGreeting=true;
                ShowPage(MainPage);
            }))];
}

void UColdSteelNpcDialogue::ChooseMerchantAction(int32 Choice)
{
    const FSpeaker* Speaker = MerchantSpeaker(Conversation.Get());
    if (!Speaker || Page != MainPage || Choice < 1 || Choice > Speaker->MainChoiceCount()) return;
    if (Choice == 3 && !Speaker->Lesson) return;
    LastMerchantChoice = Choice;
    switch (Choice)
    {
    case 1: ShowPage(MerchantTopicsPage); break;
    case 2:
        if(Conversation->IsMasterArtisan())ShowPage(WorkshopPage);
        else Conversation->TradeWithMerchant();
        break;
    case 3:
        ShowPage(ArtisanLessonPage);
        break;
    }
}

void UColdSteelNpcDialogue::RequestArtisanTraining()
{
    if (!Conversation.IsValid()) return;
    if (Conversation->IsCarpenter()) Conversation->RequestCarpenterTraining();
    else if (Conversation->IsBlacksmith()) Conversation->RequestSmithTraining();
}

void UColdSteelNpcDialogue::ChooseMerchantTopic(int32 Index)
{
    if (Page != MerchantTopicsPage || Index < 0 || Index >= MerchantTopicCount) return;
    MerchantTopicIndex = Index;
    ShowPage(MerchantStoryPage);
}

void UColdSteelNpcDialogue::ReturnToParentPage()
{
    if(Page==WorkshopPage && WorkshopMarket){WorkshopMarket->RequestClose();return;}
    if (Page == MainPage)
    {
        if (Conversation.IsValid()) Conversation->Close();
        return;
    }
    if (Page == MerchantFollowUpPage) ShowPage(MerchantStoryPage);
    else if (Page == MerchantStoryPage) ShowPage(MerchantTopicsPage);
    else ShowPage(MainPage);
}

TSharedRef<SWidget> UColdSteelNpcDialogue::MerchantDialogue(const FSpeaker& Speaker)
{
    const bool bMain = Page == MainPage;
    const bool bTopics = Page == MerchantTopicsPage;
    const auto& Topic = Speaker.Topics[MerchantTopicIndex];
    const TCHAR* Reply = bMain ? Speaker.Greeting : bTopics ? Speaker.TopicPrompt :
        Page == MerchantFollowUpPage ? Topic.FollowUpReply : Topic.Reply;
    auto DialogueBody = SNew(SVerticalBox);
    if(bMain && Conversation->IsMasterArtisan() && bResumeWorkshopGreeting)
    {
        bResumeWorkshopGreeting=false;
        DialogueBody->AddSlot().AutoHeight()[Label(TEXT("图纸收好了。还想看看哪一项？"),18,TextPrimary,false,true)];
    }
    else DialogueBody->AddSlot().AutoHeight()[SAssignNew(Speech,SColdSteelNpcSpeech).Passages(TArray<FColdSteelSpokenPassage>{{Reply}})];
    auto Actions = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(ActionGap, ActionGap));

    if (bMain || bTopics)
    {
        const TCHAR* const MainChoices[] = {Speaker.ChatLabel, Speaker.TradeLabel, Conversation->IsBlacksmith()?TEXT("修炼技能"):TEXT("学习技能")};
        auto Choices = bMain ? Actions : SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(ActionGap, ActionGap));
        const int32 Count = bMain ? Speaker.MainChoiceCount() : MerchantTopicCount;
        for (int32 Index = 0; Index < Count; ++Index)
        {
            const TCHAR* Caption = bMain ? MainChoices[Index] : Speaker.Topics[Index].Title;
            const auto Choice = DialogueButton(TreeStyle.Muted,
                Label(Caption, 16, TextPrimary, true),
                FString::FromInt(Index + 1), [this, bMain, Index]
                {
                    if (bMain) ChooseMerchantAction(Index + 1);
                    else ChooseMerchantTopic(Index);
                }, true);
            const auto ChoiceBox = SNew(SBox).MinDesiredWidth(bMain ? 108.f : 134.f)[Choice];
            if (bMain && Index == 2 && !Speaker.Lesson)
            {
                Choice->SetEnabled(false);
                ChoiceBox->SetVisibility(EVisibility::Visible);
                ColdSteelToolTip::Set(*ChoiceBox, FText::FromString(Speaker.UnavailableLessonHint));
            }
            Choices->AddSlot()[ChoiceBox];
            if (Index == (bMain ? LastMerchantChoice - 1 : MerchantTopicIndex)) DefaultChoice = Choice;
        }
        if (bTopics) DialogueBody->AddSlot().AutoHeight().Padding(0, 12, 0, 0)[Choices];
    }
    if (!bMain)
    {
        if (Page == MerchantStoryPage && Topic.FollowUp)
        {
            DefaultChoice = DialogueButton(TreeStyle.Muted, Label(Topic.FollowUp, 16, TextPrimary, true),
                TEXT("1"), [this] { ShowPage(MerchantFollowUpPage); }, true);
            Actions->AddSlot()[DefaultChoice.ToSharedRef()];
        }
        const TCHAR* Back = Page == MerchantFollowUpPage ? TEXT("返回上一问") : bTopics ? TEXT("返回交谈") : TEXT("返回话题");
        ReturnButton = DialogueButton(TreeStyle.Quiet, Label(Back, 14, TextSecondary),
            TEXT("Esc"), [this] { ReturnToParentPage(); });
        Actions->AddSlot()[SNew(SBox).MinDesiredWidth(126)[ReturnButton.ToSharedRef()]];
        if (!DefaultChoice) DefaultChoice = ReturnButton;
    }
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1).Padding(0, 0, 0, 6)[DialogueBody]
        + SVerticalBox::Slot().AutoHeight()[Footer(Actions)];
}

TSharedRef<SWidget> UColdSteelNpcDialogue::ArtisanLesson()
{
    TArray<FColdSteelSpokenPassage> Passages;
    const bool bCarpenter = Conversation.IsValid() && Conversation->IsCarpenter();
    const int32 Stage = Conversation.IsValid()
        ? (bCarpenter ? Conversation->CarpenterTrainingStage() : Conversation->SmithTrainingStage()) : 0;
    if (!bCarpenter) PresentedSmithStep = Stage;
    const int32 CompleteStep = bCarpenter ? 4 : 7;
    if (Stage == CompleteStep)
    {
        Passages.Add({bCarpenter ? TEXT("长杖是你亲手锯出来的。往后每做一件，记住上回哪一锯最顺。")
                                : TEXT("好剑，收好！往后听见这铺子里有锤声，就进来坐坐。")});
    }
    else if (bCarpenter)
    {
        Passages = {
            {CarpenterLessonText::Quality(), TEXT("木芯与成品品质")},
            {CarpenterLessonText::Materials(), TEXT("第一步　备料")},
            {CarpenterLessonText::Working(), TEXT("第二步　上台切割")},
            {CarpenterLessonText::Finish(), TEXT("第三步　收尾")}
        };
    }
    else
    {
        auto AimGuide = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(24,2))
            + SWrapBox::Slot()[ForgeAimExample(false)]
            + SWrapBox::Slot()[ForgeAimExample(true)];
        Passages = {
            {BlacksmithLessonText::Quality(), TEXT("成品品质")},
            {BlacksmithLessonText::Mining(), TEXT("采矿教程　寻找露天铁矿脉")},
            {BlacksmithLessonText::Delivery(), TEXT("采矿教程　回店交矿")},
            {BlacksmithLessonText::Smelting(), TEXT("冶炼教程　添柴、炼矿、取锭")},
            {BlacksmithLessonText::Materials(), TEXT("打铁教程　选料开炉")},
            {BlacksmithLessonText::Hammering(), TEXT("打铁教程　锤炼"), AimGuide},
            {BlacksmithLessonText::Finish(), TEXT("打铁教程　领取成品")}
        };
    }
    if (Stage > 0 && Stage < CompleteStep) Passages.RemoveAt(0, Stage);
    auto LessonBody = SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[SAssignNew(Speech, SColdSteelNpcSpeech).Passages(MoveTemp(Passages))]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
        [SAssignNew(FeedbackText, STextBlock).Font(TextFont(14 * .75f)).AutoWrapText(true).ColorAndOpacity(HUDGoldLight)];

    ReturnButton = DialogueButton(TreeStyle.Quiet, Label(TEXT("返回交谈"), 14, TextSecondary), TEXT("Esc"), [this] { ReturnToParentPage(); });
    TrainingRetry = DialogueButton(TreeStyle.Muted, Label(!bCarpenter && Stage==0 ? TEXT("接取任务并领取十字镐") : !bCarpenter && Stage==2 ? TEXT("交付十块铁矿石") : Stage==0 ? TEXT("接取任务并领料") : TEXT("领取教学材料"), 14, TextPrimary, true), FString(),
        [this] { RequestArtisanTraining(); });
    DefaultChoice = Conversation.IsValid()&&Conversation->CanCollectTrainingSupplies()?TrainingRetry:ReturnButton;
    auto Actions = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(ActionGap, ActionGap))
        + SWrapBox::Slot()[TrainingRetry.ToSharedRef()]
        + SWrapBox::Slot()[ReturnButton.ToSharedRef()];

    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
        [SAssignNew(TrainingProgress, STextBlock).Font(TextFont(14 * .75f, true)).ColorAndOpacity(TextPrimary)]
        + SVerticalBox::Slot().FillHeight(1).Padding(0, 0, 0, 6)[LessonBody]
        + SVerticalBox::Slot().AutoHeight()[Footer(Actions)];
}

void UColdSteelNpcDialogue::RefreshArtisanLesson()
{
    if (!TrainingProgress || !TrainingRetry || !Conversation.IsValid()) return;
    const bool bCarpenter = Conversation->IsCarpenter();
    const int32 Stage = bCarpenter ? Conversation->CarpenterTrainingStage() : Conversation->SmithTrainingStage();
    const bool bPending = Conversation->IsPending();
    static const TCHAR* const SmithStatus[] = {
        TEXT("铁匠修炼 · 从采矿到成剑"), TEXT("采矿 · 采集并拾取十块铁矿石"), TEXT("采矿 · 回铁匠处交付十块铁矿石"), TEXT("冶炼 · 在高炉炼矿并领取三块金属锭"),
        TEXT("打铁 · 合金胚 ×1、任选同种金属锭 ×3"), TEXT("打铁 · 在铁砧上锤炼锻钢双手剑"),
        TEXT("打铁 · 领取亲手打造的锻钢双手剑"), TEXT("已完成铁匠修炼")
    };
    static const TCHAR* const CarpenterStatus[] = {
        TEXT("支线任务 · 制作并领取一把学徒长杖"), TEXT("第一步 · 到木工台为学徒长杖备料"), TEXT("第二步 · 上锯加工学徒长杖"),
        TEXT("第三步 · 领取合格的学徒长杖"), TEXT("已完成木工修炼")
    };
    const auto& Status = bCarpenter ? CarpenterStatus : SmithStatus;
    const int32 StageCount = bCarpenter ? UE_ARRAY_COUNT(CarpenterStatus) : UE_ARRAY_COUNT(SmithStatus);
    const TCHAR* Current = (Stage >= 0 && Stage < StageCount) ? Status[Stage] : TEXT("正在同步修炼进度");
    TrainingProgress->SetText(FText::FromString(Stage == 0 && bPending ? TEXT("正在确认修炼进度…") : Current));
    const bool bRetry = Conversation->CanCollectTrainingSupplies() && !bPending;
    const bool bMoveFocus = !bRetry && TrainingRetry->HasAnyUserFocus();
    DefaultChoice=bRetry?TrainingRetry:ReturnButton;
    TrainingRetry->SetVisibility(bRetry ? EVisibility::Visible : EVisibility::Collapsed);
    if (bMoveFocus) FocusPage();
}

TSharedRef<SWidget> UColdSteelNpcDialogue::Magic()
{
    const TArray<FColdSteelSpokenPassage> Teaching = {
        {TEXT("光不替人做选择。愿你使用它时，仍记得那些需要帮助的人。")},
        {TEXT("圣光可以治愈同伴，也能伤到敌人。对付僵尸时，它的力量尤其强。要为自己疗伤，按住 Alt 再使用圣光的快捷键。")},
        {TEXT("等你到了十五级，我就能把圣光教给你。学会后，去技能树里把它放进快捷栏，也可以继续修炼。")}
    };
    auto Caption = SAssignNew(LessonLabel, STextBlock).Font(TextFont(14 * .75f, true)).ColorAndOpacity(TextPrimary);
    LessonButton = DialogueButton(TreeStyle.Muted, Caption, FString(),
        [this] { if (Conversation.IsValid()) Conversation->RequestAction(TEXT("holyLight")); });
    ReturnButton = DialogueButton(TreeStyle.Quiet, Label(TEXT("返回交谈"), 14, TextSecondary), TEXT("Esc"), [this] { ShowPage(0); });

    auto Actions = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(ActionGap, ActionGap))
        + SWrapBox::Slot()[SNew(SBox).WidthOverride(156)[LessonButton.ToSharedRef()]]
        + SWrapBox::Slot()[SNew(SBox).WidthOverride(156)[ReturnButton.ToSharedRef()]];
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1).Padding(0, 0, 0, 6)
        [SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[SAssignNew(Speech, SColdSteelNpcSpeech).Passages(Teaching)]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
            [SAssignNew(LessonReason, STextBlock).Font(TextFont(14 * .75f)).AutoWrapText(true).ColorAndOpacity(TextSecondary)]
            + SVerticalBox::Slot().AutoHeight()
            [SAssignNew(FeedbackText, STextBlock).Font(TextFont(14 * .75f)).AutoWrapText(true).ColorAndOpacity(HUDGoldLight)]]
        + SVerticalBox::Slot().AutoHeight()[Footer(Actions)];
}

void UColdSteelNpcDialogue::FocusPage()
{
    if (auto* PC = GetOwningPlayer()) SetUserFocus(PC);
}

FReply UColdSteelNpcDialogue::NativeOnFocusReceived(const FGeometry& Geometry, const FFocusEvent& Event)
{
    if(Page==WorkshopPage && WorkshopMarket)
        if(auto Target=WorkshopMarket->FocusTarget())return FReply::Handled().SetUserFocus(Target.ToSharedRef(),Event.GetCause());
    if (DefaultChoice && DefaultChoice->IsEnabled() && (Page != MainPage || bHeardNunIntro || MerchantSpeaker(Conversation.Get())))
        return FReply::Handled().SetUserFocus(DefaultChoice.ToSharedRef(), Event.GetCause());
    return Super::NativeOnFocusReceived(Geometry, Event);
}

FReply UColdSteelNpcDialogue::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    const FKey Key = Event.GetKey();
    if (Key == EKeys::Escape || Key == EKeys::Gamepad_FaceButton_Right)
    {
        if (!Event.IsRepeat()) ReturnToParentPage();
        return FReply::Handled();
    }
    const FSpeaker* Speaker = MerchantSpeaker(Conversation.Get());
    const bool bAdvanceKey = Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Left;
    const bool bAcceptKey = Key == EKeys::Enter || Key == EKeys::Gamepad_FaceButton_Bottom;
    // A/Enter can select a focused option during a reading pause. X/Space always
    // advance the speech, regardless of which action currently owns keyboard focus.
    if (Speech && (bAdvanceKey || bAcceptKey) && Event.IsRepeat()) return FReply::Handled();
    if (Speech && Speech->HasMore() && (bAdvanceKey || (bAcceptKey &&
        (Speech->IsRevealing() || (!Speaker && Page == MainPage && !bHeardNunIntro)))))
    {
        Speech->RevealOrAdvance();
        return FReply::Handled();
    }
    const int32 Choice = NumberChoice(Key);
    if (Choice && Speaker && Page == MainPage && Choice <= Speaker->MainChoiceCount())
    {
        if (!Event.IsRepeat()) ChooseMerchantAction(Choice);
        return FReply::Handled();
    }
    if (Choice && Speaker && Page == MerchantTopicsPage && Choice <= MerchantTopicCount)
    {
        if (!Event.IsRepeat()) ChooseMerchantTopic(Choice - 1);
        return FReply::Handled();
    }
    if (Choice == 1 && Speaker && Page == MerchantStoryPage && Speaker->Topics[MerchantTopicIndex].FollowUp)
    {
        if (!Event.IsRepeat()) ShowPage(MerchantFollowUpPage);
        return FReply::Handled();
    }
    if (Choice && !Speaker && Page == MainPage && bHeardNunIntro && Choice <= 2)
    {
        if (!Event.IsRepeat()) ShowPage(Choice == 1 ? VillagePage : HolyLightPage);
        return FReply::Handled();
    }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}

FReply UColdSteelNpcDialogue::NativeOnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event)
{
    if (Event.GetEffectingButton() == EKeys::LeftMouseButton && Speech && Speech->RevealOrAdvance())
        return FReply::Handled();
    return Super::NativeOnMouseButtonDown(Geometry, Event);
}

FReply UColdSteelNpcDialogue::NativeOnMouseButtonDoubleClick(const FGeometry& Geometry, const FPointerEvent& Event)
{
    if (Event.GetEffectingButton() == EKeys::LeftMouseButton && Speech && Speech->RevealOrAdvance())
        return FReply::Handled();
    return Super::NativeOnMouseButtonDoubleClick(Geometry, Event);
}
